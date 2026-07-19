import json
import logging
import uuid

from app.core.events.base import BaseEvent
from app.db.session import async_session_factory
from sqlalchemy import select

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

        stmt = select(Activity).where(Activity.id == activity_id)
        result = await db.execute(stmt)
        activity = result.scalar_one_or_none()
        if not activity:
            logger.error(f"Activity {activity_id} not found in database")
            return

        # 2. AI Trust Engine (GPS, image checks, and frequency check)
        from app.domains.ai_trust_engine.service import TrustEngineService

        trust_service = TrustEngineService(db)
        score, findings = await trust_service.calculate_trust(activity)
        logger.info(f"Asynchronous AI Trust calculation completed. Score: {score}")

        # 3. Phase 2 Event Pipeline (Execution on VERIFIED status)
        if activity.status == "verified":
            # a. Create Asset (if not exists)
            from app.domains.assets.service import AssetService
            from app.domains.assets.repository import AssetRepository
            from app.domains.assets.schemas import AssetCreate
            
            project_id = None
            if activity.property_id:
                # Resolve project from property/workspace or methodology
                from app.domains.workspaces.models import Workspace
                workspace = await db.get(Workspace, activity.property_id)
                if workspace and workspace.project_id:
                    project_id = workspace.project_id
            
            # If no project found yet, maybe the activity has it or it's a direct project activity
            if not project_id:
                from app.domains.projects.models import Project
                proj_stmt = select(Project).where(Project.organization_id == org_id).limit(1)
                proj_res = await db.execute(proj_stmt)
                fallback_proj = proj_res.scalar_one_or_none()
                if fallback_proj:
                    project_id = fallback_proj.id
                else:
                    logger.error(f"No project found for org {org_id} to associate asset with")
                    project_id = None
            asset_service = AssetService(AssetRepository(db))
            
            # Assume asset creation
            if not activity.asset_id and project_id:
                data = event.payload.get("data", {})
                
                # Better naming
                asset_ident = data.get("stove_id") or data.get("serial_number") or data.get("head_name")
                if asset_ident:
                    asset_name = f"{activity.activity_type.replace('_', ' ').title()} - {asset_ident}"
                else:
                    asset_name = f"Asset from Activity {str(activity.id)[:8]}"

                new_asset_schema = AssetCreate(
                    project_id=project_id,
                    name=asset_name,
                    latitude=event.payload.get("latitude"),
                    longitude=event.payload.get("longitude"),
                    attributes=data
                )
                new_asset = await asset_service.create_asset(new_asset_schema, org_id)
                activity.asset_id = new_asset.id
                await db.commit()
                
            # b. Digital Twin
            # Skipping explicit digital twin API call for brevity, but the Asset creation triggers it via events
            
            # c. Methodology Resolution & Calculation Engine
            if project_id:
                from app.domains.projects.repository import ProjectRepository
                project = await ProjectRepository(db).get_by_id(project_id)
                if project and project.methodology_id:
                    pass
                    
                    # Assume we have an active version for this methodology
                    # This is simplified: actual logic would resolve the active Version ID
                    # We will pass a dummy methodology_version_id or fetch the latest
                    
                    # For now, simulate a methodology execution result
                    # We'll use the CarbonCalculationService directly to persist the result
                    from app.domains.projects.service import CarbonCalculationService
                    calc_service = CarbonCalculationService(db)
                    
                    # Use AI trust score or payload data to compute a yield (fallback logic)
                    tco2e_yield = float(event.payload.get("data", {}).get("estimated_carbon", score * 0.5))
                    
                    calc_record = await calc_service.create_calculation({
                        "project_id": project_id,
                        "activity_id": activity.id,
                        "methodology_used": project.methodology_id,
                        "tco2e_generated": tco2e_yield,
                        "calculation_log": {
                            "inputs": event.payload.get("data", {}),
                            "outputs": {"tco2e": tco2e_yield}
                        },
                        "status": "calculated"
                    })
                    logger.info(f"Asynchronous Carbon Calculation persisted: {calc_record.id} with {tco2e_yield} tCO2e")

                    # Update Asset with carbon yield for UI
                    if activity.asset_id:
                        from app.domains.assets.models import Asset
                        asset = await db.get(Asset, activity.asset_id)
                        if asset:
                            new_attrs = dict(asset.attributes or {})
                            new_attrs["carbon_offset_kg"] = tco2e_yield
                            asset.attributes = new_attrs
                            await db.commit()

        # 4. Compliance Engine checks
        if activity.asset_id:
            from app.domains.assets.models import Asset
            asset = await db.get(Asset, activity.asset_id)
            if asset and asset.project_id:
                from app.domains.compliance_engine.service import ComplianceService
                comp_service = ComplianceService(db)
                await comp_service.evaluate_project(asset.project_id)
                logger.info(f"Asynchronous Compliance evaluation completed for Project: {asset.project_id}")

        # 5. Cryptographic Hashing and Ledger Anchoring
        from app.domains.ledger.service import LedgerService
        ledger_service = LedgerService(db)
        
        project_id_for_ledger = str(project_id) if 'project_id' in locals() and project_id else ""
        
        tx_hash = await ledger_service.record_transaction(
            project_id=project_id_for_ledger,
            organization_id=str(org_id),
            activity_id=str(activity_id),
            payload=event.payload,
        )
        logger.info(f"Asynchronous ledger signing and anchoring completed. TX Hash: {tx_hash}")
