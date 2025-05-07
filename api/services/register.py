from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sys
import os
from uuid import uuid4

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise ValueError("MONGO_URL environment variable is not set")

client = MongoClient(MONGO_URL)
db = client["G1"]
collection = db["authentification"]


def generate_token(api_key_name: str):
    expires_delta = timedelta(minutes=43800)
    expiration = datetime.now() + expires_delta
    
    # Créer un payload au format dictionnaire
    payload = {
        "api_key_name": api_key_name,
        "exp": expiration.timestamp()
    }
    
    rand_token = str(uuid4())
    
    api_token = {
        "api_key_name": api_key_name,
        "token": rand_token,
        "expires_at": expiration.isoformat()
    }
    return api_token

def register_token_key(api_name: str):
    token = generate_token(api_name)
    collection.insert_one(token)
    print(token)

if __name__ == "__main__":
    var = sys.argv[1]
    register_token_key(var)
