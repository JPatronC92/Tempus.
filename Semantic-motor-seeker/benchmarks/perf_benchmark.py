import time
import sys
import os
import logging
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging to suppress output during benchmark
logging.basicConfig(level=logging.ERROR)

async def run_benchmark():
    # Mock external dependencies in sys.modules so app.service can be imported
    sys.modules["sentence_transformers"] = MagicMock()
    sys.modules["qdrant_client"] = MagicMock()
    sys.modules["qdrant_client.http"] = MagicMock()
    sys.modules["qdrant_client.http.models"] = MagicMock()
    sys.modules["numpy"] = MagicMock()

    # Also need to mock jas_vector_core if it's used conditionally
    sys.modules["jas_vector_core"] = MagicMock()

    # Now we can safely import app.service
    import app.service

    # Setup Mock Qdrant Client behavior
    # We patch the class on the imported module
    with patch('app.service.AsyncQdrantClient') as MockQdrant, \
         patch('app.service.SentenceTransformer') as MockModel:

        mock_client = MagicMock()
        MockQdrant.return_value = mock_client

        # Dictionary to store created collections in our mock
        mock_storage = {}

        async def get_collection_side_effect(collection_name):
            # Simulate network round-trip latency (e.g., 5ms)
            await asyncio.sleep(0.005)
            if collection_name in mock_storage:
                return True
            raise Exception("Collection not found")

        async def create_collection_side_effect(collection_name, vectors_config):
            # Simulate creation latency (e.g., 20ms)
            await asyncio.sleep(0.02)
            mock_storage[collection_name] = True

        mock_client.get_collection.side_effect = get_collection_side_effect
        mock_client.create_collection.side_effect = create_collection_side_effect

        print("Initializing Service...")
        service = app.service.UnifiedSearchService()

        collection_name = "client_benchmark_perf"
        iterations = 500

        print(f"Running benchmark with {iterations} iterations...")
        print("Simulated Latency: 5ms for check, 20ms for creation")

        start_time = time.time()

        for _ in range(iterations):
            await service._ensure_collection(collection_name)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_ms = (total_time / iterations) * 1000

        print(f"\n--- Benchmark Results ---")
        print(f"Total Time: {total_time:.4f} seconds")
        print(f"Average Time per Call: {avg_time_ms:.2f} ms")
        print(f"Total 'get_collection' calls (approx): {mock_client.get_collection.call_count}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
