"""
App ORM model representing registered consuming applications.
"""

from sqlalchemy import Column, String, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class App(Base, TimestampMixin):
    """
    Represents a registered multi-tenant application.

    Attributes:
        id: Unique identifier string for the application (e.g. "ecommerce_web").
        name: Human-readable display name.
        api_key_hash: SHA-256 hash of the API key for secure authentication.
    """

    __tablename__ = "apps"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key_hash = Column(String, unique=True, nullable=False, index=True)

    # Dynamic relationship to files
    files = relationship("FileRecord", back_populates="app", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<App id={self.id!r} name={self.name!r}>"
