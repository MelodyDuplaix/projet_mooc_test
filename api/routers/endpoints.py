from fastapi import APIRouter, Request, Depends, Form, HTTPException, Path
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
from api.services.auth import get_api_key
from api.services.database_helper import connect_to_db, get_similar_documents, get_all_data_similar_documents, get_similars_messages_from_vector
from api.services.sentiment import get_message_for_thread
from api.services.embedding import embedding_message
from api.services.clustering_module import get_all_data, get_topic_details
from api.services.clustering_participants import run_participant_clustering, get_participant_clusters_info, recommend_similar_users
from pymongo import MongoClient

router = APIRouter()

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/recherche", response_class=HTMLResponse)
def recherche_form(request: Request):
    # This route definition might also be duplicated if it exists in main.py
    return templates.TemplateResponse("resultats.html", {"request": request})

@router.post("/recherche", response_class=HTMLResponse)
def recherche_submit(request: Request, query: str = Form(...)):
    # Add your actual search logic here
    resultats = [] # Replace with your real search logic
    return templates.TemplateResponse(
        "resultats.html",
        {
            "request": request,
            "query": query,
            "resultats": resultats
        }
    )

@router.get("/question", response_class=HTMLResponse)
def question_form(request: Request):
    # This route definition might also be duplicated if it exists in main.py
    return templates.TemplateResponse("question.html", {"request": request})

@router.post("/question", response_class=HTMLResponse, tags=["rag"]) # Ajout du tag rag pour cohérence
async def question_submit(request: Request, question: str = Form(...)): # Ajout de auth
    """
    Processes a user question, finds similar messages, and renders them in a HTML response.

    Args:
        request (Request): The request object.
        question (str): The user's question from the form.
        auth (dict, optional): The authentication information. Defaults to Depends(get_api_key).

    Returns:
        HTMLResponse: Renders the question.html template with the question and similar messages.
    """
    conn = connect_to_db()
    similar_docs = [] # Initialize similar_docs list

    if conn:
        vector = embedding_message(question)
        if vector:
            # Utilise la logique de recherche similaire à celle de /answers
            found_similar_docs = get_similars_messages_from_vector(conn, vector, limit=10)
            if found_similar_docs:
                similar_docs = get_all_data_similar_documents(found_similar_docs, os.getenv("MONGO_URL"), "G1", conn)
            # else: No similar messages found, similar_docs remains empty
        # else: Failed to create embedding, similar_docs remains empty

        conn.close() # Close connection regardless of finding documents

    # else: Failed to connect to the database, similar_docs remains empty

    return templates.TemplateResponse(
        "question.html",
        {
            "request": request,
            "question": question,
            "reponse": similar_docs
        }
    )

@router.get("/clustering_threads", response_class=HTMLResponse)
def clustering_threads(request: Request):
    data = get_all_data()
    return templates.TemplateResponse("clustering_threads.html", {"request": request, "data": data})

def get_mongo_conn():
    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    db = client["G1"]  # Remplace "G1" par le nom de ta base si besoin
    return db

@router.get("/discussion_thread", response_class=HTMLResponse)
async def discussion_thread_form(request: Request):
    db = get_mongo_conn()
    threads = list(db.threads.find({}, {"id": 1, "content.title": 1}))
    return templates.TemplateResponse("discussion_thread.html", {"request": request, "thread": None, "messages": [], "threads": threads})

@router.post("/discussion_thread", response_class=HTMLResponse)
async def discussion_thread_search(request: Request, thread_id: str = Form(...)):
    try:
        mongo_url = os.getenv("MONGO_URL")
        if not mongo_url:
            raise ValueError("MONGO_URL environment variable is not set")
        db = get_mongo_conn()
        thread_doc = db.documents.find_one({"_id": thread_id})
        thread_title = thread_doc["title"] if thread_doc else "Thread not found"
        messages = get_message_for_thread(thread_id, mongo_url, "G1")
        threads = list(db.threads.find({}, {"id": 1, "content.title": 1}))
    except Exception as e:
        messages = []
    return templates.TemplateResponse(
        "discussion_thread.html",
        {"request": request, "thread": {"title": thread_title}, "messages": messages, "threads": threads} 
    )

@router.get("/clustering_thread/{id}", response_class=HTMLResponse)
def clustering_thread_details(request: Request, id: int = Path(...)):
    topic_data = get_topic_details(id)
    if not topic_data:
        raise HTTPException(status_code=404, detail="Topic not found")
    return templates.TemplateResponse("topic_details.html", {"request": request, **topic_data})


@router.get("/thread/{thread_id}", response_class=HTMLResponse)
async def thread_page(request: Request, thread_id: str):
    db = get_mongo_conn()
    thread_doc = db.threads.find_one({"_id": thread_id})
    return templates.TemplateResponse("detail_thread.html", {"request": request, "thread": thread_doc})

@router.get("/clustering_participants", response_class=HTMLResponse)
def clustering_participants(request: Request):
    result = run_participant_clustering(k=5, force=False)
    df_clustered = result["df_clustered"]
    X_combined = result["X_combined"]
    clusters_info = get_participant_clusters_info(df_clustered)
    print(clusters_info["stats"])
    print(type(clusters_info["stats"]))
    return templates.TemplateResponse(
        "clustering_participants.html",
        {
            "request": request,
            "clusters_info": clusters_info,
            "df_clustered": df_clustered,
            "X_combined": X_combined
        }
    )

@router.post("/clustering_participants", response_class=HTMLResponse)
async def similarity_results(request: Request, user_id: str = Form(...)):
    result = run_participant_clustering(k=5, force=False)
    if not result or "df_clustered" not in result or result["df_clustered"].empty:
        return templates.TemplateResponse("clustering_participants.html", {"request": request, "error": "Erreur lors du clustering"})
    df_clustered = result["df_clustered"]
    X_combined = result["X_combined"]
    clusters_info = get_participant_clusters_info(df_clustered)
    
    matching_users = df_clustered[df_clustered['user_id'].str.contains(user_id, case=False, na=False)]
    if matching_users.empty:
        return templates.TemplateResponse("clustering_participants.html", {"request": request, "clusters_info": clusters_info, "df_clustered": df_clustered, "X_combined": X_combined, "error": "Aucun utilisateur trouvé"})
    
    selected_user = matching_users['user_id'].iloc[0] # Select the first matching user
    similarity_results = recommend_similar_users(selected_user, df_clustered, X_combined, top_n=3)
    return templates.TemplateResponse(
        "clustering_participants.html",
        {
            "request": request,
            "clusters_info": clusters_info,
            "df_clustered": df_clustered,
            "X_combined": X_combined,
            "similarity_results": similarity_results,
            "selected_user": selected_user
        }
    )
