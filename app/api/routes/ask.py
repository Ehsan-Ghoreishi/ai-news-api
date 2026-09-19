"""Grounded question-answering HTTP endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.answer_agent import answer_from_context
from app.agents.embedding_agent import create_embedding
from app.database.connection import get_db
from app.database.repository import get_news_item, search_similar_chunks
from app.schemas.news import AnswerCitation, AskRequest, AskResponse

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("/", response_model=AskResponse)
def ask_news(request: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    """Retrieve relevant news chunks and answer from that evidence only."""
    query_embedding = create_embedding(request.question)
    results = search_similar_chunks(db, query_embedding, limit=request.limit)
    if not results:
        return AskResponse(question=request.question, answer="Not enough information", supported=False, citations=[])

    grounded = answer_from_context(request.question, [result.chunk_content for result in results])

    # SearchResult has no source_id, so we look each news item up to build the citation.
    citations = [
        AnswerCitation(
            news_item_id=result.news_item_id,
            source_id=get_news_item(db, result.news_item_id).source_id,
            title=result.title,
            url=result.url,
            chunk_content=result.chunk_content,
        )
        for result in results
    ]
    return AskResponse(question=request.question, answer=grounded.answer, supported=grounded.supported, citations=citations)
