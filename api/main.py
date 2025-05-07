from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.services.auth import get_api_key
import config
from api.services import sentiment as sentiment_analysis_service  # Import with a more descriptive alias
from pydantic import BaseModel



# Create FastAPI app
app = FastAPI(
    title="SmartHome",
    description="SmartHome description",
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


@app.get("/", tags=[""])
async def periodic_update(request: Request, auth: dict = Depends(get_api_key)):
    return JSONResponse(content={"message": "Hello World!"})


@app.post("/thread_sentiment", tags=["Analyse de sentiments"])
async def analyse_thread_sentiment(request: Request, id:str, auth: dict = Depends(get_api_key)):

    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        return JSONResponse(content={"error": "MONGO_URL environment variable is not set"}, status_code=500)
    result = sentiment_analysis_service.get_message_for_thread(id, mongo_url, "G1")
    return JSONResponse(content=result)
 

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD)

