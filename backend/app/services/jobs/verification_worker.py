"""
=============================================================================
VeriField Nexus — Verification Worker
=============================================================================
Background job that processes pending activities:
1. Fetches activities with status='pending'
2. Runs Trust Engine scoring
3. Runs AI Anomaly Detection
4. Updates activity status based on score

Note: The db session is injected by the scheduler (job_scheduler.py) using
a DEDICATED connection pool that is fully isolated from the HTTP request
pool. Do NOT call async_session_factory() here.
=============================================================================
"""

import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.services.trust_engine import TrustEngine
from app.services.ai_detector import AnomalyDetector

logger = logging.getLogger("verifield.jobs.verification")


async def process_pending_activities(db: AsyncSession, batch_size: int = 10) -> dict:
    """
    Process a batch of pending activities through the Trust Engine
    and AI Anomaly Detector.

    Args:
        db: An already-open AsyncSession from the scheduler's dedicated pool.
            The caller is responsible for lifecycle management.
        batch_size: Maximum number of activities to process per run.
                    Kept at 10 (down from 20) to stay well within the
                    50-second wall-clock budget even on slow connections.

    Returns:
        dict with counts of processed, verified, review, flagged, errors
    """
    stats = {
        "processed": 0,
        "verified": 0,
        "review": 0,
        "flagged": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    # Fetch pending activities (oldest first)
    result = await db.execute(
        select(Activity)
        .where(Activity.status == "pending")
        .order_by(Activity.created_at.asc())
        .limit(batch_size)
    )
    pending = result.scalars().all()

    if not pending:
        logger.debug("No pending activities to process")
        return stats

    logger.info(f"Processing {len(pending)} pending activities")

    for activity in pending:
        try:
            # Run Trust Engine
            trust_engine = TrustEngine(db)
            score, flags = await trust_engine.calculate_trust_score(activity)

            # Run AI Anomaly Detector
            try:
                detector = AnomalyDetector(db)
                anomaly_flags = await detector.analyze_activity(activity)
                # If anomalies detected, force status to 'flagged'
                if anomaly_flags and activity.status == "verified":
                    activity.status = "flagged"
                    activity.trust_flags["anomaly_detected"] = True
            except Exception as e:
                logger.warning(f"Anomaly detection failed for {activity.id}: {e}")

            stats["processed"] += 1

            # Count by final status
            if activity.status == "verified":
                stats["verified"] += 1
                try:
                    from app.services.quantification_engine import QuantificationEngine
                    quant_engine = QuantificationEngine(db)
                    await quant_engine.quantify_activity(activity.id, None)
                except Exception as qe:
                    logger.error(f"Quantification failed for {activity.id}: {qe}")
            elif activity.status == "review":
                stats["review"] += 1
            elif activity.status == "flagged":
                stats["flagged"] += 1

            logger.info(
                f"Activity {activity.id}: score={score:.1f} "
                f"status={activity.status} flags={len(flags)}"
            )

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Failed to process activity {activity.id}: {e}")
            # Mark as review so it doesn't block the queue forever
            activity.status = "review"
            activity.trust_flags = {"processing_error": str(e)}

    # Single commit for the entire batch — reduces DB round-trips from N to 1
    # and ensures all changes are atomic (all succeed or all roll back together).
    try:
        await db.commit()
    except Exception as commit_err:
        logger.error(f"Batch commit failed: {commit_err}")
        await db.rollback()
        stats["errors"] += stats["processed"]
        stats["processed"] = 0

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(
        f"Verification batch complete: {stats['processed']} processed, "
        f"{stats['verified']} verified, {stats['review']} review, "
        f"{stats['flagged']} flagged, {stats['errors']} errors"
    )
    return stats
