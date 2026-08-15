import json
import logging
import uuid
from typing import Any, Dict

from fastapi import (APIRouter, Depends, HTTPException, WebSocket,
                     WebSocketDisconnect)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.hardware.models.device import Device
from app.domains.hardware.services.provisioning import HardwareFleetService
from app.domains.hardware.services.telemetry_processor import processor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/provision", tags=["Hardware Fleet"])
async def provision_hardware(
    serial_number: str,
    hardware_type: str,
    metadata_config: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("admin:all")),
):
    """
    Provisions a new hardware device into the fleet.
    """
    svc = HardwareFleetService(db)
    device = await svc.provision_device(serial_number, hardware_type, metadata_config)
    return device


@router.get("/devices", tags=["Hardware Fleet"])
async def list_fleet_devices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("project:read")),
):
    """
    Lists hardware devices. Non-Super Admin users see only devices
    linked to their organization via the DigitalTwin → Asset chain.
    """
    if user.role == "SUPER_ADMIN":
        svc = HardwareFleetService(db)
        devices = await svc.list_devices()
        return {"devices": devices}

    # Tenant-scoped: Device → DigitalTwin → Asset → organization_id
    from app.domains.digital_twins.models.twin import DigitalTwin
    from app.domains.assets.models import Asset

    stmt = (
        select(Device)
        .join(DigitalTwin, DigitalTwin.device_id == Device.id)
        .join(Asset, Asset.id == DigitalTwin.asset_id)
        .where(Asset.organization_id == user.organization_id)
    )
    result = await db.execute(stmt)
    devices = result.scalars().all()
    return {"devices": devices}


@router.post("/devices/{device_id}/deactivate", tags=["Hardware Fleet"])
async def deactivate_device(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("admin:all")),
):
    """
    Deactivates a hardware device.
    """
    svc = HardwareFleetService(db)
    device = await svc.deactivate_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.websocket("/ws/telemetry/{device_id}")
async def websocket_telemetry_endpoint(
    websocket: WebSocket,
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time IIoT telemetry ingestion.
    Requires device authentication via provision_token as the first message.

    Protocol:
    1. Client connects to /ws/telemetry/{device_id}
    2. Server accepts the WebSocket connection
    3. Client MUST send auth message as first frame: {"provision_token": "<token>"}
    4. Server validates token against Device record
    5. If valid and device is active, telemetry ingestion begins
    6. If invalid, server closes connection with 4001/4003
    """
    await websocket.accept()
    logger.info(f"WebSocket connection attempt for device: {device_id}")

    # --- Phase 1: Device Authentication ---
    try:
        auth_data = await websocket.receive_text()
        try:
            auth_payload = json.loads(auth_data)
        except json.JSONDecodeError:
            await websocket.close(code=4001, reason="Invalid authentication frame")
            return

        token = auth_payload.get("provision_token")
        if not token:
            await websocket.close(code=4001, reason="Missing provision_token")
            return

        try:
            device_uid = uuid.UUID(str(device_id))
        except (ValueError, TypeError):
            await websocket.close(code=4001, reason="Invalid device ID format")
            return

        # Validate device exists, is active, and token matches
        result = await db.execute(
            select(Device).where(Device.id == device_uid)
        )
        device = result.scalar_one_or_none()

        if not device:
            await websocket.close(code=4001, reason="Device not found")
            return

        if not device.provision_token or device.provision_token != token:
            logger.warning(f"Invalid provision_token for device {device_id}")
            await websocket.close(code=4003, reason="Invalid credentials")
            return

        # Device must be in an active lifecycle state
        active_states = {"Provision", "Assign", "Calibrate", "Activate", "Monitor", "Maintenance"}
        if device.status not in active_states:
            await websocket.close(code=4003, reason=f"Device is not active (status: {device.status})")
            return

        logger.info(f"Device {device_id} authenticated successfully")
        await websocket.send_json({"status": "authenticated"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected during auth for device: {device_id}")
        return

    # --- Phase 2: Telemetry Ingestion ---
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                success = processor.process_telemetry(device_id, payload)
                if success:
                    await websocket.send_json({"status": "received"})
                else:
                    await websocket.send_json(
                        {"status": "rejected", "reason": "validation failed"}
                    )
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for device: {device_id}")
