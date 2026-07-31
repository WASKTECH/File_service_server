"""
Utility script to seed an initial consuming application and API key with SHA-256 hashing.

Usage:
    python seed_app.py
"""

import secrets
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.app_model import App
from app.core.security import hash_api_key
from app.repositories.app_repository import AppRepository


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    app_repo = AppRepository(db)

    app_id = "main_app_1"
    name = "Main Application"

    existing = app_repo.get_by_id(app_id)
    if existing:
        print(f"[INFO] Application '{app_id}' already exists in database.")
        print(f"   App ID: {existing.id}")
        print("   Note: Raw API key cannot be retrieved because it is securely hashed with SHA-256.")
    else:
        raw_api_key = secrets.token_hex(16)
        key_hash = hash_api_key(raw_api_key)
        app_repo.create(app_id=app_id, name=name, api_key_hash=key_hash)

        print("==================================================")
        print(" [OK] Application created successfully!")
        print("==================================================")
        print(f"   App ID:  {app_id}")
        print(f"   API Key: {raw_api_key}")
        print("   IMPORTANT: Store this API Key securely. It will not be shown again!")
        print("==================================================")

    db.close()


if __name__ == "__main__":
    seed()
