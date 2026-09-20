"""LLM calls only."""

from openai import OpenAI

from app.schemas.news import GroundedAnswer

ANSWER_MODEL = "gpt-4o-mini"

client = OpenAI()

INSTRUCTIONS = (
    "Answer only from the supplied context. Do not use outside knowledge. "
    "For a numeric question, return only the number and requested unit. "
    "For a true/false question, start the answer with 'true' or 'false'. "
    "If the context does not contain enough evidence, set supported to false "
    "and answer 'Not enough information'."
)


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
