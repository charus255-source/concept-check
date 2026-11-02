"""Source-answer, supported paraphrase, adversarial, and determinism regressions."""

import copy
import ast
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException

from concept_app.verification import VerificationUnavailable, verify, validate_source
from concept_app.verification.engine import GOLDEN_PAIRS
from concept_app.verification.rules import RULES
from verification_fixtures import CORRECT, CONTRADICTION


class VerificationTests(unittest.TestCase):
    def test_rejecting_browser_calls_alone_does_not_supply_the_safe_design(self):
        answer = ("To prevent exposing a private API key to website visitors, you must never "
                  "call the third-party API directly from the browser (frontend).")
        for case_id in (3, 13):
            with self.subTest(case=case_id):
                result = verify(GOLDEN_PAIRS[case_id], answer)
                self.assertEqual(result["status"], "WRONG")
                self.assertTrue(all(not check["met"] for check in result["checks"]))
                # This is incomplete, not advice to expose the key.
                self.assertEqual(result["contradictions"], [])

    def test_complete_api_auth_paraphrases_preserve_case_specific_requirements(self):
        answers = [
            "Have the frontend talk to our backend. Keep the API key exclusively server-side. "
            "Our backend forwards the call to the provider.",
            "Requests from the browser should go through the backend. The private key must "
            "remain on the server. The third-party API is called by the backend.",
            "The frontend communicates with the backend. Keep the private key on the server. "
            "The backend sends the request to the third-party API.",
        ]
        with patch("requests.request", side_effect=AssertionError("Python alone grades")), \
                patch("requests.post", side_effect=AssertionError("No model grading")):
            for answer in answers:
                with self.subTest(answer=answer):
                    result = verify(GOLDEN_PAIRS[13], answer)
                    self.assertEqual(result["status"], "PASS", result)
                    self.assertEqual(verify(GOLDEN_PAIRS[3], answer)["status"], "WRONG")
                    exposed = "Visitors can inspect the JavaScript and copy the key. " + answer
                    self.assertEqual(verify(GOLDEN_PAIRS[3], exposed)["status"], "PASS")
                    for check in result["checks"]:
                        for span in check["evidence"]:
                            self.assertEqual(answer[span["start"]:span["end"]], span["text"])

    def test_api_auth_missing_each_safe_design_requirement_is_wrong(self):
        incomplete = [
            ("Keep the API key exclusively server-side. The backend forwards the request "
             "to the provider.", "c13.01"),
            ("The frontend communicates with the backend. The backend sends the request "
             "to the third-party API.", "c13.02"),
            ("Requests from the browser should go through the backend. The private key "
             "must remain on the server.", "c13.03"),
        ]
        for answer, missing in incomplete:
            with self.subTest(missing=missing):
                result = verify(GOLDEN_PAIRS[13], answer)
                self.assertEqual(result["status"], "WRONG")
                self.assertFalse(next(c["met"] for c in result["checks"] if c["check_id"] == missing))

    def test_api_auth_quoted_or_hypothetical_design_is_not_an_assertion(self):
        design = ("The frontend communicates with the backend. Keep the API key exclusively "
                  "server-side. The third-party API is called by the backend.")
        for answer in ('"' + design + '"',
                       'Suppose the frontend communicates with the backend. ' +
                       'Keep the API key exclusively server-side. ' +
                       'The third-party API is called by the backend.'):
            with self.subTest(answer=answer):
                self.assertEqual(verify(GOLDEN_PAIRS[13], answer)["status"], "WRONG")

    def test_complete_api_auth_design_can_include_the_reported_browser_warning(self):
        answer = ("To prevent exposing a private API key to website visitors, you must never "
                  "call the third-party API directly from the browser (frontend). "
                  "The frontend communicates with the backend. Keep the API key exclusively "
                  "server-side. The backend sends the request to the third-party API.")
        result = verify(GOLDEN_PAIRS[13], answer)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["contradictions"], [])

    def test_api_auth_paraphrases_do_not_accept_negated_or_wrong_actor_relations(self):
        answers = [
            "The frontend must not communicate with the backend. Keep the key exclusively "
            "server-side. The backend forwards the call to the provider.",
            "The frontend talks to the backend. The private key must not remain on the server. "
            "The backend sends the request to the provider.",
            "The frontend communicates with the backend. Keep the key server-side. "
            "The third-party API must not be called by the backend.",
            "The frontend communicates with the backend. Keep the key server-side. "
            "The third-party API is called by the browser.",
            "The frontend talks to the backend. Keep the key server-side. "
            "The backend does not forward the request to the provider.",
        ]
        for answer in answers:
            with self.subTest(answer=answer):
                self.assertEqual(verify(GOLDEN_PAIRS[13], answer)["status"], "WRONG")

    def test_api_auth_complete_design_cannot_override_unsafe_key_advice(self):
        correct = ("The frontend communicates with the backend. Keep the private key on the "
                   "server. The backend sends the request to the third-party API. ")
        for advice in (
            "Hide the private key in frontend JavaScript.",
            "The browser calls the third-party API using the private key.",
            "Call the third-party API from the browser using the private key.",
        ):
            with self.subTest(advice=advice):
                result = verify(GOLDEN_PAIRS[13], correct + advice)
                self.assertEqual(result["status"], "WRONG")
                self.assertTrue(result["contradictions"])
        for advice in (
            "Never call the third-party API from the browser using the private key.",
            "Do not hide the private key in frontend JavaScript.",
        ):
            with self.subTest(rejected_advice=advice):
                self.assertEqual(verify(GOLDEN_PAIRS[13], correct + advice)["status"], "PASS")

    def test_audited_valid_backend_paraphrase(self):
        answer = ("Apply the discount rules on the server. A visitor can alter the browser code, "
                  "so it cannot be the authority.")
        self.assertEqual(verify(GOLDEN_PAIRS[1], answer)["status"], "PASS")

    def test_conflicting_numeric_target_is_wrong(self):
        for target in (999, 4821, 1729):
            answer = f"Change the order ID in the request to 729. Change the order ID in the request to {target}."
            with self.subTest(target=target):
                result = verify(GOLDEN_PAIRS[12], answer)
                self.assertEqual(result["status"], "WRONG")
                self.assertTrue(result["contradictions"])

    def test_frontend_environment_key_advice_cannot_pass(self):
        answer = (GOLDEN_PAIRS[13]["case_answer"] +
                  " Also put the private key in frontend environment variables so it stays secret.")
        self.assertEqual(verify(GOLDEN_PAIRS[13], answer)["status"], "WRONG")

    def test_all_twenty_authoritative_answers_pass_without_network(self):
        self.assertEqual(set(GOLDEN_PAIRS), set(range(1, 21)))
        self.assertEqual(set(RULES), set(GOLDEN_PAIRS))
        with patch("requests.request", side_effect=AssertionError("Grading must not use a provider")):
            for case_id, case in GOLDEN_PAIRS.items():
                with self.subTest(case=case_id):
                    self.assertEqual(verify(case, case["case_answer"])["status"], "PASS")

    def test_sixty_authored_supported_paraphrases(self):
        for case_id, answers in CORRECT.items():
            self.assertEqual(len(answers), 3)
            for answer in answers:
                with self.subTest(case=case_id, answer=answer):
                    result = verify(GOLDEN_PAIRS[case_id], answer)
                    self.assertEqual(result["status"], "PASS", result)

    def test_appended_contradiction_overrides_correct_answer_for_every_case(self):
        for case_id, bad_advice in CONTRADICTION.items():
            with self.subTest(case=case_id):
                answer = GOLDEN_PAIRS[case_id]["case_answer"] + " " + bad_advice
                result = verify(GOLDEN_PAIRS[case_id], answer)
                self.assertEqual(result["status"], "WRONG")
                self.assertTrue(result["contradictions"], result)

    def test_quoted_reference_is_not_an_assertion(self):
        for case_id, case in GOLDEN_PAIRS.items():
            with self.subTest(case=case_id):
                self.assertEqual(verify(case, '"' + case["case_answer"] + '"')["status"], "WRONG")

    def test_disconnected_keyword_lists_do_not_pass(self):
        answer = "backend browser code key server storage learner_id attempts learners.id gap row success database 729"
        for case_id, case in GOLDEN_PAIRS.items():
            with self.subTest(case=case_id):
                self.assertEqual(verify(case, answer)["status"], "WRONG")

    def test_bad_source_is_unavailable_never_wrong(self):
        for field in ("case_question", "case_answer", "idea_id"):
            changed = copy.deepcopy(GOLDEN_PAIRS[1])
            changed[field] += " changed"
            with self.subTest(field=field), self.assertRaises(VerificationUnavailable):
                verify(changed, "Some learner answer")
        with self.assertRaises(VerificationUnavailable):
            verify({"case_id": 99}, "Some learner answer")

    def test_missing_source_fields_are_unavailable(self):
        with self.assertRaises(VerificationUnavailable):
            validate_source({"case_id": 1})

    def test_invalid_answer_is_not_a_grade(self):
        for answer in ("", "   ", None, "x" * 6001):
            with self.subTest(answer_type=type(answer)), self.assertRaises(ValueError):
                verify(GOLDEN_PAIRS[1], answer)

    def test_evidence_offsets_and_unicode_normalization(self):
        answer = "Return  ＨＴＴＰ ２０１ Created."
        result = verify(GOLDEN_PAIRS[18], answer)
        self.assertEqual(result["status"], "PASS")
        for check in result["checks"]:
            for span in check["evidence"]:
                self.assertEqual(answer[span["start"]:span["end"]], span["text"])

    def test_repeated_serialized_results_are_identical(self):
        for case_id, case in GOLDEN_PAIRS.items():
            with self.subTest(case=case_id):
                first = json.dumps(verify(case, case["case_answer"]), sort_keys=True)
                self.assertEqual(first, json.dumps(verify(case, case["case_answer"]), sort_keys=True))

    def test_case_specific_criteria_are_not_copied_from_other_case(self):
        for first, second in [(3, 13), (4, 14), (5, 15), (7, 17), (8, 18)]:
            answer = GOLDEN_PAIRS[second]["case_answer"]
            self.assertEqual(verify(GOLDEN_PAIRS[second], answer)["status"], "PASS")
            self.assertEqual(verify(GOLDEN_PAIRS[first], answer)["status"], "WRONG")

    def test_numeric_target_is_exact(self):
        self.assertEqual(verify(GOLDEN_PAIRS[12], "Change the order ID in the request to 1729.")["status"], "WRONG")

    def test_negation_cannot_supply_positive_evidence(self):
        answers = {
            13: "Do not route the request through the backend. The server must not store the key or make the authorized API call.",
            14: "Do not save attempts in a database and never retrieve them.",
            15: "Do not store each attempt as a separate row with a learner reference.",
            18: "Do not return HTTP 201 Created.",
        }
        for case_id, answer in answers.items():
            with self.subTest(case=case_id):
                self.assertEqual(verify(GOLDEN_PAIRS[case_id], answer)["status"], "WRONG")

    def test_rejected_bad_advice_is_not_a_contradiction(self):
        answer = GOLDEN_PAIRS[13]["case_answer"] + " It is wrong to store the key in the browser."
        self.assertEqual(verify(GOLDEN_PAIRS[13], answer)["status"], "PASS")

    def test_incomplete_answers_report_missing_checks_for_every_case(self):
        incomplete = {
            1: "Users can inspect browser code.",
            2: "The request should carry the order ID.",
            3: GOLDEN_PAIRS[13]["case_answer"],
            4: "Save progress in a database and retrieve it on return.",
            5: "Each attempt has a learner_id referencing its learner.",
            6: "Store each attempt as a separate row.",
            7: "The concept list lives in code.",
            8: "Return an appropriate HTTP status code.",
            9: "Use a foreign key from attempts.learner_id to learners.id.",
            10: "The retry attempt references the gap.",
            11: "The server validates the price using trusted business rules.",
            12: "Only update the displayed label.",
            13: "The backend securely stores the key.",
            14: "Save attempts in durable storage.",
            15: "Store each attempt as a separate row.",
            16: "Each attempt has its own row.",
            17: "No.",
            18: "Return the resource identifier.",
            19: "A foreign key constraint references learners.id.",
            20: "Store the gap as a record.",
        }
        for case_id, answer in incomplete.items():
            with self.subTest(case=case_id):
                result = verify(GOLDEN_PAIRS[case_id], answer)
                self.assertEqual(result["status"], "WRONG")
                self.assertTrue(any(not check["met"] for check in result["checks"]))

    def test_negated_data_placements_cannot_pass(self):
        answer = ("The concept list must not live in code. Secrets must not belong in server-side environment configuration. "
                  "Attempts must not live in durable database storage. The loading message must not live in temporary UI state.")
        result = verify(GOLDEN_PAIRS[7], answer)
        self.assertEqual(result["status"], "WRONG")
        self.assertTrue(all(not check["met"] for check in result["checks"]))

    def test_whitespace_does_not_change_assessment(self):
        case = GOLDEN_PAIRS[17]
        result = verify(case, '  \n' + case["case_answer"] + ' \n')
        self.assertEqual(result["status"], "PASS")

    def test_quoted_identifiers_are_not_discarded_as_propositions(self):
        answer = 'Use a foreign key from attempts.learner_id to "learners.id". The constraint rejects attempts for nonexistent learners.'
        self.assertEqual(verify(GOLDEN_PAIRS[9], answer)["status"], "PASS")

    def test_a_different_actor_cannot_supply_the_backends_api_call(self):
        for bridge in ("but", "and then", ", while"):
            answer = ("The browser calls the backend. The backend stores the key " + bridge +
                      " the browser makes the authorized API call.")
            with self.subTest(bridge=bridge):
                result = verify(GOLDEN_PAIRS[13], answer)
                self.assertEqual(result["status"], "WRONG")
                self.assertFalse(result["checks"][2]["met"])

    def test_legacy_grading_path_returns_gone_without_database_or_model(self):
        legacy_path = Path("03-fastapi/api/index.py")
        if not legacy_path.is_file():
            self.skipTest("The legacy lecture application is not included in the MVP checkout.")
        source = legacy_path.read_text(encoding="utf-8")
        module = ast.parse(source)
        functions = [node for node in module.body if isinstance(node, ast.FunctionDef)
                     and node.name in {"verify", "evaluate_route"}]
        self.assertEqual(len(functions), 2)
        for function in functions:
            function.decorator_list = []
        isolated = ast.Module(body=functions, type_ignores=[])
        namespace = {"HTTPException": HTTPException, "Any": Any, "EvaluateIn": SimpleNamespace}
        exec(compile(isolated, "legacy-grading-contract", "exec"), namespace)
        with self.assertRaises(HTTPException) as caught:
            namespace["evaluate_route"](SimpleNamespace(answer="A learner answer"))
        self.assertEqual(caught.exception.status_code, 410)


if __name__ == "__main__":
    unittest.main()
