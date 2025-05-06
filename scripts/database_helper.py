import os
from dotenv import load_dotenv
import psycopg2

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
    
if __name__ == "__main__":
    conn = connect_to_db()
    if conn:
        vectors = get_all_vectors_from_db(conn)
        if vectors:
            print(f"Fetched {len(vectors)} vectors from the database.")
        else:
            print("No vectors found in the database.")
        first_doc = vectors[0][0] if vectors else None
        print(f"First document ID: {first_doc}")
        similar_docs = get_similar_documents(conn, first_doc, limit=10)
        if similar_docs:
            print(f"Found {len(similar_docs)} similar documents.")
            for doc in similar_docs:
                print(doc)
        else:
            print("No similar documents found.")
        conn.close()
    else:
        print("Failed to connect to the database.")