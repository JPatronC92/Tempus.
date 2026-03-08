
import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch
import sys
import logging
import importlib

# Set up logging for the test itself
logging.basicConfig(level=logging.INFO)
test_logger = logging.getLogger("benchmark_logging")

# Mock dependencies globally before importing app.service
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = MagicMock()

# Now we can import app.service safely
import app.service

class BlockingHandler(logging.Handler):
    def emit(self, record):
        # Simulate blocking I/O (e.g. slow disk write or network logging)
        time.sleep(0.2)

@pytest.fixture
def service():
    # Reload service to ensure a fresh state
    importlib.reload(app.service)

    # Patch dependencies inside the service
    with patch('app.service.SentenceTransformer') as mock_model_cls:
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384
        mock_model_cls.return_value = mock_model

        with patch('app.service.QdrantClient') as mock_qdrant_cls:
            svc = app.service.UnifiedSearchService()
            return svc

@pytest.mark.asyncio
async def test_logging_blocking(service):
    """
    Benchmark to measure event loop blocking caused by synchronous logging.
    """
    # Attach blocking handler to app.service logger
    target_logger = logging.getLogger("app.service")
    blocking_handler = BlockingHandler()
    target_logger.addHandler(blocking_handler)
    target_logger.setLevel(logging.INFO)

    # Also ensure the mocked Qdrant doesn't error out on usage
    service.qdrant.upsert = MagicMock()

    # Monitor coroutine to detect loop blocking
    async def monitor():
        start = time.time()
        max_delay = 0
        while True:
            step_start = time.time()
            await asyncio.sleep(0.01) # Check every 10ms
            step_end = time.time()

            actual_duration = step_end - step_start
            delay = actual_duration - 0.01 # Excess time

            if delay > max_delay:
                max_delay = delay

            # Run for a bit longer than the expected block
            if time.time() - start > 1.0:
                break
        return max_delay

    test_logger.info("Starting benchmark with BlockingHandler (0.2s delay)...")

    monitor_task = asyncio.create_task(monitor())

    # Run ingest
    start_ingest = time.time()
    await service.ingest_file("benchmark_ns", b"fake_content", "test.txt", {})
    end_ingest = time.time()

    max_loop_delay = await monitor_task

    test_logger.info(f"Ingest Duration: {end_ingest - start_ingest:.4f}s")
    test_logger.info(f"Max Event Loop Delay: {max_loop_delay:.4f}s")

    # Cleanup
    target_logger.removeHandler(blocking_handler)

    # Threshold: If logging is synchronous, delay will be around 0.2s
    # If offloaded, delay should be minimal (e.g. < 0.05s)
    threshold = 0.1

    if max_loop_delay > threshold:
        test_logger.error(f"FAIL: Event loop blocked for {max_loop_delay:.4f}s (Threshold: {threshold}s)")
        # We want this to fail initially to prove the issue
        pytest.fail(f"Event loop blocked for {max_loop_delay:.4f}s")
    else:
        test_logger.info("PASS: Event loop was not blocked.")

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
