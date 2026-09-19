"""Grounded question-answering HTTP endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.agents.answer_agent import answer_from_context
from app.agents.embedding_agent import create_embedding
from app.api.rate_limit import limiter
from app.database.connection import get_db
from app.database.repository import get_news_item, search_similar_chunks
from app.schemas.news import AnswerCitation, AskRequest, AskResponse

router = APIRouter(prefix="/ask", tags=["ask"])

# Each call costs OpenAI credits and this endpoint is public/unauthenticated,
# so cap it per client IP to bound cost and abuse.
ASK_RATE_LIMIT = "10/minute"


@router.post(
    "/",
    response_model=AskResponse,
    summary="Ask a grounded question over the indexed news corpus",
    description=(
        "Retrieves the most relevant chunks for the question via semantic search, then asks an "
        "LLM to answer strictly from that retrieved context - never from outside knowledge. If the "
        "retrieved evidence doesn't support a confident answer, `supported` is `false` and `answer` "
        "is `\"Not enough information\"` instead of a hallucinated guess.\n\n"
        f"Rate limited to {ASK_RATE_LIMIT.split('/')[0]} requests/minute per client IP, "
        "since each call spends OpenAI credits."
    ),
    responses={429: {"description": "Rate limit exceeded (10 requests/minute per client IP)."}},
)
@limiter.limit(ASK_RATE_LIMIT)
def ask_news(request: Request, ask_request: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    """Retrieve relevant news chunks and answer from that evidence only."""
    query_embedding = create_embedding(ask_request.question)
    results = search_similar_chunks(db, query_embedding, limit=ask_request.limit)
    if not results:
        return AskResponse(
            question=ask_request.question, answer="Not enough information", supported=False, citations=[]
        )

    grounded = answer_from_context(ask_request.question, [result.chunk_content for result in results])

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
    return AskResponse(
        question=ask_request.question, answer=grounded.answer, supported=grounded.supported, citations=citations
    )
