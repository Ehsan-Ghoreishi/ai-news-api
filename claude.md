# Project
AI News API: collects AI news, normalizes it into one NewsItem schema,
enriches it with an LLM, stores it in PostgreSQL, serves it via FastAPI.

# Workflow
External Sources → Scrapers → Normalization → LLM Enrichment → PostgreSQL → FastAPI
The batch pipeline WRITES to PostgreSQL. The API only READS from it.

# Tech
Python 3.11+, uv, Pydantic, OpenAI API, SQLAlchemy, PostgreSQL (pgvector), FastAPI, Docker

# Structure
app/main.py            FastAPI entry point
app/pipeline.py        runs ingestion → enrichment (→ indexing)
app/api/routes/        HTTP endpoints (news.py, health.py)
app/scrapers/          fetch external data, return NewsItem objects
app/agents/            LLM calls only
app/services/          workflows: ingestion.py, enrichment.py
app/database/          connection, models, repository
app/schemas/news.py    the one canonical NewsItem

# Principles
- Keep it simple. Build incrementally, one tested piece at a time.
- One NewsItem schema shared everywhere.
- Scraping, LLM, database and API logic stay in separate folders.
- The API never scrapes during a request.
- I am learning: explain non-obvious code briefly in comments.
