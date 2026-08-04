# Multi-Tenant File Service API

An enterprise-grade, multi-tenant **File Management Service** built on **FastAPI**, **PostgreSQL**, and **AWS S3**. 

This service offloads heavy binary payloads entirely to AWS S3 using **presigned URLs**. The API server operates strictly as a metadata management, authentication, and authorization plane — it **never handles binary streams**, ensuring high throughput, zero memory exhaustion, and sub-millisecond response times.

---

## 🏛️ System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Client Application       │
                                  │   (Web / Mobile / Microservice)│
                                  └───────────────┬───────────────┘
                                                  │
                            1. POST /api/v1/files/upload-url (Header: x-api-key)
                                                  │
                                                  ▼
                        ┌──────────────────────────────────────────────────┐
                        │             FastAPI File Service API             │
                        │                                                  │
                        │   ┌────────────────────┐  ┌───────────────────┐  │
                        │   │  Auth & Security   │  │   File Service    │  │
                        │   │ (SHA-256 Key Hash) │  │  (Domain Logic)   │  │
                        │   └────────────────────┘  └─────────┬─────────┘  │
                        └─────────────────────────────────────┼────────────┘
                                                              │
                       ┌──────────────────────────────────────┴──────────────────────────────────────┐
                       │                                                                             │
    2. Presigned S3 PUT URL                                                       3. Metadata Persist
   (Content-Type, Bucket, Expiry)                                                  (Status: PENDING)
                       │                                                                             │
                       ▼                                                                             ▼
            ┌─────────────────────┐                                                       ┌─────────────────────┐
            │    AWS S3 Bucket    │                                                       │ PostgreSQL Database │
            │ {app_id}/{uuid}-name│                                                       │ (apps & files tables│
            └─────────────────────┘                                                       └─────────────────────┘
                       ▲                                                                             ▲
                       │                                                                             │
         4. Direct Binary Upload (PUT)                                                               │
                       │                                                                             │
                       └──────────────────────────────┬──────────────────────────────────────────────┘
                                                      │
                                    5. POST /api/v1/files/{uuid}/confirm (Verify S3 Head Object)
                                                      │
                                                      ▼
                        ┌──────────────────────────────────────────────────┐
                        │      Metadata Updated: PENDING ➔ COMPLETED       │
                        └──────────────────────────────────────────────────┘
```

---

## 🔒 Multi-Tenant Security & Isolation Model

Each consuming application is isolated across five distinct security layers:

1. **Authentication (Hashed API Keys)**:
   - Each application is assigned a unique API key sent in the `x-api-key` HTTP header.
   - Database stores **SHA-256 hashed API keys** (never raw keys). Comparisons are performed in constant-time (`secrets.compare_digest`) to defeat timing attacks.
2. **Public Identifier Isolation (UUIDv4)**:
   - External clients reference files using cryptographically random **UUIDv4** strings (`/files/550e8400-e29b-41d4-a716-446655440000`).
   - Prevents sequential integer enumeration attacks (Insecure Direct Object Reference).
3. **Database Multi-Tenancy**:
   - All queries filter strictly by `app_id`. App A cannot read, modify, or delete files belonging to App B. Cross-tenant access attempts return `404 Not Found` to conceal object existence.
4. **Physical S3 Key Namespacing**:
   - Object keys are namespaced as `{app_id}/{uuid}-{safe_filename}`, establishing hard multi-tenant separation at the storage tier.
5. **Download Security**:
   - Presigned download URLs inject `Content-Disposition: attachment; filename="..."` headers, enforcing safe browser download behavior and mitigating cross-site scripting (XSS) risks.

---

## ⚡ Tech Stack

| Layer | Component | Technology |
| :--- | :--- | :--- |
| **Framework** | API Server | FastAPI (Python 3.11+) |
| **Database** | Metadata Store | PostgreSQL 16 (SQLAlchemy 2.0 ORM) |
| **Storage** | Binary File Store | AWS S3 (Presigned PUT/GET URLs via Boto3) |
| **Settings** | Configuration | Pydantic Settings (`pydantic-settings`) |
| **CI/CD** | Pipeline | GitHub Actions (Ruff, Pytest, Coverage) |
| **Container** | Orchestration | Docker & Docker Compose |

---

## 📚 Documentation Index

Comprehensive documentation for developers, DevOps, and operational teams is available in the [`docs/`](file:///c:/Users/eddie/OneDrive/Documents/File_service_server/docs) directory and `terraform/`:

| Document | Link | Audience | Contents |
| :--- | :--- | :--- | :--- |
| **System Architecture** | [ARCHITECTURE.md](file:///c:/Users/eddie/OneDrive/Documents/File_service_server/docs/ARCHITECTURE.md) | Architects / Leads | AWS topology, module graph, network isolation, 4-layer defense-in-depth |
| **Deployment Guide** | [DEPLOYMENT_GUIDE.md](file:///c:/Users/eddie/OneDrive/Documents/File_service_server/docs/DEPLOYMENT_GUIDE.md) | DevOps / Developers | Step-by-step AWS deployment, Docker ➔ ECR ➔ ECS, CI/CD GitHub Actions setup |
| **Operational Runbook** | [OPERATIONAL_RUNBOOK.md](file:///c:/Users/eddie/OneDrive/Documents/File_service_server/docs/OPERATIONAL_RUNBOOK.md) | Operations / On-Call | Day-2 ops, health checks, database queries, secrets rotation, 4 incident playbooks |
| **Disaster Recovery** | [DISASTER_RECOVERY.md](file:///c:/Users/eddie/OneDrive/Documents/File_service_server/docs/DISASTER_RECOVERY.md) | Security / Reliability | RPO/RTO targets, 7 recovery scenarios (database failure, data corruption, S3 delete) |
| **Cost Estimation** | [COST_ESTIMATION.md](file:///c:/Users/eddie/OneDrive/Documents/File_service_server/docs/COST_ESTIMATION.md) | CTO / Finance | AWS service cost breakdowns ($101/mo dev vs $619/mo prod), optimization tips |
| **Terraform Reference** | [terraform/README.md](file:///c:/Users/eddie/OneDrive/Documents/File_service_server/terraform/README.md) | Infrastructure Engineers | All 12 IaC modules, variable definitions, outputs, local vs remote state setup |

---

## 📁 Repository Structure

```
.
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── files.py         # File CRUD & presigned URL endpoints
│   │       │   └── health.py        # System health & readiness probes
│   │       └── router.py            # V1 Master API router
│   ├── core/
│   │   ├── config.py                # Pydantic Settings configuration
│   │   ├── exceptions.py            # Centralized exception handlers & error envelopes
│   │   ├── logging.py               # Structured logging & Request ID tracking
│   │   └── security.py              # SHA-256 API key hashing & comparison
│   ├── db/
│   │   ├── base.py                  # Declarative Base, Timestamp & Soft-Delete mixins
│   │   └── session.py               # Engine configuration & Session management
│   ├── dependencies/
│   │   └── deps.py                  # FastAPI dependency injection (auth, db, services)
│   ├── models/
│   │   ├── app_model.py             # App tenant ORM model
│   │   └── file_record.py           # FileRecord ORM model with composite indexes
│   ├── repositories/
│   │   ├── app_repository.py        # Database data access for Apps
│   │   └── file_repository.py       # Database data access for Files
│   ├── schemas/
│   │   ├── app_schemas.py           # App request/response schemas
│   │   ├── common.py                # Generic APIResponse & PaginatedData wrappers
│   │   └── file_schemas.py          # File request/response schemas
│   ├── services/
│   │   ├── file_service.py          # Core file domain orchestrator
│   │   └── s3_service.py            # AWS S3 Boto3 integration
│   └── main.py                      # FastAPI application entrypoint
├── tests/
│   └── test_main.py                 # Comprehensive unit & integration tests
├── .env.example                     # Environment configuration template
├── docker-compose.yml               # Local PostgreSQL & API service stack
├── Dockerfile                       # Multi-stage production container build
├── requirements.txt                 # Python dependencies
└── seed_app.py                      # Tenant application seeding script
```

---

## ⚙️ Environment Configuration

Copy `.env.example` to `.env` and configure your environment settings:

```ini
PROJECT_NAME="File Service API"
ENVIRONMENT=development    # development | staging | production
DEBUG=false
API_V1_PREFIX=/api/v1

# AWS S3 Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
S3_BUCKET=your_s3_bucket_name
S3_PRESIGNED_UPLOAD_EXPIRATION=300
S3_PRESIGNED_DOWNLOAD_EXPIRATION=300
MAX_FILE_SIZE_BYTES=104857600   # 100 MB

# Database Configuration
DATABASE_URL=postgresql://fileapi:devpassword123@localhost:5432/filedb

# Docker Compose Database Settings
POSTGRES_USER=fileapi
POSTGRES_PASSWORD=devpassword123
POSTGRES_DB=filedb
```

---

## 🚀 Quick Start Guide

### 1. Start PostgreSQL with Docker

```bash
docker compose up -d db
```

Verify container status:
```bash
docker ps
```

### 2. Virtual Environment Setup

```bash
# Create Virtual Environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Linux / macOS)
source venv/bin/activate

# Install Dependencies
python -m pip install -r requirements.txt
```

### 3. Seed App Registration & Generate API Key

```bash
python seed_app.py
```
*Console Output*:
```text
==================================================
 [OK] Application created successfully!
==================================================
   App ID:  main_app
   API Key: 4f8a91b2c3d4e5f6789012345678abcd
   IMPORTANT: Store this API Key securely. It will not be shown again!
==================================================
```

### 4. Run the API Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```
*(If port 8000 is occupied on Windows, use `--port 8001`)*

Interactive documentation is available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Probe**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 🛠️ Developer Manual Testing Guide

This guide details how backend engineers can manually test the entire file lifecycle, security controls, and database states.

### Setting Test Variables (PowerShell & Bash)

**PowerShell (Windows)**:
```powershell
$apiKey = "YOUR_RAW_API_KEY_HERE"
$baseUrl = "http://localhost:8000/api/v1"
```

**Bash (Linux/Mac)**:
```bash
export API_KEY="YOUR_RAW_API_KEY_HERE"
export BASE_URL="http://localhost:8000/api/v1"
```

---

### Step 1: Request Presigned Upload URL (`POST /files/upload-url`)

**PowerShell**:
```powershell
$body = '{"filename": "document.pdf", "content_type": "application/pdf", "owner_id": "user_123"}'
curl.exe -X POST "$baseUrl/files/upload-url" -H "Content-Type: application/json" -H "x-api-key: $apiKey" -d $body
```

**Bash**:
```bash
curl -X POST "$BASE_URL/files/upload-url" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"filename": "document.pdf", "content_type": "application/pdf", "owner_id": "user_123"}'
```

**Response Payload**:
```json
{
  "success": true,
  "data": {
    "file_uuid": "e6d564b0-a9f5-4fda-b01d-0f1443865571",
    "upload_url": "https://bucket.s3.amazonaws.com/main_app/e6d564b0...pdf?AWSAccessKeyId=...&Signature=...",
    "expires_in_seconds": 300
  },
  "message": "Presigned upload URL generated successfully"
}
```

---

### Step 2: Upload File Binary Directly to S3 (`PUT <upload_url>`)

Create a local dummy file and stream it directly to AWS S3:

**PowerShell**:
```powershell
Set-Content -Path document.pdf -Value "Sample PDF Binary Content Data"
$uploadUrl = "<PASTE_UPLOAD_URL_HERE>"
curl.exe -X PUT $uploadUrl -H "Content-Type: application/pdf" --data-binary "@document.pdf"
```

**Bash**:
```bash
echo "Sample PDF Binary Content Data" > document.pdf
curl -X PUT "<UPLOAD_URL>" -H "Content-Type: application/pdf" --data-binary "@document.pdf"
```
*(S3 returns HTTP `200 OK` with 0 output bytes on success)*

---

### Step 3: Confirm Upload with Backend (`POST /files/{uuid}/confirm`)

Verifies object presence in S3 (`head_object`), fetches byte size, and updates database status to `COMPLETED`.

**PowerShell**:
```powershell
$fileUuid = "<PASTE_FILE_UUID_HERE>"
curl.exe -X POST "$baseUrl/files/$fileUuid/confirm" -H "x-api-key: $apiKey"
```

**Bash**:
```bash
curl -X POST "$BASE_URL/files/$FILE_UUID/confirm" -H "x-api-key: $API_KEY"
```

**Response Payload**:
```json
{
  "success": true,
  "data": {
    "file_uuid": "e6d564b0-a9f5-4fda-b01d-0f1443865571",
    "status": "COMPLETED",
    "size": 31,
    "confirmed_at": "2026-07-31T11:45:00.000000Z"
  },
  "message": "File upload confirmed successfully"
}
```

---

### Step 4: List Tenant Files (`GET /files`)

Retrieve a paginated list of active files scoped strictly to the calling application:

**PowerShell**:
```powershell
curl.exe -X GET "$baseUrl/files?page=1&page_size=20&status=COMPLETED" -H "x-api-key: $apiKey"
```

---

### Step 5: Get File Metadata (`GET /files/{uuid}`)

**PowerShell**:
```powershell
curl.exe -X GET "$baseUrl/files/$fileUuid" -H "x-api-key: $apiKey"
```

---

### Step 6: Generate Download Presigned URL (`GET /files/{uuid}/download-url`)

Generates a temporary signed S3 download URL:

**PowerShell**:
```powershell
curl.exe -X GET "$baseUrl/files/$fileUuid/download-url?expires_in=300" -H "x-api-key: $apiKey"
```
*(Paste the returned `download_url` into your web browser to trigger an instant download directly from S3)*

---

### Step 7: Delete File (`DELETE /files/{uuid}`)

Deletes the binary object from S3 and soft-deletes the metadata in PostgreSQL:

**PowerShell**:
```powershell
curl.exe -X DELETE "$baseUrl/files/$fileUuid" -H "x-api-key: $apiKey"
```

---

## 🔒 Security Verification Tests

Backend engineers should verify these security assertions manually:

| Test Case | Command Execution | Expected Status Code | Reason |
| :--- | :--- | :--- | :--- |
| **1. Missing API Key Header** | Request `/upload-url` without `x-api-key` | `422 Unprocessable Entity` | FastAPI header validation dependency rejects request. |
| **2. Invalid API Key** | Request `/upload-url` with `x-api-key: badkey` | `401 Unauthorized` | Key hash lookup fails in PostgreSQL `apps` table. |
| **3. Cross-Tenant Data Access** | App B queries App A's `file_uuid` | `404 Not Found` | Query contains `WHERE app_id = :app_b_id`. Hides file existence. |
| **4. Cross-Tenant Deletion** | App B sends `DELETE` for App A's file | `404 Not Found` | Scope check prevents unauthorized deletion. |
| **5. Unconfirmed Download** | Request download link for `PENDING` file | `400 Bad Request` | `FILE_NOT_READY` error prevents downloading incomplete drafts. |
| **6. Expired Presigned PUT URL** | Wait 5 minutes after `/upload-url` before `PUT` | S3 XML `AccessDenied: Request has expired` | AWS S3 signature expiration enforcement. |

---

## 🗄️ PostgreSQL Database Inspection

Inspect database records directly via Docker container:

```bash
# Query registered apps and SHA-256 key hashes
docker exec -it file-service-db psql -U fileapi -d filedb -c "SELECT id, name, api_key_hash, created_at FROM apps;"

# Query active file metadata
docker exec -it file-service-db psql -U fileapi -d filedb -c "SELECT uuid, original_filename, app_id, status, size FROM files WHERE deleted_at IS NULL;"
```

---

## 🧪 Automated Testing Suite

The repository includes a comprehensive unit and integration test suite in `tests/test_main.py` using mocked AWS S3 interfaces (`unittest.mock.patch`) and an isolated SQLite test database.

### Running Tests

```bash
# Run all tests with verbose output
python -m pytest -v

# Run with test coverage breakdown
python -m pytest --cov=app --cov-report=term-missing
```

### Test Case Coverage Summary

- `test_health_check_endpoint`: Verifies `/health` probe returns system health status.
- `test_auth_missing_header_returns_422`: Enforces mandatory `x-api-key` header presence.
- `test_auth_invalid_key_returns_401`: Validates zero-knowledge SHA-256 API key authentication.
- `test_request_upload_url_success`: Verifies pending record creation and presigned PUT URL generation.
- `test_request_upload_url_invalid_disallowed_mime_type`: Validates MIME type restriction rules.
- `test_confirm_upload_success`: Mocks S3 `head_object` and tests status transition to `COMPLETED`.
- `test_confirm_upload_missing_in_s3_fails`: Prevents phantom file records when object is missing in S3.
- `test_get_download_url_completed_file`: Tests presigned download link generation.
- `test_get_download_url_pending_file_fails`: Rejects download URL generation for `PENDING` uploads.
- `test_multi_tenant_isolation_prevents_cross_access`: Asserts 404 response on cross-tenant file access attempts.
- `test_delete_file_soft_deletes_record`: Tests S3 `delete_object` invocation and database soft delete.

---

## ❓ Troubleshooting Common Issues

### 1. `WinError 10013` (Port 8000 Blocked on Windows)
- **Cause**: Windows Hyper-V or another process is holding port 8000.
- **Fix**: Run Uvicorn on port 8001:
  `python -m uvicorn app.main:app --reload --port 8001`

### 2. `Fatal error in launcher`
- **Cause**: Project directory was renamed/moved, breaking virtual environment python paths in `.exe` wrappers.
- **Fix**: Run commands with `python -m <module>` (e.g. `python -m uvicorn ...`, `python -m pytest`).

### 3. `psycopg2.errors.UndefinedColumn: column apps.api_key_hash does not exist`
- **Cause**: Existing database container has an outdated schema from a previous build.
- **Fix**: Drop old tables and re-run seeding:
  `docker exec -it file-service-db psql -U fileapi -d filedb -c "DROP TABLE IF EXISTS files CASCADE; DROP TABLE IF EXISTS apps CASCADE;"`
  `python seed_app.py`

### 4. `UPLOAD_VERIFICATION_FAILED: Object not found in S3 bucket`
- **Cause**: `POST /confirm` was executed before running the `PUT` upload to S3, or the upload failed.
- **Fix**: Ensure `curl -X PUT` to S3 returns `200 OK` before calling `/confirm`.
