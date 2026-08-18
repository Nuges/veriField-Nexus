import asyncio
import logging
from app.domains.jobs.engine import job_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verifield.worker")

async def run():
    logger.info("Starting VeriField Nexus background worker...")
    job_engine.start()
    try:
        # Keep running
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping VeriField Nexus worker...")
        job_engine.stop()

if __name__ == "__main__":
    asyncio.run(run())
