"""This file loads configuration values from environment variables.
It centralizes settings like database, model, auth, and file storage options."""


import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI-compatible API configuration used for chat, embeddings, and optional Whisper.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY is not None:
    OPENAI_API_KEY = OPENAI_API_KEY.strip()
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
if OPENAI_BASE_URL is not None:
    OPENAI_BASE_URL = OPENAI_BASE_URL.strip()
if not OPENAI_BASE_URL:
    raise ValueError("OPENAI_BASE_URL environment variable is required")

# Chat model (e.g. gpt-4o-mini for OpenAI or another OpenAI-compatible provider)
LLM_CHAT_MODEL = os.getenv("LLM_CHAT_MODEL", "gpt-4o-mini")
if LLM_CHAT_MODEL is not None:
    LLM_CHAT_MODEL = LLM_CHAT_MODEL.strip()

# Embedding model used for chunk and query vectors.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
if EMBEDDING_MODEL is not None:
    EMBEDDING_MODEL = EMBEDDING_MODEL.strip()

# Whisper API settings. The same OpenAI key/base URL above are reused if local Whisper is unavailable.
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
