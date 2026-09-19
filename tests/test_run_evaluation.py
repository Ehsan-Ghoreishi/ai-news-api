import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from week6.evaluations.run_evaluation import _ask, report


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


class TestAsk(unittest.TestCase):
    @patch("week6.evaluations.run_evaluation.time.sleep")
    @patch("week6.evaluations.run_evaluation.requests.post")
    def test_retries_after_rate_limit(self, mock_post, mock_sleep):
        rate_limited = MagicMock(status_code=429)
        ok = MagicMock(status_code=200)
        ok.json.return_value = {"answer": "42", "supported": True, "citations": []}
        mock_post.side_effect = [rate_limited, ok]

        result = _ask("http://testserver", "some question")

        self.assertEqual(result["answer"], "42")
        mock_sleep.assert_called_once_with(61)
        self.assertEqual(mock_post.call_count, 2)

    @patch("week6.evaluations.run_evaluation.time.sleep")
    @patch("week6.evaluations.run_evaluation.requests.post")
    def test_gives_up_after_max_retries(self, mock_post, mock_sleep):
        import requests

        rate_limited = MagicMock(status_code=429)
        rate_limited.raise_for_status.side_effect = requests.exceptions.HTTPError("429")
        mock_post.return_value = rate_limited

        with self.assertRaises(requests.exceptions.HTTPError):
            _ask("http://testserver", "some question")

        self.assertEqual(mock_post.call_count, 4)  # initial attempt + 3 retries


if __name__ == "__main__":
    unittest.main()
