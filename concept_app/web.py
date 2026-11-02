"""Same-origin chat API with server-only credentials and signed learner sessions."""

import hashlib
import base64
import hmac
import json
import logging
import re
import secrets
import time
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from concept_app.catalog import IDEAS
from concept_app.config import Settings
from concept_app.probing import ProbingUnavailable, probe
from concept_app.catalog import public_case
from concept_app.verification import verify, validate_source, VerificationUnavailable

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Concept Check", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "public"), name="static")
logger = logging.getLogger(__name__)


@app.get("/")
def home():
    return FileResponse(ROOT / "public" / "index.html")


@app.get("/api/ideas")
def ideas():
    return [{"id": key, "title": value} for key, value in IDEAS.items()]


def configuration():
    try:
        return Settings.load()
    except ValueError:
        raise HTTPException(503, "The learning service is not configured yet.") from None


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


def signed_identity(learner_id, settings):
    value = str(learner_id)
    signature = hmac.new(settings.supabase_service_key.encode(), value.encode(), hashlib.sha256).hexdigest()
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
        "select": "id,case_id,gap_id,learner_response,recited_sentence,passed,created_at",
        "limit": "500",
    })
    if not rows:
        return {"attempts": []}
    cases = database(settings, "GET", "cases", params={"select": "case_id,idea_id,case_question"})
    case_map = {row["case_id"]: row for row in cases}
    gaps = database(settings, "GET", "gaps", params={
        "attempt_id": "in.(" + ",".join(str(row["id"]) for row in rows) + ")",
        "select": "id,attempt_id,follow_up_question",
    }) if rows else []
    gap_map = {row["attempt_id"]: row for row in gaps}
    for row in rows:
        row.update(case_map.get(row["case_id"], {}))
        row["probe"] = gap_map.get(row["id"])
    return {"attempts": rows}


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
    if payload.gap_id is not None:
        gaps = database(settings, "GET", "gaps", params={
            "id": "eq." + str(payload.gap_id), "select": "attempt_id,follow_up_question",
        })
        if not gaps:
            raise HTTPException(404, "The follow-up could not be found.")
        originals = database(settings, "GET", "attempts", params={
            "id": "eq." + str(gaps[0]["attempt_id"]),
            "learner_id": "eq." + str(identity), "select": "case_id",
        })
        if not originals:
            raise HTTPException(404, "The follow-up could not be found.")
        cases = database(settings, "GET", "cases", params={
            "case_id": "eq." + str(originals[0]["case_id"]),
            "idea_id": "eq." + payload.idea_id, "select": "case_id,case_question",
        })
        if not cases:
            raise HTTPException(422, "This follow-up belongs to a different concept.")
        saved = database(settings, "POST", "attempts", data={
            "learner_id": identity, "case_id": cases[0]["case_id"],
            "gap_id": payload.gap_id, "learner_response": explanation, "passed": None,
        })
        return {"attempt_id": saved[0]["id"], "stage": "retry",
                "message": "Your second try is saved as practice. Now apply your reasoning to a different case.",
                "gap_id": payload.gap_id, "assessed": False}
    cases = database(settings, "GET", "cases", params={
        "idea_id": "eq." + payload.idea_id, "select": "case_id,case_question",
        "order": "case_id.asc", "limit": "1",
    })
    if not cases:
        raise HTTPException(409, "There is no learning case for this concept yet.")
    try:
        result = probe(settings, payload.idea_id, explanation)
    except ProbingUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    saved = database(settings, "POST", "attempts", data={
        "learner_id": identity, "case_id": cases[0]["case_id"],
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
            "select": "id,case_id", "limit": "1",
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
    return hmac.new(settings.supabase_service_key.encode(),
                    ("assessment.v1." + encoded).encode(), hashlib.sha256).hexdigest()


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


@app.post("/api/assessment/case")
def assessment_case(payload: CaseRequest, request: Request, response: Response):
    check_origin(request)
    settings = configuration()
    identity = require_learner(request, settings)
    response.headers["Cache-Control"] = "no-store"
    cases = database(settings, "GET", "cases", params={
        "idea_id": "eq." + payload.idea_id, "select": SOURCE_FIELDS, "order": "case_id.asc",
    })
    if not cases:
        raise HTTPException(404, "No authoritative cases are available for this idea.")
    original_case = None
    if payload.gap_id is not None:
        original = owned_gap(settings, identity, payload.gap_id)
        if original["case_id"] not in {case["case_id"] for case in cases}:
            raise HTTPException(422, "The gap belongs to a different concept.")
        original_case = original["case_id"]
        retries = database(settings, "GET", "attempts", params={
            "gap_id": "eq." + str(payload.gap_id), "learner_id": "eq." + str(identity),
            "id": "neq." + str(original["id"]), "passed": "is.null", "select": "id", "limit": "1",
        })
        if not retries:
            raise HTTPException(409, "Save your second try before requesting the after-practice case.")
    seen = database(settings, "GET", "attempts", params={
        "learner_id": "eq." + str(identity), "passed": "not.is.null", "select": "case_id",
    })
    seen_ids = {row["case_id"] for row in seen}
    candidates = [case for case in cases if case["case_id"] not in seen_ids and case["case_id"] != original_case]
    if not candidates:
        raise HTTPException(409, "You have no unseen case left for this concept. Previously answered cases will not be reused as fresh proof.")
    case = candidates[0]
    return {**public_case(case), "challenge": issue_challenge(settings, identity, case, payload.gap_id),
            "phase": "after" if payload.gap_id is not None else "before"}


class AssessmentRequest(BaseModel):
    challenge: str = Field(min_length=1, max_length=8192)
    answer: str = Field(min_length=1, max_length=6000)


@app.post("/api/assessment/answer")
def assessment_answer(payload: AssessmentRequest, request: Request, response: Response):
    check_origin(request)
    settings = configuration()
    identity = require_learner(request, settings)
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
    if gap_id is not None:
        original = owned_gap(settings, identity, gap_id)
        originals = database(settings, "GET", "cases", params={
            "case_id": "eq." + str(original["case_id"]), "select": "idea_id", "limit": "1",
        })
        if original["case_id"] == case["case_id"] or not originals or originals[0]["idea_id"] != case["idea_id"]:
            raise HTTPException(422, "The case must be a different case for the gap's concept.")
    seen = database(settings, "GET", "attempts", params={
        "learner_id": "eq." + str(identity), "case_id": "eq." + str(case["case_id"]),
        "passed": "not.is.null", "select": "id", "limit": "1",
    })
    if seen:
        raise HTTPException(409, "This case has already been answered. Request another unseen case.")
    # This guards sequential replay. Cross-instance atomic reservation needs DB support.
    result = verify(case, payload.answer)
    saved = database(settings, "POST", "attempts", data={
        "learner_id": identity, "case_id": case["case_id"], "gap_id": gap_id,
        "learner_response": payload.answer, "passed": result["status"] == "PASS",
    })
    return {**result, "attempt_id": saved[0]["id"], "gap_id": gap_id,
            "message": "PASS — the documented case checks were met." if result["status"] == "PASS" else
            "WRONG — the documented checks were not all met, or the answer contained conflicting advice."}
