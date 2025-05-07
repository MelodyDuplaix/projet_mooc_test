import json
from datetime import datetime, timedelta
import os
import sys
from uuid import uuid4

FILE_PATH = "./data/token_key_list.json"

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

def register_token_key(api_name: str):
    global FILE_PATH
    key_list = load_token_key_list()
    token = generate_token(api_name)
    key_list.append(token)
    

    with open(FILE_PATH, "w") as json_file:
        json.dump(key_list, json_file, indent=4, ensure_ascii=False)
    
    print(token)

if __name__ == "__main__":
    var = sys.argv[1]
    register_token_key(var)



