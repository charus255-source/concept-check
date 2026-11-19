"""Same-origin chat API with server-only credentials and signed learner sessions."""

import hashlib
import base64
import hmac
import json
import logging
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from concept_app.catalog import IDEAS, LESSONS, WORDS
from concept_app.config import Settings
from concept_app.probing import ProbingUnavailable, probe
from concept_app.catalog import public_case
from concept_app.quoting import find_quotes
from concept_app.verification import verify, validate_source, VerificationUnavailable

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Concept Check", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "public"), name="static")
logger = logging.getLogger(__name__)


@app.get("/")
def home():
    # Always revalidate the page, so a deploy never mixes old HTML with new styles.
    return FileResponse(ROOT / "public" / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/how")
def how_i_built_this():
    return FileResponse(ROOT / "public" / "how.html", headers={"Cache-Control": "no-cache"})


@app.get("/api/ideas")
def ideas():
    return [{"id": key, "title": value, "lesson": LESSONS[key],
             "words": [{"term": term, "meaning": meaning} for term, meaning in WORDS[key]]}
            for key, value in IDEAS.items()]


def configuration():
    try:
        return Settings.load()
    except ValueError:
        raise HTTPException(503, "The learning service is not configured yet.") from None


class DuplicateRow(HTTPException):
    """A unique constraint rejected the write (for example, a second graded answer)."""

    def __init__(self):
        super().__init__(409, "This case has already been answered. Request another unseen case.")


class DatabaseUnavailable(HTTPException):
    """A provider failure with safe diagnostics, never raw provider text."""

    def __init__(self, category):
        self.category = category
        detail = (
            "The server cannot connect to the learning database. "
            "Start the local server with network access and try again."
            if category == "network_permission" else
            "The learning database is unavailable. Please try again."
        )
        super().__init__(503, detail)


def network_error_number(error):
    """Inspect wrapped socket failures without logging exception strings or URLs."""
    pending, seen = [error], set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        number = getattr(current, "winerror", None) or getattr(current, "errno", None)
        if number in (10013, 13):
            return number
        pending.extend(item for item in (
            getattr(current, "__cause__", None), getattr(current, "__context__", None),
            getattr(current, "reason", None), *getattr(current, "args", ()),
        ) if isinstance(item, BaseException))
    return None


def database(settings, method, table, *, params=None, data=None):
    response = None
    try:
        response = requests.request(
            method, settings.supabase_url.rstrip("/") + "/rest/v1/" + table,
            headers={"apikey": settings.supabase_service_key,
                     "Authorization": "Bearer " + settings.supabase_service_key,
                     "Prefer": "return=representation"},
            params=params, json=data, timeout=(5, 15),
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        status = response.status_code if response is not None else None
        code = None
        if response is not None:
            try:
                candidate = response.json().get("code")
                if isinstance(candidate, str) and re.fullmatch(r"[A-Z0-9]{2,12}", candidate):
                    code = candidate
            except (ValueError, AttributeError):
                pass
        if status == 409 and code == "23505":
            raise DuplicateRow() from None
        number = network_error_number(exc)
        category = (
            "network_permission" if number else
            "timeout" if isinstance(exc, requests.Timeout) else
            "connection" if isinstance(exc, requests.ConnectionError) else
            "http" if isinstance(exc, requests.HTTPError) else "invalid_response"
        )
        logger.warning(
            "Database operation failed: method=%s table=%s category=%s status=%s code=%s os_error=%s",
            method, table, category, status, code, number,
        )
        raise DatabaseUnavailable(category) from None


# Per-instance limits. Serverless instances do not share memory, so this bounds
# bursts on each instance; a shared store (for example Upstash) is needed for a global cap.
LIMITS = {"session": (10, 3600), "check": (30, 3600), "case": (60, 3600), "answer": (40, 3600)}
_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def client_address(request):
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def rate_limit(request, bucket):
    limit, window = LIMITS[bucket]
    key = (bucket, client_address(request))
    now = time.monotonic()
    with _hits_lock:
        hits = _hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(429, "Too many requests from this connection. Please wait a while and try again.")
        hits.append(now)


def signed_identity(learner_id, settings):
    value = str(learner_id)
    signature = hmac.new(settings.session_secret.encode(), ("session.v2." + value).encode(),
                         hashlib.sha256).hexdigest()
    return value + "." + signature


def learner(request, settings):
    token = request.cookies.get("concept_session", "")
    if not re.fullmatch(r"[0-9]{1,19}\.[0-9a-f]{64}", token):
        return None
    value = token.partition(".")[0]
    if value.isdigit() and hmac.compare_digest(token, signed_identity(value, settings)):
        return int(value)
    return None


def require_learner(request, settings):
    identity = learner(request, settings)
    if identity is None:
        raise HTTPException(401, "Start a learning session first.")
    return identity


def check_origin(request):
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Please submit from the Concept Check application.")


@app.post("/api/session")
def start_session(request: Request, response: Response):
    check_origin(request)
    settings = configuration()
    identity = learner(request, settings)
    if identity is None:
        rate_limit(request, "session")
        identity = database(settings, "POST", "learners", data={
            "learner_name": "Learner " + secrets.token_hex(8),
        })[0]["id"]
    response.set_cookie("concept_session", signed_identity(identity, settings),
                        httponly=True, secure=request.url.scheme == "https",
                        samesite="strict", max_age=60 * 60 * 24 * 30)
    response.headers["Cache-Control"] = "no-store"
    return {"ready": True}


@app.get("/api/history")
def history(request: Request, response: Response):
    settings = configuration()
    identity = require_learner(request, settings)
    response.headers["Cache-Control"] = "no-store"
    rows = database(settings, "GET", "attempts", params={
        "learner_id": "eq." + str(identity), "order": "created_at.asc,id.asc",
        "select": "id,case_id,idea_id,event_type,gap_id,learner_response,recited_sentence,passed,rule_version,created_at",
        "limit": "500",
    })
    if not rows:
        return {"attempts": []}
    cases = database(settings, "GET", "cases", params={"select": SOURCE_FIELDS})
    case_map = {row["case_id"]: row for row in cases}
    gaps = database(settings, "GET", "gaps", params={
        "attempt_id": "in.(" + ",".join(str(row["id"]) for row in rows) + ")",
        "select": "id,attempt_id,follow_up_question",
    }) if rows else []
    gap_map = {row["attempt_id"]: row for row in gaps}
    for row in rows:
        case = case_map.get(row["case_id"], {})
        row["idea_id"] = row.get("idea_id") or case.get("idea_id")
        # Practice events are not answers to a case, so they show no case question.
        row["case_question"] = case.get("case_question") if row.get("event_type") == "graded" else None
        row["probe"] = gap_map.get(row["id"])
        row["result"] = saved_result(row, case) if row.get("event_type") == "graded" else None
        row.pop("rule_version", None)
    return {"attempts": rows}


def saved_result(row, case):
    """Rebuild the detail of a saved grade, so history shows what was right and missing.

    The saved pass/fail always wins. Answers graded before rule versions were stored
    (no rule_version) show no detail."""
    if not row.get("rule_version") or not case:
        return None
    try:
        result = verify(case, row["learner_response"])
    except (VerificationUnavailable, ValueError):
        return None
    if row["passed"]:
        for check in result["checks"]:
            check["met"] = True
        result["met"], result["contradictions"] = result["total"], []
    regraded = not row["passed"] and result["status"] == "PASS"
    result["status"] = "PASS" if row["passed"] else "NOT_YET"
    result["message"] = result_message(result)
    if regraded:
        result["message"] = ("Not yet when you answered. The checks have since been made fairer, "
                             "and this answer now covers every idea.")
    result["model_answer"] = case["case_answer"]
    return result


class ExplanationRequest(BaseModel):
    explanation: str = Field(min_length=10, max_length=6000)
    idea_id: str = "API_AUTH"
    gap_id: int | None = Field(default=None, gt=0)


@app.post("/api/check")
def check_explanation(payload: ExplanationRequest, request: Request, response: Response):
    check_origin(request)
    settings = configuration()
    identity = require_learner(request, settings)
    response.headers["Cache-Control"] = "no-store"
    explanation = payload.explanation.strip()
    if len(explanation) < 10:
        raise HTTPException(422, "Write at least 10 characters in your own words.")
    if payload.idea_id not in IDEAS:
        raise HTTPException(422, "Choose a Module 2 concept.")
    rate_limit(request, "check")
    if payload.gap_id is not None:
        original = owned_gap(settings, identity, payload.gap_id)
        if original["idea_id"] != payload.idea_id:
            raise HTTPException(422, "This follow-up belongs to a different concept.")
        # A second try is practice: it answers the follow-up, not a case.
        saved = database(settings, "POST", "attempts", data={
            "learner_id": identity, "idea_id": payload.idea_id, "event_type": "retry",
            "gap_id": payload.gap_id, "learner_response": explanation, "passed": None,
        })
        return {"attempt_id": saved[0]["id"], "stage": "retry",
                "message": "Your second try is saved. Practice is not graded: a new case will show whether it clicked.",
                "gap_id": payload.gap_id, "assessed": False}
    try:
        result = probe(settings, payload.idea_id, explanation)
    except ProbingUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    # An explanation is its own event type. It is not tied to a case the learner never saw.
    saved = database(settings, "POST", "attempts", data={
        "learner_id": identity, "idea_id": payload.idea_id, "event_type": "explanation",
        "learner_response": explanation, "recited_sentence": result["recited_sentence"],
        "passed": None,
    })
    gaps = database(settings, "POST", "gaps", data={
        "attempt_id": saved[0]["id"], "follow_up_question": result["follow_up_question"],
    })
    return {**result, "attempt_id": saved[0]["id"], "gap_id": gaps[0]["id"], "stage": "probe"}


SOURCE_FIELDS = "case_id,idea_id,case_question,case_answer"


def owned_gap(settings, identity, gap_id):
    gaps = database(settings, "GET", "gaps", params={
        "id": "eq." + str(gap_id), "select": "attempt_id", "limit": "1",
    })
    if gaps:
        originals = database(settings, "GET", "attempts", params={
            "id": "eq." + str(gaps[0]["attempt_id"]), "learner_id": "eq." + str(identity),
            "select": "id,idea_id", "limit": "1",
        })
        if originals:
            return originals[0]
    raise HTTPException(404, "The learning gap could not be found in your session.")


def reviewed_source(case):
    try:
        return validate_source(case)
    except VerificationUnavailable as exc:
        raise HTTPException(503, str(exc)) from None


def challenge_signature(encoded, settings):
    return hmac.new(settings.session_secret.encode(),
                    ("assessment.v2." + encoded).encode(), hashlib.sha256).hexdigest()


def issue_challenge(settings, identity, case, gap_id):
    payload = {"learner_id": identity, "case_id": case["case_id"],
               "gap_id": gap_id, "source": reviewed_source(case),
               "expires": int(time.time()) + 1800}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True).encode()).decode()
    return encoded + "." + challenge_signature(encoded, settings)


def read_challenge(token, settings, identity):
    try:
        encoded, signature = token.split(".")
        if not hmac.compare_digest(signature.encode("ascii"), challenge_signature(encoded, settings).encode()):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded))
        if (not isinstance(payload, dict) or type(payload.get("expires")) is not int
                or payload["expires"] < int(time.time())
                or type(payload.get("learner_id")) is not int or payload["learner_id"] != identity
                or type(payload.get("case_id")) is not int
                or (payload.get("gap_id") is not None and type(payload["gap_id"]) is not int)):
            raise ValueError
        return payload
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise HTTPException(409, "This practice case expired or is invalid. Request a fresh case.") from None


class CaseRequest(BaseModel):
    idea_id: str
    gap_id: int | None = Field(default=None, gt=0)


def next_step(settings, identity, idea_id):
    """When a concept runs out of fresh cases, name the concepts that still have one."""
    cases = database(settings, "GET", "cases", params={"select": "case_id,idea_id"})
    seen = graded_case_ids(settings, identity)
    open_ideas = [IDEAS[idea] for idea in IDEAS if idea != idea_id and any(
        case["idea_id"] == idea and case["case_id"] not in seen for case in cases)]
    if not open_ideas:
        return "You have answered every case. Your results are saved in your history."
    return ("You have answered every case for this concept, and answered cases are not reused. "
            "Next, try: " + "; ".join(open_ideas[:3]) + ".")


def graded_case_ids(settings, identity):
    seen = database(settings, "GET", "attempts", params={
        "learner_id": "eq." + str(identity), "event_type": "eq.graded", "select": "case_id",
    })
    return {row["case_id"] for row in seen}


@app.post("/api/assessment/case")
def assessment_case(payload: CaseRequest, request: Request, response: Response):
    check_origin(request)
    settings = configuration()
    identity = require_learner(request, settings)
    rate_limit(request, "case")
    response.headers["Cache-Control"] = "no-store"
    if payload.idea_id not in IDEAS:
        raise HTTPException(422, "Choose a Module 2 concept.")
    cases = database(settings, "GET", "cases", params={
        "idea_id": "eq." + payload.idea_id, "select": SOURCE_FIELDS, "order": "case_id.asc",
    })
    if not cases:
        raise HTTPException(404, "No authoritative cases are available for this idea.")
    if payload.gap_id is not None:
        original = owned_gap(settings, identity, payload.gap_id)
        if original["idea_id"] != payload.idea_id:
            raise HTTPException(422, "The gap belongs to a different concept.")
        retries = database(settings, "GET", "attempts", params={
            "gap_id": "eq." + str(payload.gap_id), "learner_id": "eq." + str(identity),
            "event_type": "eq.retry", "select": "id", "limit": "1",
        })
        if not retries:
            raise HTTPException(409, "Save your second try before requesting the after-practice case.")
    seen_ids = graded_case_ids(settings, identity)
    candidates = [case for case in cases if case["case_id"] not in seen_ids]
    if not candidates:
        raise HTTPException(409, next_step(settings, identity, payload.idea_id))
    case = candidates[0]
    return {**public_case(case), "challenge": issue_challenge(settings, identity, case, payload.gap_id),
            "phase": "after" if payload.gap_id is not None else "before"}


class AssessmentRequest(BaseModel):
    challenge: str = Field(min_length=1, max_length=8192)
    answer: str = Field(min_length=1, max_length=6000)


QUESTION_START = re.compile(
    r"\s*(?:do|does|did|is|are|was|what|why|how|can|could|should|would|will|which|who|where|when|"
    r"u mean|you mean|meaning|sorry|i don'?t (?:understand|get|know)|i do not (?:understand|get|know)|not sure what|"
    r"please|pls|plz|tell me|help|explain (?:the|your|it|this|that|me)|what'?s)\b", re.I)


def is_question(answer):
    """A clarifying question typed into the case box, not an attempt at the case."""
    text = answer.strip()
    return len(text.split()) <= 40 and (text.endswith("?") or bool(QUESTION_START.match(text)))


def result_message(result):
    if result["status"] == "PASS":
        return f"Pass. All {result['total']} ideas are covered."
    if result["contradictions"]:
        return (f"Not yet. You covered {result['met']} of {result['total']} ideas, "
                "but part of your answer gives advice that would break this case.")
    if result["met"]:
        return f"Almost there. You covered {result['met']} of {result['total']} ideas."
    return f"Not yet. None of the {result['total']} ideas showed up in this answer yet."


@app.post("/api/assessment/answer")
def assessment_answer(payload: AssessmentRequest, request: Request, response: Response):
    check_origin(request)
    settings = configuration()
    identity = require_learner(request, settings)
    rate_limit(request, "answer")
    response.headers["Cache-Control"] = "no-store"
    if not payload.answer.strip():
        raise HTTPException(422, "Write your answer to the case.")
    challenge = read_challenge(payload.challenge, settings, identity)
    cases = database(settings, "GET", "cases", params={
        "case_id": "eq." + str(challenge["case_id"]), "select": SOURCE_FIELDS, "limit": "1",
    })
    if not cases:
        raise HTTPException(503, "The case source is unavailable. No grade has been assigned.")
    case = cases[0]
    if reviewed_source(case) != challenge["source"]:
        raise HTTPException(503, "The case source changed. No grade has been assigned.")
    gap_id = challenge["gap_id"]
    if gap_id is not None and owned_gap(settings, identity, gap_id)["idea_id"] != case["idea_id"]:
        raise HTTPException(422, "The case must belong to the gap's concept.")
    if case["case_id"] in graded_case_ids(settings, identity):
        raise HTTPException(409, "This case has already been answered. Request another unseen case.")
    result = verify(case, payload.answer, quote_finder=lambda ideas: find_quotes(
        settings, case["case_question"], ideas, payload.answer))
    if result["met"] == 0 and not result["contradictions"] and is_question(payload.answer):
        # Not graded and not saved: the case stays open. Restate it, never hint at the answer.
        return {"status": "QUESTION", "case_question": case["case_question"],
                "message": "That sounds like a question, so it was not graded and nothing was saved. "
                           "The case is asking:\n\n" + case["case_question"] +
                           "\n\nAnswer it in your own words: what should happen, and why?"}
    # The unique index on (learner_id, case_id) for graded rows blocks simultaneous duplicates.
    saved = database(settings, "POST", "attempts", data={
        "learner_id": identity, "case_id": case["case_id"], "idea_id": case["idea_id"],
        "event_type": "graded", "gap_id": gap_id, "learner_response": payload.answer,
        "passed": result["status"] == "PASS", "rule_version": result["rule_version"],
        "source_fingerprint": result["source_fingerprint"],
    })
    # The case is graded and never reused, so its reviewed answer can now be shown.
    return {**result, "attempt_id": saved[0]["id"], "gap_id": gap_id,
            "message": result_message(result), "model_answer": case["case_answer"]}
