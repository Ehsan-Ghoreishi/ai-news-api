"""Ingestion workflow."""

from app.database.connection import SessionLocal
from app.database.repository import insert_news_item
from app.scrapers.hackernews import scrape_top_stories


def run_ingestion() -> None:
    """Scrape news items and store each one in the database, skipping duplicates."""
    items = scrape_top_stories()

    db = SessionLocal()
    try:
        for item in items:
            insert_news_item(db, item)
    finally:
        db.close()


if __name__ == "__main__":
    run_ingestion()
