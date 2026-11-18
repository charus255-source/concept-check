"""Measure how often the grader is unfair, using answers a human has labelled.

Usage:  python scripts/measure_unfair_rate.py [labelled.csv]

The CSV needs the columns case_id, human_label (correct/incorrect) and answer.
* Unfair NOT YET rate: answers a human marked correct that the grader did not pass.
* Unsafe PASS rate:    answers a human marked incorrect that the grader passed.
Run it on real learner answers (names removed) before and after changing the rules.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from concept_app.verification import verify  # noqa: E402
from concept_app.verification.engine import GOLDEN_PAIRS  # noqa: E402


def main(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    correct = [row for row in rows if row["human_label"] == "correct"]
    incorrect = [row for row in rows if row["human_label"] == "incorrect"]
    unfair = [row for row in correct
              if verify(GOLDEN_PAIRS[int(row["case_id"])], row["answer"])["status"] != "PASS"]
    unsafe = [row for row in incorrect
              if verify(GOLDEN_PAIRS[int(row["case_id"])], row["answer"])["status"] == "PASS"]
    print(f"Unfair NOT YET: {len(unfair)}/{len(correct)} correct answers were not passed")
    for row in unfair:
        print(f"  case {row['case_id']}: {row['answer']}")
    print(f"Unsafe PASS:    {len(unsafe)}/{len(incorrect)} incorrect answers were passed")
    for row in unsafe:
        print(f"  case {row['case_id']}: {row['answer']}")
    return 1 if unsafe else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "evaluation" / "sample_answers.csv"))
