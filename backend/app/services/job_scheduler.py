"""
=============================================================================
VeriField Nexus — Background Job Scheduler
=============================================================================
Lightweight in-process scheduler using APScheduler.
No Redis/Celery required — ideal for low-cost Nigerian deployment.

Jobs:
1. Verification Worker: Process pending activities every 60s
2. Sensor Sweep: Recompute sensor stats for recently updated assets

Usage:
    Called from main.py lifespan events:
    - startup: scheduler.start()
    - shutdown: scheduler.shutdown()
=============================================================================
"""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.jobs.verification_worker import process_pending_activities

logger = logging.getLogger("verifield.scheduler")

# Global scheduler instance
scheduler = AsyncIOScheduler(
    job_defaults={
        "coalesce": True,          # Merge missed runs into one
        "max_instances": 1,        # Only one instance of each job at a time
        "misfire_grace_time": 30,  # Allow 30s grace for misfires
    }
)


async def _run_verification_worker():
    """Wrapper to run the verification worker with retry on DB errors."""
    import asyncio
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            stats = await asyncio.wait_for(
                process_pending_activities(batch_size=20),
                timeout=25.0
            )
            if stats["processed"] > 0:
                logger.info(f"Verification sweep: {stats}")
            return
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Verification worker error (attempt {attempt + 1}), retrying in 5s: {e}")
                await asyncio.sleep(5)
            else:
                logger.error(f"Verification worker error (final attempt): {e}")


def start_scheduler():
    """Start the background job scheduler."""
    # Process pending activities every 60 seconds
    scheduler.add_job(
        _run_verification_worker,
        trigger=IntervalTrigger(seconds=60),
        id="verification_worker",
        name="Process Pending Activities",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background job scheduler started")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background job scheduler stopped")
