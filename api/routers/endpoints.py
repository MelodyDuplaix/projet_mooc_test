from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
from api.services.auth import get_api_key
from api.services.database_helper import connect_to_db, get_similar_documents, get_all_data_similar_documents, get_similars_messages_from_vector
from api.services import sentiment as sentiment_analysis_service
from api.services.embedding import embedding_message
from api.services.clustering_module import get_all_data

router = APIRouter()

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

def get_flag(langue):
    """Helper function to get flag emojis for languages (if used in template)."""
    flags = {
        "fr": "🇫🇷",
        "en": "🇬🇧",
        "es": "🇪🇸",
        "de": "🇩🇪",
        "it": "🇮🇹",
        # Add other languages if needed
    }
    return flags.get(langue, "🏳️") # White flag if language is unknown

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
async def question_submit(request: Request, question: str = Form(...), auth: dict = Depends(get_api_key)): # Ajout de auth
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


    # Adapter le renvoi de la réponse pour utiliser le template et les résultats
    return templates.TemplateResponse(
        "question.html",
        {
            "request": request,
            "question": question,
            "reponse": similar_docs
        }
    )

@router.get("/discussion", response_class=HTMLResponse)
def discussion_page(request: Request):
    # This route definition might also be duplicated if it exists in main.py
    messages = [
        {"auteur": "Alice", "texte": "Super projet !", "sentiment": "Très positif", "langue": "fr"},
        {"auteur": "Bob", "texte": "Pas mal", "sentiment": "Positif", "langue": "fr"},
        {"auteur": "Eve", "texte": "Bof", "sentiment": "Neutre", "langue": "en"},
        {"auteur": "John", "texte": "Nul", "sentiment": "Négatif", "langue": "fr"},
        {"auteur": "Jane", "texte": "Horrible", "sentiment": "Très négatif", "langue": "fr"},
    ]
    nb_tres_positif = sum(1 for m in messages if m["sentiment"] == "Très positif")
    nb_positif = sum(1 for m in messages if m["sentiment"] == "Positif")
    nb_neutre = sum(1 for m in messages if m["sentiment"] == "Neutre")
    nb_negatif = sum(1 for m in messages if m["sentiment"] == "Négatif")
    nb_tres_negatif = sum(1 for m in messages if m["sentiment"] == "Très négatif")
    langues = list(set(m["langue"] for m in messages))
    thread = {"titre": "Avis du forum", "messages": messages}
    return templates.TemplateResponse(
        "discussion_thread.html",
        {
            "request": request,
            "thread": thread,
            "nb_tres_positif": nb_tres_positif,
            "nb_positif": nb_positif,
            "nb_neutre": nb_neutre,
            "nb_negatif": nb_negatif,
            "nb_tres_negatif": nb_tres_negatif,
            "langues": langues,
            "get_flag": get_flag,
        }
    )

@router.get("/clustering_threads", response_class=HTMLResponse)
def clustering_threads(request: Request):
    data = get_all_data()
    return templates.TemplateResponse("clustering_threads.html", {"request": request, "data": data})

@router.get("/clustering_participants", response_class=HTMLResponse)
def clustering_participants(request: Request):
    # This route definition might also be duplicated if it exists in main.py
    clusters = [
        {
            "nom": "Gros contributeurs",
            "participants": [
                {"nom": "Alice", "nb_messages": 42, "langue": "fr", "role": "apprenant", "style": "positif", "forums": ["IA", "Python"]},
                {"nom": "Bob", "nb_messages": 38, "langue": "en", "role": "apprenant", "style": "neutre", "forums": ["Python", "Projet final"]}
            ]
        },
        {
            "nom": "Nouveaux inscrits",
            "participants": [
                {"nom": "Eve", "nb_messages": 5, "langue": "fr", "role": "apprenant", "style": "positif", "forums": ["Introduction"]},
                {"nom": "John", "nb_messages": 3, "langue": "en", "role": "apprenant", "style": "neutre", "forums": ["Introduction", "Projet final"]}
            ]
        },
        {
            "nom": "Modérateurs",
            "participants": [
                {"nom": "Jane", "nb_messages": 60, "langue": "fr", "role": "modérateur", "style": "positif", "forums": ["IA", "Python", "Projet final"]}
            ]
        }
    ]
    return templates.TemplateResponse(
        "clustering_participants.html",
        {"request": request, "clusters": clusters, "get_flag": get_flag}
    )

@router.get("/discussion_thread", response_class=HTMLResponse)
def discussion_thread_page(request: Request):
    # This route definition might also be duplicated if it exists in main.py
    messages = [
        {"auteur": "Alice", "texte": "Super projet !", "sentiment": "Très positif", "langue": "fr"},
        {"auteur": "Bob", "texte": "Pas mal", "sentiment": "Positif", "langue": "fr"},
        {"auteur": "Eve", "texte": "Bof", "sentiment": "Neutre", "langue": "en"},
        {"auteur": "John", "texte": "Nul", "sentiment": "Négatif", "langue": "fr"},
        {"auteur": "Jane", "texte": "Horrible", "sentiment": "Très négatif", "langue": "fr"},
    ]
    nb_tres_positif = sum(1 for m in messages if m["sentiment"] == "Très positif")
    nb_positif = sum(1 for m in messages if m["sentiment"] == "Positif")
    nb_neutre = sum(1 for m in messages if m["sentiment"] == "Neutre")
    nb_negatif = sum(1 for m in messages if m["sentiment"] == "Négatif")
    nb_tres_negatif = sum(1 for m in messages if m["sentiment"] == "Très négatif")
    langues = list(set(m["langue"] for m in messages))
    thread = {"titre": "Avis du forum", "messages": messages}
    return templates.TemplateResponse(
        "discussion_thread.html",
        {
            "request": request,
            "thread": thread,
            "nb_tres_positif": nb_tres_positif,
            "nb_positif": nb_positif,
            "nb_neutre": nb_neutre,
            "nb_negatif": nb_negatif,
            "nb_tres_negatif": nb_tres_negatif,
            "langues": langues,
            "get_flag": get_flag,
        }
    )

# Ajoute ici d'autres routes comme dans l'ancien main.py si besoin
