"""The one canonical NewsItem schema."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class NewsItem(BaseModel):
    id: int | None  # database primary key; None before the row is inserted
    source: str  # name of the scraper/site this came from, e.g. "techcrunch"
    source_id: str  # the article's id/slug on the source site, for dedup
    title: str  # article headline
    url: HttpUrl  # link to the original article; validated as a real URL
    author: str | None  # article byline, if the source provides one
    content: str | None  # raw scraped article text/body
    scraped_at: datetime  # when our scraper fetched this item
    summary: str | None  # LLM-generated summary, filled in during enrichment
    tags: list[str] = []  # LLM-generated topic tags, filled in during enrichment


class ArticleEnrichment(BaseModel):
    summary: str  # LLM-generated summary text
    tags: list[str]  # LLM-generated topic tags
