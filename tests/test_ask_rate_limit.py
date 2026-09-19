"""Verifies POST /ask/ enforces its per-IP rate limit (10/minute, see app/api/rate_limit.py)."""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.api.rate_limit import limiter
from app.database.connection import get_db
from app.main import app

app.dependency_overrides[get_db] = lambda: iter([MagicMock()])

client = TestClient(app)


class TestAskRateLimit(unittest.TestCase):
    def setUp(self):
        # Counters are shared across the whole test run (in-memory storage keyed by
        # client IP), so start each test with a clean slate.
        limiter.reset()

    @patch("app.api.routes.ask.search_similar_chunks")
    @patch("app.api.routes.ask.create_embedding")
    def test_eleventh_request_within_a_minute_is_rejected(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1] * 1536
        mock_search.return_value = []  # short-circuits to the "not enough info" path

        for i in range(10):
            response = client.post("/ask/", json={"question": f"question {i}"})
            self.assertEqual(response.status_code, 200)

        response = client.post("/ask/", json={"question": "one too many"})
        self.assertEqual(response.status_code, 429)


if __name__ == "__main__":
    unittest.main()
