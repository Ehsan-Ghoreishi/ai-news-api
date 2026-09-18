"""LLM calls only."""

from openai import OpenAI

MODEL = "text-embedding-3-small"

client = OpenAI()


def create_embedding(text: str) -> list[float]:
    """Embed a chunk of text into a 1536-dim vector."""
    response = client.embeddings.create(model=MODEL, input=text)
    return response.data[0].embedding
