"""
File schemas for API requests, responses, and query parameters.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class UploadRequest(BaseModel):
    """Payload to request a presigned upload URL."""

    filename: str = Field(..., min_length=1, max_length=255, description="Original filename with extension")
    content_type: str = Field(..., min_length=3, max_length=128, description="MIME type of file (e.g. application/pdf)")
    owner_id: Optional[str] = Field(None, max_length=255, description="Optional end-user ID within the consuming app")


class UploadUrlResponse(BaseModel):
    """Response containing presigned S3 upload URL and public UUID."""

    upload_url: str = Field(..., description="Presigned S3 PUT URL valid for temporary direct binary upload")
    file_uuid: str = Field(..., description="Public UUID identifier of file record")
    expires_in_seconds: int = Field(300, description="Seconds until upload URL expires")


class ConfirmResponse(BaseModel):
    """Response for file upload verification."""

    file_uuid: str
    status: str
    size: int
    confirmed_at: datetime


class FileResponse(BaseModel):
    """Public file record metadata response schema."""

    file_uuid: str = Field(..., alias="uuid")
    s3_key: str
    original_filename: str
    app_id: str
    owner_id: Optional[str]
    content_type: Optional[str]
    size: Optional[int]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DownloadUrlResponse(BaseModel):
    """Response containing presigned S3 download URL."""

    download_url: str = Field(..., description="Presigned S3 GET URL")
    filename: str = Field(..., description="Original filename for download")
    expires_in_seconds: int = Field(..., description="Expiration window in seconds")


class FileListParams(BaseModel):
    """Query parameters for file listing with pagination and filtering."""

    owner_id: Optional[str] = None
    status: Optional[str] = "COMPLETED"
    page: int = Field(1, ge=1, description="Page number starting at 1")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
