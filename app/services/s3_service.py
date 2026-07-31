"""
Service wrapper around AWS S3 client using boto3.
"""

from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.exceptions import S3OperationError
from app.core.logging import logger


class S3Service:
    """Manages AWS S3 presigned URL generation and object verification."""

    def __init__(self, s3_client=None, bucket_name: Optional[str] = None):
        self.bucket = bucket_name or settings.S3_BUCKET
        if s3_client:
            self.client = s3_client
        else:
            self.client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            )

    def generate_presigned_upload_url(self, key: str, content_type: str, expires_in: int = 300) -> str:
        """Generate presigned S3 PUT URL for client upload."""
        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate S3 upload URL: {e}")
            raise S3OperationError("Could not generate presigned upload URL")

    def generate_presigned_download_url(
        self, key: str, original_filename: str, expires_in: int = 300
    ) -> str:
        """
        Generate presigned S3 GET URL for client download.

        Injects Content-Disposition header so browser downloads trigger file save.
        """
        try:
            disposition = f'attachment; filename="{original_filename}"'
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ResponseContentDisposition": disposition,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate S3 download URL: {e}")
            raise S3OperationError("Could not generate presigned download URL")

    def head_object(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Query S3 object metadata.

        Returns dict containing ContentLength if exists, None if object not found.
        """
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            return response
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code"))
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return None
            logger.error(f"S3 HeadObject failed for key {key}: {e}")
            raise S3OperationError(f"Failed to verify S3 object: {e}")

    def delete_object(self, key: str) -> bool:
        """Delete object from S3 bucket."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            logger.warning(f"Failed to delete S3 object {key}: {e}")
            return False
