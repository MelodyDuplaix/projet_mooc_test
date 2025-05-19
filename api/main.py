from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from api.services import embedding # Commented out as embedding is imported inside a function in endpoints.py
from api.services.auth import get_api_key
import config
# from api.services.database_helper import connect_to_db, get_all_vectors_from_db, get_similar_documents, get_all_data_similar_documents, get_similars_messages_from_vector # Commented out as these are used in endpoints.py
# from api.services.mongo_helper import get_data_for_thread # Not used in the provided code snippets
# from api.services import sentiment as sentiment_analysis_service  # Import with a more descriptive alias # Used in endpoints.py
from pydantic import BaseModel

# Import the router from the endpoints file
from api.routers.endpoints import router

# Create FastAPI app
app = FastAPI(
    title="API",
    description="API pour analyser les threads et messages des forums de discussion des moocs de fun mooc",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files from the templates folder
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

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

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Include the router from api.routers.endpoints
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD)

