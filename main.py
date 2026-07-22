# main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
from botocore.exceptions import ClientError

from s3_client import s3, BUCKET
from auth import get_current_app
from db import get_db, engine
from models import Base, App, FileRecord

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Internal File API")

class UploadRequest(BaseModel):
    filename: str
    content_type: str
    owner_id: str | None = None

class FileResponse(BaseModel):
    id: int
    s3_key: str
    original_filename: str
    app_id: str
    owner_id: str | None
    content_type: str | None
    size: int | None
    status: str
    uploaded_at: str

    class Config:
        from_attributes = True

@app.post("/files/upload-url")
def get_upload_url(
    req: UploadRequest,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    # Sanitize filename to prevent path traversal
    safe_filename = Path(req.filename).name
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Namespace the S3 key by app_id — hard isolation at the storage layer
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

@app.post("/files/{file_id}/confirm")
def confirm_upload(
    file_id: int,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
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
                detail="File upload verification failed: File not found in S3 bucket.",
            )
        raise HTTPException(status_code=500, detail=f"S3 Error: {str(e)}")

@app.get("/files")
def list_files(
    owner_id: str | None = Query(None, description="Filter by end-user ID"),
    status: str | None = Query("COMPLETED", description="Filter by status (PENDING, COMPLETED, FAILED, or ALL)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
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

@app.get("/files/{file_id}")
def get_file_metadata(
    file_id: int,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
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

@app.get("/files/{file_id}/download-url")
def get_download_url(
    file_id: int,
    expires_in: int = Query(300, ge=60, le=86400, description="Expiration time in seconds"),
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id,
        FileRecord.app_id == current_app.id,   # <-- isolation check
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if record.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"File is not in COMPLETED state (current status: {record.status})")

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": record.s3_key},
        ExpiresIn=expires_in,
    )
    return {"download_url": url, "filename": record.original_filename}

@app.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id,
        FileRecord.app_id == current_app.id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        s3.delete_object(Bucket=BUCKET, Key=record.s3_key)
    except ClientError:
        pass  # Proceed to remove DB record even if S3 delete fails

    db.delete(record)
    db.commit()
    return {"status": "deleted", "file_id": file_id}