import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
import psycopg2
from scripts.mongo_helper import get_data_for_thread

load_dotenv()

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
if not all([db_host, db_port, db_name, db_user, db_password]):
    raise ValueError("One or more database environment variables are not set: (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)")

def connect_to_db():
    """
    Fonction qui se connecte à la base de données PostgreSQL.

    Returns:
        con: Connection à la base de données.
    """
    try:
        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        return connection
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None
    
def get_all_vectors_from_db(conn):
    """
    Récupère tous les vecteurs de la base de données.
    
    Args:
        conn: Connection à la base de données.
        
    Returns:
        list: Liste de tous les vecteurs.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM embedding")
        vectors = cursor.fetchall()
        return vectors
    except Exception as e:
        print(f"Error fetching vectors from the database: {e}")
        return []
    
def get_similar_documents(conn, id, limit=5):
    """
    Récupère les documents similaires à un document donné.
    
    Args:
        conn: Connection à la base de données.
        id: ID du document à comparer.
        limit: Nombre de documents similaires à récupérer.
        
    Returns:
        list: Liste de documents similaires.
    """
    try:
        query = """
        SELECT id, vector, 1 - (vector <=> (SELECT vector FROM embedding e2 WHERE id = %s)) AS similarity
        FROM embedding e 
        WHERE id != %s
        ORDER BY similarity DESC
        LIMIT %s;
        """
        cursor = conn.cursor()
        cursor.execute(query, (id, id, limit))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting similar documents: {e}")
        return []

def get_all_data_similar_documents(doc_list, mongo_url, collection_name):
    """
    Récupère les données de tous les messages similaires à partir de la liste d'IDs, et récupère le thread si c'est un message.
    
    Args:
        doc_list: Liste d'IDs de documents similaires.
        mongo_url: URL de connexion à MongoDB.
        collection_name: Nom de la collection dans MongoDB.
        
    Returns:
        list: Liste de données de documents similaires.
    """
    data_list = []
    seen = set()  # Ensemble pour suivre les combinaisons uniques (id, title)
    
    for doc in doc_list:
        id = doc[0]
        simalarity_score = doc[2]
        data = get_data_for_thread(mongo_url, collection_name, id)
        if data:
            data["similarity_score"] = simalarity_score
            unique_key = (data.get("id"), data.get("title"))
            
            if unique_key not in seen:
                seen.add(unique_key)
                if not data.get("title", False):
                    thread_id = data.get("thread_id", None)
                    thread_data = get_data_for_thread(mongo_url, collection_name, thread_id)
                    if thread_data:
                        thread_data["similarity_score"] = simalarity_score
                        thread_unique_key = (thread_data.get("id"), thread_data.get("title"))
                        if thread_unique_key not in seen:
                            seen.add(thread_unique_key)
                            data_list.append(thread_data)
                else:
                    data_list.append(data)
    return data_list

if __name__ == "__main__":
    conn = connect_to_db()
    if conn:
        first_doc = "52ef565b4b4451380f0008b2"
        print(f"First message ID: {first_doc}")
        similar_docs = get_similar_documents(conn, first_doc, limit=10)
        if similar_docs:
            similar_docs = get_all_data_similar_documents(similar_docs, os.getenv("MONGO_URL"), "G1")
            print(f"Found {len(similar_docs)} similar message.")
            for doc in similar_docs:
                print(doc["id"], doc["similarity_score"], doc["title"], doc["body"][:100])
        else:
            print("No similar messages found.")
        conn.close()
    else:
        print("Failed to connect to the database.")