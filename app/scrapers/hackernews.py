"""Scrapers that fetch external data and return NewsItem objects."""

from datetime import datetime, timezone

import requests
import trafilatura

from app.schemas.news import NewsItem

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"


def scrape_top_stories(limit: int = 5) -> list[NewsItem]:
    """Fetch the top HN stories and return them as NewsItems with extracted article text."""
    story_ids = requests.get(TOP_STORIES_URL).json()

    items: list[NewsItem] = []
    for story_id in story_ids:
        if len(items) >= limit:
            break

        story = requests.get(ITEM_URL.format(item_id=story_id)).json()
        url = story.get("url")
        if not url:  # self/"Ask HN" posts have no external url; skip them
            continue

        downloaded = trafilatura.fetch_url(url)
        content = trafilatura.extract(downloaded) if downloaded else None

        items.append(
            NewsItem(
                id=None,
                source="hackernews",
                source_id=str(story_id),
                title=story.get("title", ""),
                url=url,
                author=story.get("by"),
                content=content,
                scraped_at=datetime.now(timezone.utc),
                summary=None,
                tags=[],
            )
        )

    return items


if __name__ == "__main__":
    for item in scrape_top_stories():
        print(item.title)
