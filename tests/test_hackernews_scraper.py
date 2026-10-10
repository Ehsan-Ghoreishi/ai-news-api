"""Scraper tests. HTTP and trafilatura are mocked - no network calls."""

import unittest
from unittest.mock import MagicMock, patch

from app.scrapers import hackernews

LONG_TEXT = "x" * (hackernews.MIN_CONTENT_CHARS + 1)


def _fake_get(stories: dict[int, dict]):
    def get(url: str):
        response = MagicMock()
        if url == hackernews.TOP_STORIES_URL:
            response.json.return_value = list(stories)
        else:
            item_id = int(url.rsplit("/", 1)[1].removesuffix(".json"))
            response.json.return_value = stories[item_id]
        return response

    return get


class TestScrapeTopStories(unittest.TestCase):
    def _scrape(self, stories: dict[int, dict], extracted: dict[str, str | None], limit: int):
        with (
            patch.object(hackernews.requests, "get", side_effect=_fake_get(stories)),
            patch.object(hackernews.trafilatura, "fetch_url", side_effect=lambda url: url),
            patch.object(hackernews.trafilatura, "extract", side_effect=lambda page: extracted[page]),
        ):
            return hackernews.scrape_top_stories(limit=limit)

    def test_skips_stories_without_a_url(self):
        stories = {1: {"title": "Ask HN: x"}, 2: {"title": "Real", "url": "https://a.example/2", "by": "me"}}
        items = self._scrape(stories, {"https://a.example/2": LONG_TEXT}, limit=5)
        self.assertEqual([i.source_id for i in items], ["2"])

    def test_skips_pages_with_no_or_too_little_extracted_text(self):
        stories = {
            1: {"title": "Stub", "url": "https://a.example/1"},
            2: {"title": "Empty", "url": "https://a.example/2"},
            3: {"title": "Good", "url": "https://a.example/3"},
        }
        extracted = {
            "https://a.example/1": "Please enable JavaScript",
            "https://a.example/2": None,
            "https://a.example/3": LONG_TEXT,
        }
        items = self._scrape(stories, extracted, limit=5)
        self.assertEqual([i.title for i in items], ["Good"])

    def test_skipped_stories_do_not_count_toward_the_limit(self):
        stories = {i: {"title": f"S{i}", "url": f"https://a.example/{i}"} for i in range(1, 7)}
        extracted = {f"https://a.example/{i}": (LONG_TEXT if i % 2 == 0 else "stub") for i in range(1, 7)}
        items = self._scrape(stories, extracted, limit=2)
        self.assertEqual([i.source_id for i in items], ["2", "4"])

    def test_scanning_is_bounded(self):
        stories = {i: {"title": f"S{i}", "url": f"https://a.example/{i}"} for i in range(1, 50)}
        extracted = {f"https://a.example/{i}": "stub" for i in range(1, 50)}
        items = self._scrape(stories, extracted, limit=2)
        self.assertEqual(items, [])  # nothing usable, and it gave up after limit * multiplier candidates


if __name__ == "__main__":
    unittest.main()
