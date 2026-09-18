"""Creates all tables. Run with: python -m app.database.create_tables"""

from sqlalchemy import text

from app.database.connection import Base, engine
from app.database.models import NewsChunkModel, NewsItemModel  # noqa: F401  (registers the tables with Base)

if __name__ == "__main__":
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    print("Tables created.")
