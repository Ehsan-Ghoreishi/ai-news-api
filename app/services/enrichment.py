"""LLM enrichment workflow."""

from app.agents.news_agent import enrich_article
from app.database.connection import SessionLocal
from app.database.repository import get_unenriched_news_items, save_enrichment


def run_enrichment() -> None:
    """Read unenriched NewsItems from the database, enrich them, save results back."""
    db = SessionLocal()
    try:
        items = get_unenriched_news_items(db)
        for item in items:
            enrichment = enrich_article(item.title, item.content or "")
            save_enrichment(db, item.id, enrichment)
    finally:
        db.close()


if __name__ == "__main__":
    run_enrichment()
