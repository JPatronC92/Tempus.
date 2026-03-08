
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock, AsyncMock, patch

# Mock dependencies globally before imports
mock_qdrant = MagicMock()
mock_models = MagicMock()
mock_qdrant.http.models = mock_models

with patch.dict("sys.modules", {
    "qdrant_client": mock_qdrant,
    "qdrant_client.http": mock_qdrant.http,
    "qdrant_client.http.models": mock_models,
    "sentence_transformers": MagicMock(),
    "numpy": MagicMock(),
}):
    # Import app modules after mocking
    from fastapi.testclient import TestClient
    from app.main import app, get_service
    from app.service import UnifiedSearchService
    from app import middleware

# Mock API Keys
middleware.VALID_API_KEYS = {"test_api_key": {"tier": "default", "active": True}}

# Mock Service
mock_service = AsyncMock(spec=UnifiedSearchService)
mock_service.model = MagicMock() # Mock the model attribute for health check

# Override Dependency
def override_get_service():
    return mock_service

app.dependency_overrides[get_service] = override_get_service

client = TestClient(app)

def test_health_check():
    """Test /health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_root():
    """Test root endpoint / (Dashboard)"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<!DOCTYPE html>" in response.text

def test_index_documents():
    """Test /v1/index endpoint with mocked service"""
    # Setup mock return value
    mock_service.index_documents.return_value = {
        "indexed_count": 2,
        "total_documents": -1,
        "namespace": "test_namespace"
    }

    payload = [
        {"id": "doc1", "text": "Hello world", "metadata": {"category": "test"}},
        {"id": "doc2", "text": "Another document", "metadata": {}}
    ]
    headers = {"X-API-Key": "test_api_key"}

    response = client.post("/v1/index", json=payload, headers=headers)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["indexed_count"] == 2
    
    # Verify service call
    mock_service.index_documents.assert_called()

def test_search_documents():
    """Test /v1/search endpoint with mocked service"""
    # Setup mock return value
    mock_service.search.return_value = {
        "results": [
            {"id": "doc1", "score": 0.95, "text_snippet": "Hello world", "metadata": {}},
            {"id": "doc2", "score": 0.85, "text_snippet": "Another doc", "metadata": {}}
        ],
        "total_documents": 100,
        "processing_time_ms": 15.5
    }

    payload = {
        "query": "Hello",
        "top_k": 2
    }
    headers = {"X-API-Key": "test_api_key"}

    response = client.post("/v1/search", json=payload, headers=headers)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["query"] == "Hello"
    
    # Verify service call
    mock_service.search.assert_called()

def test_delete_document():
    """Test /v1/documents/{doc_id} delete endpoint"""
    # Setup mock return value
    mock_service.delete_document.return_value = True

    headers = {"X-API-Key": "test_api_key"}
    doc_id = "doc1"

    response = client.delete(f"/v1/documents/{doc_id}", headers=headers)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert f"Documento {doc_id} eliminado" in data["message"]
    
    # Verify service call
    mock_service.delete_document.assert_called()
