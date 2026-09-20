"""News HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.repository import get_all_news_items, get_news_item
from app.schemas.news import NewsItem

router = APIRouter(prefix="/news", tags=["news"])


@router.get(
    "/",
    response_model=list[NewsItem],
    summary="List recent news items",
    description="Returns the 50 most recently scraped news items, newest first. Read-only - never triggers scraping.",
)
def list_news(db: Session = Depends(get_db)) -> list[NewsItem]:  # noqa: B008  (FastAPI DI idiom)
    return get_all_news_items(db, limit=50)


@router.get(
    "/{item_id}",
    response_model=NewsItem,
    summary="Get a single news item",
    description="Fetch one news item by its database id.",
    responses={404: {"description": "No news item exists with the given id."}},
)
def read_news(item_id: int, db: Session = Depends(get_db)) -> NewsItem:  # noqa: B008  (FastAPI DI idiom)
    item = get_news_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="News item not found")
    return item
