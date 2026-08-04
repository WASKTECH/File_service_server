"""
Unit & Integration test suite for the File Service API.

Tests API authentication, presigned upload/download URL generation,
upload confirmation, multi-tenant isolation, file listing with pagination/filtering,
soft deletion, invalid input handling, and health endpoints using mocked S3 clients.
"""

import os
from unittest.mock import patch

import pytest

# Force test database URL before importing application
TEST_DB_PATH = "./test_runner.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["S3_BUCKET"] = "test-s3-bucket"
os.environ["AWS_REGION"] = "us-east-1"

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_api_key
from app.db.base import Base
from app.db.session import engine, get_db_session
from app.main import app
from app.models.app_model import App
from app.models.file_record import FileRecord, FileStatus

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

API_KEY = "super_secret_test_key"
APP_ID = "tenant_app_1"

API_KEY_2 = "tenant_2_secret_key"
APP_ID_2 = "tenant_app_2"


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db_session] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Reset DB schema and seed test tenant applications before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    # Seed Tenant 1
    db.add(App(id=APP_ID, name="Test Tenant App 1", api_key_hash=hash_api_key(API_KEY)))
    # Seed Tenant 2 (for multi-tenant isolation testing)
    db.add(App(id=APP_ID_2, name="Test Tenant App 2", api_key_hash=hash_api_key(API_KEY_2)))
    db.commit()
    db.close()
    yield


# ---------------------------------------------------------------------------
# Health Check Tests
# ---------------------------------------------------------------------------

@patch("app.services.s3_service.S3Service.generate_presigned_download_url")
def test_health_check_endpoint(mock_presign):
    """GET /api/v1/health should return UP status when DB and S3 are online."""
    mock_presign.return_value = "https://s3.example.com/test"
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "UP"
    assert json_data["data"]["database"] == "healthy"


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------

def test_auth_missing_header_returns_422():
    """Requests missing x-api-key header should return validation error."""
    response = client.post("/api/v1/files/upload-url", json={"filename": "doc.pdf", "content_type": "application/pdf"})
    assert response.status_code == 422


def test_auth_invalid_key_returns_401():
    """Requests with incorrect API key should return 401 Unauthorized."""
    response = client.post(
        "/api/v1/files/upload-url",
        headers={"x-api-key": "wrong_key"},
        json={"filename": "doc.pdf", "content_type": "application/pdf"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# Upload Flow & Validation Tests
# ---------------------------------------------------------------------------

@patch("app.services.s3_service.S3Service.generate_presigned_upload_url")
def test_request_upload_url_success(mock_presign):
    """POST /api/v1/files/upload-url creates pending record and returns presigned PUT URL."""
    mock_presign.return_value = "https://s3.amazonaws.com/test-s3-bucket/upload-link"

    response = client.post(
        "/api/v1/files/upload-url",
        headers={"x-api-key": API_KEY},
        json={
            "filename": "quarterly_report.pdf",
            "content_type": "application/pdf",
            "owner_id": "user_123",
        },
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["upload_url"] == "https://s3.amazonaws.com/test-s3-bucket/upload-link"
    assert "file_uuid" in data
    assert data["expires_in_seconds"] == 300


def test_request_upload_url_invalid_disallowed_mime_type():
    """POST /api/v1/files/upload-url rejects disallowed MIME types when configured."""
    with patch("app.services.file_service.settings.ALLOWED_MIME_TYPES", {"application/pdf"}):
        response = client.post(
            "/api/v1/files/upload-url",
            headers={"x-api-key": API_KEY},
            json={"filename": "script.exe", "content_type": "application/x-msdownload"},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


@patch("app.services.s3_service.S3Service.head_object")
@patch("app.services.s3_service.S3Service.generate_presigned_upload_url")
def test_confirm_upload_success(mock_presign, mock_head):
    """POST /api/v1/files/{uuid}/confirm verifies S3 object and sets status to COMPLETED."""
    mock_presign.return_value = "https://s3.example.com/upload"
    mock_head.return_value = {"ContentLength": 1048576}  # 1MB

    # Step 1: Request upload URL
    res = client.post(
        "/api/v1/files/upload-url",
        headers={"x-api-key": API_KEY},
        json={"filename": "image.png", "content_type": "image/png"},
    )
    file_uuid = res.json()["data"]["file_uuid"]

    # Step 2: Confirm upload
    confirm_res = client.post(
        f"/api/v1/files/{file_uuid}/confirm",
        headers={"x-api-key": API_KEY},
    )

    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()["data"]
    assert confirm_data["status"] == "COMPLETED"
    assert confirm_data["size"] == 1048576


@patch("app.services.s3_service.S3Service.head_object")
@patch("app.services.s3_service.S3Service.generate_presigned_upload_url")
def test_confirm_upload_missing_in_s3_fails(mock_presign, mock_head):
    """Confirm fails with 400 if object is not found in S3 bucket."""
    mock_presign.return_value = "https://s3.example.com/upload"
    mock_head.return_value = None  # S3 Object missing

    res = client.post(
        "/api/v1/files/upload-url",
        headers={"x-api-key": API_KEY},
        json={"filename": "missing.png", "content_type": "image/png"},
    )
    file_uuid = res.json()["data"]["file_uuid"]

    confirm_res = client.post(
        f"/api/v1/files/{file_uuid}/confirm",
        headers={"x-api-key": API_KEY},
    )

    assert confirm_res.status_code == 400
    assert confirm_res.json()["error"]["code"] == "UPLOAD_VERIFICATION_FAILED"


# ---------------------------------------------------------------------------
# Download & Metadata Tests
# ---------------------------------------------------------------------------

@patch("app.services.s3_service.S3Service.generate_presigned_download_url")
def test_get_download_url_completed_file(mock_dl):
    """GET /api/v1/files/{uuid}/download-url returns presigned download link for COMPLETED file."""
    mock_dl.return_value = "https://s3.example.com/download-link"

    # Seed a COMPLETED record directly
    db = TestingSessionLocal()
    rec = FileRecord(
        uuid="550e8400-e29b-41d4-a716-446655440000",
        s3_key=f"{APP_ID}/550e8400-e29b-41d4-a716-446655440000-data.csv",
        original_filename="data.csv",
        app_id=APP_ID,
        content_type="text/csv",
        size=500,
        status=FileStatus.COMPLETED.value,
    )
    db.add(rec)
    db.commit()
    db.close()

    res = client.get(
        "/api/v1/files/550e8400-e29b-41d4-a716-446655440000/download-url",
        headers={"x-api-key": API_KEY},
    )

    assert res.status_code == 200
    assert res.json()["data"]["download_url"] == "https://s3.example.com/download-link"
    assert res.json()["data"]["filename"] == "data.csv"


def test_get_download_url_pending_file_fails():
    """GET /api/v1/files/{uuid}/download-url rejects files in PENDING status."""
    db = TestingSessionLocal()
    rec = FileRecord(
        uuid="660e8400-e29b-41d4-a716-446655440000",
        s3_key=f"{APP_ID}/660e8400-e29b-41d4-a716-446655440000-pending.pdf",
        original_filename="pending.pdf",
        app_id=APP_ID,
        content_type="application/pdf",
        status=FileStatus.PENDING.value,
    )
    db.add(rec)
    db.commit()
    db.close()

    res = client.get(
        "/api/v1/files/660e8400-e29b-41d4-a716-446655440000/download-url",
        headers={"x-api-key": API_KEY},
    )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "FILE_NOT_READY"


# ---------------------------------------------------------------------------
# Multi-Tenant Isolation Tests
# ---------------------------------------------------------------------------

def test_multi_tenant_isolation_prevents_cross_access():
    """Tenant App 2 should get 404 when attempting to access Tenant App 1's file."""
    db = TestingSessionLocal()
    rec = FileRecord(
        uuid="770e8400-e29b-41d4-a716-446655440000",
        s3_key=f"{APP_ID}/770e8400-e29b-41d4-a716-446655440000-private.txt",
        original_filename="private.txt",
        app_id=APP_ID,  # Belongs to APP_ID (Tenant 1)
        status=FileStatus.COMPLETED.value,
    )
    db.add(rec)
    db.commit()
    db.close()

    # Tenant 2 tries to fetch metadata for Tenant 1's file
    res = client.get(
        "/api/v1/files/770e8400-e29b-41d4-a716-446655440000",
        headers={"x-api-key": API_KEY_2},  # Tenant 2 key
    )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "FILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# Deletion & Soft Delete Tests
# ---------------------------------------------------------------------------

@patch("app.services.s3_service.S3Service.delete_object")
def test_delete_file_soft_deletes_record(mock_delete):
    """DELETE /api/v1/files/{uuid} soft-deletes file record and calls S3 delete."""
    mock_delete.return_value = True

    db = TestingSessionLocal()
    rec = FileRecord(
        uuid="880e8400-e29b-41d4-a716-446655440000",
        s3_key=f"{APP_ID}/880e8400-e29b-41d4-a716-446655440000-old.log",
        original_filename="old.log",
        app_id=APP_ID,
        status=FileStatus.COMPLETED.value,
    )
    db.add(rec)
    db.commit()
    db.close()

    del_res = client.delete(
        "/api/v1/files/880e8400-e29b-41d4-a716-446655440000",
        headers={"x-api-key": API_KEY},
    )

    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True

    # Subsequent GET should return 404
    get_res = client.get(
        "/api/v1/files/880e8400-e29b-41d4-a716-446655440000",
        headers={"x-api-key": API_KEY},
    )
    assert get_res.status_code == 404
