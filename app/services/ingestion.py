"""Ingestion workflow."""

from pathlib import Path

from app.scrapers.hackernews import scrape_top_stories

RAW_DIR = Path("data/raw")


def run_ingestion() -> None:
    """Scrape news items and save each one as its own JSON file in data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    items = scrape_top_stories()
    for item in items:
        path = RAW_DIR / f"{item.source}_{item.source_id}.json"
        path.write_text(item.model_dump_json(indent=2))


if __name__ == "__main__":
    run_ingestion()
