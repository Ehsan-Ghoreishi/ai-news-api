"""Scrapers that fetch external data and return NewsItem objects."""

import os
from datetime import UTC, datetime

import requests
import trafilatura

from app.schemas.news import NewsItem

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

# The index is what /ask/ can answer from, so a tiny corpus means most questions come back
# "not enough information". 30 per run keeps the weekly job cheap (a few cents of embeddings
# and enrichment) while giving the Q&A real coverage. Override with SCRAPE_LIMIT.
DEFAULT_SCRAPE_LIMIT = int(os.environ.get("SCRAPE_LIMIT", "30"))

# Pages that need JavaScript, paywalls and PDFs often extract to a few words of boilerplate.
# Indexing those only adds noise to retrieval, so skip anything shorter than this.
MIN_CONTENT_CHARS = 500

# Skipped stories (no url / no usable text) don't count toward `limit`, so look past it - but
# bounded, so one bad day of top stories can't turn into hundreds of slow page fetches.
MAX_CANDIDATES_MULTIPLIER = 3


def scrape_top_stories(limit: int = DEFAULT_SCRAPE_LIMIT) -> list[NewsItem]:
    """Fetch the top HN stories and return them as NewsItems with extracted article text."""
    story_ids = requests.get(TOP_STORIES_URL).json()

    items: list[NewsItem] = []
    for story_id in story_ids[: limit * MAX_CANDIDATES_MULTIPLIER]:
        if len(items) >= limit:
            break

        story = requests.get(ITEM_URL.format(item_id=story_id)).json()
        url = story.get("url")
        if not url:  # self/"Ask HN" posts have no external url; skip them
            continue

        downloaded = trafilatura.fetch_url(url)
        content = trafilatura.extract(downloaded) if downloaded else None
        if not content or len(content) < MIN_CONTENT_CHARS:
            continue

        items.append(
            NewsItem(
                id=None,
                source="hackernews",
                source_id=str(story_id),
                title=story.get("title", ""),
                url=url,
                author=story.get("by"),
                content=content,
                scraped_at=datetime.now(UTC),
                summary=None,
                tags=[],
            )
        )

    return items


if __name__ == "__main__":
    for item in scrape_top_stories():
        print(item.title)
