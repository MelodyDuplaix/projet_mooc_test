import os
from pathlib import Path
from dotenv import load_dotenv


# Path
BASE_DIR = Path(__file__).resolve().parent
#MODELS_DIR = os.path.join(BASE_DIR, "models")
#DATA_DIR = os.path.join(BASE_DIR, "data")

#load_dotenv(os.path.join(BASE_DIR, ".env"))
#POSTGRES_URI = os.getenv("POSTGRES_URI")
#DB_SCHEMA = os.getenv("DB_SCHEMA")


HOST = "0.0.0.0"
PORT = 8000
RELOAD = True


LATTITUDE = 47.278
LONGITUDE = 0.6455