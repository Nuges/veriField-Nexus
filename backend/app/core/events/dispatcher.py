import json
import logging
import uuid

from app.core.events.base import BaseEvent
from app.db.session import async_session_factory

logger = logging.getLogger("verifield.events.dispatcher")


async def dispatch_async_event(event_json: str):
    """
    Deserializes event payload and runs processing engines in the background worker.
    """
    try:
        data = json.loads(event_json)
        event = BaseEvent(**data)
        logger.info(
            f"Background worker enqueued event: {event.event_type} (ID: {event.event_id})"
        )

        # Route based on event type
        if event.event_type == "activity.created":
            await _handle_activity_created(event)
        else:
            logger.debug(
                f"Event type {event.event_type} has no registered worker handlers."
            )
    except Exception as e:
        logger.error(f"Failed to dispatch async event: {e}")


async def _handle_activity_created(event: BaseEvent):
    activity_id_str = event.payload.get("activity_id")
    org_id_str = event.payload.get("organization_id")

    if not activity_id_str or not org_id_str:
        logger.error("Event payload missing activity_id or organization_id")
        return

    activity_id = uuid.UUID(activity_id_str)
    org_id = uuid.UUID(org_id_str)

    async with async_session_factory() as db:
        # 1. Retrieve Activity model
        from app.domains.activities.models import Activity

        activity = await db.get(Activity, activity_id)
        if not activity:
            logger.error(f"Activity {activity_id} not found in database")
            return

        # 2. AI Trust Engine (GPS, image checks, and frequency check)
        from app.domains.ai_trust_engine.service import TrustEngineService

        trust_service = TrustEngineService(db)
        score, findings = await trust_service.calculate_trust(activity)
        logger.info(f"Asynchronous AI Trust calculation completed. Score: {score}")

        # 3. Compliance Engine checks
        project_id = None
        if activity.asset_id:
            from app.domains.assets.models import Asset

            asset = await db.get(Asset, activity.asset_id)
            if asset and asset.project_id:
                project_id = asset.project_id
                from app.domains.compliance_engine.service import \
                    ComplianceService

                comp_service = ComplianceService(db)
                await comp_service.evaluate_project(project_id)
                logger.info(
                    f"Asynchronous Compliance evaluation completed for Project: {project_id}"
                )

        # 4. Cryptographic Hashing and Ledger Anchoring
        from app.domains.ledger.service import LedgerService

        ledger_service = LedgerService(db)
        tx_hash = await ledger_service.record_transaction(
            project_id=str(project_id) if project_id else "",
            organization_id=str(org_id),
            activity_id=str(activity_id),
            payload=event.payload,
        )
        logger.info(
            f"Asynchronous ledger signing and anchoring completed. TX Hash: {tx_hash}"
        )
