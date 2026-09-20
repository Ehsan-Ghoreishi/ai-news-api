"""LLM calls only."""

from openai import OpenAI

from app.schemas.news import ArticleEnrichment

MODEL = "gpt-4o-mini"

client = OpenAI()


def enrich_article(title: str, content: str) -> ArticleEnrichment:
    """Ask the LLM for a short summary and topic tags for one article."""
    response = client.responses.parse(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": "You summarize AI news articles and extract topic tags.",
            },
            {
                "role": "user",
                "content": f"Title: {title}\n\nContent:\n{content}",
            },
        ],
        text_format=ArticleEnrichment,
    )
    if response.output_parsed is None:
        raise RuntimeError("OpenAI response did not include parsed ArticleEnrichment output")
    return response.output_parsed
