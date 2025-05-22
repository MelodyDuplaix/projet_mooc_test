import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
import psycopg2
from api.services.mongo_helper import get_data_for_thread
import csv
from datetime import datetime

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
    
def get_all_vectors_from_db(conn, limit=10000000000):
    """
    Récupère tous les vecteurs de la base de données.
    
    Args:
        conn: Connection à la base de données.
        
    Returns:
        list: Liste de tous les vecteurs.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM embedding LIMIT %s;", (limit,))
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
        WITH reference AS (
            SELECT 
                e.vector AS ref_vector,
                c.name AS course_name
            FROM embedding e
            JOIN threads t ON t.id = e.id
            JOIN courses c ON c.id = t.course_id
            WHERE e.id = %s
        )
        SELECT 
            e.id,
            e.vector,
            1 - (e.vector <=> r.ref_vector) AS similarity,
            c.name
        FROM embedding e
        LEFT JOIN threads t1 ON t1.id = e.id
        LEFT JOIN threads t2 ON t2.id = e.thread_id
        LEFT JOIN courses c ON c.id = COALESCE(t1.course_id, t2.course_id)
        JOIN reference r ON c.name = r.course_name
        WHERE e.id != %s
        ORDER BY similarity DESC
        LIMIT %s;
        """
        cursor = conn.cursor()
        cursor.execute(query, (id, id, limit))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting similar documents: {e}")
        return []
    
def get_similars_messages_from_vector(conn, vector, limit=5, course_name=None):
    """
    Récupère les messages (ou threads) similaires à un vecteur donné, avec ou sans filtrage par cours.
    
    Args:
        conn: Connexion à la base de données.
        vector: Vecteur à comparer.
        limit: Nombre d'éléments similaires à récupérer.
        course_name: Nom du cours (optionnel). Si None, cherche dans tous les cours.
        
    Returns:
        list: Liste d'éléments similaires.
    """
    try:
        print(vector)
        
        # Clause WHERE dynamique
        where_clause = "WHERE c.name = %s" if course_name else ""
        
        query = f"""
        WITH embeddings_with_course AS (
            SELECT 
                e.id,
                e.vector,
                c.name AS course_name
            FROM embedding e
            LEFT JOIN threads t1 ON t1.id = e.id
            LEFT JOIN threads t2 ON t2.id = e.thread_id
            LEFT JOIN courses c ON c.id = COALESCE(t1.course_id, t2.course_id)
            {where_clause}
        )
        SELECT 
            id,
            vector,
            1 - (vector <=> %s::vector) AS similarity
        FROM embeddings_with_course
        ORDER BY similarity DESC
        LIMIT %s;
        """
        
        cursor = conn.cursor()
        if course_name:
            cursor.execute(query, (course_name, vector, limit))
        else:
            cursor.execute(query, (vector, limit))
        
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting similar messages: {e}")
        return []

def get_similarity_score_between_vectors(conn, id1, id2):
    """
    Récupère le score de similarité entre deux vecteurs.

    Args:
        conn (conn): Connection à la base de données.
        id1 (str): ID du premier vecteur.
        id2 (str): ID du deuxième vecteur.
    """
    try:
        query = """
        SELECT 1 - (vector <=> (SELECT vector FROM embedding e2 WHERE id = %s)) AS similarity
        FROM embedding e 
        WHERE id = %s;
        """
        cursor = conn.cursor()
        cursor.execute(query, (id2, id1))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting similarity score: {e}")
        return None

def get_all_data_similar_documents(doc_list, mongo_url, collection_name, conn):
    """
    Récupère toutes les données des documents similaires à partir de la liste de documents fournie.

    Args:
        doc_list (list): Liste de documents similaires.
        mongo_url (str): URL de connexion à la base de données MongoDB.
        collection_name (str): Nom de la collection dans MongoDB.
        conn (conn): Connection à la base de données PostgreSQL.

    Returns:
        list[dict]: Liste de dictionnaires contenant les données des documents similaires.
    """
    data_list = []
    seen = set()
    thread_children_map = {}

    for doc in doc_list:
        id = doc[0]
        similarity_score = doc[2]
        data = get_data_for_thread(mongo_url, collection_name, id)
        if data:
            data["similarity_score"] = similarity_score
            unique_key = (data.get("id"), data.get("title"))

            if unique_key not in seen:
                seen.add(unique_key)
                if not data.get("title", False):
                    thread_id = data.get("thread_id", None)
                    if thread_id:
                        if thread_id not in thread_children_map:
                            thread_children_map[thread_id] = []
                        thread_children_map[thread_id].append({
                            "id": id,
                            "similarity_score": similarity_score
                        })
                else:
                    data_list.append(data)

    for thread_id, children_data in thread_children_map.items():
        thread_data = get_data_for_thread(mongo_url, collection_name, thread_id)
        if thread_data:
            thread_data["similarity_score"] = get_similarity_score_between_vectors(
                conn, thread_id, children_data[0]["id"]
            )
            thread_data["similar_messages"] = children_data
            unique_key = (thread_data.get("id"), thread_data.get("title"))
            if unique_key not in seen:
                seen.add(unique_key)
                data_list.append(thread_data)

    return data_list

if __name__ == "__main__":
    conn = connect_to_db()
    if conn:
        first_doc = "57458c6954ecc0b0c30001d6"
        print(f"First message ID: {first_doc}")
        similar_docs = get_similar_documents(conn, first_doc, limit=10)
        if similar_docs:
            similar_docs = get_all_data_similar_documents(similar_docs, os.getenv("MONGO_URL"), "G1", conn)
            print(f"Found {len(similar_docs)} similar message.")
            for doc in similar_docs:
                print(doc["id"], doc["similarity_score"], doc["title"], doc.get("similar_messages", []))
            csv_file = f"data/similar_messages.csv"
            with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                for doc in similar_docs:
                    writer.writerow([doc["id"], doc["similarity_score"], doc["title"], doc.get("similar_messages", []), datetime.now()])
        else:
            print("No similar messages found.")
        conn.close()
    else:
        print("Failed to connect to the database.") 