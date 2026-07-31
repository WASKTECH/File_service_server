"""
Business logic service orchestrating File metadata and S3 storage operations.
"""

import uuid
import math
from pathlib import Path
from typing import Tuple, List, Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.core.exceptions import (
    FileNotFoundError,
    InvalidFileTypeError,
    AppBaseException,
)
from app.models.app_model import App
from app.models.file_record import FileRecord, FileStatus
from app.repositories.file_repository import FileRepository
from app.services.s3_service import S3Service
from app.schemas.file_schemas import (
    UploadRequest,
    UploadUrlResponse,
    ConfirmResponse,
    DownloadUrlResponse,
    FileResponse,
)
from app.schemas.common import PaginatedData, PaginationMeta


class FileService:
    """Core domain service for file upload, confirmation, listing, and deletion."""

    def __init__(self, file_repo: FileRepository, s3_service: S3Service):
        self.file_repo = file_repo
        self.s3_service = s3_service

    def request_upload_url(self, app: App, payload: UploadRequest) -> UploadUrlResponse:
        """
        Validate upload request and issue a presigned S3 PUT URL.

        Steps:
        1. Sanitize filename.
        2. Validate content-type against allowed whitelist (if configured).
        3. Generate UUIDv4 for public file identity and s3_key namespace.
        4. Generate S3 presigned PUT URL.
        5. Persist FileRecord with PENDING status in DB.
        """
        # 1. Sanitize filename to prevent path traversal
        safe_filename = Path(payload.filename).name
        if not safe_filename:
            raise AppBaseException(
                message="Invalid filename provided.",
                code="INVALID_FILENAME",
                status_code=400,
            )

        # 2. Content-type validation
        if settings.ALLOWED_MIME_TYPES and payload.content_type not in settings.ALLOWED_MIME_TYPES:
            raise InvalidFileTypeError(payload.content_type)

        # 3. Key formatting & UUID generation
        file_uuid = str(uuid.uuid4())
        s3_key = f"{app.id}/{file_uuid}-{safe_filename}"

        # 4. Generate S3 Presigned Upload URL
        expiration = settings.S3_PRESIGNED_UPLOAD_EXPIRATION
        upload_url = self.s3_service.generate_presigned_upload_url(
            key=s3_key,
            content_type=payload.content_type,
            expires_in=expiration,
        )

        # 5. DB Persistence
        self.file_repo.create(
            uuid_str=file_uuid,
            s3_key=s3_key,
            original_filename=safe_filename,
            app_id=app.id,
            owner_id=payload.owner_id,
            content_type=payload.content_type,
        )

        return UploadUrlResponse(
            upload_url=upload_url,
            file_uuid=file_uuid,
            expires_in_seconds=expiration,
        )

    def confirm_upload(self, app: App, file_uuid: str) -> ConfirmResponse:
        """
        Confirm file upload by querying S3 head_object.

        Updates file status to COMPLETED and records byte size.
        """
        record = self.file_repo.get_by_uuid_and_app(uuid_str=file_uuid, app_id=app.id)
        if not record:
            raise FileNotFoundError()

        # Check S3 object metadata
        head = self.s3_service.head_object(record.s3_key)
        if not head:
            self.file_repo.update_status(record, FileStatus.FAILED.value)
            raise AppBaseException(
                message="File upload verification failed: Object not found in S3 bucket.",
                code="UPLOAD_VERIFICATION_FAILED",
                status_code=400,
            )

        size = head.get("ContentLength", 0)

        # Enforce file size limit check
        if settings.MAX_FILE_SIZE_BYTES and size > settings.MAX_FILE_SIZE_BYTES:
            self.file_repo.update_status(record, FileStatus.FAILED.value, size=size)
            self.s3_service.delete_object(record.s3_key)
            raise AppBaseException(
                message=f"Uploaded file size ({size} bytes) exceeds maximum limit ({settings.MAX_FILE_SIZE_BYTES} bytes).",
                code="FILE_TOO_LARGE",
                status_code=400,
            )

        updated_record = self.file_repo.update_status(record, FileStatus.COMPLETED.value, size=size)

        return ConfirmResponse(
            file_uuid=updated_record.uuid,
            status=updated_record.status,
            size=updated_record.size or 0,
            confirmed_at=updated_record.updated_at,
        )

    def get_file(self, app: App, file_uuid: str) -> FileResponse:
        """Retrieve single file metadata by public UUID."""
        record = self.file_repo.get_by_uuid_and_app(uuid_str=file_uuid, app_id=app.id)
        if not record:
            raise FileNotFoundError()
        return FileResponse.model_validate(record)

    def get_download_url(self, app: App, file_uuid: str, expires_in: Optional[int] = None) -> DownloadUrlResponse:
        """Generate presigned download URL for COMPLETED file."""
        record = self.file_repo.get_by_uuid_and_app(uuid_str=file_uuid, app_id=app.id)
        if not record:
            raise FileNotFoundError()

        if record.status != FileStatus.COMPLETED.value:
            raise AppBaseException(
                message=f"File is not ready for download (current status: {record.status})",
                code="FILE_NOT_READY",
                status_code=400,
            )

        expiration = expires_in or settings.S3_PRESIGNED_DOWNLOAD_EXPIRATION
        download_url = self.s3_service.generate_presigned_download_url(
            key=record.s3_key,
            original_filename=record.original_filename,
            expires_in=expiration,
        )

        return DownloadUrlResponse(
            download_url=download_url,
            filename=record.original_filename,
            expires_in_seconds=expiration,
        )

    def list_files(
        self,
        app: App,
        owner_id: Optional[str] = None,
        status: Optional[str] = "COMPLETED",
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedData[FileResponse]:
        """Query files with multi-tenant filtering and page pagination."""
        items, total = self.file_repo.list_files(
            app_id=app.id,
            owner_id=owner_id,
            status=status,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        file_responses = [FileResponse.model_validate(f) for f in items]

        meta = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

        return PaginatedData(items=file_responses, pagination=meta)

    def delete_file(self, app: App, file_uuid: str) -> None:
        """Delete file from S3 and mark record as soft-deleted in DB."""
        record = self.file_repo.get_by_uuid_and_app(uuid_str=file_uuid, app_id=app.id)
        if not record:
            raise FileNotFoundError()

        # Delete from S3 (log warning if fails)
        self.s3_service.delete_object(record.s3_key)

        # Soft delete DB record
        self.file_repo.soft_delete(record)
