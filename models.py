# models.py
"""
Database models for the File Service.

Defines the SQLAlchemy ORM models that represent the core entities:
- App: A consuming application registered with an API key.
- FileRecord: Metadata for a file stored in AWS S3.
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


class App(Base):
    """
    Represents a registered consuming application.

    Each app receives a unique API key used to authenticate requests.
    All files uploaded through this app are namespaced under its `id`,
    ensuring hard multi-tenant isolation at both the database and S3 layer.

    Attributes:
        id:      Unique identifier for the app (e.g. "ecommerce_web").
        name:    Human-readable display name (e.g. "E-Commerce Frontend").
        api_key: Secret key sent via the `x-api-key` header to authenticate.
    """

    __tablename__ = "apps"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False)

    # Relationship to access all files belonging to this app
    files = relationship("FileRecord", back_populates="app", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<App id={self.id!r} name={self.name!r}>"


class FileRecord(Base):
    """
    Metadata record for a file stored in AWS S3.

    Lifecycle:
        1. PENDING   → Created when the client requests a presigned upload URL.
        2. COMPLETED → Set after the client confirms upload and S3 verification passes.
        3. FAILED    → Set if S3 verification finds the object missing.

    Attributes:
        id:                Auto-incrementing primary key.
        s3_key:            Full S3 object key (e.g. "app_id/uuid-filename.pdf").
        original_filename: The sanitized original filename from the client.
        app_id:            Foreign key linking to the owning App.
        owner_id:          Optional end-user identifier within the consuming app.
        content_type:      MIME type (e.g. "application/pdf", "image/png").
        size:              File size in bytes, populated during upload confirmation.
        status:            Upload lifecycle state: PENDING | COMPLETED | FAILED.
        uploaded_at:       UTC timestamp when the record was created.
    """

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    s3_key = Column(String, unique=True, nullable=False)
    original_filename = Column(String, nullable=False)
    app_id = Column(String, ForeignKey("apps.id"), nullable=False)
    owner_id = Column(String, nullable=True)
    content_type = Column(String)
    size = Column(Integer, nullable=True)
    status = Column(String, default="PENDING", nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship back to the owning App
    app = relationship("App", back_populates="files")

    def __repr__(self) -> str:
        return (
            f"<FileRecord id={self.id} filename={self.original_filename!r} "
            f"status={self.status!r}>"
        )