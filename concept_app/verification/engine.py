"""Pure deterministic verifier. Standard library only; no provider clients."""

import hashlib
import json
from pathlib import Path

from .normalize import normalize
from .patterns import match_facts
from .rules import RULES, VERSION

FIELDS = ("case_id", "idea_id", "case_question", "case_answer")
GOLDEN_PAIRS = {row["case_id"]: row for row in json.loads(
    Path(__file__).with_name("golden_pairs.json").read_text(encoding="utf-8"))}


class VerificationUnavailable(ValueError):
    """A source/rule error, never a learner's WRONG result."""


def fingerprint(case):
    payload = {key: case[key] for key in FIELDS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_source(case):
    case_id = case.get("case_id")
    if type(case_id) is not int or case_id not in RULES or case_id not in GOLDEN_PAIRS:
        raise VerificationUnavailable("No reviewed verification rule exists for this case.")
    try:
        actual = fingerprint(case)
    except (KeyError, TypeError, ValueError):
        raise VerificationUnavailable("The case source is incomplete. Verification is unavailable.") from None
    if actual != fingerprint(GOLDEN_PAIRS[case_id]):
        raise VerificationUnavailable("The case has changed since its verification rules were reviewed.")
    return actual


def verify(case, answer):
    source_fingerprint = validate_source(case)
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 6000:
        raise ValueError("Provide a nonblank answer of at most 6,000 characters.")
    case_id = case["case_id"]
    rule = RULES[case_id]
    facts = match_facts(normalize(answer))
    checks = [{"check_id": f"c{case_id:02d}.{index:02d}",
               "met": bool(facts[check.fact]), "feedback": check.feedback,
               "evidence": list(facts[check.fact])}
              for index, check in enumerate(rule.required, 1)]
    contradictions = [{"check_id": name, "evidence": list(facts[name])}
                      for name in rule.contradictions if facts[name]]
    passed = all(check["met"] for check in checks) and not contradictions
    return {"case_id": case_id, "rule_version": VERSION, "source_fingerprint": source_fingerprint,
            "status": "PASS" if passed else "WRONG", "checks": checks,
            "contradictions": contradictions}
