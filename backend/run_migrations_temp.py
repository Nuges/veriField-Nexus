import asyncio
from app.main import lifespan
from fastapi import FastAPI

app = FastAPI()

async def main():
    print("Starting migrations...")
    async with lifespan(app):
        print("Lifespan started. Waiting for 60 seconds to ensure background tasks complete...")
        await asyncio.sleep(60)
        print("Done waiting.")

if __name__ == "__main__":
    asyncio.run(main())
