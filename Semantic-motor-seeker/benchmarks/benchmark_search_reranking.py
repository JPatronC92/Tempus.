import sys
import time
import asyncio
import numpy as np
from unittest.mock import MagicMock

# Mock jas_vector_core
class MockJasVectorCore:
    def cosine_similarity_search(self, query_vector, candidate_vectors, top_k):
        # Simulate some work - simple dot product
        # query_vector: (dim,)
        # candidate_vectors: (n, dim)
        scores = np.dot(candidate_vectors, query_vector)
        # return list of (index, score)
        indices = np.argsort(scores)[::-1][:top_k]
        return [(int(i), float(scores[i])) for i in indices]

sys.modules["jas_vector_core"] = MockJasVectorCore()

# Mock sentence_transformers
class MockSentenceTransformer:
    def __init__(self, *args, **kwargs):
        pass
    def encode(self, *args, **kwargs):
        return np.random.rand(384).astype(np.float32)

sys.modules["sentence_transformers"] = MagicMock()
sys.modules["sentence_transformers"].SentenceTransformer = MockSentenceTransformer

# Mock qdrant_client
sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = MagicMock()

# Define qmodels mock objects
class PointStruct:
    def __init__(self, id, vector, payload):
        self.id = id
        self.vector = vector
        self.payload = payload
        self.score = 0.0

class ScoredPoint:
    def __init__(self, id, version, score, payload, vector=None):
        self.id = id
        self.version = version
        self.score = score
        self.payload = payload
        self.vector = vector

class PayloadSelectorExclude:
    def __init__(self, exclude):
        pass

# Attach these classes to qmodels mock
qmodels = sys.modules["qdrant_client.http.models"]
qmodels.PointStruct = PointStruct
qmodels.ScoredPoint = ScoredPoint
qmodels.PayloadSelectorExclude = PayloadSelectorExclude

# Now import app.engine
# We need to make sure RUST_AVAILABLE becomes True
import app.engine
import importlib
importlib.reload(app.engine)

from app.engine import UnifiedSearchService

# Mock Qdrant Vector Store search method
app.engine.QdrantVectorStore = MagicMock()

class MockVectorStore:
    def __init__(self):
        self.client = MagicMock()

    async def search(self, *args, **kwargs):
        limit = kwargs.get('limit', 10)
        dim = 384
        # return dummy points
        return [
            qmodels.ScoredPoint(
                id=str(i),
                version=1,
                score=0.9,
                payload={"original_id": str(i), "text_snippet": "foo"},
                vector=[0.1]*dim
            ) for i in range(limit)
        ]

    async def ensure_collection(self, *args, **kwargs):
        pass

async def run_benchmark():
    service = UnifiedSearchService()
    service.vector_store = MockVectorStore()
    service.qdrant = MagicMock()

    # Verify RUST_AVAILABLE is True
    print(f"RUST_AVAILABLE: {app.engine.RUST_AVAILABLE}")

    TOP_K = 2000 # Increased to make the impact more visible

    # Warmup
    try:
        await service.search("test", "query", top_k=TOP_K)
    except Exception as e:
        print(f"Warmup failed: {e}")
        import traceback
        traceback.print_exc()
        return

    start_time = time.time()
    iterations = 50
    for _ in range(iterations):
        await service.search("test", "query", top_k=TOP_K)
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations
    print(f"Average time per search (top_k={TOP_K}): {avg_time:.6f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
