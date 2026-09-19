# Project Journey

This is an honest account of how `ai-news-api` was actually built, based on
the real git history, not a cleaned-up retelling. It started as a weekly
learning project (the `week6/` directory name is a leftover from that
structure) and was later hardened into something worth putting in a
portfolio. Some things were broken along the way and got fixed later; this
doc says so.

## Week 1 — Project skeleton

The repo started as an empty skeleton: `pyproject.toml`, a `Dockerfile`, a
`docker-compose.yml` stub, and empty files for every module the eventual
architecture would need (`app/scrapers/`, `app/agents/`, `app/services/`,
`app/database/`, `app/api/routes/`). No logic yet - just the shape of the
thing, decided up front: scraping, LLM calls, database access, and the API
would live in separate folders and not import each other's internals.

## Week 2 — Scraping and enrichment, no database yet

First real code: a HackerNews scraper (`app/scrapers/hackernews.py`) that
returns `NewsItem` objects, and an enrichment agent that calls OpenAI's
structured-output API (`client.responses.parse`) to generate a summary and
tags for each article.

There was no database yet. `run_ingestion()` scraped stories and wrote each
one as a JSON file to `data/raw/`; `run_enrichment()` read those files back,
called the LLM, and wrote the enriched result to `data/enriched/`. It's a
slow, disk-based pipeline, but it let the scraping and LLM logic get built
and tested independently of any storage decision - a deliberate simplicity
trade-off, not an oversight.

There's also a `playground/01_first_call.py` script from this point:
literally the first exploratory call to the OpenAI API in this project,
first as plain text, then as a structured-output call. It's still in the
repo as a record of that first step.

## Week 3 — A real database and the first API routes

Postgres came in via `docker-compose.yml`, along with SQLAlchemy models
(`NewsItemModel`), a `connection.py` with a `get_db` FastAPI dependency, and
a `repository.py` layer for reads/writes. `run_ingestion` and
`run_enrichment` were rewired from JSON files to `insert_news_item` /
`get_unenriched_news_items` / `save_enrichment` calls against Postgres.

This is also where the API itself starts existing as a real service:
`/health/` and `/news/` (list + get-by-id), both read-only, matching the
principle that the API never scrapes or writes during a request - only the
batch pipeline does.

## Week 4 — pgvector and semantic search

The `docker-compose.yml` Postgres image was swapped for
`pgvector/pgvector:pg17` specifically for this step (there's a comment in
the compose file, still there today, noting the vector extension was "needed
in week 4"). This added:

- `NewsChunkModel`, with an HNSW index on the embedding column
  (`vector_ip_ops` for inner-product similarity)
- `app/services/indexing.py`: chunks article content with `tiktoken`
  (500-token chunks) and embeds each chunk via `text-embedding-3-small`
- `search_similar_chunks()` in the repository, using pgvector's
  `max_inner_product` operator
- the `/search/` endpoint: embed the query, return the top-k most similar
  chunks

At this point the pipeline was ingestion → enrichment → indexing, and the
API could do real semantic search - but there was no LLM-generated answer
yet, just ranked raw chunks.

## Week 5 — Actually deploying it

The original `Dockerfile` was:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
CMD ["python", "-m", "app.main"]
```

That doesn't actually start a server - `app/main.py` just defines the
FastAPI `app` object, there's no `uvicorn.run()` call anywhere in it. It
would have built, and then served nothing. Getting this onto Cloud Run
forced fixing it: install `uv`, sync dependencies into a venv with
`--frozen --no-dev`, and run `uvicorn app.main:app` with the port read from
Cloud Run's `$PORT` env var instead of hardcoded. The live URL was added to
the README right after this actually worked.

## Week 6 — The RAG pipeline and the first evaluation harness

This is where it became a RAG system rather than just semantic search:

- `app/agents/answer_agent.py`: given a question and a set of retrieved
  chunks, asks `gpt-4o-mini` to answer strictly from that context via a
  structured `GroundedAnswer { answer, supported }` output, explicitly
  instructed to say "Not enough information" and set `supported: false`
  rather than guess
- `POST /ask/`: embeds the question, retrieves chunks, calls the answer
  agent, and builds citations back to the source articles
- `week6/evaluations/`: a small harness (`questions.json`,
  `run_evaluation.py`, `scoring.py`) that hits a running `/ask/` endpoint
  with known questions and checks both retrieval (did it cite the right
  source article?) and answer correctness (number/boolean/text matching)

The original set was 10 questions, generated from the 5 articles indexed at
the time, and scored 100% end-to-end. That's a real result, but a 10-question
eval on 5 articles is a smoke test, not evidence of a robust system - see
below.

## Making it portfolio-ready

Everything above was the learning-project phase. What follows is a later,
deliberate pass to turn a working prototype into something that holds up to
scrutiny - done in one sitting, not spread over weeks, so it's listed
separately rather than folded into the week numbering above.

**The evaluation set was thin, and the corpus had already moved on.**
Re-running the harness meant first checking what was actually in the
database - and the local dev Postgres (via `docker-compose`) no longer
contained the 5 articles the original 10 questions were written against, because
the HackerNews scraper pulls whatever is *currently* trending, and the local
dev DB is not idempotent, it just gets whatever articles exist the next time
someone runs `run_ingestion()`. The production Supabase instance still had
the original articles (plus a few more accumulated since), so the expanded
30-question set - 27 fact-based questions across all 6 indexed articles with
real, retrievable content, plus 3 deliberately unanswerable questions to
check the API correctly declines instead of hallucinating - was generated
and run against production data, read-only, not invented.

Result: **29/30 (96.7%) end-to-end accuracy.** The one failure is a genuine
retrieval-recall miss, not a bug: for a question about a specific
percentage figure buried deep in one article, the top-5 retrieved chunks
didn't include the paragraph containing it, so the model answered from a
different, nearby percentage in the context it did get. That's a real,
useful signal about `limit=5` chunk retrieval on longer articles, and it's
reported honestly rather than fixed by rewriting the question to something
easier.

**There were no tests for the HTTP layer.** `tests/test_evaluation_scoring.py`
covered the scoring logic, but nothing exercised `/search/` or `/ask/` as
actual endpoints. `tests/test_api_routes.py` now does, using FastAPI's
`TestClient` with the database dependency overridden and every LLM/embedding
call mocked, so the suite runs in milliseconds and never touches production
Supabase or spends OpenAI credits.

**`/ask/` was public, unauthenticated, and uncapped.** Every call costs
OpenAI credits (one embedding + one `gpt-4o-mini` call). It's now rate
limited to 10 requests/minute per client IP via `slowapi`.

**The OpenAPI docs were structurally present but empty.** FastAPI generates
`/docs` for free, but every route lacked a summary or description, and the
Pydantic field "descriptions" in `app/schemas/news.py` were actually just
Python comments, invisible to Swagger UI. Routes now have real
summaries/descriptions and schemas have real examples pulled from actual
indexed articles.

**There was no CI.** A GitHub Actions workflow now runs the unit test suite
on every push. The evaluation harness is intentionally *not* a hard CI
requirement - it needs a real database and spends real API credits per run,
so it stays opt-in behind repo secrets rather than gating every push on
production infrastructure being reachable.

**Adding the rate limit broke the evaluation harness.** This surfaced
immediately when re-running `run_evaluation.py` one final time after all the
above changes: with 30 questions hitting `/ask/` back-to-back and no
authentication distinguishing the harness from any other caller, it tripped
its own 10-requests/minute limit partway through and failed with a 429. The
harness now backs off and retries after a rate-limit response instead of
treating it as fatal (`week6/evaluations/run_evaluation.py`), the same way
any well-behaved client hitting a public rate-limited API should. It's a
small thing, but it's a real example of two independently-reasonable
changes (protect a costly endpoint; write a thorough eval) interacting in a
way neither one alone would have caught.

## What's still rough

- The evaluation corpus is small. Production has 9 indexed articles, but 1
  (a Science.org piece on North Korean nuclear tests) never got any content
  scraped and has zero indexed chunks, and 2 more (an Android 17 Mastodon
  post, an Apple Xcode release-notes page) only indexed a JavaScript-required
  stub instead of real article text. That leaves 6 articles with real,
  retrievable content to write questions against. 96.7% on 30 questions is a
  meaningfully better signal than 100% on 10, but it's still not a large or
  continuously-refreshed benchmark.
- The local dev database and production database can silently diverge
  (see above) since ingestion isn't idempotent against a fixed article set.
  Nothing currently detects or prevents that.
- There's no authentication on any endpoint. Rate limiting bounds cost, it
  doesn't add access control.
