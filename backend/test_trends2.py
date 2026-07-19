import asyncio
from httpx import AsyncClient

async def run():
    async with AsyncClient() as client:
        res = await client.get("http://127.0.0.1:8000/api/v1/reporting/metrics/trends?days=60", headers={"Authorization": "Bearer dev_token"})
        print(res.status_code)
        print(res.json())

asyncio.run(run())
