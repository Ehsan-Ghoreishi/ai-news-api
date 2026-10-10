"""Unit tests for the LLM answer agent. The OpenAI client is mocked - no network calls."""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.agents import answer_agent
from app.schemas.news import GroundedAnswer


def _system_prompt(mock_client: MagicMock) -> str:
    kwargs = mock_client.responses.parse.call_args.kwargs
    return kwargs["input"][0]["content"]


class TestAnswerFromContext(unittest.TestCase):
    def _mock_client(self, parsed: GroundedAnswer | None) -> MagicMock:
        mock_client = MagicMock()
        mock_client.responses.parse.return_value = MagicMock(output_parsed=parsed)
        return mock_client

    def test_defaults_to_concise_prompt_so_evaluation_behaviour_is_unchanged(self):
        mock_client = self._mock_client(GroundedAnswer(answer="42", supported=True))
        with patch.object(answer_agent, "client", mock_client):
            answer_agent.answer_from_context("q?", ["ctx"])
        self.assertEqual(_system_prompt(mock_client), answer_agent.CONCISE_INSTRUCTIONS)

    def test_detailed_style_uses_the_explanatory_prompt(self):
        mock_client = self._mock_client(GroundedAnswer(answer="Because...", supported=True))
        with patch.object(answer_agent, "client", mock_client):
            answer_agent.answer_from_context("why?", ["ctx"], style="detailed")
        self.assertEqual(_system_prompt(mock_client), answer_agent.DETAILED_INSTRUCTIONS)

    def test_detailed_prompt_asks_for_full_sentences_not_bare_values(self):
        self.assertIn("complete sentences", answer_agent.DETAILED_INSTRUCTIONS)
        self.assertNotIn("only the number", answer_agent.DETAILED_INSTRUCTIONS)

    def test_contexts_are_numbered_in_the_user_message(self):
        mock_client = self._mock_client(GroundedAnswer(answer="a", supported=True))
        with patch.object(answer_agent, "client", mock_client):
            answer_agent.answer_from_context("q?", ["first", "second"], style="detailed")
        user_message = mock_client.responses.parse.call_args.kwargs["input"][1]["content"]
        self.assertIn("[1] first", user_message)
        self.assertIn("[2] second", user_message)

    def test_unparseable_response_raises(self):
        mock_client = self._mock_client(None)
        with patch.object(answer_agent, "client", mock_client), self.assertRaises(RuntimeError):
            answer_agent.answer_from_context("q?", ["ctx"])


class TestAnswerFromGeneralKnowledge(unittest.TestCase):
    def test_returns_stripped_text_using_general_knowledge_prompt(self):
        mock_client = MagicMock()
        mock_client.responses.create.return_value = MagicMock(output_text="  Paris.  ")
        with patch.object(answer_agent, "client", mock_client):
            answer = answer_agent.answer_from_general_knowledge("Capital of France?")
        self.assertEqual(answer, "Paris.")
        kwargs = mock_client.responses.create.call_args.kwargs
        self.assertEqual(kwargs["input"][0]["content"], answer_agent.GENERAL_KNOWLEDGE_INSTRUCTIONS)
        self.assertEqual(kwargs["input"][1]["content"], "Capital of France?")

    def test_empty_output_raises(self):
        mock_client = MagicMock()
        mock_client.responses.create.return_value = MagicMock(output_text="   ")
        with patch.object(answer_agent, "client", mock_client), self.assertRaises(RuntimeError):
            answer_agent.answer_from_general_knowledge("anything")


if __name__ == "__main__":
    unittest.main()
