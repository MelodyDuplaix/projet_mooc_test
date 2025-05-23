from typing import Dict
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.services import embedding
from api.services.auth import get_api_key
import config
from api.services.database_helper import connect_to_db, get_all_vectors_from_db, get_similar_documents, get_all_data_similar_documents, get_similars_messages_from_vector # Commented out as these are used in endpoints.py
from api.services.mongo_helper import get_data_for_thread
from api.services import sentiment as sentiment_analysis_service
from api.services import clustering_module
from api.services.clustering_participants import run_participant_clustering
import psycopg2

# Import the router from the endpoints file
from api.routers.endpoints import router

# Create FastAPI app
app = FastAPI(
    title="API",
    description="API pour analyser les threads et messages des forums de discussion des moocs de fun mooc",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_tags=[
        {
            "name": "Analyse de sentiments",
            "description": "Analyse de sentiments des messages et threads.",
        },
        {
            "name": "rag",
            "description": "Récupération de documents similaires.",
        },
        {
            "name": "check",
            "description": "Vérification de l'état du service.",
        },
    ]
)

# Mount static files from the templates folder
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

#app.mount("/assets", StaticFiles(directory="app/templates/assets",
#          html=True), name="assets")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router, include_in_schema=False)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.get("/api", tags=["check"], summary="Vérification de l'api", description="Route pour vérifier que l'api est en ligne.", 
         responses={200: {"description": "L'api est en ligne."}, 500: {"description": "L'api n'est pas en ligne."}}, 
         response_model=Dict[str, str])
async def periodic_update(request: Request, auth: dict = Depends(get_api_key)):
    return JSONResponse(content={"message": "Hello World!"})


@app.get(f"/api/similars", tags=["rag"], summary="Récupération de documents similaires", description="Route qui permet de récupérer les messages similaires à un message donné.", 
         responses={200: {"description": "Les messages similaires ont été récupérés avec succès."}, 404: {"description": "Aucun message similaire trouvé."}, 500: {"description": "Erreur lors de la récupération des messages similaires."}},
         response_model=Dict[str, str])
async def get_similars_for_tread(request: Request, id: str, auth: dict = Depends(get_api_key)):
    """
    Get the similar messages for a given thread ID.

    Args:
        request (Request): the request object.
        id (str): the thread ID to search for similar messages.
        auth (dict, optional): the authentication information. Defaults to Depends(get_api_key).

    Returns:
        JsonReponse: a JSON response containing an eventual error message and the data containing the similar messages and their similarity scores.
    """
    conn = connect_to_db()
    if conn:
        similar_docs = get_similar_documents(conn, id, limit=10)
        if similar_docs:
            similar_docs = get_all_data_similar_documents(similar_docs, os.getenv("MONGO_URL"), "G1", conn)
            conn.close()  
            return JSONResponse(content={"error": None, "data": similar_docs}, status_code=200)
        else:
            conn.close()  
            return JSONResponse(content={"error": "No similar messages found."}, status_code=404)  
    else:
        return JSONResponse(content={"error": "Failed to connect to the database."}, status_code=500)
    
@app.post("/api/thread_sentiment", tags=["Analyse de sentiments"], summary="Analyse de sentiments des threads", description="Route qui permet d'obtenir les résultats de l'analyse de sentiment d'un thread précis.", 
          responses={200: {"description": "Analyse de sentiment réussie."}, 500: {"description": "Erreur lors de l'analyse de sentiment."}},
          response_model=Dict[str, str])
async def analyse_thread_sentiment(request: Request, id:str, auth: dict = Depends(get_api_key)):

    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        return JSONResponse(content={"error": "MONGO_URL environment variable is not set"}, status_code=500)
    result = sentiment_analysis_service.get_message_for_thread(id, mongo_url, "G1")
    return JSONResponse(content=result)
 
@app.get("/api/answers", tags=["rag"], summary="Récupération de documents par rapport à une question", description="Route qui permet de récupérer les threads ayant des messages similaires à une question.", 
         responses={200: {"description": "Les messages similaires ont été récupérés avec succès."}, 404: {"description": "Aucun message similaire trouvé."}, 500: {"description": "Erreur lors de la récupération des messages similaires."}}, 
         response_model=Dict[str, str])
def get_threads_similars_for_text(request: Request, text: str, course_name: str | None, auth: dict = Depends(get_api_key)):
    """
    Get the similar messages for a given text.

    Args:
        request (Request): the request object.
        text (str): the text to search for similar messages.
        course_name (str): the course name to search for similar messages.
        auth (dict, optional): the authentication information. Defaults to Depends(get_api_key).

    Returns:
        JsonReponse: a JSON response containing an eventual error message and the data containing the similar messages and their similarity scores.
    """
    from api.services.embedding import embedding_message
    conn = connect_to_db()
    if conn:
        vector = embedding_message(text)
        if vector:
            similar_docs = get_similars_messages_from_vector(conn, vector, limit=10, course_name=course_name)
            if similar_docs:
                similar_docs = get_all_data_similar_documents(similar_docs, os.getenv("MONGO_URL"), "G1", conn)
                conn.close()  
                return JSONResponse(content={"error": None, "data": similar_docs}, status_code=200)
            else:
                conn.close()  
                return JSONResponse(content={"error": "No similar messages found."}, status_code=404)  
        else:
            conn.close()  
            return JSONResponse(content={"error": "Failed to create embedding."}, status_code=500)
        
    else:
        return JSONResponse(content={"error": "Failed to connect to the database."}, status_code=500)


@app.get("/api/clustering/all", tags=["clustering"], summary="Récupération de toutes les données de clustering", description="Route qui permet de récupérer toutes les données de clustering.", response_model=Dict[str, str])
async def get_all_clustering_data(request: Request, auth: dict = Depends(get_api_key)):
    data = clustering_module.get_all_data()
    if data:
        def convert_dataframes_to_dicts(data):
            if isinstance(data, dict):
                return {k: convert_dataframes_to_dicts(v) for k, v in data.items()}
            elif isinstance(data, pd.DataFrame):
                return data.to_dict(orient='records')
            elif isinstance(data, list):
                return [convert_dataframes_to_dicts(item) for item in data]
            else:
                return data
        return JSONResponse(content=convert_dataframes_to_dicts(data))
    else:
        return JSONResponse(content={"error": "No clustering data found."}, status_code=404)

@app.get("/api/clustering/stats", tags=["clustering"], summary="Récupération des statistiques de clustering", description="Route qui permet de récupérer les statistiques de clustering.", response_model=Dict[str, str])
async def get_clustering_stats(request: Request, auth: dict = Depends(get_api_key)):
    stats = clustering_module.get_stats()
    return JSONResponse(content=stats)

@app.get("/api/clustering/topics", tags=["clustering"], summary="Récupération du tableau des topics", description="Route qui permet de récupérer le tableau des topics.", response_model=Dict[str, str])
async def get_clustering_table(request: Request, auth: dict = Depends(get_api_key)):
    table = clustering_module.get_topics_table()
    return JSONResponse(content=table)

@app.get("/api/clustering/topic_details/{topic_id}", tags=["clustering"], summary="Récupération des détails d'un topic", description="Route qui permet de récupérer les détails d'un topic.", response_model=Dict[str, str])
async def get_clustering_topic_details(request: Request, topic_id: int, auth: dict = Depends(get_api_key)):
    details = clustering_module.get_topic_details(topic_id)
    return JSONResponse(content=details)

@app.post("/api/clustering/force_reload", tags=["clustering"], summary="Forcer le rechargement des données de clustering", description="Route qui permet de forcer le rechargement des données de clustering.", response_model=Dict[str, str])
async def force_reload_clustering_data(request: Request, auth: dict = Depends(get_api_key)):
    try:
        clustering_module.force_reload()
        return JSONResponse(content={"message": "success"})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

def check_table_exists(conn, table_name):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, (table_name,))
        return cur.fetchone()[0]

# Vérification des tables au démarrage
conn = connect_to_db()
if conn:
    required_tables = ["embedding", "courses", "threads"]
    missing_critical = [t for t in required_tables if not check_table_exists(conn, t)]
    if missing_critical:
        print(f"[CRITICAL] Les tables suivantes sont manquantes : {missing_critical}. Arrêt du serveur FastAPI.")
        import sys
        sys.exit(1)

    # Vérification participant_clusters
    participant_tables = ["participant_clusters", "participant_cluster_info"]
    missing_participant = [t for t in participant_tables if not check_table_exists(conn, t)]
    if missing_participant:
        print(f"[WARNING] Les tables {missing_participant} sont manquantes. Lancement du clustering participants...")
        run_participant_clustering(force=True)

    # Vérification topic_info/topic_messages
    topic_tables = ["topic_info", "topic_messages"]
    missing_topic = [t for t in topic_tables if not check_table_exists(conn, t)]
    if missing_topic:
        print(f"[WARNING] Les tables {missing_topic} sont manquantes. Lancement du clustering messages...")
        from api.services.clustering_module import reload_or_recalculate
        reload_or_recalculate(force=True)
    conn.close()
else:
    print("[CRITICAL] Impossible de se connecter à la base de données. Arrêt du serveur FastAPI.")
    import sys
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD)
