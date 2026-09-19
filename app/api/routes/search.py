"""Semantic search HTTP endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.embedding_agent import create_embedding
from app.database.connection import get_db
from app.database.repository import search_similar_chunks
from app.schemas.news import SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "/",
    response_model=list[SearchResult],
    summary="Semantic search over indexed news chunks",
    description=(
        "Embeds `q` and returns the `limit` most similar chunks across all indexed news "
        "articles, ranked by similarity. Returns raw matching chunks with no LLM synthesis - "
        "use POST /ask/ for a synthesized, grounded answer instead."
    ),
)
def search(
    q: str = Query(description="Natural-language search query.", examples=["consistent hashing memory savings"]),
    limit: int = Query(default=5, ge=1, le=50, description="Max number of chunks to return."),
    db: Session = Depends(get_db),
) -> list[SearchResult]:
    embedding = create_embedding(q)
    return search_similar_chunks(db, embedding, limit=limit)
