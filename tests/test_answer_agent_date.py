import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")

import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.agents import answer_agent


class TodayContextTests(unittest.TestCase):
    def test_context_has_current_date_and_article_date_rule(self):
        text = answer_agent._today_context()
        self.assertIn(datetime.now(UTC).strftime("%d %B %Y"), text)
        self.assertIn("not today's date", text)

    def test_every_prompt_includes_today_context(self):
        today = answer_agent._today_context()
        with patch.object(answer_agent, "client") as client:
            client.responses.parse.return_value.output_parsed = MagicMock()
            for style in ("concise", "detailed"):
                answer_agent.answer_from_context("q", ["ctx"], style=style)
                system = client.responses.parse.call_args.kwargs["input"][0]["content"]
                self.assertIn(today, system)
            client.responses.create.return_value.output_text = "answer"
            answer_agent.answer_from_general_knowledge("q")
            system = client.responses.create.call_args.kwargs["input"][0]["content"]
            self.assertIn(today, system)


if __name__ == "__main__":
    unittest.main()
