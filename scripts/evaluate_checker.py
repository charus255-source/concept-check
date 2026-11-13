"""Measure the checker: how many correct answers get NOT_YET, how many wrong ones PASS.

    python scripts/evaluate_checker.py               # real Groq model (needs .env)
    python scripts/evaluate_checker.py --rules-only  # phrase rules alone, no model
    python scripts/evaluate_checker.py --worst-case  # no network: a model that quotes
                                                     # every sentence it possibly can

--worst-case shows what Python's own vetoes stop when the model is as lenient as
possible. The real model should land well below that false-PASS number; if it does
not, tighten QUOTE_PROMPT or ANCHORS in concept_app/quoting.py.
"""

import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from concept_app import quoting  # noqa: E402
from concept_app.verification import verify  # noqa: E402
from concept_app.verification.engine import GOLDEN_PAIRS  # noqa: E402
from heldout_answers import HELDOUT_CORRECT, HELDOUT_WRONG  # noqa: E402
from verification_fixtures import NATURAL, NATURAL_WRONG  # noqa: E402


def lenient_quotes(settings, case, answer, missing, transport=None):
    """A deliberately careless model: offers every sentence for every check."""
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", answer) if part.strip()]
    facts = {f"c{case['case_id']:02d}.{index:02d}": check.fact
             for index, check in enumerate(quoting.RULES[case["case_id"]].required, 1)}
    chosen = {}
    for check in missing:
        for sentence in sentences + [answer.strip()]:
            if quoting.confirm_quote(answer, sentence, facts[check["check_id"]]):
                chosen[check["check_id"]] = sentence
                break
    return chosen


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--model"
    settings = None
    if mode == "--worst-case":
        quoting.request_quotes = lenient_quotes
        settings = SimpleNamespace(groq_api_key="")
    elif mode == "--model":
        from concept_app.config import Settings
        settings = Settings.load()

    def grade(case_id, answer):
        if mode == "--rules-only":
            return verify(GOLDEN_PAIRS[case_id], answer)
        return quoting.assisted_verify(settings, GOLDEN_PAIRS[case_id], answer)

    for label, pool, should_pass in (("Correct answers, tuned set", NATURAL, True),
                                     ("Correct answers, held-out set", HELDOUT_CORRECT, True),
                                     ("Wrong answers, tuned set", NATURAL_WRONG, False),
                                     ("Wrong answers, held-out set", HELDOUT_WRONG, False)):
        total = passed = unavailable = 0
        surprises = []
        for case_id, answers in pool.items():
            for answer in answers:
                result = grade(case_id, answer)
                total += 1
                passed += result["status"] == "PASS"
                unavailable += result.get("assist") == "unavailable"
                if (result["status"] == "PASS") != should_pass:
                    surprises.append(f"   case {case_id} {result['covered']}/{result['total']}: {answer}")
        print(f"{label}: {passed} of {total} PASS" + (f" (model unavailable for {unavailable})" if unavailable else ""))
        print(("  unfair NOT_YET:" if should_pass else "  false PASS:"), len(surprises))
        print("\n".join(surprises))


if __name__ == "__main__":
    main()
