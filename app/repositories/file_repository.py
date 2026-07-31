"""
Repository for FileRecord database queries and updates.
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.file_record import FileRecord, FileStatus


class FileRepository:
    """Encapsulates data access and persistence for FileRecords."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        uuid_str: str,
        s3_key: str,
        original_filename: str,
        app_id: str,
        owner_id: Optional[str],
        content_type: str,
    ) -> FileRecord:
        """Create a new FileRecord with PENDING status."""
        record = FileRecord(
            uuid=uuid_str,
            s3_key=s3_key,
            original_filename=original_filename,
            app_id=app_id,
            owner_id=owner_id,
            content_type=content_type,
            status=FileStatus.PENDING.value,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_uuid_and_app(self, uuid_str: str, app_id: str) -> Optional[FileRecord]:
        """Fetch active (non-deleted) FileRecord matching UUID and tenant app_id."""
        return (
            self.db.query(FileRecord)
            .filter(
                FileRecord.uuid == uuid_str,
                FileRecord.app_id == app_id,
                FileRecord.is_deleted == False,
            )
            .first()
        )

    def list_files(
        self,
        app_id: str,
        owner_id: Optional[str] = None,
        status: Optional[str] = "COMPLETED",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[FileRecord], int]:
        """
        Query files for an app with filtering and pagination.

        Returns tuple of (list_of_records, total_count).
        """
        query = self.db.query(FileRecord).filter(
            FileRecord.app_id == app_id,
            FileRecord.is_deleted == False,
        )

        if owner_id:
            query = query.filter(FileRecord.owner_id == owner_id)
        if status and status.upper() != "ALL":
            query = query.filter(FileRecord.status == status.upper())

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(FileRecord.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def update_status(self, record: FileRecord, status: str, size: Optional[int] = None) -> FileRecord:
        """Update file upload status and byte size."""
        record.status = status
        if size is not None:
            record.size = size
        self.db.commit()
        self.db.refresh(record)
        return record

    def soft_delete(self, record: FileRecord) -> None:
        """Perform soft delete on record."""
        record.soft_delete()
        self.db.commit()
