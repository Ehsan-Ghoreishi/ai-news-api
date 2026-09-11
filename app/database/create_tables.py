"""Creates all tables. Run with: python -m app.database.create_tables"""

from app.database.connection import Base, engine
from app.database.models import NewsItemModel  # noqa: F401  (registers the table with Base)

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Tables created.")
