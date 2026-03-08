# Compatibility shim. Implementation lives in app.engine
from sentence_transformers import SentenceTransformer
from qdrant_client import AsyncQdrantClient

from .engine import (
    UnifiedSearchService,
    get_vector_service,
    RUST_AVAILABLE,
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL,
)

__all__ = [
    "UnifiedSearchService",
    "get_vector_service",
    "RUST_AVAILABLE",
    "EMBEDDING_DEVICE",
    "EMBEDDING_MODEL",
    "SentenceTransformer",
    "AsyncQdrantClient",
]
