import json
import os

#Analyse sentiment
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np

#Embedding
from sentence_transformers import SentenceTransformer

#PostgreSQL
import psycopg2

#MongoDB
from pymongo import MongoClient

#Environnement
from dotenv import load_dotenv

#Barre de progression
from tqdm import tqdm

load_dotenv()

model_multilingue = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')


def base_postgres(requete, params=None, fetch_results=False):
    # Étape 1: Connexion à PostgreSQL
    # Récupération des variables d'environnement
    DB_HOST = os.getenv("DB_HOST_local")
    DB_PORT = os.getenv("DB_PORT_local")
    DB_USER = os.getenv("DB_USER_local")
    DB_PASSWORD = os.getenv("DB_PASSWORD_local")
    DB_NAME = os.getenv("DB_NAME_local")
    conn = None
    cursor = None
    results = None
    
    try:
        # Connexion à la base de données par défaut
        conn = psycopg2.connect(
            host=DB_HOST,
            port=int(DB_PORT),  # Convertir le port en entier
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        if params:
            cursor.execute(requete, params)
        else:
            cursor.execute(requete)
        
        # Si fetch_results est True, retourner les résultats
        if fetch_results:
            results = cursor.fetchall()
            
    except Exception as e:
        print(f"Erreur lors de la connexion à PostgreSQL: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return results

def connexion_mongodb_local():
    MONGO_URL = os.getenv("MONGO_URL_LOCAL")
    client = MongoClient(MONGO_URL)
    return client

def connexion_mongodb_distant():
    MONGO_URL = os.getenv("MONGO_URL_DIS")
    client = MongoClient(MONGO_URL)
    return client

def create_embedding_table():
    requete = """
    CREATE TABLE IF NOT EXISTS embedding (
        id TEXT PRIMARY KEY,
        vector vector(384)
    );
    """
    base_postgres(requete)

def add_embedding():
    client = connexion_mongodb_local()
    # Utiliser une taille de lot appropriée
    batch_size = 1000
    
    # Récupérer tous les IDs déjà traités dans PostgreSQL
    existing_ids = set()
    requete = "SELECT id FROM embedding"
    try:
        # Utiliser notre fonction base_postgres modifiée pour récupérer les IDs existants
        rows = base_postgres(requete, fetch_results=True)
        if rows:
            for row in rows:
                existing_ids.add(row[0])
        print(f"{len(existing_ids)} embeddings déjà traités trouvés dans la base de données")
    except Exception as e:
        print(f"Erreur lors de la récupération des IDs existants: {e}")
    
    # Récupérer le nombre total de documents
    total_docs = client['mooc']['documents'].count_documents({}) # Changer en "G1" si on veut traiter les documents de la base de données distantes
    # Calculer le nombre de documents restants à traiter
    remaining_docs = total_docs - len(existing_ids)
    
    print(f"Total des documents: {total_docs}")
    print(f"Documents restants à traiter: {remaining_docs}")
    
    # Si tous les documents sont déjà traités, terminer
    if remaining_docs <= 0:
        print("Tous les documents ont déjà été traités. Rien à faire.")
        return
    
    # Utiliser une approche avec skip/limit pour la pagination
    processed = 0
    skip = 0
    
    # Traiter les documents par lots en utilisant la pagination
    with tqdm(total=remaining_docs, desc="Traitement des documents restants") as pbar:
        while processed < remaining_docs:
            try:
                # Récupérer un lot de documents avec pagination
                cursor = client['mooc']['documents'].find().skip(skip).limit(batch_size) # Changer en "G1" si on veut traiter les documents de la base de données distantes
                batch_docs = list(cursor)  # Convertir en liste pour éviter les problèmes de timeout
                
                if not batch_docs:
                    break  # Plus de documents à traiter
                    
                # Incrémenter le skip pour la prochaine itération
                skip += len(batch_docs)
                
                # Traiter ce lot de documents
                batch_to_process = []
                for doc in batch_docs:
                    doc_id = doc.get("id", "")
                    if doc_id not in existing_ids:
                        batch_to_process.append(doc)
                
                for doc in batch_to_process:
                    doc_id = doc.get("id", "")
                    message = doc.get("body", "")
                    
                    if not message:
                        pbar.update(1)
                        processed += 1
                        continue
                        
                    embedding_vector = model_multilingue.encode(message)
                    # Convertir le vecteur numpy en liste Python
                    embedding_list = embedding_vector.tolist()
                    # Préparer la requête avec des paramètres
                    requete = "INSERT INTO embedding (id, vector) VALUES (%s, %s::vector) ON CONFLICT (id) DO NOTHING"
                    base_postgres(requete, (doc_id, str(embedding_list)))
                    
                    # Ajouter l'ID à l'ensemble des IDs déjà traités
                    existing_ids.add(doc_id)
                    
                    pbar.update(1)
                    processed += 1
                    
                # Si nous n'avons plus rien à traiter dans ce lot, vérifiez si nous avons fini
                if not batch_to_process and skip >= total_docs:
                    break
                    
            except Exception as e:
                print(f"Erreur lors du traitement du lot: {e}")
                # Attendre un peu avant de réessayer
                import time
                time.sleep(2)
        
        print(f"Traitement terminé: {processed} nouveaux documents traités")

if __name__ == "__main__":
    add_embedding()
