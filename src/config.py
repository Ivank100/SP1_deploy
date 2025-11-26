import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB   = os.getenv("POSTGRES_DB", "notebooklm")
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
PG_DIM  = int(os.getenv("PGVECTOR_DIM", "1536"))
