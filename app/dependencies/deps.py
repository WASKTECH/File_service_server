"""
FastAPI dependency functions for authentication, DB sessions, and domain services.
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppNotFoundError
from app.db.session import get_db_session
from app.models.app_model import App
from app.repositories.app_repository import AppRepository
from app.repositories.file_repository import FileRepository
from app.services.file_service import FileService
from app.services.s3_service import S3Service


def get_current_app(
    x_api_key: str = Header(..., alias=settings.API_KEY_HEADER_NAME, description="API Key for multi-tenant application authentication"),
    db: Session = Depends(get_db_session),
) -> App:
    """
    Authenticate calling application using x-api-key header.

    Checks database for SHA-256 hash match of API Key.
    """
    app_repo = AppRepository(db)
    app = app_repo.get_by_api_key(x_api_key)
    if not app:
        raise AppNotFoundError()
    return app


def get_s3_service() -> S3Service:
    """Provide singleton S3Service instance."""
    return S3Service()


def get_file_service(
    db: Session = Depends(get_db_session),
    s3_service: S3Service = Depends(get_s3_service),
) -> FileService:
    """Provide FileService domain instance with injected dependencies."""
    file_repo = FileRepository(db)
    return FileService(file_repo=file_repo, s3_service=s3_service)
