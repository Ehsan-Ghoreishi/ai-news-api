"""LLM calls only."""

import os
from collections.abc import Callable

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


INSTRUCTIONS = (
    "Answer only from the supplied context. Do not use outside knowledge. "
    "For a numeric question, return only the number and requested unit. "
    "For a true/false question, start the answer with 'true' or 'false'. "
    "If the context does not contain enough evidence, set supported to false "
    "and answer 'Not enough information'."
)


@_observe_if_configured
def answer_from_context(question: str, contexts: list[str]) -> GroundedAnswer:
    """Ask the LLM to answer a question strictly from the given context chunks."""
    numbered_contexts = "\n\n".join(
        f"[{i}] {context}" for i, context in enumerate(contexts, start=1)
    )
    response = client.responses.parse(
        model=ANSWER_MODEL,
        input=[
            {
                "role": "system",
                "content": INSTRUCTIONS,
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
