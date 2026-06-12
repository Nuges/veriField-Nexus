import asyncio
from app.db.session import engine

async def test():
    print("Connecting to DB...")
    try:
        async with engine.connect() as conn:
            print("Successfully connected!")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
