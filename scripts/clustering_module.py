import os
import ast
import time
import numpy as np
import pandas as pd
import pickle
from pymongo import MongoClient
from dotenv import load_dotenv
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
import psycopg2
from psycopg2.extras import execute_values
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.services.database_helper import get_all_vectors_from_db, connect_to_db

MODEL_PICKLE_PATH = "data/model_bertopic.pkl"

def get_filtered_threads():
    load_dotenv()
    conn = connect_to_db()
    all_data = get_all_vectors_from_db(conn)
    df = pd.DataFrame([(row[0], row[1]) for row in all_data], columns=['id', 'vector'])

    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    db = client["G1"]
    collection = db["threads"]

    valid_ids = set(doc["_id"] for doc in collection.find({}, {"_id": 1}))
    df = df[df["id"].isin(valid_ids)]

    complete_data, all_category, all_bodies = {}, {}, {}
    for doc in collection.find():
        complete_data[doc["_id"]] = doc.get("content", {}).get("title", "")
        all_category[doc["_id"]] = doc.get("content", {}).get("courseware_title", "")
        all_bodies[doc["_id"]] = doc.get("content", {}).get("body", "")

    df["title"] = df["id"].map(complete_data).fillna("")
    df["category"] = df["id"].map(all_category).fillna("")
    df["message"] = df["id"].map(all_bodies).fillna("")

    return df[(df["title"] != "") & (df["message"] != "")].copy()

def identify_presentations(df):
    df_thread = df[df["category"] != ""].copy()

    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    title_embeddings = model.encode(df_thread['title'].tolist())
    category_embeddings = model.encode(df_thread['category'].tolist())
    X = np.hstack((title_embeddings, category_embeddings))
    X = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=2, random_state=42)
    df_thread['cluster'] = kmeans.fit_predict(X)
    df_thread['type'] = df_thread['cluster'].replace(1, "présentation").replace(0, "autre")

    df = df.merge(df_thread[['id', 'type']], on='id', how='left')
    df['type'] = df['type'].fillna("autre")

    return df[df['type'] != "présentation"].copy()

def save_topic_model(model):
    with open(MODEL_PICKLE_PATH, "wb") as f:
        pickle.dump(model, f)

def load_topic_model():
    if os.path.exists(MODEL_PICKLE_PATH):
        with open(MODEL_PICKLE_PATH, "rb") as f:
            return pickle.load(f)
    return None

def apply_topic_modeling(df, save_model=True):
    documents = df["message"].tolist()
    embeddings = df["vector"].tolist()
    embeddings = [ast.literal_eval(e) if isinstance(e, str) else e for e in embeddings]
    embeddings = np.array(embeddings)

    model = BERTopic(verbose=True)
    topics, probs = model.fit_transform(documents, embeddings)

    if save_model:
        save_topic_model(model)

    df_topics = pd.DataFrame({"id": df["id"], "topic": topics})

    topic_info = model.get_topic_info()
    topic_keywords = {
        topic_num: ", ".join([w[0] for w in model.get_topic(topic_num)]) # type: ignore
        for topic_num in topic_info['Topic'] if topic_num != -1
    }
    df_topics['topic_keywords'] = df_topics['topic'].map(lambda x: topic_keywords.get(x, ""))

    df_messages = df.merge(df_topics, on="id", how="left")
    df_messages = df_messages.merge(topic_info, left_on="topic", right_on="Topic", how="left").drop(columns=["Topic"])

    df_topics_clean = topic_info.copy()
    df_topics_clean['topic_keywords'] = df_topics_clean['Topic'].map(lambda x: topic_keywords.get(x, ""))

    return {
        "df_messages": df_messages,
        "df_topics": df_topics_clean,
        "topic_keywords": topic_keywords,
        "model": model
    }

def save_topics_to_db(conn, df_messages, df_topics):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS topic_info (
            topic_id INTEGER PRIMARY KEY,
            topic_name TEXT,
            topic_keywords TEXT,
            count INTEGER
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS topic_messages (
            id TEXT PRIMARY KEY,
            topic_id INTEGER REFERENCES topic_info(topic_id)
        )
        """)

        cur.execute("DELETE FROM topic_messages")
        cur.execute("DELETE FROM topic_info")

        topic_info_values = [
            (int(row['Topic']), row['Name'], row['topic_keywords'], int(row['Count']))
            for _, row in df_topics.iterrows()
        ]
        execute_values(cur,
            "INSERT INTO topic_info (topic_id, topic_name, topic_keywords, count) VALUES %s",
            topic_info_values
        )

        topic_messages_values = [
            (row['id'], int(row['topic'])) for _, row in df_messages.iterrows()
        ]
        execute_values(cur,
            "INSERT INTO topic_messages (id, topic_id) VALUES %s",
            topic_messages_values
        )

    conn.commit()

def reload_or_recalculate():
    start = time.time()
    print("Début du chargement ou recalcul...")

    load_dotenv()
    conn = connect_to_db()
    model = load_topic_model()

    # vérifier si la table topic_messages existe
    if conn is not None:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'topic_messages'
            );
            """)
            table_exists = cur.fetchone()[0] # type: ignore

    if model is None or not table_exists:
        print("Aucun modèle trouvé ou table de données non existente. Recalcul en cours...")
        print("Chargement des données...")
        df_raw = get_filtered_threads()

        print("Filtrage des présentations...")
        df_filtered = identify_presentations(df_raw)

        print("Application de BERTopic...")
        result = apply_topic_modeling(df_filtered)

        print("Sauvegarde des résultats en base...")
        save_topics_to_db(conn, result['df_messages'], result['df_topics'])

        end = time.time()
        print(f"Recalcul terminé en {end - start:.2f} secondes.")
        return result
    else:
        print("Modèle trouvé et donnée trouvées. Chargement des données depuis la base PostgreSQL...")
        with conn.cursor() as cur: # type: ignore
            cur.execute("SELECT id, topic_id FROM topic_messages")
            messages = cur.fetchall()
            cur.execute("SELECT topic_id, topic_name, topic_keywords, count FROM topic_info")
            topics = cur.fetchall()
        df_messages = pd.DataFrame(messages, columns=['id', 'topic'])
        df_topics = pd.DataFrame(topics, columns=['Topic', 'Name', 'topic_keywords', 'Count'])
        topic_keywords = {row['Topic']: row['topic_keywords'] for _, row in df_topics.iterrows()}

        end = time.time()
        print(f"Chargement terminé en {end - start:.2f} secondes.")
        return {
            "df_messages": df_messages,
            "df_topics": df_topics,
            "topic_keywords": topic_keywords,
            "model": model
        }

if __name__ == "__main__":
    print("Lancement du traitement de clustering principal...")
    result = reload_or_recalculate()
    print(result["df_messages"].head())
    print(f"Nombre de topics : {len(result['topic_keywords'])}")
    print(f"Exemple topic 0 : {result['topic_keywords'].get(0, 'Aucun')}")
