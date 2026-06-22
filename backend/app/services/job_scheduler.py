"""
=============================================================================
VeriField Nexus — Background Job Scheduler
=============================================================================
Lightweight in-process scheduler using APScheduler.
No Redis/Celery required — ideal for low-cost Nigerian deployment.

Fix history:
  v2 — Resolved deadlock caused by connection pool exhaustion:
    - Verification worker now uses a dedicated 1-connection pool that is
      completely separate from the shared request-handler pool. This means
      the background job can NEVER starve or be starved by HTTP requests.
    - Hard asyncio.wait_for wall-clock timeout (50 s) wraps the entire
      worker so a stuck coroutine is forcibly cancelled rather than
      blocking APScheduler's "max_instances" slot forever.
    - Circuit-breaker: consecutive failures trigger exponential backoff
      (up to 10 min interval) so a broken job doesn't spam Supabase.
    - Dedicated pool is torn down cleanly on scheduler shutdown.

Jobs:
  1. Verification Worker: Process pending activities (adaptive interval)

Usage:
    Called from main.py lifespan events:
    - startup: start_scheduler()
    - shutdown: shutdown_scheduler()
=============================================================================
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.services.jobs.verification_worker import process_pending_activities

logger = logging.getLogger("verifield.scheduler")

# ---------------------------------------------------------------------------
# Dedicated DB engine for background jobs
# ---------------------------------------------------------------------------
# Uses a SEPARATE pool (pool_size=1) so scheduler queries never compete with
# request-handler connections and vice-versa.  A pool of 1 is sufficient
# because all scheduler jobs run serially (max_instances=1).

def _build_job_db_url() -> str:
    url = settings.database_url or ""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


import uuid as _uuid

_job_engine = create_async_engine(
    _build_job_db_url(),
    echo=False,
    pool_size=1,           # One connection dedicated to background jobs
    max_overflow=0,        # No overflow — keeps the pool truly isolated
    pool_pre_ping=True,
    pool_recycle=300,
    pool_timeout=15,       # Give up waiting for the connection quickly
    connect_args={
        "server_settings": {"jit": "off"},
        "command_timeout": 20.0,           # Per-query hard kill at socket level
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_job_{_uuid.uuid4()}__",
    },
)

_job_session_factory = async_sessionmaker(
    _job_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# Circuit-breaker state
# ---------------------------------------------------------------------------
_consecutive_failures: int = 0
_MAX_INTERVAL_SECONDS: int = 600   # 10 minutes
_BASE_INTERVAL_SECONDS: int = 60


# ---------------------------------------------------------------------------
# Scheduler instance
# ---------------------------------------------------------------------------
scheduler = AsyncIOScheduler(
    job_defaults={
        "coalesce": True,          # Merge missed runs into one
        "max_instances": 1,        # Only one instance running at a time
        "misfire_grace_time": 30,  # Allow 30 s grace for misfires
    }
)


# ---------------------------------------------------------------------------
# Worker wrapper
# ---------------------------------------------------------------------------

async def _run_verification_worker() -> None:
    """
    Run the verification worker with a hard wall-clock timeout and
    circuit-breaker backoff on repeated failures.

    Key design decisions
    --------------------
    * Uses _job_session_factory (dedicated pool) — no contention with API.
    * asyncio.wait_for with HARD_TIMEOUT cancels any stuck coroutine.
      Because this wraps the *entire* call (including DB acquisition),
      a connection-pool stall is also cancelled within the deadline.
    * On success: reset failure counter, restore normal 60-s interval.
    * On failure: increment counter, back off exponentially up to 10 min.
    """
    global _consecutive_failures

    # Hard wall-clock limit: must finish well within the scheduler interval
    HARD_TIMEOUT = 50.0  # seconds

    try:
        async with _job_session_factory() as db:
            stats = await asyncio.wait_for(
                process_pending_activities(db=db, batch_size=10),
                timeout=HARD_TIMEOUT,
            )
        if stats["processed"] > 0:
            logger.info(f"Verification sweep complete: {stats}")
        else:
            logger.debug("Verification sweep: no pending activities")

        # Success — reset circuit breaker
        if _consecutive_failures > 0:
            _consecutive_failures = 0
            _reset_job_interval(_BASE_INTERVAL_SECONDS)

    except asyncio.TimeoutError:
        _consecutive_failures += 1
        logger.error(
            f"Verification worker timed out after {HARD_TIMEOUT}s "
            f"(failure #{_consecutive_failures})"
        )
        _apply_backoff()

    except Exception as exc:
        _consecutive_failures += 1
        logger.error(
            f"Verification worker error (failure #{_consecutive_failures}): {exc}",
            exc_info=True,
        )
        _apply_backoff()


def _apply_backoff() -> None:
    """Exponentially increase the job interval on repeated failures."""
    if _consecutive_failures < 2:
        return  # First couple of failures: keep normal cadence
    new_interval = min(
        _BASE_INTERVAL_SECONDS * (2 ** (_consecutive_failures - 1)),
        _MAX_INTERVAL_SECONDS,
    )
    _reset_job_interval(new_interval)
    logger.warning(
        f"Circuit breaker: backing off verification worker to every "
        f"{new_interval}s after {_consecutive_failures} consecutive failures"
    )


def _reset_job_interval(seconds: int) -> None:
    """Reschedule the verification job with a new interval."""
    try:
        scheduler.reschedule_job(
            "verification_worker",
            trigger=IntervalTrigger(seconds=seconds),
        )
    except Exception:
        pass  # Scheduler may be shutting down


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_scheduler() -> None:
    """Start the background job scheduler."""
    scheduler.add_job(
        _run_verification_worker,
        trigger=IntervalTrigger(seconds=_BASE_INTERVAL_SECONDS),
        id="verification_worker",
        name="Process Pending Activities",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background job scheduler started (dedicated DB pool, hard timeout=50s)")


async def shutdown_scheduler() -> None:
    """Gracefully shutdown the scheduler and its dedicated DB pool."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background job scheduler stopped")
    await _job_engine.dispose()
    logger.info("Scheduler DB pool disposed")
