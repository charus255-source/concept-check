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


class ContradictionScope(unittest.TestCase):
    def test_survive_in_a_later_clause_is_not_bad_advice(self):
        for answer in ("Yes, memory is wiped on restart, so write the answer to the database so it survives the restart.",
                       "A temporary variable is wiped on restart, so save the answer in a database so it survives a restart."):
            with self.subTest(answer=answer):
                self.assertEqual(verify(GOLDEN_PAIRS[17], answer)["contradictions"], [])

    def test_variable_surviving_is_still_bad_advice(self):
        for answer in ("A temporary variable survives a restart.", "Keep the progress in a global variable so it survives a refresh."):
            with self.subTest(answer=answer):
                self.assertNotEqual(verify(GOLDEN_PAIRS[4], answer)["contradictions"], [])


class NegatedBadAdvice(unittest.TestCase):
    def test_rejecting_the_browser_is_not_bad_advice(self):
        answers = {
            13: ["Store the key on the server, not in the browser. The browser calls the backend and the backend calls the API.",
                 "Keep the key on the server and never in the frontend. The frontend calls our backend, which calls the provider API."],
            3: ["Visitors can inspect the JavaScript and copy the key. Put the key on the server instead of in the browser; "
                "the browser calls the backend, which calls the API."],
            11: ["The server recalculates the price; it should not trust the browser-supplied price."],
        }
        for case_id, texts in answers.items():
            for answer in texts:
                with self.subTest(answer=answer):
                    self.assertEqual(verify(GOLDEN_PAIRS[case_id], answer)["status"], "PASS")

    def test_real_bad_advice_is_still_caught(self):
        for answer in ("Keep the key in the browser, not on the server. The browser calls the backend and the backend calls the API.",
                       "Store the private key in the browser."):
            with self.subTest(answer=answer):
                self.assertNotEqual(verify(GOLDEN_PAIRS[13], answer)["contradictions"], [])
