from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.rate_limit import limiter
from app.api.routes import ask, health, news, search

app = FastAPI(
    title="AI News API",
    description=(
        "Collects AI/tech news, indexes it with pgvector, and answers questions "
        "grounded strictly in the retrieved articles (RAG). This API is read-only "
        "at request time - scraping and LLM enrichment run out-of-band as a batch "
        "pipeline, never during a request."
    ),
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health.router)
app.include_router(news.router)
app.include_router(search.router)
app.include_router(ask.router)
