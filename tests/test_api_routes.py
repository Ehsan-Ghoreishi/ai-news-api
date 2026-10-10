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
    defaults = {
        "id": 1,
        "source": "hackernews",
        "source_id": "123",
        "title": "Test Article",
        "url": "https://example.com/article",
        "author": None,
        "content": "body text",
        "scraped_at": "2026-01-01T00:00:00",
        "summary": None,
        "tags": [],
    }
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
        self.assertEqual(body["answer_source"], "articles")

    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_with_no_supporting_data_returns_unsupported(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = []

        response = client.post(
            "/ask/", json={"question": "Something totally unrelated", "allow_general_knowledge": False}
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["supported"])
        self.assertEqual(body["citations"], [])
        self.assertEqual(body["answer"], "Not enough information")
        self.assertEqual(body["answer_source"], "none")

    @patch("app.api.routes.ask.get_news_item")
    @patch("app.api.routes.ask.answer_from_context")
    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_with_unsupported_answer_omits_citations(
        self, mock_embed, mock_search, mock_answer, mock_get_item
    ):
        # Chunks were retrieved (loosely similar), but the LLM judged them insufficient
        # to answer the question - citations must not reference sources that weren't
        # actually used to ground the answer.
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = [
            SearchResult(
                news_item_id=1,
                title="Unrelated Article",
                url="https://example.com/article",
                chunk_content="some loosely similar but irrelevant text",
                similarity=0.4,
            )
        ]
        mock_answer.return_value = GroundedAnswer(answer="Not enough information", supported=False)

        response = client.post(
            "/ask/",
            json={"question": "What is the answer?", "limit": 5, "allow_general_knowledge": False},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["supported"])
        self.assertEqual(body["citations"], [])
        mock_get_item.assert_not_called()

    @patch("app.api.routes.ask.answer_from_general_knowledge")
    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_with_empty_index_falls_back_to_general_knowledge(self, mock_embed, mock_search, mock_general):
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = []
        mock_general.return_value = "Paris is the capital of France."

        response = client.post("/ask/", json={"question": "What is the capital of France?"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], "Paris is the capital of France.")
        # Not backed by an article: must never look like it is.
        self.assertFalse(body["supported"])
        self.assertEqual(body["answer_source"], "general_knowledge")
        self.assertEqual(body["citations"], [])

    @patch("app.api.routes.ask.answer_from_general_knowledge")
    @patch("app.api.routes.ask.get_news_item")
    @patch("app.api.routes.ask.answer_from_context")
    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_unsupported_answer_falls_back_and_lists_closest_articles(
        self, mock_embed, mock_search, mock_answer, mock_get_item, mock_general
    ):
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = [
            SearchResult(
                news_item_id=1,
                title="Weak Match",
                url="https://example.com/weak",
                chunk_content="loosely related text",
                similarity=0.3,
            ),
            SearchResult(
                news_item_id=1,
                title="Weak Match",
                url="https://example.com/weak",
                chunk_content="another chunk of the same article",
                similarity=0.5,
            ),
            SearchResult(
                news_item_id=2,
                title="Other Article",
                url="https://example.com/other",
                chunk_content="different text",
                similarity=0.4,
            ),
        ]
        mock_answer.return_value = GroundedAnswer(answer="Not enough information", supported=False)
        mock_general.return_value = "General knowledge answer."

        response = client.post("/ask/", json={"question": "Something the articles don't cover"})

        body = response.json()
        self.assertEqual(body["answer"], "General knowledge answer.")
        self.assertFalse(body["supported"])
        self.assertEqual(body["answer_source"], "general_knowledge")
        self.assertEqual(body["citations"], [])
        mock_get_item.assert_not_called()
        # One entry per distinct article, best chunk's similarity, closest first.
        self.assertEqual([a["title"] for a in body["related_articles"]], ["Weak Match", "Other Article"])
        self.assertAlmostEqual(body["related_articles"][0]["similarity"], 0.5)

    @patch("app.api.routes.ask.answer_from_general_knowledge")
    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_strict_mode_never_calls_general_knowledge(self, mock_embed, mock_search, mock_general):
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = []

        response = client.post("/ask/", json={"question": "Anything", "allow_general_knowledge": False})

        self.assertEqual(response.json()["answer"], "Not enough information")
        mock_general.assert_not_called()

    @patch("app.api.routes.ask.get_news_item")
    @patch("app.api.routes.ask.answer_from_context")
    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_detailed_style_labels_chunks_with_titles(
        self, mock_embed, mock_search, mock_answer, mock_get_item
    ):
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
        mock_answer.return_value = GroundedAnswer(answer="It is 42, per the article.", supported=True)
        mock_get_item.return_value = _news_item()

        client.post("/ask/", json={"question": "What is the answer?"})  # detailed is the default

        args, kwargs = mock_answer.call_args
        self.assertEqual(kwargs["style"], "detailed")
        self.assertEqual(args[1], ["Article: Test Article\nthe answer is 42"])

    @patch("app.api.routes.ask.get_news_item")
    @patch("app.api.routes.ask.answer_from_context")
    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_ask_concise_style_passes_bare_chunks(self, mock_embed, mock_search, mock_answer, mock_get_item):
        # The evaluation harness depends on this exact, unlabelled input staying unchanged.
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

        client.post("/ask/", json={"question": "What is the answer?", "style": "concise"})

        args, kwargs = mock_answer.call_args
        self.assertEqual(kwargs["style"], "concise")
        self.assertEqual(args[1], ["the answer is 42"])

    def test_ask_invalid_style_is_rejected(self):
        response = client.post("/ask/", json={"question": "x", "style": "essay"})
        self.assertEqual(response.status_code, 422)

    def test_ask_missing_question_field_is_rejected(self):
        response = client.post("/ask/", json={})
        self.assertEqual(response.status_code, 422)

    def test_ask_question_wrong_type_is_rejected(self):
        response = client.post("/ask/", json={"question": 123})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
