import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test DB (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models and app after setting up test db override
from models import Base, App, FileRecord
from db import get_db
from main import app

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

API_KEY = "test_secret_key"
APP_ID = "test_app"

@pytest.fixture(autouse=True)
def setup_db():
    # Setup test app record
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    test_app = App(id=APP_ID, name="Test App", api_key=API_KEY)
    db.add(test_app)
    db.commit()
    db.close()
    yield

def test_auth_failure():
    response = client.post("/files/upload-url", headers={"x-api-key": "invalid_key"}, json={"filename": "test.txt", "content_type": "text/plain"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"

@patch("main.s3")
def test_get_upload_url(mock_s3):
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/upload-presigned-url"

    response = client.post(
        "/files/upload-url",
        headers={"x-api-key": API_KEY},
        json={"filename": "document.pdf", "content_type": "application/pdf", "owner_id": "user_1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "upload_url" in data
    assert "file_id" in data
    assert data["upload_url"] == "https://s3.example.com/upload-presigned-url"

@patch("main.s3")
def test_confirm_upload(mock_s3):
    # First request upload URL
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/upload"
    upload_res = client.post(
        "/files/upload-url",
        headers={"x-api-key": API_KEY},
        json={"filename": "report.pdf", "content_type": "application/pdf"}
    )
    file_id = upload_res.json()["file_id"]

    # Mock head_object to return file size
    mock_s3.head_object.return_value = {"ContentLength": 2048}

    confirm_res = client.post(
        f"/files/{file_id}/confirm",
        headers={"x-api-key": API_KEY}
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["status"] == "COMPLETED"
    assert confirm_data["size"] == 2048

@patch("main.s3")
def test_list_and_download_files(mock_s3):
    # Create file record directly
    db = TestingSessionLocal()
    rec = FileRecord(
        s3_key="test_app/uuid-photo.png",
        original_filename="photo.png",
        app_id=APP_ID,
        owner_id="user_2",
        content_type="image/png",
        size=512,
        status="COMPLETED"
    )
    db.add(rec)
    db.commit()
    file_id = rec.id
    db.close()

    # List files
    list_res = client.get("/files", headers={"x-api-key": API_KEY})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # Get Download URL
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/download"
    dl_res = client.get(f"/files/{file_id}/download-url", headers={"x-api-key": API_KEY})
    assert dl_res.status_code == 200
    assert dl_res.json()["download_url"] == "https://s3.example.com/download"

@patch("main.s3")
def test_delete_file(mock_s3):
    db = TestingSessionLocal()
    rec = FileRecord(
        s3_key="test_app/uuid-old.txt",
        original_filename="old.txt",
        app_id=APP_ID,
        status="COMPLETED"
    )
    db.add(rec)
    db.commit()
    file_id = rec.id
    db.close()

    del_res = client.delete(f"/files/{file_id}", headers={"x-api-key": API_KEY})
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
