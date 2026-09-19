import unittest

from week6.evaluations.scoring import score_answer


class TestScoreAnswer(unittest.TestCase):
    def test_number_match(self):
        self.assertTrue(score_answer("number", "42", "The answer is 42 articles"))

    def test_number_mismatch(self):
        self.assertFalse(score_answer("number", "42", "The answer is 43 articles"))

    def test_boolean_true(self):
        self.assertTrue(score_answer("boolean", "true", "Yes, that is correct"))

    def test_boolean_false(self):
        self.assertTrue(score_answer("boolean", "false", "No, that is not correct"))

    def test_text_exact_match(self):
        self.assertTrue(score_answer("text", "OpenAI", "The company is OpenAI"))

    def test_text_accepted_answers_match(self):
        self.assertTrue(
            score_answer(
                "text",
                "GPT-4",
                "The model used was ChatGPT",
                accepted_answers=["ChatGPT", "GPT-4 Turbo"],
            )
        )

    def test_invalid_answer_type_raises(self):
        with self.assertRaises(ValueError):
            score_answer("invalid_type", "42", "42")


if __name__ == "__main__":
    unittest.main()
