"""Real learner answers (no names), labelled by the builder. Trainer feedback: measure
the unfair WRONG rate on real learner answers and turn each failed sample into a test."""

import csv
import unittest
from pathlib import Path

from concept_app.verification import verify
from concept_app.verification.engine import GOLDEN_PAIRS

ROWS = list(csv.DictReader(open(Path(__file__).resolve().parent.parent / "evaluation" / "real_answers.csv",
                                encoding="utf-8")))


class RealLearnerAnswers(unittest.TestCase):
    def test_each_real_answer_gets_the_human_label(self):
        self.assertEqual(len(ROWS), 11)
        for row in ROWS:
            with self.subTest(source=row["source"]):
                result = verify(GOLDEN_PAIRS[int(row["case_id"])], row["answer"])
                expected = "PASS" if row["human_label"] == "correct" else "NOT_YET"
                self.assertEqual(result["status"], expected, result["checks"])
