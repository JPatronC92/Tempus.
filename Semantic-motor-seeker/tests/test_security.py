import os
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock

# Set environment variables BEFORE importing app
os.environ["VALID_API_KEYS"] = '{"test_key": {"tier": "default", "active": true}}'
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_PASSWORD"] = "dummy"
os.environ["QDRANT_API_KEY"] = "dummy"

# Mock redis (sync)
patcher = patch("redis.Redis")
mock_redis = patcher.start()
mock_redis_instance = MagicMock()
mock_redis.return_value = mock_redis_instance

# Mock aioredis (async)
aioredis_patcher = patch("redis.asyncio.Redis")
mock_aioredis = aioredis_patcher.start()
mock_aioredis_instance = AsyncMock()
mock_aioredis.return_value = mock_aioredis_instance

# Mock .get to return a valid value if needed
mock_aioredis_instance.get.return_value = "0"
mock_aioredis_instance.hget.return_value = None

# Setup register_script on aioredis instance
mock_script = AsyncMock()
mock_script.return_value = [0, 0]
mock_aioredis_instance.register_script.return_value = mock_script

# Mock Qdrant
qdrant_patcher = patch("app.vector_store.AsyncQdrantClient")
mock_qdrant = qdrant_patcher.start()
mock_qdrant_instance = AsyncMock()
mock_qdrant.return_value = mock_qdrant_instance


from app.main import app
from app.service import UnifiedSearchService

client = TestClient(app)

def test_backdoor_vulnerability():
    """
    Test that a key starting with 'sk_live_' grants Premium access even if invalid.
    """
    headers = {"X-API-Key": "sk_live_fake_backdoor_key"}
    response = client.get("/v1/usage", headers=headers)

    # Assertions for SECURE behavior
    if response.status_code == 200:
        data = response.json()
        if data.get("plan") == "Premium":
            pytest.fail("VULNERABILITY CONFIRMED: Backdoor key 'sk_live_' granted Premium plan.")

    # Secure if 403 (Invalid Key) or 200 but not Premium (if we allowed access but fixed backdoor logic)
    # Since we enforced auth in middleware, we expect 403.
    if response.status_code == 403:
        pass

def test_usage_endpoint_bypass():
    """
    Test that /v1/usage is accessible without any authentication.
    """
    # No headers
    response = client.get("/v1/usage")

    if response.status_code == 200:
         pytest.fail("VULNERABILITY CONFIRMED: /v1/usage accessible without auth.")

    # 422 is acceptable (FastAPI validation error for missing header), meaning access was blocked/invalid.
    # 403 is acceptable (Middleware blocked it).
    if response.status_code not in [403, 422]:
         pytest.fail(f"Unexpected status code: {response.status_code}")

    # With invalid key
    headers = {"X-API-Key": "invalid_key"}
    response = client.get("/v1/usage", headers=headers)
    if response.status_code == 200:
        pytest.fail("VULNERABILITY CONFIRMED: /v1/usage accessible with invalid key.")

    # Should be 403 (Middleware blocked invalid key)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_metadata_overwrite_service():
    """
    Test that metadata can overwrite protected fields in index_documents.
    """
    service = UnifiedSearchService()
    service.vector_store = MagicMock()
    service.vector_store.ensure_collection = AsyncMock()
    service.vector_store.upsert_points = AsyncMock()

    # Mock embedding model
    service._model = MagicMock()
    mock_vector = MagicMock()
    mock_vector.__getitem__.return_value = [0.1] * 384
    service._model.encode.return_value = mock_vector

    # Input document with malicious metadata
    doc = {
        "id": "doc1",
        "text": "Valid text",
        "metadata": {
            "full_text": "MALICIOUS OVERWRITE",
            "original_id": "hacked_id"
        }
    }

    await service.index_documents("test_ns", [doc])

    # Inspect calls
    call_args = service.vector_store.upsert_points.call_args
    if not call_args:
        pytest.fail("upsert_points was not called")

    points = call_args[1]['points']
    payload = points[0].payload

    if payload.get("full_text") == "MALICIOUS OVERWRITE":
         pytest.fail("VULNERABILITY CONFIRMED: 'full_text' was overwritten by metadata.")

    if payload.get("original_id") == "hacked_id":
         pytest.fail("VULNERABILITY CONFIRMED: 'original_id' was overwritten by metadata.")

    # Verify values are correct
    assert payload.get("full_text") == "Valid text"
    assert payload.get("original_id") == "doc1"
