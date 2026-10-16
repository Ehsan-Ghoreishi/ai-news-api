"""LLM calls only."""

import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from dotenv import load_dotenv
from langfuse import observe
from openai import OpenAI

from app.schemas.news import GroundedAnswer

# Load .env before _observe_if_configured runs: it checks LANGFUSE_* at import
# time, and this module can be imported before app.database.connection (which
# also calls load_dotenv) depending on import order.
load_dotenv()

ANSWER_MODEL = "gpt-4o-mini"

client = OpenAI()


def _observe_if_configured(func: Callable) -> Callable:
    """Wrap with Langfuse tracing only when credentials are set.

    Keeps the app (and the test suite, which runs with no
    LANGFUSE_* env vars) fully functional without Langfuse -
    observability is additive, never a hard dependency.
    """
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        return observe()(func)
    return func


def _today_context() -> str:
    """Today's date, so the model never mistakes a date inside an article for the current one."""
    today = datetime.now(UTC).strftime("%A, %d %B %Y")
    return (
        f"Today's date is {today} (UTC). Dates mentioned inside articles are when those articles "
        "were written or when events happened; they are not today's date. Use today's date only "
        "for questions about the current date or relative time (today, this week, how long ago)."
    )


# 'concise' is the original, extraction-style prompt. The evaluation harness relies on it
# (it scores bare numbers / true-false exactly), so keep its behaviour stable.
CONCISE_INSTRUCTIONS = (
    "Answer only from the supplied context. Do not use outside knowledge. "
    "For a numeric question, return only the number and requested unit. "
    "For a true/false question, start the answer with 'true' or 'false'. "
    "If the context does not contain enough evidence, set supported to false "
    "and answer 'Not enough information'."
)

# 'detailed' is what a person asking a real question wants: a full answer, not a token.
DETAILED_INSTRUCTIONS = (
    "You answer questions about news articles. Use ONLY the supplied context; do not use outside "
    "knowledge, and never invent facts. "
    "Write a clear, helpful answer in complete sentences: give the direct answer first, then the "
    "key supporting details (names, numbers, reasons, caveats) found in the context. "
    "For a yes/no question, begin with 'Yes' or 'No' and then explain why. "
    "For an open or broad question (explain, summarize, compare, what's new), synthesize across "
    "all the relevant context items and mention the article titles when useful. "
    "Aim for 2-6 sentences; be longer only if the question genuinely needs it. "
    "If the context contains part of the answer, answer that part and say what is missing. "
    "If the context does not contain enough evidence to answer at all, set supported to false "
    "and answer 'Not enough information'. "
    "Set supported to true only if your answer is actually backed by the context."
)

GENERAL_KNOWLEDGE_INSTRUCTIONS = (
    "Answer the user's question helpfully and accurately in 2-5 sentences, using your general "
    "knowledge. If the question depends on recent events, live data (prices, scores, today's "
    "news) or private information you cannot know, say so plainly instead of guessing. "
    "Do not claim to have read any specific article."
)


@_observe_if_configured
def answer_from_context(
    question: str,
    contexts: list[str],
    style: Literal["detailed", "concise"] = "concise",
) -> GroundedAnswer:
    """Ask the LLM to answer a question strictly from the given context chunks.

    `style` defaults to 'concise' so existing callers (and the evaluation harness) keep
    the exact behaviour they were measured with; the API opts in to 'detailed'.
    """
    numbered_contexts = "\n\n".join(
        f"[{i}] {context}" for i, context in enumerate(contexts, start=1)
    )
    response = client.responses.parse(
        model=ANSWER_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    (DETAILED_INSTRUCTIONS if style == "detailed" else CONCISE_INSTRUCTIONS)
                    + " "
                    + _today_context()
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nContext:\n{numbered_contexts}",
            },
        ],
        text_format=GroundedAnswer,
    )
    if response.output_parsed is None:
        raise RuntimeError("OpenAI response did not include parsed GroundedAnswer output")
    return response.output_parsed


@_observe_if_configured
def answer_from_general_knowledge(question: str) -> str:
    """Answer from the model's own knowledge when the indexed articles have nothing relevant.

    The API labels this answer as unverified (answer_source='general_knowledge') and never
    attaches citations to it - it is NOT grounded in any article.
    """
    response = client.responses.create(
        model=ANSWER_MODEL,
        input=[
            {
                "role": "system",
                "content": GENERAL_KNOWLEDGE_INSTRUCTIONS + " " + _today_context(),
            },
            {"role": "user", "content": question},
        ],
    )
    text = response.output_text.strip()
    if not text:
        raise RuntimeError("OpenAI response did not include any text output")
    return text
