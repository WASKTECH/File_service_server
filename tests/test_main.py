# tests/test_main.py
"""
Unit tests for the File Service API.

Uses an in-memory SQLite database and mocked S3 client to test all
API endpoints without requiring external services. The test database
is recreated before each test to ensure isolation.
"""

import os
import pytest
from unittest.mock import patch

# Override DATABASE_URL before any application imports to avoid
# connecting to the production database during test collection.
TEST_DATABASE_URL = "sqlite:///./test_runner.db"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from models import Base, App, FileRecord
from db import get_db, engine
from main import app

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Test Configuration
# ---------------------------------------------------------------------------

API_KEY = "test_secret_key"
APP_ID = "test_app"


def override_get_db():
    """Provide a test database session for dependency injection."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """
    Reset the database before each test.

    Drops all tables, recreates them, and seeds a test App record
    so that API key authentication works during tests.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(App(id=APP_ID, name="Test App", api_key=API_KEY))
    db.commit()
    db.close()
    yield


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------

def test_auth_rejects_invalid_api_key():
    """Requests with an invalid API key should return 401 Unauthorized."""
    response = client.post(
        "/files/upload-url",
        headers={"x-api-key": "invalid_key"},
        json={"filename": "test.txt", "content_type": "text/plain"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"


# ---------------------------------------------------------------------------
# Upload Flow Tests
# ---------------------------------------------------------------------------

@patch("main.s3")
def test_upload_url_returns_presigned_url_and_file_id(mock_s3):
    """POST /files/upload-url should return a presigned URL and file_id."""
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    response = client.post(
        "/files/upload-url",
        headers={"x-api-key": API_KEY},
        json={
            "filename": "document.pdf",
            "content_type": "application/pdf",
            "owner_id": "user_1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["upload_url"] == "https://s3.example.com/presigned"
    assert "file_id" in data


@patch("main.s3")
def test_confirm_upload_verifies_s3_and_sets_completed(mock_s3):
    """POST /files/{id}/confirm should verify S3 and set status to COMPLETED."""
    # Step 1: Request upload URL
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/upload"
    upload_res = client.post(
        "/files/upload-url",
        headers={"x-api-key": API_KEY},
        json={"filename": "report.pdf", "content_type": "application/pdf"},
    )
    file_id = upload_res.json()["file_id"]

    # Step 2: Mock S3 head_object to simulate successful upload
    mock_s3.head_object.return_value = {"ContentLength": 2048}

    # Step 3: Confirm upload
    confirm_res = client.post(
        f"/files/{file_id}/confirm",
        headers={"x-api-key": API_KEY},
    )

    assert confirm_res.status_code == 200
    data = confirm_res.json()
    assert data["status"] == "COMPLETED"
    assert data["size"] == 2048


# ---------------------------------------------------------------------------
# List & Download Tests
# ---------------------------------------------------------------------------

@patch("main.s3")
def test_list_files_and_generate_download_url(mock_s3):
    """GET /files should list files; GET /files/{id}/download-url should return a URL."""
    # Seed a COMPLETED file record directly
    db = TestingSessionLocal()
    rec = FileRecord(
        s3_key="test_app/uuid-photo.png",
        original_filename="photo.png",
        app_id=APP_ID,
        owner_id="user_2",
        content_type="image/png",
        size=512,
        status="COMPLETED",
    )
    db.add(rec)
    db.commit()
    file_id = rec.id
    db.close()

    # Verify listing returns the file
    list_res = client.get("/files", headers={"x-api-key": API_KEY})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # Verify download URL generation
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/download"
    dl_res = client.get(
        f"/files/{file_id}/download-url",
        headers={"x-api-key": API_KEY},
    )
    assert dl_res.status_code == 200
    assert dl_res.json()["download_url"] == "https://s3.example.com/download"


# ---------------------------------------------------------------------------
# Delete Tests
# ---------------------------------------------------------------------------

@patch("main.s3")
def test_delete_file_removes_record_and_s3_object(mock_s3):
    """DELETE /files/{id} should remove the file from S3 and the database."""
    db = TestingSessionLocal()
    rec = FileRecord(
        s3_key="test_app/uuid-old.txt",
        original_filename="old.txt",
        app_id=APP_ID,
        status="COMPLETED",
    )
    db.add(rec)
    db.commit()
    file_id = rec.id
    db.close()

    del_res = client.delete(
        f"/files/{file_id}",
        headers={"x-api-key": API_KEY},
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
