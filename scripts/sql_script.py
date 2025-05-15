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
    
def alter_table_thread_id():
    # D'abord, ajout de la colonne thread_id
    requete_add_column = """
    ALTER TABLE test.embedding
    ADD COLUMN thread_id varchar(255);
    """
    base_postgres(requete_add_column)
    
    # Ensuite, ajout de la contrainte de clé étrangère
    requete_add_foreign_key = """
    ALTER TABLE test.embedding
    ADD CONSTRAINT fk_thread
    FOREIGN KEY (thread_id) REFERENCES test.threads(id);
    """
    base_postgres(requete_add_foreign_key)

def create_course_table():
    requete = """
    CREATE TABLE IF NOT EXISTS test.courses (
        id SERIAL PRIMARY KEY,
        name TEXT
    );
    """
    base_postgres(requete)
    
def create_thread_table():
    requete = """
    CREATE TABLE IF NOT EXISTS test.threads (
        id varchar(255) PRIMARY KEY,
        course_id int,
        FOREIGN KEY (course_id) REFERENCES test.courses(id)
    );
    """
    base_postgres(requete)

if __name__ == "__main__":
    # Assurons-nous que le schéma 'test' existe d'abord
    requete_schema = "CREATE SCHEMA IF NOT EXISTS test;"
    base_postgres(requete_schema)
    
    # Ensuite, créons les tables
    create_course_table()
    create_thread_table()

    # alter table
    alter_table_thread_id()
