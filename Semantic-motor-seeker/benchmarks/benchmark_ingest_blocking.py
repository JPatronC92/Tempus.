
import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import importlib
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

# Mock dependencies
# Mock dependencies
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = MagicMock()

import app.engine

@pytest.fixture
def service():
    # Reload service to apply mocks
    importlib.reload(app.engine)

    # Reload service to apply mocks
    importlib.reload(app.engine)

    with patch('app.engine.SentenceTransformer') as mock_model_cls:
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384
        mock_model_cls.return_value = mock_model

        with patch('app.engine.QdrantVectorStore') as mock_store_cls:
            mock_store_instance = MagicMock()
            
            # Make async methods awaitable
            mock_store_instance.ensure_collection = AsyncMock()
            mock_store_instance.upsert_points = AsyncMock()
            
            mock_store_cls.return_value = mock_store_instance
            
            svc = app.engine.UnifiedSearchService()
            return svc

@pytest.mark.asyncio
async def test_ingest_file_benchmark(service):
    """
    Benchmark to measure event loop blocking during file ingestion.
    """
    SIMULATED_PARSE_TIME = 0.5 # seconds

    # Mock parsers.extract_text_content to be slow
    def slow_extract(file_obj, filename):
        time.sleep(SIMULATED_PARSE_TIME)
        return "Parsed content"

    # We patch app.parsers.extract_text_content
    # Since engine.py imports parsers, we can patch app.parsers.extract_text_content
    with patch('app.parsers.extract_text_content', side_effect=slow_extract):
        # Monitor coroutine to detect loop blocking
        async def monitor():
            start = time.time()
            max_delay = 0
            while True:
                step_start = time.time()
                await asyncio.sleep(0.01) # Check every 10ms
                step_end = time.time()

                actual_duration = step_end - step_start
                delay = actual_duration - 0.01
                if delay > max_delay:
                    max_delay = delay

                if time.time() - start > (SIMULATED_PARSE_TIME + 0.5):
                    break
            return max_delay

        logger.info(f"Starting benchmark. Simulated Parse Time: {SIMULATED_PARSE_TIME}s")

        monitor_task = asyncio.create_task(monitor())

        # Run ingest (simulating a PDF upload)
        start_ingest = time.time()
        try:
            await service.ingest_file("benchmark_ns", b"fake_content", "test.pdf", {})
        except Exception as e:
            logger.error(f"Ingest failed: {e}")
            traceback.print_exc()
            raise e
        end_ingest = time.time()

        max_loop_delay = await monitor_task

        ingest_duration = end_ingest - start_ingest

        logger.info(f"Ingest Duration: {ingest_duration:.4f}s")
        logger.info(f"Max Event Loop Delay: {max_loop_delay:.4f}s")

        # Assertion: If offloaded correctly, max_loop_delay should be small (e.g. < 0.05s)
        # If blocking, it would be close to SIMULATED_PARSE_TIME (0.5s)

        threshold = 0.1
        if max_loop_delay > threshold:
            logger.error(f"FAIL: Event loop blocked for {max_loop_delay:.4f}s (Threshold: {threshold}s)")
            pytest.fail(f"Event loop blocked for {max_loop_delay:.4f}s")
        else:
            logger.info("PASS: Event loop was not blocked.")

if __name__ == "__main__":
    # Allow running directly
    sys.exit(pytest.main(["-v", __file__]))
