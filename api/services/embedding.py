import json
import os

#Analyse sentiment
from transformers import AutoTokenizer, AutoModelForSequenceClassification # type: ignore
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
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    conn = None
    cursor = None
    results = None
    
    try:
        # Connexion à la base de données par défaut
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
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

def connexion_mongodb():
    MONGO_URL = os.getenv("MONGO_URL")
    client = MongoClient(MONGO_URL)
    return client

def embedding_message(message):
    """
    Fonction pour créer un embedding à partir d'un message.
    
    Args:
        message (str): Le message à encoder.
        
    Returns:
        list: Le vecteur d'embedding du message.
    """
    if not message:
        return None
    
    # Créer l'embedding
    embedding_vector = model_multilingue.encode(message)
    
    # Convertir le vecteur numpy en liste Python
    embedding_list = embedding_vector.tolist()
    
    return embedding_list

def add_embedding():
    client = connexion_mongodb()
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
    total_docs = client['G1']['documents'].count_documents({})
    # Calculer le nombre de documents restants à traiter
    remaining_docs = total_docs - len(existing_ids)
    
    print(f"Total des documents: {total_docs}")
    print(f"Documents restants à traiter: {remaining_docs}")
    
    # Si tous les documents sont déjà traités, terminer
    if remaining_docs <= 0:
        print("Tous les documents ont déjà été traités. Rien à faire.")
        return
    
    # Créer un filtre pour exclure les documents déjà traités
    # Note: Cette approche fonctionne mieux si le nombre d'IDs existants n'est pas trop grand
    processed = 0
    filtered_docs = 0
    
    # Traiter les documents par lots en excluant ceux déjà traités
    with tqdm(total=remaining_docs, desc="Traitement des documents restants") as pbar:
        # Pour chaque lot de documents
        while processed < remaining_docs:
            # Récupérer un lot de documents non traités
            cursor = client['G1']['documents'].find()
            batch_count = 0
            batch_docs = []
            
            for doc in cursor:
                doc_id = doc.get("id", "")
                if doc_id not in existing_ids:
                    batch_docs.append(doc)
                    batch_count += 1
                    filtered_docs += 1
                
                # Si nous avons assez de documents pour ce lot ou si nous avons parcouru tous les docs
                if batch_count >= batch_size or filtered_docs >= total_docs:
                    break
            
            if not batch_docs:
                break
                
            # Traiter ce lot de documents
            for doc in batch_docs:
                doc_id = doc.get("id", "")
                message = doc.get("body", "")
                
                if message == "":
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
            
            # Si nous avons parcouru tous les documents, terminer
            if filtered_docs >= total_docs:
                break
        
        print(f"Traitement terminé: {processed} nouveaux documents traités")

if __name__ == "__main__":
    add_embedding()