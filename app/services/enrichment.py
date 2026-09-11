"""LLM enrichment workflow."""

import json
from pathlib import Path

from app.agents.news_agent import enrich_article
from app.schemas.news import NewsItem

RAW_DIR = Path("data/raw")
ENRICHED_DIR = Path("data/enriched")


def run_enrichment() -> None:
    """Read scraped NewsItems from data/raw/, enrich them, write results to data/enriched/."""
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

    for path in RAW_DIR.glob("*.json"):
        item = NewsItem.model_validate(json.loads(path.read_text()))

        enrichment = enrich_article(item.title, item.content or "")
        item.summary = enrichment.summary
        item.tags = enrichment.tags

        out_path = ENRICHED_DIR / path.name
        out_path.write_text(item.model_dump_json(indent=2))


if __name__ == "__main__":
    run_enrichment()
