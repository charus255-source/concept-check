"""'Words you'll need' must explain vocabulary only, never an answer."""

import unittest

from fastapi.testclient import TestClient

from concept_app.catalog import IDEAS, WORDS
from concept_app.verification import verify
from concept_app.verification.engine import GOLDEN_PAIRS
from concept_app.web import app


class WordsYouNeed(unittest.TestCase):
    def test_every_concept_has_words(self):
        self.assertEqual(set(WORDS), set(IDEAS))
        for idea, words in WORDS.items():
            self.assertGreaterEqual(len(words), 2, idea)

    def test_no_word_list_meets_any_graded_idea(self):
        for idea, words in WORDS.items():
            text = " ".join(f"{term}: {meaning}" for term, meaning in words)
            for case in GOLDEN_PAIRS.values():
                if case["idea_id"] == idea:
                    with self.subTest(idea=idea, case=case["case_id"]):
                        result = verify(case, text)
                        self.assertEqual(result["met"], 0, [c["evidence"] for c in result["checks"] if c["met"]])

    def test_words_are_served_without_a_session(self):
        rows = TestClient(app).get("/api/ideas").json()
        self.assertTrue(all(row["words"] for row in rows))


class Lessons(unittest.TestCase):
    def test_every_concept_has_a_complete_lesson(self):
        from concept_app.catalog import LESSONS
        self.assertEqual(set(LESSONS), set(IDEAS))
        for idea, lesson in LESSONS.items():
            with self.subTest(idea=idea):
                self.assertEqual(set(lesson), {"idea", "analogy", "example", "mistake"})
                self.assertTrue(all(len(text) > 20 for text in lesson.values()))

    def test_lessons_are_served_with_the_concepts(self):
        rows = TestClient(app).get("/api/ideas").json()
        self.assertTrue(all(row["lesson"]["idea"] for row in rows))


class HowIBuiltThis(unittest.TestCase):
    def test_page_and_sketches_are_served(self):
        client = TestClient(app)
        self.assertIn("How I built this", client.get("/how").text)
        for name in ("architecture-sketch.jpg", "data-design-sketch.jpg"):
            response = client.get("/static/notes/" + name)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "image/jpeg")
