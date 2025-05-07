from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.services import embedding
from api.services.auth import get_api_key
import config
from api.services.database_helper import connect_to_db, get_all_vectors_from_db, get_similar_documents, get_all_data_similar_documents, get_similars_messages_from_vector
from api.services.mongo_helper import get_data_for_thread


# Create FastAPI app
app = FastAPI(
    title="API",
    description="API pour analyser les threads et messages des forums de discussion des moocs de fun mooc",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files from the templates folder
#app.mount("/static", StaticFiles(directory="app/templates",
#          html=True), name="static")

#app.mount("/assets", StaticFiles(directory="app/templates/assets",
#          html=True), name="assets")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["check"])
async def periodic_update(request: Request, auth: dict = Depends(get_api_key)):
    return JSONResponse(content={"message": "Hello World!"})


@app.get(f"/similars", tags=["rag"])
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
 
@app.get("/answers", tags=["rag"])
def get_threads_similars_for_text(request: Request, text: str, auth: dict = Depends(get_api_key)):
    """
    Get the similar messages for a given text.

    Args:
        request (Request): the request object.
        text (str): the text to search for similar messages.
        auth (dict, optional): the authentication information. Defaults to Depends(get_api_key).

    Returns:
        JsonReponse: a JSON response containing an eventual error message and the data containing the similar messages and their similarity scores.
    """
    from api.services.embedding import embedding_message
    conn = connect_to_db()
    if conn:
        vector = embedding_message(text)
        if vector:
            similar_docs = get_similars_messages_from_vector(conn, vector, limit=10)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD)

 