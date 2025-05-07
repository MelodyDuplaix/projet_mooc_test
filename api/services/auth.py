import json
from datetime import datetime, timedelta
import os
from typing import Optional
from uuid import uuid4

from fastapi import Security, status, HTTPException
from fastapi.security import APIKeyHeader

FILE_PATH = "./data/token_key_list.json"
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

def load_token_key_list():
    global FILE_PATH
    file_path = FILE_PATH
    
    # Vérifier si le dossier existe, sinon le créer
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Vérifier si le fichier existe
    if not os.path.exists(file_path):
        # Créer un fichier avec une liste vide
        with open(file_path, "w") as json_file:
            json.dump([], json_file, indent=4, ensure_ascii=False)
        return []
    
    # Ouvrir et lire le fichier
    try:
        with open(file_path, "r") as json_file:
            return json.load(json_file)
    except json.JSONDecodeError:
        # Si le fichier est corrompu ou vide, retourner une liste vide
        return []

def get_token_key_list():
    return load_token_key_list()

def is_valid_token(token: str) -> bool:
    key_list = load_token_key_list()
    
    for token_entry in key_list:
        if token_entry.get("token") == token and token_entry.get("expires_at") > datetime.now().isoformat():
            return True
    return False

if __name__ == "__main__":
    load_token_key_list()
    print(is_valid_token("2b1faa73-900d-47c2-b260-35a95bf30ce7"))
    print(len("2b1faa73-900d-47c2-b260-35a95bf30ce7"))




