"""
Backwards-compatible bridge for app.services.s3_service.
"""

from app.services.s3_service import S3Service
from app.core.config import settings

_s3_service = S3Service()
s3 = _s3_service.client
BUCKET = settings.S3_BUCKET

__all__ = ["s3", "BUCKET", "S3Service"]