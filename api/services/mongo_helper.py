from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()

def get_data_for_thread(mongo_url, collection_name, id):
    """
    Récupère les données d'un message à partir de son ID.
    
    Args:
        mongo_url (str): URL de connexion à MongoDB.
        collection_name (str): Nom de la collection dans MongoDB.
        id (str): ID du message à récupérer.
        
    Returns:
        dict: Données du message.
    """
    client = MongoClient(mongo_url)
    result = client[collection_name]['documents'].find_one({'_id': id})
    return result

if __name__ == "__main__":
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        raise ValueError("MONGO_URL environment variable is not set")
    collection_name = "G1"
    id = "52ef4b71ab137b00720007d4"
    data = get_data_for_thread(mongo_url=mongo_url, collection_name=collection_name, id=id)
    print(data)