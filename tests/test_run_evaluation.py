import io
import unittest
from contextlib import redirect_stdout

from week6.evaluations.run_evaluation import report


class TestReport(unittest.TestCase):
    def test_accuracy_over_mixed_results(self):
        results = [
            {"id": "a", "retrieval_ok": True, "answer_ok": True, "end_to_end_ok": True},
            {"id": "b", "retrieval_ok": False, "answer_ok": False, "end_to_end_ok": False},
            # expect_supported: false question - retrieval_ok is not applicable
            {"id": "c", "retrieval_ok": None, "answer_ok": True, "end_to_end_ok": True},
        ]
        with redirect_stdout(io.StringIO()):
            accuracy = report(results)
        self.assertAlmostEqual(accuracy, 2 / 3)

    def test_retrieval_accuracy_excludes_none(self):
        results = [
            {"id": "a", "retrieval_ok": True, "answer_ok": True, "end_to_end_ok": True},
            {"id": "b", "retrieval_ok": None, "answer_ok": True, "end_to_end_ok": True},
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            report(results)
        self.assertIn("Retrieval accuracy: 1/1 (100.0%)", output.getvalue())
        self.assertIn("n/a", output.getvalue())


if __name__ == "__main__":
    unittest.main()
