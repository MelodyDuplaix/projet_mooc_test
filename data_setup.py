import csv
from embedding_utils import embed_content
from db_utils import create_table, insert_data, connect_db, get_embedding, get_similar_documents, create_similarity_indexes_table, get_all_documents
import google.generativeai as genai
# from google.genai import types  # Ce module n'existe pas dans google-generativeai
import os
from dotenv import load_dotenv
import time
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Request

app = FastAPI()

load_dotenv()

API_KEY = os.getenv("GENAI_API_KEY")

# Configure l'API Google Generative AI si la clé API est disponible
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    print("Attention : Clé API GENAI non trouvée. Les fonctionnalités d'IA seront désactivées.")

templates = Jinja2Templates(directory="api/templates")

def insert_documents(cursor, client):
    try:
        csv_file = open('data/doc_embed.csv', 'r', newline='', encoding='utf-8')
        csv_reader = csv.reader(csv_file)
        next(csv_reader)

        for row in csv_reader:
            id = row[0]
            content = row[1]
            embeddings = embed_content(client, content)
            if embeddings:
                embeddings = [float(x) for x in embeddings]
                insert_data(cursor, id, content, embeddings)
            time.sleep(1)

        csv_file.close()
    except Exception as e:
        print(f"An error occurred during document insertion: {e}")


def get_similar_docs(cursor, doc_id):
    try:
        first_embedding = get_embedding(cursor, doc_id)
        if first_embedding:
            similar_rows = get_similar_documents(cursor, first_embedding)
            for row in similar_rows:
                print(f"ID: {row[0]}, Text: {row[1]}, Similarity: {row[3]}")
    except Exception as e:
        print(f"An error occurred during similar document retrieval: {e}")


# conn = connect_db()
# if conn:
#     cursor = conn.cursor()
#     get_similar_docs(cursor, 2)
#     data = create_similarity_indexes_table(cursor)
#     csv.writer(open('data/similarity_indexes.csv', 'w', newline='', encoding='utf-8')).writerows(data)
#     data = get_all_documents(cursor)
#     csv.writer(open('data/documents.csv', 'w', newline='', encoding='utf-8')).writerows(data)
#     conn.close()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
