"""Every labelled sample answer is a regression test (trainer feedback, priority 2).

evaluation/sample_answers.csv holds the trainer's failing answers plus authored
answers for the phrase families named in the feedback. evaluation/heldout_answers.csv
was written after the rules and is only measured, never tuned against.
"""

import csv
import unittest
from pathlib import Path

from concept_app.verification import verify
from concept_app.verification.engine import GOLDEN_PAIRS

ROOT = Path(__file__).resolve().parent.parent


def rows(name):
    return list(csv.DictReader(open(ROOT / "evaluation" / name, encoding="utf-8")))


class PhraseFamilyRegressions(unittest.TestCase):
    def test_every_labelled_sample_gets_the_human_label_from_rules_alone(self):
        for row in rows("sample_answers.csv"):
            with self.subTest(case=row["case_id"], answer=row["answer"]):
                result = verify(GOLDEN_PAIRS[int(row["case_id"])], row["answer"])
                expected = "PASS" if row["human_label"] == "correct" else "NOT_YET"
                self.assertEqual(result["status"], expected, result["checks"])

    def test_no_incorrect_heldout_answer_passes(self):
        for row in rows("heldout_answers.csv"):
            if row["human_label"] == "incorrect":
                with self.subTest(answer=row["answer"]):
                    result = verify(GOLDEN_PAIRS[int(row["case_id"])], row["answer"])
                    self.assertEqual(result["status"], "NOT_YET")

    def test_trainer_examples(self):
        self.assertEqual(verify(GOLDEN_PAIRS[4], "Progress vanishes because it only lived in a variable. "
                                "Persist it in a database and read it back later.")["status"], "PASS")
        self.assertEqual(verify(GOLDEN_PAIRS[15], "Create one row per attempt with a foreign key "
                                "to the learner.")["status"], "PASS")

    def test_graded_result_counts_ideas(self):
        result = verify(GOLDEN_PAIRS[4], "Save progress in a database.")
        self.assertEqual((result["status"], result["met"], result["total"]), ("NOT_YET", 1, 3))
