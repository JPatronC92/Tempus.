import asyncio
import time
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies to avoid loading models and redis
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()

# Import app.main after mocking
from app.main import get_document, UnifiedSearchService

# Create a mock service
mock_service = MagicMock(spec=UnifiedSearchService)

# Define an async non-blocking get_document method
async def async_get_doc(namespace, doc_id):
    print(f"  -> Service.get_document called (async sleep 1s)...")
    await asyncio.sleep(1.0)
    print(f"  -> Service.get_document finished")
    return {"id": doc_id, "text": "foo", "metadata": {}, "indexed_at": 123}

mock_service.get_document = async_get_doc

async def main():
    print("--- Benchmarking get_document (Async) ---")

    stop_signal = asyncio.Event()

    async def run_heartbeat():
        max_lag = 0
        last_time = time.time()
        print("Heartbeat started")
        while not stop_signal.is_set():
            await asyncio.sleep(0.1)
            now = time.time()
            diff = now - last_time
            if diff > 0.2:
                print(f"  ⚠️ LAG: {diff:.3f}s")
                max_lag = max(max_lag, diff)
            last_time = now
        print(f"Heartbeat stopped. Max lag: {max_lag:.3f}s")
        return max_lag

    hb_task = asyncio.create_task(run_heartbeat())

    # Give it a moment
    await asyncio.sleep(0.2)

    print("Calling get_document endpoint...")
    start_time = time.time()

    try:
        # Call the endpoint function directly
        # We pass the mock_service which has the async method
        response = await get_document(
            doc_id="test-doc",
            client_id="test-key",
            service=mock_service
        )
        print("Endpoint returned.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    duration = time.time() - start_time
    print(f"Total duration: {duration:.3f}s")

    stop_signal.set()
    max_lag = await hb_task

    print(f"Max Heartbeat Lag: {max_lag:.3f}s")

    if max_lag > 0.5:
        print("❌ FAILED: Event loop was blocked!")
        sys.exit(1)
    else:
        print("✅ PASSED: Event loop remained responsive.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
