"""HTTP-level tests for the API routes.

These never touch a real database or the OpenAI API: get_db is overridden
with a stub session, and the LLM/embedding/repository calls each route makes
are mocked directly. DATABASE_URL and OPENAI_API_KEY are stubbed before
app.main is imported since connection.py and the agent modules read them
at import time to construct clients - the values are never actually used
to connect anywhere.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.database.connection import get_db
from app.main import app
from app.schemas.news import GroundedAnswer, NewsItem, SearchResult

app.dependency_overrides[get_db] = lambda: iter([MagicMock()])

client = TestClient(app)


def _news_item(**overrides) -> NewsItem:
    defaults = dict(
        id=1,
        source="hackernews",
        source_id="123",
        title="Test Article",
        url="https://example.com/article",
        author=None,
        content="body text",
        scraped_at="2026-01-01T00:00:00",
        summary=None,
        tags=[],
    )
    defaults.update(overrides)
    return NewsItem(**defaults)


class TestSearchRoute(unittest.TestCase):
    @patch("app.api.routes.search.search_similar_chunks")
    @patch("app.api.routes.search.create_embedding")
    def test_search_with_valid_query(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = [
            SearchResult(
                news_item_id=1,
                title="Test Article",
                url="https://example.com/article",
                chunk_content="relevant chunk",
                similarity=0.9,
            )
        ]

        response = client.get("/search/", params={"q": "test query"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["news_item_id"], 1)
        self.assertEqual(body[0]["chunk_content"], "relevant chunk")
        mock_embed.assert_called_once_with("test query")
        mock_search.assert_called_once()

    def test_search_missing_query_param_is_rejected(self):
        response = client.get("/search/")
        self.assertEqual(response.status_code, 422)


class TestAskRoute(unittest.TestCase):
    @patch("app.api.routes.ask.get_news_item")
    @patch("app.api.routes.ask.answer_from_context")
    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_with_supporting_data(self, mock_embed, mock_search, mock_answer, mock_get_item):
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = [
            SearchResult(
                news_item_id=1,
                title="Test Article",
                url="https://example.com/article",
                chunk_content="the answer is 42",
                similarity=0.9,
            )
        ]
        mock_answer.return_value = GroundedAnswer(answer="42", supported=True)
        mock_get_item.return_value = _news_item()

        response = client.post("/ask/", json={"question": "What is the answer?", "limit": 5})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["supported"])
        self.assertEqual(body["answer"], "42")
        self.assertEqual(len(body["citations"]), 1)
        self.assertEqual(body["citations"][0]["source_id"], "123")

    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_with_no_supporting_data_returns_unsupported(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = []

        response = client.post("/ask/", json={"question": "Something totally unrelated"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["supported"])
        self.assertEqual(body["citations"], [])
        self.assertEqual(body["answer"], "Not enough information")

    def test_ask_missing_question_field_is_rejected(self):
        response = client.post("/ask/", json={})
        self.assertEqual(response.status_code, 422)

    def test_ask_question_wrong_type_is_rejected(self):
        response = client.post("/ask/", json={"question": 123})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
