import os
import ast
import time
import numpy as np
import pandas as pd
import pickle
from pymongo import MongoClient
from dotenv import load_dotenv
from psycopg2.extras import execute_values
import sys
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from api.services.database_helper import get_all_vectors_from_db, connect_to_db

MODEL_PICKLE_PATH = "data/model_bertopic.pkl"

def get_filtered_threads():
    """
    Récupère les threads filtrés et leurs vecteurs associés depuis les bases de données.

    Returns:
        pandas.DataFrame: DataFrame contenant les threads filtrés avec leurs vecteurs, titres et catégories.  Retourne un DataFrame vide si aucun thread correspondant n'est trouvé.
    """
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
    """
    Identifie les présentations parmi les threads en utilisant le clustering.

    Args:
        df (pandas.DataFrame): DataFrame contenant les threads avec une colonne 'category'.

    Returns:
        pandas.DataFrame: DataFrame avec une colonne 'type' ajoutée indiquant si chaque thread est une présentation ('présentation') ou non ('autre'). Retourne un DataFrame vide si le DataFrame d'entrée est vide ou s'il manque les colonnes nécessaires.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sentence_transformers import SentenceTransformer
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
    """
    Sauvegarde le modèle de topic dans un fichier pickle.

    Args:
        model (bertopic.BERTopic): Le modèle BERTopic à sauvegarder.
    """
    with open(MODEL_PICKLE_PATH, "wb") as f:
        pickle.dump(model, f)

def load_topic_model():
    """
    Charge le modèle de topic depuis un fichier pickle.

    Returns:
        bertopic.BERTopic or None: Le modèle BERTopic chargé, ou None si le fichier n'existe pas ou si le chargement échoue.
    """
    if os.path.exists(MODEL_PICKLE_PATH):
        with open(MODEL_PICKLE_PATH, "rb") as f:
            return pickle.load(f)
    return None

def apply_topic_modeling(df, save_model=True):
    """
    Applique la modélisation de sujets aux messages des threads.

    Args:
        df (pandas.DataFrame): DataFrame contenant les threads avec les colonnes 'message' et 'vector'.
        save_model (bool, optional):  Indique s'il faut sauvegarder le modèle entraîné. Defaults to True.

    Returns:
        dict: Un dictionnaire contenant le DataFrame traité, les informations sur les sujets, les mots clés et le modèle BERTopic. Retourne None si le DataFrame d'entrée est invalide ou si la modélisation des sujets échoue.
    """
    from bertopic import BERTopic
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
    """
    Sauvegarde les résultats de la modélisation des topics dans la base de données PostgreSQL.

    Args:
        conn: Objet de connexion à la base de données.
        df_messages (pandas.DataFrame): DataFrame contenant les messages et leurs ID de sujet.
        df_topics (pandas.DataFrame): DataFrame contenant les informations sur les sujets.
    """
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

class ClusteringDataCache:
    """Cache les données de clustering pour un accès plus rapide."""
    _instance = None

    def __init__(self):
        self.data = None
        self.last_load = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ClusteringDataCache()
        return cls._instance

    def reload(self, force=False):
        """
        Recharge les données de clustering depuis la base de données, en forçant un recalcul si nécessaire.

        Args:
            force (bool, optional):  Force le recalcul des données de clustering. Defaults to False.
        """
        if self.data is None or force:
            self.data = _load_all_clustering_data()
            self.last_load = time.time()

    def get_data(self):
        """
        Retourne les données de clustering mises en cache. Recharge les données si elles ne sont pas déjà en cache.

        Returns:
            dict: Les données de clustering mises en cache.
        """
        if self.data is None:
            self.reload()
        return self.data

def _load_all_clustering_data():
    """
    Charge toutes les données de clustering, soit depuis le cache, soit en les recalculant.

    Returns:
        dict: Un dictionnaire contenant toutes les données de clustering, y compris les statistiques, les tableaux, les détails des sujets, etc. Retourne None si le chargement ou le traitement des données échoue.
    """
    start = time.time()
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
    else:
        table_exists = False

    if model is None or not table_exists:
        df_raw = get_filtered_threads()
        df_filtered = identify_presentations(df_raw)
        result = apply_topic_modeling(df_filtered)
        save_topics_to_db(conn, result['df_messages'], result['df_topics'])
        df_messages = result['df_messages']
        df_topics = result['df_topics']
        topic_keywords = result['topic_keywords']
    else:
        with conn.cursor() as cur: # type: ignore
            cur.execute("SELECT id, topic_id FROM topic_messages")
            messages = cur.fetchall()
            cur.execute("SELECT topic_id, topic_name, topic_keywords, count FROM topic_info")
            topics = cur.fetchall()
        df_messages = pd.DataFrame(messages, columns=['id', 'topic'])
        df_topics = pd.DataFrame(topics, columns=['Topic', 'Name', 'topic_keywords', 'Count'])
        topic_keywords = {row['Topic']: row['topic_keywords'] for _, row in df_topics.iterrows()}

        # Pour les exemples de messages, il faut récupérer les textes depuis MongoDB
        mongo_url = os.getenv("MONGO_URL")
        client = MongoClient(mongo_url)
        db = client["G1"]
        collection = db["threads"]
        id_to_message = {doc["_id"]: doc.get("content", {}).get("body", "") for doc in collection.find({}, {"_id": 1, "content.body": 1})}
        df_messages["message"] = df_messages["id"].map(id_to_message).fillna("")

    # Statistiques globales
    total_topics = len(df_topics)
    total_messages = len(df_messages)
    mean_messages_per_topic = df_topics["Count"].mean() if total_topics > 0 else 0
    median_messages_per_topic = df_topics["Count"].median() if total_topics > 0 else 0

    # Tableau paginé/filtrable
    topics_table = [
        {
            "topic_id": int(row["Topic"]),
            "topic_name": row["Name"],
            "topic_keywords": row["topic_keywords"],
            "count": int(row["Count"])
        }
        for _, row in df_topics.iterrows()
    ]

    # Détails par topic
    topic_details = {}
    for _, row in df_topics.iterrows():
        topic_id = int(row["Topic"])
        messages = df_messages[df_messages["topic"] == topic_id]["message"].dropna().tolist()
        topic_details[topic_id] = {
            "topic_name": row["Name"],
            "topic_keywords": row["topic_keywords"],
            "count": int(row["Count"]),
            "messages": messages
        }

    end = time.time()
    print(f"Chargement clustering terminé en {end - start:.2f} secondes.")

    return {
        "stats": {
            "total_topics": total_topics,
            "total_messages": total_messages,
            "mean_messages_per_topic": mean_messages_per_topic,
            "median_messages_per_topic": median_messages_per_topic,
        },
        "topics_table": topics_table,
        "topic_details": topic_details,
        "df_messages": df_messages,
        "topic_keywords": topic_keywords
    }

def reload_or_recalculate(force=False):
    """
    Recharge ou recalcule les données de clustering en fonction du cache et du drapeau force.

    Args:
        force (bool, optional): Force un recalcul. Defaults to False.

    Returns:
        dict: Les données de clustering.
    """
    cache = ClusteringDataCache.get_instance()
    cache.reload(force=force)
    return cache.get_data()

def get_stats():
    """
    Retourne les statistiques de clustering.

    Returns:
        dict: Un dictionnaire contenant les statistiques de clustering.
    """
    return reload_or_recalculate()["stats"] # type: ignore

def get_topics_table():
    """
    Retourne le tableau des topics.

    Returns:
        list: Une liste de dictionnaires, où chaque dictionnaire représente un topic.
    """
    return reload_or_recalculate()["topics_table"] # type: ignore

def get_topic_details(topic_id):
    """
    Retourne les détails d'un topic spécifique.

    Args:
        topic_id (int): L'ID du topic.

    Returns:
        dict: Un dictionnaire contenant les détails du topic spécifié. Retourne un dictionnaire vide si le topic n'est pas trouvé.
    """
    return reload_or_recalculate()["topic_details"].get(topic_id, {}) # type: ignore

def get_all_data():
    """
    Retourne toutes les données de clustering.

    Returns:
        dict: Un dictionnaire contenant toutes les données de clustering.
    """
    return reload_or_recalculate()

def force_reload():
    """Force le rechargement des données de clustering, en ignorant le cache."""
    reload_or_recalculate(force=True)

if __name__ == "__main__":
    print("Lancement du traitement de clustering principal...")
    data = get_all_data()
    print(pd.DataFrame(data["topics_table"]).head()) # type: ignore
    print(f"Nombre de topics : {len(data['topic_keywords'])}") # type: ignore
    print(f"Exemple topic 0 : {data['topic_keywords'].get(0, 'Aucun')}") # type: ignore
