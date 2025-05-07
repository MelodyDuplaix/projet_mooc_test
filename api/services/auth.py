import json
from datetime import datetime, timedelta
import os
from typing import Optional
from uuid import uuid4

from fastapi import Security, status, HTTPException
from fastapi.security import APIKeyHeader
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise ValueError("MONGO_URL environment variable is not set")

client = MongoClient(MONGO_URL)
db = client["G1"]
collection = db["authentification"]

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: Optional[str] = Security(API_KEY_HEADER)):
    if api_key_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )
    
    if not is_valid_token(api_key_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    
    return {"api_key": api_key_header}

def get_token_key_list():
    return list(collection.find())

def is_valid_token(token: str) -> bool:
    for token_entry in get_token_key_list():
        if token_entry.get("token") == token and token_entry.get("expires_at") > datetime.now().isoformat():
            return True
    return False

if __name__ == "__main__":
    print(is_valid_token("2b1faa73-900d-47c2-b260-35a95bf30ce7"))
    print(len("2b1faa73-900d-47c2-b260-35a95bf30ce7"))
