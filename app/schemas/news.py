"""The one canonical NewsItem schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class NewsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lets this validate directly from ORM objects

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


class SearchResult(BaseModel):
    news_item_id: int  # id of the article this chunk belongs to
    title: str  # article headline
    url: HttpUrl  # link to the original article
    chunk_content: str  # the matched chunk's text
    similarity: float  # similarity score of the chunk to the query


class AskRequest(BaseModel):
    question: str  # the user's natural-language question
    limit: int = 5  # max number of chunks to retrieve for grounding


class GroundedAnswer(BaseModel):
    answer: str  # LLM-generated answer text
    supported: bool  # whether the answer is actually backed by the retrieved chunks


class AnswerCitation(BaseModel):
    news_item_id: int  # id of the article this citation comes from
    source_id: str  # the article's id/slug on the source site
    title: str  # article headline
    url: HttpUrl  # link to the original article
    chunk_content: str  # the cited chunk's text


class AskResponse(BaseModel):
    question: str  # the original question asked
    answer: str  # LLM-generated answer text
    supported: bool  # whether the answer is actually backed by the retrieved chunks
    citations: list[AnswerCitation]  # chunks/articles used to support the answer
