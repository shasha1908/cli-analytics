"""API key authentication."""
import hashlib
import secrets
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.models import ApiKey

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    return f"cli_{secrets.token_urlsafe(32)}"


def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    from app.db import SessionLocal
    db = SessionLocal()
    try:
        key_record = db.query(ApiKey).filter(
            ApiKey.key_hash == hash_key(api_key),
            ApiKey.is_active == True
        ).first()
        if not key_record:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return key_record
    finally:
        db.close()
