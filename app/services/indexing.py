"""Semantic indexing workflow: chunk articles, embed them, store the vectors."""

import tiktoken

from app.agents.embedding_agent import create_embedding
from app.database.connection import SessionLocal
from app.database.repository import get_unindexed_news_items, insert_news_chunks

CHUNK_TOKENS = 500
ENCODING = tiktoken.get_encoding("cl100k_base")


def _chunk_text(text: str, chunk_tokens: int = CHUNK_TOKENS) -> list[str]:
    """Split text into chunks of at most `chunk_tokens` tokens each."""
    tokens = ENCODING.encode(text)
    return [ENCODING.decode(tokens[i : i + chunk_tokens]) for i in range(0, len(tokens), chunk_tokens)]


def run_indexing() -> None:
    """Chunk and embed news items that have content but haven't been indexed yet."""
    db = SessionLocal()
    try:
        items = get_unindexed_news_items(db)
        for item in items:
            chunks = _chunk_text(item.content or "")
            embeddings = [create_embedding(chunk) for chunk in chunks]
            insert_news_chunks(db, item.id, chunks, embeddings)
    finally:
        db.close()


if __name__ == "__main__":
    run_indexing()
