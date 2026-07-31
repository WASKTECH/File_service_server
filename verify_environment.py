"""
Environment and system verification script for File Service API.
"""

import sys
import boto3
from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine
from app.services.s3_service import S3Service

print("==================================================")
print("  FILE SERVICE SERVER — ENVIRONMENT & SYSTEM CHECK")
print("==================================================")

print(f"[ENV] Environment: {settings.ENVIRONMENT}")
print(f"[DB]  Database URL: {settings.DATABASE_URL}")

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("[OK]  Database Connection: SUCCESS")
except Exception as e:
    print(f"[ERR] Database Connection Failed: {e}")

print(f"[AWS] S3 Bucket: {settings.S3_BUCKET} | Region: {settings.AWS_REGION}")

try:
    s3_service = S3Service()
    url = s3_service.generate_presigned_download_url("test_key.txt", "test_key.txt", expires_in=60)
    print("[OK]  AWS S3 Presigned URL Generation: SUCCESS")
    print(f"      Sample URL: {url[:80]}...")
except Exception as e:
    print(f"[ERR] AWS S3 Verification Failed: {e}")

print("==================================================")
print("  RUN UNIT TESTS: python -m pytest")
print("  START API:      uvicorn app.main:app --reload")
print("  SWAGGER DOCS:   http://localhost:8000/docs")
print("==================================================")
