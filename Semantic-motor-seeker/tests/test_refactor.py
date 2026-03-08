import pytest
import io
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from qdrant_client.http import models as qmodels

from app.parsers import parse_csv, MAX_TEXT_LENGTH
from app.vector_store import QdrantVectorStore
from app.engine import UnifiedSearchService

# --- Test Parsers ---
def test_parse_csv_truncation():
    # Create a CSV content that exceeds MAX_TEXT_LENGTH
    with patch("app.parsers.MAX_TEXT_LENGTH", 50):
        long_line = "a" * 60 + "\n"
        file_obj_2 = io.BytesIO((long_line * 2).encode("utf-8"))

        result_2 = parse_csv(file_obj_2)
        assert len(result_2) >= 60 # It reads at least one line
        # Logic: read line, append, check if current >= MAX. If so, break.
        assert result_2 == long_line

# --- Test Vector Store ---
@pytest.mark.asyncio
async def test_upsert_points_batch():
    mock_client = AsyncMock()
    store = QdrantVectorStore()
    store.client = mock_client

    # Test with PointStruct list
    points_list = [qmodels.PointStruct(id="1", vector=[0.1]*10, payload={"a": 1})]
    await store.upsert_points("test_coll", points_list)
    mock_client.upsert.assert_called_with(collection_name="test_coll", points=points_list)

# --- Test Engine ---
@pytest.mark.asyncio
async def test_engine_ingest_file():
    # Mock embedding model
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3] # Single vector

    with patch("app.engine.SentenceTransformer", return_value=mock_model), \
         patch("app.engine.QdrantVectorStore") as MockStore, \
         patch("app.parsers.extract_text_content", return_value="some text"):
        
        mock_store_instance = MockStore.return_value
        mock_store_instance.ensure_collection = AsyncMock()
        mock_store_instance.upsert_points = AsyncMock()
        mock_store_instance.client = AsyncMock()

        service = UnifiedSearchService()

        file_obj = io.BytesIO(b"content")
        await service.ingest_file("ns", file_obj, "test.txt", {})

        # Verify model encode called
        mock_model.encode.assert_called_with("some text")

        # Verify upsert called
        call_args = mock_store_instance.upsert_points.call_args
        assert call_args is not None
        _, kwargs = call_args
        points = kwargs["points"]

        assert len(points) == 1
        assert points[0].vector == [0.1, 0.2, 0.3]

@pytest.mark.asyncio
async def test_engine_index_documents():
    mock_model = MagicMock()
    # Return list of vectors
    mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.1], [0.2]])

    with patch("app.engine.SentenceTransformer", return_value=mock_model), \
         patch("app.engine.QdrantVectorStore") as MockStore:

        mock_store_instance = MockStore.return_value
        mock_store_instance.ensure_collection = AsyncMock()
        mock_store_instance.upsert_points = AsyncMock()
        mock_store_instance.client = AsyncMock()

        service = UnifiedSearchService()

        docs = [{"id": "1", "text": "d1"}, {"id": "2", "text": "d2"}]
        await service.index_documents("ns", docs)

        # Verify upsert called
        call_args = mock_store_instance.upsert_points.call_args
        _, kwargs = call_args
        points = kwargs["points"]

        assert len(points) == 2
        assert points[0].vector == [0.1]
        assert points[1].vector == [0.2]
