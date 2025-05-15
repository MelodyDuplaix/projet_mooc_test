import os
from sql_script import base_postgres

#MongoDB
from pymongo import MongoClient

#Environnement
from dotenv import load_dotenv

load_dotenv()

def connexion_mongodb_local():
    MONGO_URL = os.getenv("MONGO_URL_LOCAL")
    client = MongoClient(MONGO_URL)
    return client

def add_thread_id():
    client = connexion_mongodb_local()
    cursor = client['mooc']['documents'].find().limit(10)
    for doc in cursor:
        thread_id = doc.get("thread_id", "")
        doc_id = doc.get("id", "")
        if thread_id and doc_id:
            requete = "UPDATE embedding SET thread_id = %s WHERE id = %s"
            base_postgres(requete, (thread_id, doc_id))
            print(f"Thread ID {thread_id} mis à jour pour le document ID {doc_id}")
            """requete = "UPDATE embedding SET thread_id = %s WHERE id = %s"
            base_postgres(requete, (thread_id, doc_id))"""

if __name__ == "__main__":
    add_thread_id()