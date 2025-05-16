import os
import ast
import numpy as np
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.services.database_helper import get_all_vectors_from_db, connect_to_db


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

    complete_data = {}
    all_category = {}
    for doc in collection.find():
        complete_data[doc["_id"]] = doc.get("content", {}).get("title", "")
        all_category[doc["_id"]] = doc.get("content", {}).get("courseware_title", "")

    df["title"] = df["id"].map(complete_data).fillna("")
    df["category"] = df["id"].map(all_category).fillna("")
    
    return df[df["title"] != ""].copy()


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


def add_message_bodies(df):
    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    db = client["G1"]
    collection = db["threads"]

    documents = {}
    for doc in collection.find():
        documents[doc["_id"]] = doc.get("content", {}).get("body", "")

    df['message'] = df['id'].map(documents).fillna("")
    return df[df['message'] != ""].copy()


def apply_topic_modeling(df):
    documents = df["message"].tolist()
    embeddings = df["vector"].tolist()
    embeddings = [ast.literal_eval(e) if isinstance(e, str) else e for e in embeddings]
    embeddings = np.array(embeddings)

    model = BERTopic(verbose=True)
    topics, probs = model.fit_transform(documents, embeddings)

    df_topics = pd.DataFrame({"id": df["id"], "topic": topics})

    topic_info = model.get_topic_info()
    topic_keywords = {
        topic_num: ", ".join([w[0] for w in model.get_topic(topic_num)]) # type: ignore
        for topic_num in topic_info['Topic'] if topic_num != -1
    }
    df_topics['topic_keywords'] = df_topics['topic'].map(lambda x: topic_keywords.get(x, ""))

    df = df.merge(df_topics, on="id", how="left")
    df = df.merge(topic_info, left_on="topic", right_on="Topic", how="left").drop(columns=["Topic"])

    return {
        "df": df,
        "topic_info": topic_info,
        "topic_keywords": topic_keywords,
        "model": model
    }


if __name__ == "__main__":
    df_raw = get_filtered_threads()
    df_filtered = identify_presentations(df_raw)
    df_with_messages = add_message_bodies(df_filtered)
    result = apply_topic_modeling(df_with_messages)

    print(result["df"].head())
    print("Nombre de topics:", len(result["topic_keywords"]))
    print("Exemple topic:", result["topic_keywords"].get(0, "Aucun"))
