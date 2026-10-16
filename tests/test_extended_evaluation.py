import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation import run_evaluation

EXTENDED = Path(run_evaluation.__file__).parent / "questions_extended.json"
ANSWER_TYPES = {"number", "text", "boolean"}


class EvaluateMultipleFilesTests(unittest.TestCase):
    def test_evaluate_reads_every_question_file_and_records_answers(self):
        first = [
            {"id": "a", "question": "Q a?", "answer_type": "number",
             "expected_answer": "5", "source_id": "1"}
        ]
        second = [{"id": "t", "question": "Q t?", "expect_supported": False}]
        payloads = {
            "Q a?": {"answer": "5", "supported": True, "citations": [{"source_id": "1"}]},
            "Q t?": {"answer": "Not enough information", "supported": False, "citations": []},
        }
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name, data in (("one.json", first), ("two.json", second)):
                path = Path(tmp) / name
                path.write_text(json.dumps(data), encoding="utf-8")
                paths.append(path)
            with patch.object(run_evaluation, "_ask", side_effect=lambda _url, q: payloads[q]):
                results = run_evaluation.evaluate("http://x", tuple(paths))
        self.assertEqual([r["id"] for r in results], ["a", "t"])
        self.assertTrue(all(r["end_to_end_ok"] for r in results))
        self.assertEqual(results[0]["answer"], "5")
        self.assertEqual(results[0]["cited_source_ids"], ["1"])


class ExtendedQuestionFileTests(unittest.TestCase):
    def setUp(self):
        self.questions = json.loads(EXTENDED.read_text(encoding="utf-8"))

    def test_ids_are_unique_across_both_files(self):
        original = json.loads(run_evaluation.QUESTIONS_PATH.read_text(encoding="utf-8"))
        ids = [q["id"] for q in original + self.questions]
        self.assertEqual(len(ids), len(set(ids)))

    def test_answerable_questions_are_complete(self):
        for q in self.questions:
            if q.get("expect_supported", True):
                self.assertIn(q["answer_type"], ANSWER_TYPES, q["id"])
                self.assertTrue(str(q["expected_answer"]).strip(), q["id"])
                self.assertTrue(str(q["source_id"]).strip(), q["id"])
                if q["answer_type"] == "number":
                    float(q["expected_answer"])

    def test_questions_are_standalone_sentences(self):
        for q in self.questions:
            self.assertTrue(q["question"].endswith("?"), q["id"])
            self.assertGreaterEqual(len(q["question"].split()), 6, q["id"])

    def test_has_unanswerable_questions(self):
        traps = [q for q in self.questions if q.get("expect_supported") is False]
        self.assertGreaterEqual(len(traps), 5)
