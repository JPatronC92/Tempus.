# app/models.py
"""
Modelos Pydantic para la API B2B
Motor de Búsqueda Semántica Unificado
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# --- Input Models ---
class DocumentInput(BaseModel):
    """Documento para indexar (JSON)"""
    id: str = Field(..., description="ID único del documento")
    text: str = Field(..., min_length=1, description="Contenido del documento")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Metadatos adicionales")


class SearchQuery(BaseModel):
    """Consulta de búsqueda individual"""
    query: str = Field(..., min_length=1, description="Texto de búsqueda")
    top_k: int = Field(default=10, ge=1, le=100, description="Número de resultados")
    similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Umbral mínimo de similitud")


class BatchSearchQuery(BaseModel):
    """Consulta de búsqueda por lotes"""
    queries: List[str] = Field(..., min_length=1, description="Lista de textos de búsqueda")
    top_k: int = Field(default=10, ge=1, le=100, description="Número de resultados por query")
    similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Umbral mínimo de similitud")


class FileIngestionMetadata(BaseModel):
    """Metadatos para ingesta de archivos"""
    custom_id: Optional[str] = Field(None, description="ID personalizado para el documento")
    tags: Optional[List[str]] = Field(default=[], description="Etiquetas para el documento")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Metadatos adicionales")


# --- Result Models ---
class SearchResult(BaseModel):
    """Resultado de búsqueda individual"""
    id: str
    score: float
    text_snippet: str
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Respuesta completa de búsqueda"""
    results: List[SearchResult]
    query: str
    total_documents: int
    processing_time_ms: float


class BatchSearchResponse(BaseModel):
    """Respuesta de búsqueda por lotes"""
    results: List[List[SearchResult]]
    queries: List[str]
    total_documents: int
    processing_time_ms: float


class IndexResponse(BaseModel):
    """Respuesta de indexación"""
    status: str
    indexed_count: int
    client_id: str


class FileIndexResponse(BaseModel):
    """Respuesta de indexación de archivo"""
    status: str
    document_id: str
    filename: str
    file_type: str
    content_length: int
    client_id: str


class DocumentResponse(BaseModel):
    """Documento individual"""
    id: str
    text_snippet: str
    content_length: int
    metadata: Dict[str, Any] = {}
    indexed_at: Optional[datetime] = None


class ClientStats(BaseModel):
    """Estadísticas de un cliente"""
    client_id: str
    total_documents: int
    embedding_dimension: int
    rust_acceleration: bool
    created_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Estado del servicio"""
    status: str
    version: str
    rust_core_available: bool
    model_loaded: bool


class DeleteResponse(BaseModel):
    """Respuesta de eliminación"""
    status: str
    message: str
    deleted_count: Optional[int] = None

