import os
from dotenv import load_dotenv

load_dotenv()

# API Keys - REQUIRED (no defaults for security)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if DEEPSEEK_API_KEY is not None:
    DEEPSEEK_API_KEY = DEEPSEEK_API_KEY.strip()
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable is required")

DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
if DEEPSEEK_BASE_URL is not None:
    DEEPSEEK_BASE_URL = DEEPSEEK_BASE_URL.strip()
if not DEEPSEEK_BASE_URL:
    raise ValueError("DEEPSEEK_BASE_URL environment variable is required")

# OpenAI API (optional - only needed if using Whisper API instead of local)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional - local Whisper is used if not set
if OPENAI_API_KEY is not None:
    OPENAI_API_KEY = OPENAI_API_KEY.strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
if OPENAI_BASE_URL is not None:
    OPENAI_BASE_URL = OPENAI_BASE_URL.strip()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")

# Database Configuration - REQUIRED (no defaults for security)
PG_HOST = os.getenv("POSTGRES_HOST")
if not PG_HOST:
    raise ValueError("POSTGRES_HOST environment variable is required")

PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))  # Default PostgreSQL port
PG_DB = os.getenv("POSTGRES_DB")
if not PG_DB:
    raise ValueError("POSTGRES_DB environment variable is required")

PG_USER = os.getenv("POSTGRES_USER")
if not PG_USER:
    raise ValueError("POSTGRES_USER environment variable is required")

PG_PASS = os.getenv("POSTGRES_PASSWORD")
if not PG_PASS:
    raise ValueError("POSTGRES_PASSWORD environment variable is required")

PG_DIM = int(os.getenv("PGVECTOR_DIM", "1536"))

# File storage
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# Flashcard count range (user-selectable) - easy to modify
FLASHCARD_COUNT_MIN = 1
FLASHCARD_COUNT_MAX = 5

# JWT Authentication - REQUIRED (no defaults for security)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required. Generate a secure random key.")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
