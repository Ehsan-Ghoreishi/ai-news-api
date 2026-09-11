"""SQLAlchemy models."""

from datetime import datetime

from sqlalchemy import ARRAY, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class NewsItemModel(Base):
    """ORM model for the news_items table; mirrors the NewsItem schema."""

    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_source_source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String)
    source_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str | None] = mapped_column(String, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
