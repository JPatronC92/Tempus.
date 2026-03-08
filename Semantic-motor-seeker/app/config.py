import os
import json

# --- Environment & Debug ---
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",")] if os.getenv("ALLOWED_ORIGINS") else []

# --- Security ---
API_KEY_HEADER_NAME = "X-API-Key"

def load_api_keys():
    """
    Carga y valida las API Keys desde variables de entorno.
    Implementa estrategia Fail-Fast para entornos productivos.
    """
    env_keys = os.getenv("VALID_API_KEYS")

    if not env_keys:
        if DEBUG:
            return {}
        raise ValueError("CRITICAL: La variable de entorno VALID_API_KEYS es obligatoria en producción.")

    try:
        return json.loads(env_keys)
    except json.JSONDecodeError as e:
        if DEBUG:
            return {}
        raise ValueError(f"CRITICAL: Formato JSON inválido en VALID_API_KEYS: {e}")

VALID_API_KEYS = load_api_keys()

# --- Embedding Model ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
VECTOR_SIZE = 384

# --- Qdrant ---
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

if not DEBUG and not QDRANT_API_KEY:
    raise ValueError("CRITICAL: QDRANT_API_KEY is mandatory in production.")

# --- Redis ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

if not DEBUG and not REDIS_PASSWORD:
    raise ValueError("CRITICAL: REDIS_PASSWORD is mandatory in production.")

# --- File Uploads ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# --- Metadata ---
ALLOWED_METADATA_KEYS = {"source", "author", "date", "tags", "category", "title", "url"}
EXCLUDED_METADATA_KEYS = {"text_snippet", "full_text", "original_id"}

# --- Rate Limiting ---
TIERS = {
    "default": 50,
    "premium": 1000,
    "internal": 99999
}
