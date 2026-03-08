import asyncio
import time
import sys
from starlette.concurrency import run_in_threadpool

# Parameters
CONCURRENCY = 200
REQUESTS = 1000
IO_DELAY = 0.05 # 50ms simulated DB latency

def sync_db_call():
    """Simulates a blocking DB call"""
    time.sleep(IO_DELAY)
    return True

async def async_db_call():
    """Simulates a non-blocking DB call"""
    await asyncio.sleep(IO_DELAY)
    return True

async def run_threadpool_benchmark():
    start = time.time()
    tasks = []
    for _ in range(REQUESTS):
        # Limit concurrency to simulate real world load on the server
        # In a real server, request handling is concurrent up to a point
        tasks.append(run_in_threadpool(sync_db_call))

    # We batch them in chunks to simulate concurrent arrival
    # But effectively gather runs them all.
    # However, run_in_threadpool is bounded by the default threadpool size (40)
    await asyncio.gather(*tasks)
    duration = time.time() - start
    rps = REQUESTS / duration
    print(f"Threadpool (Sync) | Requests: {REQUESTS} | Time: {duration:.4f}s | RPS: {rps:.2f}")
    return rps

async def run_async_benchmark():
    start = time.time()
    tasks = []
    for _ in range(REQUESTS):
        tasks.append(async_db_call())

    await asyncio.gather(*tasks)
    duration = time.time() - start
    rps = REQUESTS / duration
    print(f"Async (Native)    | Requests: {REQUESTS} | Time: {duration:.4f}s | RPS: {rps:.2f}")
    return rps

async def main():
    print(f"--- Benchmark: {REQUESTS} requests, {IO_DELAY*1000}ms latency ---")
    print("Running Threadpool Benchmark (Current Architecture)...")
    rps_sync = await run_threadpool_benchmark()

    # Cooldown
    await asyncio.sleep(1)

    print("Running Async Benchmark (Proposed Architecture)...")
    rps_async = await run_async_benchmark()

    improvement = (rps_async - rps_sync) / rps_sync * 100
    print(f"\nImprovement: {improvement:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
