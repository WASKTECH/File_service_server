"""
App entity request and response schemas.
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AppCreate(BaseModel):
    """Payload to register a new consuming application."""

    id: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=2, max_length=128)


class AppCreateResponse(BaseModel):
    """Response returned upon App registration including raw API Key once."""

    id: str
    name: str
    api_key: str = Field(..., description="Raw secret API key — copy now, will not be displayed again!")
    created_at: datetime


class AppResponse(BaseModel):
    """Public details of registered app."""

    id: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
