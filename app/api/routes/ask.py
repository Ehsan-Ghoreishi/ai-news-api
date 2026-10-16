"""Grounded question-answering HTTP endpoint."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.agents.answer_agent import answer_from_context, answer_from_general_knowledge
from app.agents.embedding_agent import create_embedding
from app.api.rate_limit import limiter
from app.database.connection import get_db
from app.database.repository import get_news_item, search_similar_chunks
from app.schemas.news import (
    AnswerCitation,
    AskRequest,
    AskResponse,
    RelatedArticle,
    SearchResult,
)
from app.services.grounding import verified_citation_indices

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ask", tags=["ask"])

# Each call costs OpenAI credits and this endpoint is public/unauthenticated,
# so cap it per client IP to bound cost and abuse.
ASK_RATE_LIMIT = "10/minute"


NOT_ENOUGH_INFORMATION = "Not enough information"
MAX_RELATED_ARTICLES = 3


def _related_articles(results: list[SearchResult]) -> list[RelatedArticle]:
    """The closest distinct articles among the retrieved chunks (best chunk per article)."""
    best: dict[int, SearchResult] = {}
    for result in results:
        if result.news_item_id not in best or result.similarity > best[result.news_item_id].similarity:
            best[result.news_item_id] = result
    ranked = sorted(best.values(), key=lambda r: r.similarity, reverse=True)[:MAX_RELATED_ARTICLES]
    return [RelatedArticle(title=r.title, url=r.url, similarity=r.similarity) for r in ranked]


def _unsupported_response(ask_request: AskRequest, results: list[SearchResult]) -> AskResponse:
    """Build the response for a question the indexed articles can't answer.

    By default we still try to help: answer from the model's general knowledge, but label it
    clearly (answer_source='general_knowledge', supported=False, no citations) so nobody mistakes
    it for an article-backed answer. With allow_general_knowledge=False we decline instead.
    """
    related = _related_articles(results)
    if ask_request.allow_general_knowledge:
        return AskResponse(
            question=ask_request.question,
            answer=answer_from_general_knowledge(ask_request.question),
            supported=False,
            answer_source="general_knowledge",
            related_articles=related,
            citations=[],
        )
    return AskResponse(
        question=ask_request.question,
        answer=NOT_ENOUGH_INFORMATION,
        supported=False,
        answer_source="none",
        related_articles=related,
        citations=[],
    )


@router.post(
    "/",
    response_model=AskResponse,
    summary="Ask a grounded question over the indexed news corpus",
    description=(
        "Retrieves the most relevant chunks for the question via semantic search, then asks an "
        "LLM to answer strictly from that retrieved context, with citations. If the indexed "
        "articles don't contain the answer, `supported` is `false`: by default the model then "
        "answers from its general knowledge and the response is labelled "
        "`answer_source=\"general_knowledge\"` (unverified, no citations); with "
        "`allow_general_knowledge=false` it returns `\"Not enough information\"` instead.\n\n"
        "`style=\"detailed\"` (default) gives a full explanatory answer; `style=\"concise\"` "
        "returns just the bare answer.\n\n"
        f"Rate limited to {ASK_RATE_LIMIT.split('/')[0]} requests/minute per client IP, "
        "since each call spends OpenAI credits."
    ),
    responses={429: {"description": "Rate limit exceeded (10 requests/minute per client IP)."}},
)
@limiter.limit(ASK_RATE_LIMIT)
def ask_news(
    request: Request, ask_request: AskRequest, db: Session = Depends(get_db)  # noqa: B008  (FastAPI DI idiom)
) -> AskResponse:
    """Retrieve relevant news chunks and answer from that evidence only."""
    query_embedding = create_embedding(ask_request.question)
    results = search_similar_chunks(db, query_embedding, limit=ask_request.limit)
    if not results:
        return _unsupported_response(ask_request, results)

    if ask_request.style == "detailed":
        # Label each chunk with its article title so the model can name its sources.
        contexts = [f"Article: {result.title}\n{result.chunk_content}" for result in results]
    else:
        contexts = [result.chunk_content for result in results]
    grounded = answer_from_context(ask_request.question, contexts, style=ask_request.style)

    if not grounded.supported:
        return _unsupported_response(ask_request, results)

    # Do not trust `supported` on its own: the model must also quote the sentence that answers
    # the question, and that sentence must exist verbatim in a retrieved chunk. Otherwise the
    # answer is treated as unsupported (this is what blocks an answer about company A being
    # given for a question about company B).
    cited_indices = verified_citation_indices(
        grounded.evidence, grounded.used_context_indices, [r.chunk_content for r in results]
    )
    if cited_indices is None:
        logger.info("Rejecting answer: its evidence sentence is not in the retrieved chunks")
        return _unsupported_response(ask_request, results)
    cited_results = [results[i] for i in cited_indices]

    # Citations are only built for article-grounded answers (unsupported ones returned above),
    # and only for chunks that contain the verified evidence or that the model said it used.
    # SearchResult has no source_id, so we look each news item up to build the citation.
    # The lookup can miss (e.g. item deleted after indexing) - skip those rather than crash.
    citations = []
    for result in cited_results:
        news_item = get_news_item(db, result.news_item_id)
        if news_item is None:
            logger.warning("Skipping citation for missing news_item_id=%s", result.news_item_id)
            continue
        citations.append(
            AnswerCitation(
                news_item_id=result.news_item_id,
                source_id=news_item.source_id,
                title=result.title,
                url=result.url,
                chunk_content=result.chunk_content,
            )
        )
    return AskResponse(
        question=ask_request.question,
        answer=grounded.answer,
        supported=True,
        answer_source="articles",
        citations=citations,
    )
