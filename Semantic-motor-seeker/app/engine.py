import asyncio
import copy
import functools
import logging
import os
import re
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any, BinaryIO, Dict, List, Optional

import numpy as np
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

from . import parsers
from .vector_store import VECTOR_SIZE, QdrantVectorStore

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
HEX32_PATTERN = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)

EXCLUDED_METADATA_KEYS = {"text_snippet", "full_text", "original_id"}

RUST_AVAILABLE = False
try:
    import jas_vector_core

    RUST_AVAILABLE = True
    logger.info("🚀 Rust Core Activado")
except ImportError:
    logger.warning("⚠️ Rust Core no encontrado, usando Python fallback")


def ttl_cache(seconds: int = 60, maxsize: int = 128, copy_func=copy.deepcopy):
    def decorator(func):
        cache = OrderedDict()
        lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (args[1:], tuple(sorted(kwargs.items()))) if args else (tuple(), tuple(sorted(kwargs.items())))

            with lock:
                if key in cache:
                    timestamp, val = cache[key]
                    if time.monotonic() - timestamp < seconds:
                        cache.move_to_end(key)
                        return copy_func(val)
                    del cache[key]

            val = func(*args, **kwargs)
            now = time.monotonic()

            with lock:
                cache[key] = (now, val)
                if len(cache) > maxsize:
                    cache.popitem(last=False)

            return copy_func(val)

        return wrapper

    return decorator


def async_ttl_cache(seconds: int = 60, maxsize: int = 128, copy_func=copy.deepcopy):
    def decorator(func):
        cache = OrderedDict()
        lock = asyncio.Lock()

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = (args[1:], tuple(sorted(kwargs.items()))) if args else (tuple(), tuple(sorted(kwargs.items())))

            async with lock:
                if key in cache:
                    timestamp, val = cache[key]
                    if time.monotonic() - timestamp < seconds:
                        cache.move_to_end(key)
                        return copy_func(val)
                    del cache[key]

            val = await func(*args, **kwargs)
            now = time.monotonic()

            async with lock:
                cache[key] = (now, val)
                if len(cache) > maxsize:
                    cache.popitem(last=False)

            return copy_func(val)

        return wrapper

    return decorator


class UnifiedSearchService:
    def __init__(self):
        logger.info("🔄 Inicializando UnifiedSearchService conectado a Qdrant...")

        logger.info("🧠 Cargando modelo de embeddings %s en dispositivo: %s", EMBEDDING_MODEL, EMBEDDING_DEVICE)
        self.model = SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)

        self.vector_store = QdrantVectorStore()
        self.qdrant = self.vector_store.client

        self.model_name = EMBEDDING_MODEL
        self.embedding_dim = VECTOR_SIZE

    def _get_collection_name(self, namespace: str) -> str:
        return f"client_{namespace}"

    def _to_uuid(self, id_str: str) -> str:
        if isinstance(id_str, uuid.UUID):
            return str(id_str)

        s_id = str(id_str)
        length = len(s_id)

        if length == 36 and UUID_PATTERN.match(s_id):
            return s_id

        if length == 32 and HEX32_PATTERN.match(s_id):
            return s_id

        if length in (36, 38, 45):
            try:
                uuid.UUID(s_id)
                return s_id
            except ValueError:
                pass

        return str(uuid.uuid5(uuid.NAMESPACE_DNS, s_id))

    async def ingest_file(self, namespace: str, file_obj: BinaryIO, filename: str, metadata: Dict) -> Dict[str, Any]:
        collection_name = self._get_collection_name(namespace)
        await self.vector_store.ensure_collection(collection_name)

        t_extract_start = time.time()
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        text_content = await asyncio.to_thread(parsers.extract_text_content, file_obj, filename)
        await asyncio.to_thread(
            logger.info,
            "Text extraction for %s took %.4fs",
            filename,
            time.time() - t_extract_start,
        )

        start_time = time.time()
        vector = await asyncio.to_thread(self.model.encode, text_content)
        if hasattr(vector, "tolist"):
            vector = vector.tolist()

        doc_id = str(uuid.uuid4())
        # Metadata filtering
        safe_metadata = {k: v for k, v in metadata.items() if k not in EXCLUDED_METADATA_KEYS}
        
        payload = {
            **safe_metadata,
            "filename": filename,
            "text_snippet": text_content[:500],
            "full_text": text_content,
            "indexed_at": time.time(),
        }

        await self.vector_store.upsert_points(
            collection_name=collection_name,
            points=[
                qmodels.PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

        return {
            "status": "success",
            "document_id": doc_id,
            "file_type": filename.split(".")[-1],
            "content_length": len(text_content),
            "processing_time": time.time() - start_time,
        }

    async def index_documents(self, namespace: str, documents: List[Dict]) -> Dict[str, Any]:
        collection_name = self._get_collection_name(namespace)
        await self.vector_store.ensure_collection(collection_name)

        texts = [doc["text"] for doc in documents]
        vectors = await asyncio.to_thread(lambda: self.model.encode(texts).tolist())

        points = []
        for i, doc in enumerate(documents):
            original_id = doc["id"]
            final_id = self._to_uuid(original_id)

            # Metadata filtering
            metadata = doc.get("metadata", {})
            safe_metadata = {k: v for k, v in metadata.items() if k not in EXCLUDED_METADATA_KEYS}

            payload = {
                **safe_metadata,
                "original_id": original_id,
                "text_snippet": doc["text"][:500],
                "full_text": doc["text"],
                "indexed_at": time.time(),
            }

            points.append(qmodels.PointStruct(id=final_id, vector=vectors[i], payload=payload))

        if points:
            await self.vector_store.upsert_points(collection_name=collection_name, points=points)

        return {
            "indexed_count": len(points),
            "total_documents": -1,
            "namespace": namespace,
        }

    @functools.lru_cache(maxsize=1024)
    def _encode_query_cached(self, query: str):
        return self.model.encode(query)

    @staticmethod
    def _format_search_result(point) -> Dict[str, Any]:
        payload = point.payload
        doc_id = payload.get("original_id", str(point.id))
        text_snippet = payload.get("text_snippet", "")

        for k in EXCLUDED_METADATA_KEYS:
            payload.pop(k, None)

        return {
            "id": doc_id,
            "score": point.score,
            "text_snippet": text_snippet,
            "metadata": payload,
        }

    async def search(self, namespace: str, query: str, top_k: int = 5, threshold: float = 0.0) -> Dict[str, Any]:
        collection_name = self._get_collection_name(namespace)
        t0 = time.time()

        query_embedding = await asyncio.to_thread(self._encode_query_cached, query)

        if isinstance(query_embedding, np.ndarray):
            query_vector_np = query_embedding.astype(np.float32, copy=False)
            query_vector = query_vector_np.tolist()
        else:
            query_vector = query_embedding.tolist() if hasattr(query_embedding, "tolist") else query_embedding
            query_vector_np = np.array(query_vector, dtype=np.float32)

        try:
            search_result = await self.vector_store.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=threshold,
                with_payload=qmodels.PayloadSelectorExclude(exclude=["full_text"]),
                with_vectors=True if RUST_AVAILABLE else False,
            )
        except Exception:
            return {"results": [], "total_documents": 0, "processing_time_ms": 0}

        final_results_order = []

        if RUST_AVAILABLE and len(search_result) > 50:
            try:
                q_vec_np = query_vector_np
                # Offload CPU-bound numpy array creation to a thread to avoid blocking the event loop
                c_vecs_np = await asyncio.to_thread(
                    lambda: np.array([point.vector for point in search_result], dtype=np.float32)
                )

                reranked_indices = await asyncio.to_thread(
                    jas_vector_core.cosine_similarity_search,
                    q_vec_np,
                    c_vecs_np,
                    len(search_result),
                )

                for idx, new_score in reranked_indices:
                    point = search_result[idx]
                    point.score = float(new_score)
                    final_results_order.append(point)

            except Exception as exc:
                logger.error("Error en Rust Acceleration: %s. Usando orden original.", exc, exc_info=True)
                final_results_order = search_result
        else:
            final_results_order = search_result

        results = [self._format_search_result(point) for point in final_results_order[:top_k]]

        return {
            "results": results,
            "total_documents": -1,
            "processing_time_ms": (time.time() - t0) * 1000,
        }

    async def batch_search(self, namespace: str, queries: List[str], top_k: int, threshold: float) -> Dict[str, Any]:
        collection_name = self._get_collection_name(namespace)
        t0 = time.time()

        query_vectors = await asyncio.to_thread(lambda: self.model.encode(queries).tolist())

        search_queries = [
            qmodels.SearchRequest(
                vector=vec,
                limit=top_k,
                score_threshold=threshold,
                with_payload=qmodels.PayloadSelectorExclude(exclude=["full_text"]),
            )
            for vec in query_vectors
        ]

        try:
            batch_results = await self.vector_store.search_batch(
                collection_name=collection_name, requests=search_queries
            )
        except Exception:
            return {"results": [[] for _ in queries], "total_documents": 0, "processing_time_ms": 0}

        formatter = self._format_search_result
        formatted_results = [[formatter(point) for point in result_group] for result_group in batch_results]

        return {
            "results": formatted_results,
            "total_documents": -1,
            "processing_time_ms": (time.time() - t0) * 1000,
        }

    async def delete_document(self, namespace: str, doc_id: str) -> bool:
        collection_name = self._get_collection_name(namespace)
        final_id = self._to_uuid(doc_id)

        try:
            await self.vector_store.delete(
                collection_name=collection_name,
                points=qmodels.PointIdsList(points=[final_id]),
            )
            return True
        except Exception:
            return False

    async def clear_namespace(self, namespace: str) -> None:
        collection_name = self._get_collection_name(namespace)
        try:
            await self.vector_store.delete_collection(collection_name)
        except Exception:
            pass

    @async_ttl_cache(seconds=60, copy_func=copy.copy)
    async def get_stats(self, namespace: str) -> Dict[str, Any]:
        collection_name = self._get_collection_name(namespace)
        try:
            info = await self.vector_store.get_collection(collection_name)
            return {
                "total_documents": info.points_count,
                "embedding_dimension": VECTOR_SIZE,
                "rust_acceleration": RUST_AVAILABLE,
                "storage": "Qdrant Persistent",
            }
        except Exception:
            return {"total_documents": 0, "embedding_dimension": VECTOR_SIZE, "rust_acceleration": RUST_AVAILABLE}

    async def get_document(self, namespace: str, doc_id: str) -> Optional[Dict[str, Any]]:
        collection_name = self._get_collection_name(namespace)

        ids_to_try = []
        try:
            uuid.UUID(doc_id)
            ids_to_try.append(doc_id)
        except ValueError:
            pass
        hashed_id = self._to_uuid(doc_id)
        if hashed_id not in ids_to_try:
            ids_to_try.append(hashed_id)

        try:
            points = await self.vector_store.retrieve(
                collection_name=collection_name,
                ids=ids_to_try,
                with_payload=True,
            )
            if points:
                p = points[0]
                original_id = p.payload.get("original_id", str(p.id))
                return {
                    "id": original_id,
                    "text": p.payload.get("full_text", ""),
                    "metadata": p.payload,
                    "indexed_at": p.payload.get("indexed_at"),
                }
        except Exception:
            pass
        return None

    async def list_documents(self, namespace: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Lista los documentos más recientes indexados"""
        collection_name = self._get_collection_name(namespace)
        try:
            # Usamos un scroll para obtener los puntos
            result = await self.qdrant.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            points = result[0]
            
            docs = []
            for p in points:
                docs.append({
                    "id": p.payload.get("original_id", str(p.id)),
                    "text_snippet": p.payload.get("text_snippet", ""),
                    "metadata": {k: v for k, v in p.payload.items() if k not in EXCLUDED_METADATA_KEYS},
                    "indexed_at": p.payload.get("indexed_at")
                })
            return docs
        except Exception:
            return []


_service_instance = None


def get_vector_service() -> UnifiedSearchService:
    global _service_instance
    if _service_instance is None:
        _service_instance = UnifiedSearchService()
    return _service_instance
