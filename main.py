"""
Root entrypoint delegating to refactored app.main module.
Preserves backwards compatibility for uvicorn main:app.
"""

from app.main import app

__all__ = ["app"]