# app/main.py
"""
Semantic Engine B2B - API Server Unificado
Motor de búsqueda semántica como servicio con soporte para archivos
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime

# starlette.concurrency.run_in_threadpool is no longer needed
from typing import List

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# IMPORTAR EL MIDDLEWARE y las KEYS
from .middleware import VALID_API_KEYS, RateLimitMiddleware
from .models import (
    BatchSearchQuery,
    BatchSearchResponse,
    ClientStats,
    DeleteResponse,
    DocumentInput,
    DocumentResponse,
    FileIndexResponse,
    HealthResponse,
    IndexResponse,
    SearchQuery,
    SearchResponse,
)

# removed auth import
from .service import RUST_AVAILABLE, UnifiedSearchService, get_vector_service

# Configuración Redis (Lazy loading para evitar crash al inicio)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    return _redis_client


# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("uvicorn")

# --- App Configuration ---
app = FastAPI(
    title="Semantic Engine B2B",
    description="Motor de búsqueda semántica de alto rendimiento para empresas (Unified)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(RateLimitMiddleware)

# CORS Configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
debug_mode = os.getenv("DEBUG", "false").lower() == "true"

if allowed_origins_env:
    origins = [origin.strip() for origin in allowed_origins_env.split(",")]
elif debug_mode:
    origins = ["*"]
else:
    # Production without allowed_origins - restrictive default
    origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }
    schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


# --- Dependency Injection ---
def get_service() -> UnifiedSearchService:
    service = get_vector_service()
    if service is None:
        raise RuntimeError("Service not initialized")
    return service


def get_client_namespace(api_key: str) -> str:
    """
    Genera un namespace único para el cliente
    Usado para aislar datos entre clientes
    """
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


# --- Health Endpoints ---
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Verifica el estado del servicio"""
    service = get_vector_service()
    return HealthResponse(
        status="healthy", version="2.0.0", rust_core_available=RUST_AVAILABLE, model_loaded=service.model is not None
    )


@app.get("/", tags=["UI"])
async def root():
    """Sirve la interfaz gráfica (Dashboard)"""
    return FileResponse("app/static/index.html")


# --- Ingestion Endpoints ---


@app.post("/v1/index", response_model=IndexResponse, tags=["Ingestion"])
async def index_documents(
    documents: List[DocumentInput],
    client_id: str = Header(..., alias="X-API-Key"),
    service: UnifiedSearchService = Depends(get_service),
):
    """
    Indexa documentos JSON puros.
    Ideal para datos estructurados o pre-procesados.
    """
    if not documents:
        raise HTTPException(status_code=400, detail="No se proporcionaron documentos")

    namespace = get_client_namespace(client_id)

    # Convertir a formato interno
    docs = [{"id": doc.id, "text": doc.text, "metadata": doc.metadata or {}} for doc in documents]

    result = await service.index_documents(namespace, docs)

    return IndexResponse(status="success", indexed_count=result["indexed_count"], client_id=client_id[:16] + "...")


@app.post("/v1/ingest/files", response_model=FileIndexResponse, tags=["Ingestion"])
async def ingest_file(
    file: UploadFile = File(...),
    metadata: str = Form(default="{}"),
    tags: str = Form(default="[]"),
    client_id: str = Header(..., alias="X-API-Key"),
    service: UnifiedSearchService = Depends(get_service),
):
    """
    Indexa archivos binarios (PDF, DOCX, Excel, CSV, TXT).
    Extrae texto automáticamente y genera embeddings.
    """
    try:
        meta_dict = json.loads(metadata)
    except json.JSONDecodeError:
        meta_dict = {}

    namespace = get_client_namespace(client_id)

    result = await service.ingest_file(
        namespace=namespace, file_obj=file.file, filename=file.filename, metadata=meta_dict
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return FileIndexResponse(
        status="success",
        document_id=result["document_id"],
        filename=file.filename,
        file_type=result["file_type"],
        content_length=result["content_length"],
        client_id=client_id[:16] + "...",
    )


# --- Search Endpoints ---


@app.post("/v1/search", response_model=SearchResponse, tags=["Search"])
async def search_documents(
    query: SearchQuery,
    client_id: str = Header(..., alias="X-API-Key"),
    service: UnifiedSearchService = Depends(get_service),
):
    """
    Búsqueda semántica individual.
    """
    namespace = get_client_namespace(client_id)

    result = await service.search(
        namespace=namespace, query=query.query, top_k=query.top_k, threshold=query.similarity_threshold
    )

    return SearchResponse(
        results=result["results"],
        query=query.query,
        total_documents=result["total_documents"],
        processing_time_ms=result["processing_time_ms"],
    )


@app.post("/v1/search/batch", response_model=BatchSearchResponse, tags=["Search"])
async def batch_search_documents(
    query_batch: BatchSearchQuery,
    client_id: str = Header(..., alias="X-API-Key"),
    service: UnifiedSearchService = Depends(get_service),
):
    """
    Búsqueda semántica por lotes (Múltiples queries).
    Altamente optimizada usando paralelismo en Rust.
    """
    namespace = get_client_namespace(client_id)

    result = await service.batch_search(
        namespace=namespace,
        queries=query_batch.queries,
        top_k=query_batch.top_k,
        threshold=query_batch.similarity_threshold,
    )

    return BatchSearchResponse(
        results=result["results"],
        queries=query_batch.queries,
        total_documents=result["total_documents"],
        processing_time_ms=result["processing_time_ms"],
    )


# --- Management Endpoints ---


@app.get("/v1/documents", response_model=List[DocumentResponse], tags=["Management"])
async def list_documents(
    limit: int = 20,
    client_id: str = Header(..., alias="X-API-Key"),
    service: UnifiedSearchService = Depends(get_service),
):
    """Lista los documentos indexados"""
    namespace = get_client_namespace(client_id)
    docs = await service.list_documents(namespace, limit)
    
    return [
        DocumentResponse(
            id=doc["id"],
            text_snippet=doc["text_snippet"],
            content_length=len(doc["text_snippet"]), # Simplificado para la lista
            metadata=doc["metadata"],
            indexed_at=datetime.fromtimestamp(doc["indexed_at"]) if doc["indexed_at"] else None,
        ) for doc in docs
    ]


@app.get("/v1/documents/{doc_id}", response_model=DocumentResponse, tags=["Management"])
async def get_document(
    doc_id: str, client_id: str = Header(..., alias="X-API-Key"), service: UnifiedSearchService = Depends(get_service)
):
    """Obtiene un documento por su ID"""
    namespace = get_client_namespace(client_id)
    # Optimization: Native async call
    doc = await service.get_document(namespace=namespace, doc_id=doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return DocumentResponse(
        id=doc["id"],
        text_snippet=doc["text"][:500],  # Preview
        content_length=len(doc["text"]),
        metadata=doc["metadata"],
        indexed_at=doc["indexed_at"],
    )


@app.delete("/v1/documents/{doc_id}", response_model=DeleteResponse, tags=["Management"])
async def delete_document(
    doc_id: str, client_id: str = Header(..., alias="X-API-Key"), service: UnifiedSearchService = Depends(get_service)
):
    """Elimina un documento específico"""
    namespace = get_client_namespace(client_id)
    # Optimization: Native async call
    deleted = await service.delete_document(namespace, doc_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return DeleteResponse(status="success", message=f"Documento {doc_id} eliminado", deleted_count=1)


@app.get("/v1/stats", response_model=ClientStats, tags=["Account"])
async def get_client_stats(
    client_id: str = Header(..., alias="X-API-Key"), service: UnifiedSearchService = Depends(get_service)
):
    """Obtiene estadísticas del índice del cliente"""
    namespace = get_client_namespace(client_id)
    # Optimization: Native async call
    stats = await service.get_stats(namespace)

    return ClientStats(
        client_id=client_id[:16] + "...",
        total_documents=stats["total_documents"],
        embedding_dimension=stats["embedding_dimension"],
        rust_acceleration=stats["rust_acceleration"],
    )


@app.delete("/v1/index", response_model=DeleteResponse, tags=["Management"])
async def clear_index(
    client_id: str = Header(..., alias="X-API-Key"), service: UnifiedSearchService = Depends(get_service)
):
    """Elimina todos los documentos indexados del cliente"""
    namespace = get_client_namespace(client_id)
    # Optimization: Native async call
    await service.clear_namespace(namespace)

    return DeleteResponse(status="success", message="Índice limpiado correctamente", deleted_count=-1)


@app.get("/v1/usage", tags=["Account"])
async def get_usage_stats(client_id: str = Header(..., alias="X-API-Key")):
    """
    Reporte de consumo en tiempo real para Dashboard de Clientes.
    Muestra uso diario y estado del Rate Limit actual.
    """
    today = time.strftime("%Y-%m-%d")
    current_minute = int(time.time() // 60)

    # Keys
    usage_key = f"usage:{client_id}:{today}"
    rate_key = f"ratelimit:{client_id}:{current_minute}"

    try:
        redis_conn = get_redis_client()
        # Obtener datos de Redis
        total_today, current_rpm = await asyncio.gather(redis_conn.get(usage_key), redis_conn.get(rate_key))
        total_today = total_today or 0
        current_rpm = current_rpm or 0

        # Determinar Plan Usando Datos Centralizados (Redis -> Fallback)
        client_data_str = await redis_conn.hget("api_keys", client_id)
        if client_data_str:
            client_data = json.loads(client_data_str)
        else:
            client_data = VALID_API_KEYS.get(client_id, {})

        plan = client_data.get("tier", "default").capitalize()
        limit = 1000 if plan.lower() == "premium" else 50

        return {
            "client_id": f"{client_id[:8]}...",
            "plan": plan,
            "period": today,
            "usage": {
                "requests_today": int(total_today),
                "current_rpm": int(current_rpm),  # Requests Per Minute actuales
                "limit_rpm": limit,
            },
            "status": "healthy" if int(current_rpm) < limit else "throttled",
        }
    except aioredis.RedisError:
        raise HTTPException(status_code=503, detail="Servicio de métricas no disponible")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
