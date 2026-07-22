# auth.py
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from models import App
from db import get_db

def get_current_app(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> App:
    app = db.query(App).filter(App.api_key == x_api_key).first()
    if not app:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return app