# main.py
"""
File Service API — Centralized file management built on AWS S3.

This FastAPI application provides a REST API for uploading, downloading,
and managing files across multiple consuming applications. Files are stored
in AWS S3 using presigned URLs to offload bandwidth from the API server.

Architecture:
    - Clients request a presigned URL, upload directly to S3, then confirm.
    - Each consuming app is isolated by API key and namespaced S3 key prefixes.
    - File metadata (filename, size, status) is tracked in a relational database.

Endpoints:
    POST   /files/upload-url          → Request a presigned S3 upload URL.
    POST   /files/{file_id}/confirm   → Confirm upload and verify S3 object.
    GET    /files                     → List files with filtering and pagination.
    GET    /files/{file_id}           → Retrieve file metadata.
    GET    /files/{file_id}/download-url → Generate a presigned S3 download URL.
    DELETE /files/{file_id}           → Delete file from S3 and database.
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from pathlib import Path
from contextlib import asynccontextmanager
import uuid
from botocore.exceptions import ClientError

from s3_client import s3, BUCKET
from auth import get_current_app
from db import get_db, engine
from models import Base, App, FileRecord


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup if they don't already exist."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="File Service API",
    description="Centralized file management service built on AWS S3.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class UploadRequest(BaseModel):
    """Request body for initiating a file upload."""

    filename: str
    content_type: str
    owner_id: str | None = None


class FileResponse(BaseModel):
    """Standard response schema for file metadata."""

    id: int
    s3_key: str
    original_filename: str
    app_id: str
    owner_id: str | None
    content_type: str | None
    size: int | None
    status: str
    uploaded_at: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/files/upload-url", summary="Request a presigned upload URL")
def get_upload_url(
    req: UploadRequest,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    """
    Generate a presigned S3 PUT URL for direct file upload.

    The client uses the returned URL to upload the file binary directly
    to S3, bypassing this server entirely. A database record is created
    with status PENDING until the upload is confirmed.

    Returns:
        upload_url: Presigned S3 PUT URL (valid for 5 minutes).
        file_id:    Database ID to use when confirming the upload.
    """
    # Sanitize filename to prevent path traversal attacks
    safe_filename = Path(req.filename).name
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Namespace the S3 key by app_id for hard multi-tenant isolation
    key = f"{current_app.id}/{uuid.uuid4()}-{safe_filename}"

    presigned_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET, "Key": key, "ContentType": req.content_type},
        ExpiresIn=300,
    )

    record = FileRecord(
        s3_key=key,
        original_filename=safe_filename,
        app_id=current_app.id,
        owner_id=req.owner_id,
        content_type=req.content_type,
        status="PENDING",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"upload_url": presigned_url, "file_id": record.id}


@app.post("/files/{file_id}/confirm", summary="Confirm a completed upload")
def confirm_upload(
    file_id: int,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    """
    Verify that a file was successfully uploaded to S3.

    Calls S3 head_object to check the file exists and retrieves its size.
    On success, the record status is set to COMPLETED. If the file is not
    found in S3, the status is set to FAILED.

    Returns:
        status:  "COMPLETED" on success.
        file_id: The confirmed file's database ID.
        size:    File size in bytes as reported by S3.
    """
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id,
        FileRecord.app_id == current_app.id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="File record not found")

    try:
        head = s3.head_object(Bucket=BUCKET, Key=record.s3_key)
        record.size = head.get("ContentLength")
        record.status = "COMPLETED"
        db.commit()
        db.refresh(record)
        return {
            "status": "COMPLETED",
            "file_id": record.id,
            "size": record.size,
        }
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchKey", "NotFound"):
            record.status = "FAILED"
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="File upload verification failed: file not found in S3.",
            )
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")


@app.get("/files", summary="List files")
def list_files(
    owner_id: str | None = Query(None, description="Filter by end-user ID"),
    status: str | None = Query(
        "COMPLETED",
        description="Filter by status: PENDING, COMPLETED, FAILED, or ALL",
    ),
    limit: int = Query(50, ge=1, le=200, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    """
    List files belonging to the authenticated application.

    Supports filtering by owner_id and status, with limit/offset pagination.
    By default, only COMPLETED files are returned. Pass status=ALL to
    include PENDING and FAILED records.
    """
    query = db.query(FileRecord).filter(FileRecord.app_id == current_app.id)

    if owner_id:
        query = query.filter(FileRecord.owner_id == owner_id)
    if status and status.upper() != "ALL":
        query = query.filter(FileRecord.status == status.upper())

    total = query.count()
    items = query.order_by(FileRecord.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "files": [
            {
                "id": f.id,
                "s3_key": f.s3_key,
                "original_filename": f.original_filename,
                "owner_id": f.owner_id,
                "content_type": f.content_type,
                "size": f.size,
                "status": f.status,
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
            }
            for f in items
        ],
    }


@app.get("/files/{file_id}", summary="Get file metadata")
def get_file_metadata(
    file_id: int,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    """
    Retrieve metadata for a single file.

    Returns all stored metadata without generating a download URL.
    Use the /files/{file_id}/download-url endpoint to get a presigned link.
    """
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id,
        FileRecord.app_id == current_app.id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "id": record.id,
        "s3_key": record.s3_key,
        "original_filename": record.original_filename,
        "app_id": record.app_id,
        "owner_id": record.owner_id,
        "content_type": record.content_type,
        "size": record.size,
        "status": record.status,
        "uploaded_at": record.uploaded_at.isoformat() if record.uploaded_at else None,
    }


@app.get("/files/{file_id}/download-url", summary="Generate a presigned download URL")
def get_download_url(
    file_id: int,
    expires_in: int = Query(
        300, ge=60, le=86400,
        description="URL expiration time in seconds (default: 5 min, max: 24 hrs)",
    ),
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    """
    Generate a temporary presigned S3 GET URL for downloading a file.

    Only files with status COMPLETED can be downloaded. The URL expires
    after the specified number of seconds (default 300s / 5 minutes).
    """
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id,
        FileRecord.app_id == current_app.id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if record.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"File is not ready for download (current status: {record.status})",
        )

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": record.s3_key},
        ExpiresIn=expires_in,
    )
    return {"download_url": url, "filename": record.original_filename}


@app.delete("/files/{file_id}", summary="Delete a file")
def delete_file(
    file_id: int,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    """
    Delete a file from both S3 and the database.

    The database record is removed even if the S3 deletion fails,
    preventing orphaned metadata from blocking future operations.
    """
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id,
        FileRecord.app_id == current_app.id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        s3.delete_object(Bucket=BUCKET, Key=record.s3_key)
    except ClientError:
        pass  # Still remove DB record to avoid orphaned metadata

    db.delete(record)
    db.commit()
    return {"status": "deleted", "file_id": file_id}