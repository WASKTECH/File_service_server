"""
Custom application exceptions and FastAPI exception handlers.

Provides uniform error response JSON structures across all endpoints.
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppBaseException(Exception):
    """Base exception class for File Service domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AppNotFoundError(AppBaseException):
    def __init__(self, message: str = "Application not found or unauthorized"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class FileNotFoundError(AppBaseException):
    def __init__(self, message: str = "File record not found"):
        super().__init__(
            message=message,
            code="FILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidFileTypeError(AppBaseException):
    def __init__(self, content_type: str):
        super().__init__(
            message=f"Content type '{content_type}' is not allowed.",
            code="INVALID_FILE_TYPE",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class FileTooLargeError(AppBaseException):
    def __init__(self, max_size_mb: int):
        super().__init__(
            message=f"File exceeds maximum allowed size of {max_size_mb}MB.",
            code="FILE_TOO_LARGE",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class S3OperationError(AppBaseException):
    def __init__(self, message: str = "S3 storage operation failed"):
        super().__init__(
            message=message,
            code="S3_STORAGE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


def build_error_response(status_code: int, code: str, message: str, details: Optional[Any] = None) -> JSONResponse:
    """Construct standard error JSON envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        },
    )


async def app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
    """Handler for domain-specific AppBaseException instances."""
    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handler for standard FastAPI/Starlette HTTPExceptions."""
    code_map = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        400: "BAD_REQUEST",
        422: "VALIDATION_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return build_error_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for FastAPI Pydantic validation errors."""
    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Invalid request payload or parameters",
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled exceptions."""
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred",
        details=str(exc) if request.app.debug else None,
    )
