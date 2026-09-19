"""The one canonical NewsItem schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

_NEWS_ITEM_EXAMPLE = {
    "id": 8,
    "source": "hackernews",
    "source_id": "49758580",
    "title": "Saving another 100TB of RAM with math (and Rust)",
    "url": "https://blog.cloudflare.com/saving-100-tb-of-ram-with-math/",
    "author": None,
    "content": "Cloudflare operates at a scale so big that even after working here for years...",
    "scraped_at": "2026-09-18T12:00:00Z",
    "summary": (
        "Cloudflare optimized its memory usage by over 100TB through improvements "
        "in their consistent hashing algorithm used in the Pingora Backend Router."
    ),
    "tags": ["Cloudflare", "RAM optimization", "Consistent hashing", "Rust"],
}


class NewsItem(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # lets this validate directly from ORM objects
        json_schema_extra={"examples": [_NEWS_ITEM_EXAMPLE]},
    )

    id: int | None = Field(description="Database primary key; null before the row is inserted.")
    source: str = Field(description="Name of the scraper/site this came from, e.g. 'hackernews'.")
    source_id: str = Field(description="The article's id/slug on the source site, used for dedup.")
    title: str = Field(description="Article headline.")
    url: HttpUrl = Field(description="Link to the original article.")
    author: str | None = Field(description="Article byline, if the source provides one.")
    content: str | None = Field(description="Raw scraped article text/body.")
    scraped_at: datetime = Field(description="When our scraper fetched this item.")
    summary: str | None = Field(description="LLM-generated summary, filled in during enrichment.")
    tags: list[str] = Field(default=[], description="LLM-generated topic tags, filled in during enrichment.")


class ArticleEnrichment(BaseModel):
    summary: str = Field(description="LLM-generated summary text.")
    tags: list[str] = Field(description="LLM-generated topic tags.")


class SearchResult(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "news_item_id": 8,
                    "title": "Saving another 100TB of RAM with math (and Rust)",
                    "url": "https://blog.cloudflare.com/saving-100-tb-of-ram-with-math/",
                    "chunk_content": (
                        "This simple (if wordy) change reduces the amount of memory "
                        "used for consistent hashing by a whopping 25%!"
                    ),
                    "similarity": 0.83,
                }
            ]
        }
    )

    news_item_id: int = Field(description="Id of the article this chunk belongs to.")
    title: str = Field(description="Article headline.")
    url: HttpUrl = Field(description="Link to the original article.")
    chunk_content: str = Field(description="The matched chunk's text.")
    similarity: float = Field(description="Similarity score of the chunk to the query (higher is more similar).")


class AskRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "How much RAM did Cloudflare reclaim from its consistent-hashing changes?",
                    "limit": 5,
                }
            ]
        }
    )

    question: str = Field(description="The user's natural-language question.")
    limit: int = Field(default=5, ge=1, le=20, description="Max number of chunks to retrieve for grounding.")


class GroundedAnswer(BaseModel):
    answer: str = Field(description="LLM-generated answer text.")
    supported: bool = Field(description="Whether the answer is actually backed by the retrieved chunks.")


class AnswerCitation(BaseModel):
    news_item_id: int = Field(description="Id of the article this citation comes from.")
    source_id: str = Field(description="The article's id/slug on the source site.")
    title: str = Field(description="Article headline.")
    url: HttpUrl = Field(description="Link to the original article.")
    chunk_content: str = Field(description="The cited chunk's text.")


class AskResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "How much RAM did Cloudflare reclaim from its consistent-hashing changes?",
                    "answer": "100TB",
                    "supported": True,
                    "citations": [
                        {
                            "news_item_id": 8,
                            "source_id": "49758580",
                            "title": "Saving another 100TB of RAM with math (and Rust)",
                            "url": "https://blog.cloudflare.com/saving-100-tb-of-ram-with-math/",
                            "chunk_content": (
                                "That allowed us to reclaim more than 100TB of RAM globally, on top of "
                                "the 100TB of memory the DNS team was able to shed last month."
                            ),
                        }
                    ],
                }
            ]
        }
    )

    question: str = Field(description="The original question asked.")
    answer: str = Field(description="LLM-generated answer text, or 'Not enough information' if unsupported.")
    supported: bool = Field(description="Whether the answer is actually backed by the retrieved chunks.")
    citations: list[AnswerCitation] = Field(description="Chunks/articles used to support the answer.")
