"""
Backwards-compatible bridge for app.db.session.
"""

from app.db.session import engine, SessionLocal, get_db_session as get_db

__all__ = ["engine", "SessionLocal", "get_db"]