"""The model may only point at words. Python must refuse anything else."""

import csv
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

import requests

from concept_app.quoting import find_quotes
from concept_app.verification import verify
from concept_app.verification.engine import GOLDEN_PAIRS
from concept_app.verification.quotes import ANCHORS, confirm_quote
from concept_app.verification.rules import RULES

ROOT = Path(__file__).resolve().parent.parent


def greedy(answer):
    """The worst model: it claims the whole answer proves every idea."""
    return lambda ideas: {idea["check_id"]: answer for idea in ideas}


def labelled():
    for name in ("sample_answers.csv", "heldout_answers.csv", "real_answers.csv"):
        yield from csv.DictReader(open(ROOT / "evaluation" / name, encoding="utf-8"))


class QuoteConfirmation(unittest.TestCase):
    def test_every_rule_fact_has_anchors(self):
        for rule in RULES.values():
            for check in rule.required:
                self.assertIn(check.fact, ANCHORS)

    def test_a_soft_model_cannot_pass_an_incorrect_answer(self):
        for row in labelled():
            with self.subTest(answer=row["answer"]):
                result = verify(GOLDEN_PAIRS[int(row["case_id"])], row["answer"], greedy(row["answer"]))
                expected = "PASS" if row["human_label"] == "correct" else "NOT_YET"
                self.assertEqual(result["status"], expected, result["checks"])

    def test_keyword_lists_cannot_pass_even_with_a_soft_model(self):
        for answer in ("backend browser code key server storage learner_id attempts learners.id gap row success database 729",
                       "order, request, get.", "729.", "201.", "foreign key, learners, reject, exist."):
            for case_id, case in GOLDEN_PAIRS.items():
                with self.subTest(case=case_id, answer=answer):
                    self.assertEqual(verify(case, answer, greedy(answer))["status"], "NOT_YET")

    def test_quote_must_be_copied_exactly(self):
        answer = "The server keeps the key in its environment."
        self.assertIsNotNone(confirm_quote(answer, "server_key", "The server keeps the key"))
        self.assertIsNone(confirm_quote(answer, "server_key", "The server stores the key"))

    def test_negated_quote_is_refused(self):
        answer = "The server should not keep the key."
        self.assertIsNone(confirm_quote(answer, "server_key", answer))

    def test_quote_cannot_override_bad_advice(self):
        answer = ("The frontend calls the backend, and the backend makes the call to the provider. "
                  "Keep the key on the server. Also store the private key in the browser.")
        result = verify(GOLDEN_PAIRS[13], answer, greedy(answer))
        self.assertEqual(result["status"], "NOT_YET")
        self.assertTrue(result["contradictions"])

    def test_quote_evidence_points_at_learner_text(self):
        answer = "Hmm. Users can mess with the JavaScript in their browser, so the discounts could be changed."
        quote = "Users can mess with the JavaScript in their browser"
        evidence = confirm_quote(answer, "browser_exposure", quote)
        self.assertEqual(answer[evidence["start"]:evidence["end"]], quote)


class FindQuotes(unittest.TestCase):
    settings = SimpleNamespace(groq_api_key="test")
    ideas = [{"check_id": "c04.01", "idea": "x"}]

    def transport(self, content=None, error=None):
        def post(*args, **kwargs):
            if error:
                raise error
            body = {"choices": [{"message": {"content": content}}]}
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)
        return SimpleNamespace(post=post)

    def test_returns_only_requested_string_quotes(self):
        content = json.dumps({"quotes": {"c04.01": "it was lost", "c99.01": "extra", "c04.02": 3}})
        self.assertEqual(find_quotes(self.settings, "q", self.ideas, "a", self.transport(content)),
                         {"c04.01": "it was lost"})

    def test_provider_failures_fall_back_to_rules(self):
        for transport in (self.transport(error=requests.Timeout()), self.transport("not json"),
                          self.transport(json.dumps({"quotes": []}))):
            self.assertEqual(find_quotes(self.settings, "q", self.ideas, "a", transport), {})
