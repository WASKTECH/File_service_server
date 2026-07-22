# File Service API

A centralized REST API for managing file uploads and downloads across multiple applications, built on **FastAPI** and **AWS S3**.

## Why This Exists

Instead of each application implementing its own file upload logic, this service provides a single, secure API that any internal application can use. Files are stored in AWS S3 using **presigned URLs**, meaning the API server never handles file binary data — clients upload and download directly from S3.

## Architecture

```
┌──────────────┐     1. Request upload URL      ┌───────────────────┐
│              │ ──────────────────────────────→ │                   │
│  Client App  │     2. Return presigned URL     │  File Service API │
│  (Web/Mobile)│ ←────────────────────────────── │  (FastAPI)        │
│              │                                 │                   │
│              │     3. Upload file directly      │                   │
│              │ ──────────────────────────────→ │    AWS S3 Bucket  │
│              │                                 │                   │
│              │     4. Confirm upload            │                   │
│              │ ──────────────────────────────→ │  File Service API │
└──────────────┘                                 └───────────────────┘
```

## Tech Stack

| Component      | Technology                          |
| :------------- | :---------------------------------- |
| Framework      | FastAPI (Python)                    |
| Database       | PostgreSQL (via SQLAlchemy ORM)     |
| File Storage   | AWS S3 (presigned URLs)             |
| Authentication | API key per application (`x-api-key`) |
| CI/CD          | GitHub Actions                      |
| Local DB       | Docker Compose (PostgreSQL 16)      |

## Project Structure

```
├── main.py               # API endpoints and application entry point
├── models.py             # SQLAlchemy ORM models (App, FileRecord)
├── auth.py               # API key authentication dependency
├── db.py                 # Database engine and session management
├── s3_client.py          # AWS S3 client initialization
├── docker-compose.yml    # Local PostgreSQL via Docker
├── requirements.txt      # Python dependencies
├── tests/
│   └── test_main.py      # Unit tests (pytest)
└── .github/
    └── workflows/
        └── ci.yml        # GitHub Actions CI pipeline
```

## Getting Started

### Prerequisites

- Python 3.11+
- Docker (for local PostgreSQL)
- An AWS account with an S3 bucket

### 1. Clone and Install

```bash
git clone https://github.com/WASKTECH/File_service_server.git
cd File_service_server
python -m venv venv
.\venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your AWS credentials and database URL
```

### 3. Start the Database

```bash
docker compose up -d
```

### 4. Run the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger documentation.

### 5. Seed an Application

Before making API calls, register a consuming application:

```python
# seed_app.py
from db import SessionLocal, engine
from models import App, Base
import secrets

Base.metadata.create_all(bind=engine)
db = SessionLocal()
api_key = secrets.token_hex(16)
db.add(App(id="my_app", name="My Application", api_key=api_key))
db.commit()
print(f"API Key: {api_key}")
db.close()
```

```bash
python seed_app.py
```

## API Endpoints

All endpoints require the `x-api-key` header.

| Method   | Endpoint                        | Description                            |
| :------- | :------------------------------ | :------------------------------------- |
| `POST`   | `/files/upload-url`             | Request a presigned S3 upload URL      |
| `POST`   | `/files/{file_id}/confirm`      | Confirm upload and verify S3 object    |
| `GET`    | `/files`                        | List files (with pagination & filters) |
| `GET`    | `/files/{file_id}`              | Get file metadata                      |
| `GET`    | `/files/{file_id}/download-url` | Generate a presigned download URL      |
| `DELETE` | `/files/{file_id}`              | Delete file from S3 and database       |

## Running Tests

```bash
pytest
```

Tests use an isolated SQLite database and mocked S3 — no external services required.

## Multi-Tenant Isolation

Each consuming application is isolated through three layers:

1. **Authentication**: Unique API key per application.
2. **Database**: All queries filter by `app_id` — App A cannot see App B's files.
3. **Storage**: S3 keys are prefixed with `{app_id}/` — physical namespace separation.
