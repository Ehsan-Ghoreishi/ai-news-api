# Project
AI News API: scrapes AI/tech news (Hacker News), enriches it with an LLM, chunks and embeds
it into PostgreSQL + pgvector, and serves search and grounded question answering via FastAPI.

# Workflow
Scrapers -> Ingestion -> LLM enrichment -> Chunk + embed (pgvector) -> FastAPI
The batch pipeline (app/pipeline.py) WRITES to PostgreSQL. The API only READS from it;
POST /ask/ is the only route that calls an LLM during a request.
In production the pipeline runs weekly (Cloud Run Job triggered by Cloud Scheduler, Mondays).

# Tech
Python 3.11+, uv, Pydantic, OpenAI API (gpt-4o-mini, text-embedding-3-small), SQLAlchemy,
PostgreSQL + pgvector, FastAPI, slowapi, Langfuse (optional), Docker, Google Cloud Run,
Streamlit (frontend only).

# Structure
app/main.py             FastAPI entry point
app/pipeline.py         batch pipeline: ingestion -> enrichment -> indexing
app/api/routes/         HTTP endpoints: health, news, search, ask
app/scrapers/           fetch external data, return NewsItem objects
app/agents/             LLM calls only (answer, embedding, enrichment)
app/services/           workflows: ingestion.py, enrichment.py, indexing.py
app/database/           connection, models, repository, create_tables
app/schemas/news.py     the canonical schemas (NewsItem and API models)
evaluation/             evaluation harness, question sets, results/
frontend/               Streamlit demo (own requirements.txt)
tests/                  unit tests (LLM and database are mocked)
docs/                   development history, images

# Commands
uv run pytest
uv run ruff check .
uv run mypy app/
uv run uvicorn app.main:app --reload --port 8001
uv run python -m app.pipeline
uv run python -m evaluation.run_evaluation --base-url <API_URL>

# Principles
- Keep it simple. Build incrementally, one tested piece at a time.
- One NewsItem schema shared everywhere.
- Scraping, LLM, database and API logic stay in separate folders.
- The API never scrapes during a request.
- Explain non-obvious code briefly in comments.
- Evaluation results are tied to the corpus at the time of the run. Never edit committed
  result files; every run gets its own file name.
- Never commit .env or API keys.
