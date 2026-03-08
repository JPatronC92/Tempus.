import asyncio
import sys
import time
from unittest.mock import MagicMock, AsyncMock

# Mock Qdrant modules
mock_qdrant_client = MagicMock()
mock_models = MagicMock()

# Setup mocks before importing app.vector_store
sys.modules["qdrant_client"] = mock_qdrant_client
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = mock_models

# Now import the class to test
from app.vector_store import QdrantVectorStore

async def main():
    print("Initializing benchmark...")

    # Instantiate store
    store = QdrantVectorStore()

    # Mock client methods to be async and successful
    store.client.get_collection = AsyncMock()
    store.client.create_collection = AsyncMock()

    # Configure mock behavior
    # First call: collection doesn't exist (raises exception), second call (create): succeeds
    # Actually, ensure_collection logic:
    # 1. Check cache (hit -> return)
    # 2. get_collection (success -> add to cache, return)
    # 3. create_collection (success -> add to cache)

    # Let's make get_collection succeed to simulate "collection exists" scenario,
    # because we want to fill the cache. Or make it fail then create succeed.
    # If get_collection succeeds, it adds to cache.
    store.client.get_collection.return_value = MagicMock()

    initial_size = len(store._collections_cache)
    print(f"Initial cache size: {initial_size}")

    num_collections = 10000
    print(f"Simulating access to {num_collections} unique collections...")

    start_time = time.time()
    for i in range(num_collections):
        collection_name = f"col_{i}"
        await store.ensure_collection(collection_name)

        if (i + 1) % 1000 == 0:
            print(f"Processed {i + 1} collections. Current cache size: {len(store._collections_cache)}")

    end_time = time.time()
    final_size = len(store._collections_cache)
    duration = end_time - start_time

    print(f"\nBenchmark Result:")
    print(f"Total Collections Accessed: {num_collections}")
    print(f"Final Cache Size: {final_size}")
    print(f"Time Taken: {duration:.4f}s")

    if final_size >= num_collections:
        print("STATUS: Unbounded Growth Detected (FAIL)")
    else:
        print(f"STATUS: Bounded Cache (SUCCESS). Max Size: {final_size}")

if __name__ == "__main__":
    asyncio.run(main())
