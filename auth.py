# auth.py
"""
Authentication dependency for the File Service API.

Authenticates incoming requests by matching the `x-api-key` HTTP header
against registered App records in the database. Every API endpoint uses
this dependency to identify the calling application and enforce
multi-tenant data isolation.

Usage:
    @app.get("/example")
    def example(current_app: App = Depends(get_current_app)):
        # current_app is the authenticated App instance
        ...
"""

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from models import App
from db import get_db


def get_current_app(
    x_api_key: str = Header(..., description="API key identifying the calling application"),
    db: Session = Depends(get_db),
) -> App:
    """
    FastAPI dependency that authenticates the calling application.

    Looks up the App record matching the provided API key. If no match
    is found, returns a 401 Unauthorized response.

    Args:
        x_api_key: The API key sent in the `x-api-key` request header.
        db:        Database session injected by FastAPI.

    Returns:
        The authenticated App instance.

    Raises:
        HTTPException(401): If the API key is invalid or not found.
    """
    app = db.query(App).filter(App.api_key == x_api_key).first()
    if not app:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return app