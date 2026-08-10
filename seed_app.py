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


def seed(app_id: str = "el_roi_pay_file_server", name: str = "El Roi Pay File Server", rotate: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    app_repo = AppRepository(db)

    existing = app_repo.get_by_id(app_id)
    if existing and not rotate:
        print(f"[INFO] Application '{app_id}' already exists in database.")
        print(f"   App ID: {existing.id}")
        print("   Note: Raw API key cannot be retrieved because it is securely hashed with SHA-256.")
        print("   To generate a NEW API key for this application, run:")
        print(f"     python seed_app.py {app_id} \"{name}\" --rotate")
    else:
        raw_api_key = secrets.token_hex(16)
        key_hash = hash_api_key(raw_api_key)

        if existing and rotate:
            existing.api_key_hash = key_hash
            existing.name = name
            db.commit()
            action_label = "API Key Rotated / Reset Successfully!"
        else:
            app_repo.create(app_id=app_id, name=name, api_key_hash=key_hash)
            action_label = "Application Created Successfully!"

        print("==================================================")
        print(f" [OK] {action_label}")
        print("==================================================")
        print(f"   App ID:  {app_id}")
        print(f"   API Key: {raw_api_key}")
        print("   IMPORTANT: Store this API Key securely. It will not be shown again!")
        print("==================================================")

    db.close()


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    rotate_flag = "--rotate" in args or "-r" in args
    clean_args = [a for a in args if a not in ("--rotate", "-r")]

    app_id = clean_args[0] if len(clean_args) > 0 else "el_roi_pay_file_server"
    app_name = clean_args[1] if len(clean_args) > 1 else "El Roi Pay File Server"

    seed(app_id, app_name, rotate=rotate_flag)
