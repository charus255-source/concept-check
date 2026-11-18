"""API behaviour against an in-memory stand-in for Supabase (no network)."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from concept_app import web
from concept_app.verification.engine import GOLDEN_PAIRS

ENV = {"GROQ_API_KEY": "groq", "SUPABASE_URL": "https://db.example", "SUPABASE_SERVICE_KEY": "service",
       "SESSION_SECRET": "s" * 40}


class FakeDatabase:
    """Just enough PostgREST filtering for these endpoints."""

    def __init__(self):
        self.tables = {"learners": [], "attempts": [], "gaps": [],
                       "cases": [dict(row) for row in GOLDEN_PAIRS.values()]}

    @staticmethod
    def matches(row, key, condition):
        value = row.get(key)
        if condition == "is.null":
            return value is None
        if condition == "not.is.null":
            return value is not None
        op, _, wanted = condition.partition(".")
        if op == "in":
            return str(value) in wanted.strip("()").split(",")
        if op == "eq":
            return str(value) == wanted
        if op == "neq":
            return str(value) != wanted
        raise AssertionError(condition)

    def __call__(self, settings, method, table, *, params=None, data=None):
        rows = self.tables[table]
        if method == "POST":
            if (table == "attempts" and data.get("event_type") == "graded" and any(
                    r["event_type"] == "graded" and r["learner_id"] == data["learner_id"]
                    and r["case_id"] == data["case_id"] for r in rows)):
                raise web.DuplicateRow()
            row = {"id": len(rows) + 1, "case_id": None, "gap_id": None, "created_at": "now", **data}
            rows.append(row)
            return [row]
        filters = {k: v for k, v in (params or {}).items() if k not in {"select", "order", "limit"}}
        return [dict(r) for r in rows if all(self.matches(r, k, v) for k, v in filters.items())]


def probe_result(*args):
    return {"recited_sentence": "", "follow_up_question": "What breaks?"}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDatabase()
        web._hits.clear()
        for patcher in (patch.dict(os.environ, ENV), patch.object(web, "database", self.db),
                        patch.object(web, "probe", probe_result),
                        patch.object(web, "find_quotes", lambda *args: {})):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(web.app, base_url="https://testserver")
        self.client.post("/api/session", json={})

    def explain_and_retry(self, idea="PERSISTENCE"):
        gap = self.client.post("/api/check", json={"idea_id": idea, "explanation": "It is saved somewhere."}).json()["gap_id"]
        self.client.post("/api/check", json={"idea_id": idea, "explanation": "It goes in the database.", "gap_id": gap})
        return gap

    def answer(self, idea, text, gap=None):
        case = self.client.post("/api/assessment/case", json={"idea_id": idea, "gap_id": gap})
        self.assertEqual(case.status_code, 200, case.text)
        return self.client.post("/api/assessment/answer", json={"challenge": case.json()["challenge"], "answer": text})

    def test_session_is_signed_with_session_secret_not_service_key(self):
        settings = web.Settings.load()
        token = self.client.cookies.get("concept_session")
        self.assertEqual(token, web.signed_identity(1, settings))
        with patch.dict(os.environ, {"SESSION_SECRET": "service"}):
            self.assertEqual(self.client.get("/api/history").status_code, 503)

    def test_practice_is_its_own_event_without_a_case(self):
        self.explain_and_retry()
        events = [(row["event_type"], row["case_id"], row["idea_id"]) for row in self.db.tables["attempts"]]
        self.assertEqual(events, [("explanation", None, "PERSISTENCE"), ("retry", None, "PERSISTENCE")])

    def test_graded_attempt_records_rule_version_and_fingerprint(self):
        response = self.answer("PERSISTENCE", "Save progress in a database.")
        self.assertEqual(response.json()["message"], "Almost there. You covered 1 of 3 ideas.")
        row = self.db.tables["attempts"][-1]
        self.assertEqual((row["event_type"], row["passed"]), ("graded", False))
        self.assertEqual(row["rule_version"], response.json()["rule_version"])
        self.assertEqual(len(row["source_fingerprint"]), 64)

    def test_both_cases_then_a_clear_next_step(self):
        self.answer("PERSISTENCE", "Save progress in a database.")
        gap = self.explain_and_retry()
        after = self.answer("PERSISTENCE", "Store the attempts in a database and load them again later.", gap)
        self.assertEqual(after.json()["status"], "PASS")
        exhausted = self.client.post("/api/assessment/case", json={"idea_id": "PERSISTENCE"})
        self.assertEqual(exhausted.status_code, 409)
        self.assertIn("Next, try:", exhausted.json()["detail"])

    def test_duplicate_graded_answer_is_409(self):
        case = self.client.post("/api/assessment/case", json={"idea_id": "PERSISTENCE"}).json()
        body = {"challenge": case["challenge"], "answer": "Save progress in a database."}
        self.assertEqual(self.client.post("/api/assessment/answer", json=body).status_code, 200)
        self.assertEqual(self.client.post("/api/assessment/answer", json=body).status_code, 409)

    def test_new_concepts_are_accepted(self):
        for idea in ("HTTP_RESPONSE", "REFERENTIAL_INTEGRITY", "RETRY_GAP"):
            response = self.client.post("/api/check", json={"idea_id": idea, "explanation": "Some explanation."})
            self.assertEqual(response.status_code, 200, response.text)

    def test_rate_limit(self):
        limit = web.LIMITS["check"][0]
        codes = [self.client.post("/api/check", json={"idea_id": "API_AUTH", "explanation": "Some explanation."}).status_code
                 for _ in range(limit + 1)]
        self.assertEqual(codes[-1], 429)
        self.assertEqual(set(codes[:-1]), {200})


class HistoryDetailTests(ApiTests):
    def test_history_shows_what_was_right_and_missing(self):
        self.answer("BACKEND_PURPOSE", "developer has to put the rules in backend server as code")
        graded = [row for row in self.client.get("/api/history").json()["attempts"] if row["event_type"] == "graded"]
        result = graded[0]["result"]
        self.assertEqual((result["status"], result["met"], result["total"]), ("NOT_YET", 1, 3))
        self.assertEqual(result["message"], "Almost there. You covered 1 of 3 ideas.")

    def test_answers_graded_by_older_rules_show_no_details(self):
        self.answer("BACKEND_PURPOSE", "developer has to put the rules in backend server as code")
        self.db.tables["attempts"][-1]["rule_version"] = "1.0.2"
        graded = [row for row in self.client.get("/api/history").json()["attempts"] if row["event_type"] == "graded"]
        self.assertIsNone(graded[0]["result"])


class ClarifyingQuestionTests(ApiTests):
    def test_a_question_is_not_graded_and_the_case_stays_open(self):
        case = self.client.post("/api/assessment/case", json={"idea_id": "API_REQUEST"}).json()
        for question in ("do u mean the server sent tis to user that order id is not mentioned properly",
                         "What do you mean by information?"):
            response = self.client.post("/api/assessment/answer", json={"challenge": case["challenge"], "answer": question})
            self.assertEqual(response.json()["status"], "QUESTION")
        self.assertEqual([row for row in self.db.tables["attempts"] if row["event_type"] == "graded"], [])
        answer = "The request should include the order ID 4821 in the URL so the server knows which order to fetch."
        response = self.client.post("/api/assessment/answer", json={"challenge": case["challenge"], "answer": answer})
        self.assertEqual(response.json()["status"], "PASS")

    def test_an_answer_phrased_as_a_question_is_still_graded(self):
        case = self.client.post("/api/assessment/case", json={"idea_id": "PERSISTENCE"}).json()
        response = self.client.post("/api/assessment/answer", json={
            "challenge": case["challenge"], "answer": "Should we save progress in a database?"})
        self.assertEqual(response.json()["status"], "NOT_YET")
