import asyncio
from app.main import lifespan
from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    app = FastAPI()
    print("Starting lifespan to initialize DB...")
    async with lifespan(app):
        print("Lifespan triggered. Wait 5s for DB pool pre-warming and schema creation.")
        await asyncio.sleep(5)
    print("Lifespan completed.")

if __name__ == "__main__":
    asyncio.run(main())
