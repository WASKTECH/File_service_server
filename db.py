# db.py
"""
Database connection and session management.

Creates the SQLAlchemy engine from the DATABASE_URL environment variable
and provides a dependency-injectable session generator for FastAPI routes.

Supported database URLs:
    - PostgreSQL: postgresql://user:password@host:5432/dbname
    - SQLite:     sqlite:///./local.db  (for local development)
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Please configure it in your .env file."
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy database session.

    Yields a session and ensures it is closed after the request completes,
    regardless of whether the request succeeded or raised an exception.

    Usage:
        @app.get("/example")
        def example_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()