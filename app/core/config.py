"""
Application configuration management using Pydantic Settings.

Parses and validates environment variables from `.env` or system environment.
"""


from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global Application Settings."""

    # Project Information
    PROJECT_NAME: str = "File Service API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="development | staging | production")
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = "/api/v1"

    # Database Settings
    DATABASE_URL: str = Field(
        default="sqlite:///./file_service.db",
        description="SQLAlchemy database connection string",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # AWS S3 Settings
    AWS_REGION: str = Field(default="us-east-1")
    AWS_ACCESS_KEY_ID: str = Field(default="")
    AWS_SECRET_ACCESS_KEY: str = Field(default="")
    S3_BUCKET: str = Field(default="file-service-bucket")
    S3_PRESIGNED_UPLOAD_EXPIRATION: int = Field(default=300, description="Upload URL expiration in seconds (5 min)")
    S3_PRESIGNED_DOWNLOAD_EXPIRATION: int = Field(default=300, description="Download URL expiration in seconds (5 min)")
    MAX_FILE_SIZE_BYTES: int = Field(default=104_857_600, description="100 MB max upload limit")

    # Security & Auth
    API_KEY_HEADER_NAME: str = "x-api-key"
    ALLOWED_MIME_TYPES: set[str] = Field(
        default={
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "text/plain",
            "text/csv",
            "application/json",
            "application/zip",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        description="Allowed MIME types for upload. Empty set allows all.",
    )

    # CORS Configuration
    CORS_ORIGINS: list[str] = Field(default=["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
