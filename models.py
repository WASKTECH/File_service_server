# models.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class App(Base):
    __tablename__ = "apps"
    id = Column(String, primary_key=True)       # app_id
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False)

class FileRecord(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    s3_key = Column(String, unique=True, nullable=False)
    original_filename = Column(String, nullable=False)
    app_id = Column(String, ForeignKey("apps.id"), nullable=False)
    owner_id = Column(String, nullable=True)     # optional: end-user within the app
    content_type = Column(String)
    size = Column(Integer, nullable=True)
    status = Column(String, default="PENDING", nullable=False) # PENDING, COMPLETED, FAILED
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))