"""
Repository for App database access operations.
"""


from sqlalchemy.orm import Session

from app.core.security import hash_api_key
from app.models.app_model import App


class AppRepository:
    """Encapsulates data access logic for registered Applications."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, app_id: str) -> App | None:
        """Fetch App by its unique identifier string."""
        return self.db.query(App).filter(App.id == app_id).first()

    def get_by_api_key(self, api_key: str) -> App | None:
        """
        Lookup App matching a raw API key.

        First hashes the API key, then finds candidate matching records.
        """
        key_hash = hash_api_key(api_key)
        return self.db.query(App).filter(App.api_key_hash == key_hash).first()

    def create(self, app_id: str, name: str, api_key_hash: str) -> App:
        """Create a new App record in the database."""
        app = App(id=app_id, name=name, api_key_hash=api_key_hash)
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app
