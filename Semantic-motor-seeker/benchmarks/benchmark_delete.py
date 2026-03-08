import asyncio
import time
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies BEFORE importing app.main
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = MagicMock()
sys.modules["jas_vector_core"] = MagicMock()

# Import app
from app.main import app as fastapi_app, get_service  # noqa: E402
from app.service import UnifiedSearchService  # noqa: E402
import app.middleware  # noqa: E402

# Mock VALID_API_KEYS
app.middleware.VALID_API_KEYS = {
    "test-key": {"active": True, "tier": "default"}
}

# Mock Service
mock_service = MagicMock(spec=UnifiedSearchService)

async def slow_delete_document(*args, **kwargs):
    print("  [Service] delete_document called (async sleep 1s)...")
    await asyncio.sleep(1.0)
    print("  [Service] delete_document finished sleeping")
    return True

mock_service.delete_document = slow_delete_document

# Override dependency
fastapi_app.dependency_overrides[get_service] = lambda: mock_service

async def heartbeat():
    print("  [Heartbeat] Started")
    last_time = time.time()
    max_lag = 0
    for i in range(10):
        await asyncio.sleep(0.1)
        now = time.time()
        lag = (now - last_time) - 0.1
        if lag > 0.5:
            print(f"  [Heartbeat] LAG DETECTED: {lag:.4f}s")
        last_time = now
        max_lag = max(max_lag, lag)
    print(f"  [Heartbeat] Finished. Max lag: {max_lag:.4f}s")
    return max_lag


async def call_delete_endpoint():
    print("  [Client] Sending DELETE request...")
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        response = await ac.delete("/v1/documents/test-doc", headers={"X-API-Key": "test-key"})
        print(f"  [Client] Response: {response.status_code}")
        if response.status_code != 200:
            print(f"  [Client] Response body: {response.text}")


async def main():
    print("--- Benchmark: delete_document async check ---")

    # Run heartbeat and request concurrently
    task_heartbeat = asyncio.create_task(heartbeat())

    # Give heartbeat a moment to start
    await asyncio.sleep(0.2)

    task_request = asyncio.create_task(call_delete_endpoint())

    max_lag = await task_heartbeat
    await task_request

    if max_lag > 0.5:
        print("FAIL: Event loop was blocked!")
    else:
        print("PASS: Event loop was NOT blocked.")


if __name__ == "__main__":
    asyncio.run(main())
