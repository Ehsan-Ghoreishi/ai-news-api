"""Semantic search HTTP endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.embedding_agent import create_embedding
from app.database.connection import get_db
from app.database.repository import search_similar_chunks
from app.schemas.news import SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=list[SearchResult])
def search(q: str, limit: int = 5, db: Session = Depends(get_db)) -> list[SearchResult]:
    embedding = create_embedding(q)
    return search_similar_chunks(db, embedding, limit=limit)
