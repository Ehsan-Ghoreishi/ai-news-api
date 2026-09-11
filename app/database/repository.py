"""Database repository (read/write access)."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.models import NewsItemModel
from app.schemas.news import ArticleEnrichment, NewsItem


def _to_news_item(model: NewsItemModel) -> NewsItem:
    return NewsItem.model_validate(model, from_attributes=True)


def insert_news_item(db: Session, item: NewsItem) -> None:
    """Insert a scraped item; silently skip it if (source, source_id) already exists."""
    stmt = (
        insert(NewsItemModel)
        .values(
            source=item.source,
            source_id=item.source_id,
            title=item.title,
            url=str(item.url),
            author=item.author,
            content=item.content,
            scraped_at=item.scraped_at,
            summary=item.summary,
            tags=item.tags,
        )
        .on_conflict_do_nothing(index_elements=["source", "source_id"])
    )
    db.execute(stmt)
    db.commit()


def get_unenriched_news_items(db: Session) -> list[NewsItem]:
    """Return items that have not been enriched yet (no summary)."""
    models = db.scalars(select(NewsItemModel).where(NewsItemModel.summary.is_(None))).all()
    return [_to_news_item(m) for m in models]


def save_enrichment(db: Session, item_id: int, enrichment: ArticleEnrichment) -> None:
    """Write the LLM-generated summary and tags back onto a news item."""
    model = db.get(NewsItemModel, item_id)
    if model is None:
        return
    model.summary = enrichment.summary
    model.tags = enrichment.tags
    db.commit()


def get_all_news_items(db: Session, limit: int = 100) -> list[NewsItem]:
    """Return the most recently scraped news items, newest first."""
    models = db.scalars(
        select(NewsItemModel).order_by(NewsItemModel.scraped_at.desc()).limit(limit)
    ).all()
    return [_to_news_item(m) for m in models]


def get_news_item(db: Session, item_id: int) -> NewsItem | None:
    """Fetch a single news item by primary key."""
    model = db.get(NewsItemModel, item_id)
    return _to_news_item(model) if model else None
