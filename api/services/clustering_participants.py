import os
import sys
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from psycopg2.extras import execute_values
import psycopg2
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from api.services.database_helper import connect_to_db
load_dotenv()

def get_mongo_conn():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
    client = MongoClient(mongo_url)
    db = client["G1"]
    return db

def fetch_user_profiles_and_content():
    db = get_mongo_conn()
    messages = list(db.documents.find({}))
    df_messages = pd.DataFrame(messages)
    threads = list(db.threads.find({}))
    df_threads = pd.DataFrame(threads)
    if 'content' in df_threads.columns:
        df_content = pd.json_normalize(df_threads['content'])
        df_content['_id'] = df_threads['_id']
    else:
        df_content = pd.json_normalize(threads)
    return df_content

def build_user_profiles(df_content):
    # On regroupe les informations par utilisateur (user_id)
    user_profiles = df_content.groupby('user_id').agg({
        'course_id': lambda x: list(set(x)),
        'body': lambda x: ' '.join(x) if 'body' in df_content.columns else '',
        'title': lambda x: ' || '.join(x) if 'title' in df_content.columns else '',
        'votes.count': 'sum',
        'comments_count': 'sum',
        'created_at': 'min',
        'updated_at': 'max',
        '_id': 'count'
    }).reset_index()
    user_profiles.rename(columns={'_id': 'nb_messages'}, inplace=True)
    user_profiles['engagement_score'] = (
        user_profiles['votes.count'].fillna(0)
        + user_profiles['comments_count'].fillna(0) * 2
        + user_profiles['nb_messages'] * 3
    )
    return user_profiles

def fetch_embeddings_from_postgres():
    conn = connect_to_db()
    query = """
    SELECT 
        embedding.id AS embedding_id,
        embedding.vector,
        embedding.thread_id,
        t1.course_id,
        c.name AS course_name
    FROM embedding
    LEFT JOIN threads t1 ON t1.id = embedding.id
    LEFT JOIN threads t2 ON t2.id = embedding.thread_id
    LEFT JOIN courses c ON c.id = COALESCE(t1.course_id, t2.course_id)
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def build_user_embeddings(df_content, df_emb):
    # Mapping thread_id -> user_id
    thread_to_user = df_content[['_id', 'user_id']].rename(columns={'_id': 'embedding_id'}).dropna()
    thread_user_mapping = dict(zip(thread_to_user['embedding_id'], thread_to_user['user_id']))
    df_emb['user_id'] = df_emb['embedding_id'].map(thread_user_mapping)
    df_emb = df_emb.dropna(subset=['user_id', 'vector'])
    def parse_vector(v):
        if isinstance(v, (list, tuple)) and isinstance(v[0], (float, np.floating, int)):
            return np.array(v)
        if isinstance(v, str):
            v = v.strip("[]()")
            return np.array([float(x) for x in v.split(",")])
        raise ValueError(f"Format inattendu pour le vecteur : {v}")
    mask_valid = df_emb['vector'].notnull()
    df_emb = df_emb[mask_valid].copy()
    df_emb['vector_np'] = df_emb['vector'].apply(parse_vector)
    user_embeddings = {}
    for user_id, group in df_emb.groupby('user_id'):
        vectors = list(group['vector_np'])
        if vectors:
            avg_embedding = np.mean(vectors, axis=0)
            user_embeddings[user_id] = avg_embedding
    return user_embeddings

def prepare_clustering_data(user_profiles, user_embeddings):
    users_with_embedding = list(set(user_profiles['user_id']) & set(user_embeddings.keys()))
    if not users_with_embedding:
        raise ValueError(
            f"Aucun utilisateur avec profil ET embedding. "
            f"Profils trouvés: {len(user_profiles)}, embeddings trouvés: {len(user_embeddings)}. "
            f"Exemple user_id profils: {user_profiles['user_id'].head(5).tolist()}, "
            f"embeddings: {list(user_embeddings.keys())[:5]}"
        )
    df_subset = user_profiles[user_profiles['user_id'].isin(users_with_embedding)].copy()
    embedding_matrix = np.array([user_embeddings[uid] for uid in df_subset['user_id']])
    engagement_features = df_subset[['votes.count', 'comments_count', 'nb_messages']].fillna(0).values
    scaler = StandardScaler()
    engagement_scaled = scaler.fit_transform(engagement_features)
    X_combined = np.hstack([embedding_matrix, engagement_scaled * 0.5])
    return X_combined, df_subset

def cluster_participants(X, df_subset, k=5):
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    df_subset = df_subset.copy()
    df_subset['cluster'] = labels
    return df_subset, kmeans

# --- STOCKAGE ET RECHERCHE EN BASE ---

def save_participant_clustering_to_db(df_clustered, X_combined):
    conn = connect_to_db()
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS participant_clusters (
            user_id TEXT PRIMARY KEY,
            cluster INTEGER,
            engagement_score FLOAT,
            nb_messages INTEGER,
            nb_votes INTEGER,
            nb_commentaires INTEGER,
            cours TEXT,
            vector FLOAT[]
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS participant_cluster_info (
            cluster INTEGER PRIMARY KEY,
            nb_utilisateurs INTEGER,
            engagement_score FLOAT,
            nb_messages FLOAT,
            nb_votes FLOAT,
            nb_commentaires FLOAT
        )
        """)
        cur.execute("DELETE FROM participant_clusters")
        cur.execute("DELETE FROM participant_cluster_info")
        values = [
            (
                row['user_id'],
                int(row['cluster']),
                float(row['engagement_score']),
                int(row['nb_messages']),
                int(row['votes.count']),
                int(row['comments_count']),
                ','.join(row['course_id']) if isinstance(row['course_id'], list) else '',
                list(X_combined[i])
            )
            for i, row in df_clustered.iterrows()
        ]
        execute_values(cur,
            "INSERT INTO participant_clusters (user_id, cluster, engagement_score, nb_messages, nb_votes, nb_commentaires, cours, vector) VALUES %s",
            values
        )
        stats = df_clustered.groupby('cluster').agg({
            'user_id': 'count',
            'engagement_score': 'mean',
            'nb_messages': 'mean',
            'votes.count': 'mean',
            'comments_count': 'mean'
        }).reset_index()
        info_values = [
            (
                int(row['cluster']),
                int(row['user_id']),
                float(row['engagement_score']),
                float(row['nb_messages']),
                float(row['votes.count']),
                float(row['comments_count'])
            )
            for _, row in stats.iterrows()
        ]
        execute_values(cur,
            "INSERT INTO participant_cluster_info (cluster, nb_utilisateurs, engagement_score, nb_messages, nb_votes, nb_commentaires) VALUES %s",
            info_values
        )
    conn.commit()

def load_participant_clustering_from_db():
    conn = connect_to_db()
    with conn.cursor() as cur:
        cur.execute("""
        SELECT user_id, cluster, engagement_score, nb_messages, nb_votes, nb_commentaires, cours, vector
        FROM participant_clusters
        """)
        rows = cur.fetchall()
        if not rows:
            return None, None
        df = pd.DataFrame(rows, columns=['user_id', 'cluster', 'engagement_score', 'nb_messages', 'votes.count', 'comments_count', 'course_id', 'vector'])
        df['cluster'] = df['cluster'].astype(int)
        df['engagement_score'] = df['engagement_score'].astype(float)
        df['nb_messages'] = df['nb_messages'].astype(int)
        df['votes.count'] = df['votes.count'].astype(int)
        df['comments_count'] = df['comments_count'].astype(int)
        df['course_id'] = df['course_id'].apply(lambda x: x.split(',') if x else [])
        X_combined = np.vstack(df['vector'].values)
        return df, X_combined

def run_participant_clustering(k=5, force=False):
    if not force:
        df_clustered, X_combined = load_participant_clustering_from_db()
        if df_clustered is not None and X_combined is not None:
            return {
                "df_clustered": df_clustered,
                "kmeans": None,
                "X_combined": X_combined
            }
    df_content = fetch_user_profiles_and_content()
    user_profiles = build_user_profiles(df_content)
    df_emb = fetch_embeddings_from_postgres()
    user_embeddings = build_user_embeddings(df_content, df_emb)
    X_combined, df_subset = prepare_clustering_data(user_profiles, user_embeddings)
    df_clustered, kmeans = cluster_participants(X_combined, df_subset, k=k)
    save_participant_clustering_to_db(df_clustered, X_combined)
    return {
        "df_clustered": df_clustered,
        "kmeans": kmeans,
        "X_combined": X_combined
    }

def get_cluster_stats(df_clustered):
    return df_clustered.groupby('cluster').agg({
        'votes.count': 'mean',
        'comments_count': 'mean',
        'nb_messages': 'mean',
        'engagement_score': 'mean',
        'user_id': 'count'
    }).rename(columns={'user_id': 'nb_utilisateurs'}).reset_index()

def get_top_courses_by_cluster(df_clustered, top_n=5):
    result = {}
    for cluster_id in sorted(df_clustered['cluster'].unique()):
        cluster_courses = []
        for courses_list in df_clustered[df_clustered['cluster'] == cluster_id]['course_id']:
            if isinstance(courses_list, list):
                cluster_courses.extend(courses_list)
        course_counts = pd.Series(cluster_courses).value_counts().head(top_n)
        result[cluster_id] = course_counts.to_dict()
    return result

def find_similar_users(user_id, df_clustered, X, top_n=5):
    if user_id not in df_clustered['user_id'].values:
        return []
    user_idx = df_clustered[df_clustered['user_id'] == user_id].index[0]
    user_cluster = df_clustered.loc[user_idx, 'cluster']
    same_cluster_indices = df_clustered[df_clustered['cluster'] == user_cluster].index
    user_vector = X[user_idx].reshape(1, -1)
    similarities = cosine_similarity(user_vector, X[same_cluster_indices]).flatten()
    sim_df = pd.DataFrame({
        'user_id': df_clustered.loc[same_cluster_indices, 'user_id'].values,
        'similarity': similarities
    })
    sim_df = sim_df[sim_df['user_id'] != user_id]
    top_similar = sim_df.sort_values('similarity', ascending=False).head(top_n)
    return top_similar

def recommend_similar_users(user_id, df_clustered, X, top_n=5):
    similaires = find_similar_users(user_id, df_clustered, X, top_n=top_n)
    details = df_clustered[df_clustered['user_id'].isin(similaires['user_id'])]
    resultats = []
    for _, row in details.iterrows():
        sim_score = similaires[similaires['user_id'] == row['user_id']]['similarity'].values[0]
        resultats.append({
            "user_id": row['user_id'],
            "similarité": float(sim_score),
            "engagement": float(row['engagement_score']),
            "nb_messages": int(row['nb_messages']),
            "nb_votes": int(row['votes.count']),
            "nb_commentaires": int(row['comments_count']),
            "cours": row['course_id'] if isinstance(row['course_id'], list) else []
        })
    return sorted(resultats, key=lambda x: x['similarité'], reverse=True)

def get_participant_clusters_info(df_clustered):
    stats = get_cluster_stats(df_clustered)
    top_courses = get_top_courses_by_cluster(df_clustered)
    return {
        "stats": stats,
        "top_courses": top_courses
    }

if __name__ == "__main__":
    # Lance le clustering (force recalcul si besoin)
    result = run_participant_clustering(k=5, force=True)
    df_clustered = result["df_clustered"]
    X_combined = result["X_combined"]

    # Affiche les stats de clusters
    print("Cluster stats :")
    print(get_cluster_stats(df_clustered))

    # Affiche les top cours par cluster
    print("\nTop cours par cluster :")
    print(get_top_courses_by_cluster(df_clustered))

    # Affiche les infos globales
    print("\nInfos globales :")
    print(get_participant_clusters_info(df_clustered))

    # Teste la recommandation d'utilisateurs similaires pour le premier utilisateur
    if not df_clustered.empty:
        test_user_id = df_clustered.iloc[0]['user_id']
        print(f"\nUtilisateurs similaires à {test_user_id} :")
        print(recommend_similar_users(test_user_id, df_clustered, X_combined, top_n=3))