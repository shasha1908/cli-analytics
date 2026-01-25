"""API key management endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import ApiKey
from app.auth import generate_api_key, hash_key
from pydantic import BaseModel

router = APIRouter()


class CreateKeyRequest(BaseModel):
    name: str


class CreateKeyResponse(BaseModel):
    api_key: str
    name: str
    message: str = "Save this key - it won't be shown again"


@router.post("/keys", response_model=CreateKeyResponse)
def create_api_key(req: CreateKeyRequest, db: Session = Depends(get_db)):
    """Create a new API key."""
    raw_key = generate_api_key()
    key_record = ApiKey(key_hash=hash_key(raw_key), name=req.name, is_active=True)
    db.add(key_record)
    db.commit()
    return CreateKeyResponse(api_key=raw_key, name=req.name)
