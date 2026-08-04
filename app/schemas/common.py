"""
Common request and response schemas including standard envelopes and pagination wrappers.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard success API response envelope."""

    success: bool = True
    data: T
    message: str | None = None


class PaginationMeta(BaseModel):
    """Pagination metadata details."""

    total: int = Field(description="Total matching records")
    page: int = Field(description="Current page number (1-based)")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether a next page exists")
    has_prev: bool = Field(description="Whether a previous page exists")


class PaginatedData(BaseModel, Generic[T]):
    """Paginated result container."""

    items: list[T]
    pagination: PaginationMeta
