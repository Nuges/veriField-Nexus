import asyncio
import httpx
import time
import statistics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

BASE_URL = "http://localhost:8000"
CONCURRENCY = 100
TOTAL_REQUESTS = 2000

ENDPOINTS = [
    ("/api/telemetry", "GET"),
    ("/api/metadata", "GET"),
    ("/api/calculation/run", "POST"),
    ("/api/search", "GET"),
    ("/api/dashboard", "GET")
]

async def fetch(client, url, method):
    start = time.time()
    try:
        if method == "GET":
            response = await client.get(url)
        else:
            response = await client.post(url, json={})
    except Exception as e:
        pass
    return time.time() - start

async def worker(client, queue, results):
    while True:
        try:
            url, method = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        duration = await fetch(client, url, method)
        results.append(duration)
        queue.task_done()

async def benchmark():
    queue = asyncio.Queue()
    # Populate the queue
    for _ in range(TOTAL_REQUESTS):
        for endpoint, method in ENDPOINTS:
            queue.put_nowait((f"{BASE_URL}{endpoint}", method))

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []
        for _ in range(CONCURRENCY):
            task = asyncio.create_task(worker(client, queue, results))
            tasks.append(task)
        
        logger.info(f"Starting benchmark with {CONCURRENCY} concurrent workers...")
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time

    if results:
        p50 = statistics.median(results)
        p95 = statistics.quantiles(results, n=100)[94]
        p99 = statistics.quantiles(results, n=100)[98]
        
        logger.info(f"Total time: {total_time:.2f}s")
        logger.info(f"Requests per second: {len(results)/total_time:.2f}")
        logger.info(f"P50 Latency: {p50*1000:.2f}ms")
        logger.info(f"P95 Latency: {p95*1000:.2f}ms")
        logger.info(f"P99 Latency: {p99*1000:.2f}ms")
        
        if p95 * 1000 < 200:
            logger.info("Target: API P95 < 200ms - PASS")
        else:
            logger.info("Target: API P95 < 200ms - FAIL")

if __name__ == "__main__":
    asyncio.run(benchmark())
