import asyncio
import sys
from app.db.session import async_session_factory
from app.services.jobs.verification_worker import process_pending_activities

async def run():
    print("Running process_pending_activities...")
    try:
        stats = await process_pending_activities(batch_size=20)
        print("Success stats:", stats)
    except Exception as e:
        print("Worker failed with exception:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
