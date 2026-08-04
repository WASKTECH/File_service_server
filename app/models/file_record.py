"""
FileRecord ORM model representing metadata for files stored in AWS S3.
"""

import enum
import uuid

from sqlalchemy import BigInteger, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class FileStatus(str, enum.Enum):
    """File upload lifecycle states."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileRecord(Base, TimestampMixin, SoftDeleteMixin):
    """
    File metadata ORM model.

    Attributes:
        id: Auto-incrementing internal integer primary key.
        uuid: Public UUID string (UUIDv4) preventing identifier enumeration.
        s3_key: Full AWS S3 object key (e.g., "{app_id}/{uuid}-{safe_filename}").
        original_filename: Sanitized original file name.
        app_id: Foreign key referencing the owning multi-tenant App.
        owner_id: End-user identifier within the consuming app.
        content_type: Verified MIME type.
        size: File size in bytes (populated on confirm).
        status: Upload status ("PENDING", "COMPLETED", "FAILED").
    """

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    s3_key = Column(String(512), unique=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(String(255), nullable=True, index=True)
    content_type = Column(String(128), nullable=True)
    size = Column(BigInteger, nullable=True)
    status = Column(String(20), default=FileStatus.PENDING.value, nullable=False, index=True)

    # Relationships
    app = relationship("App", back_populates="files")

    # Composite indexes for high-performance multi-tenant querying
    __table_args__ = (
        Index("ix_files_app_status", "app_id", "status"),
        Index("ix_files_app_owner", "app_id", "owner_id"),
        Index("ix_files_app_created", "app_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<FileRecord uuid={self.uuid} filename={self.original_filename!r} "
            f"status={self.status!r} app_id={self.app_id!r}>"
        )
