import json
import logging
import uuid
from typing import Any, Dict

from fastapi import (APIRouter, Depends, HTTPException, WebSocket,
                     WebSocketDisconnect)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.db.session import get_db
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
    db: AsyncSession = Depends(get_db), user=Depends(require_permission("project:read"))
):
    """
    Lists all hardware devices in the fleet.
    """
    svc = HardwareFleetService(db)
    devices = await svc.list_devices()
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
async def websocket_telemetry_endpoint(websocket: WebSocket, device_id: str):
    """
    WebSocket endpoint for real-time IIoT telemetry ingestion.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for device: {device_id}")
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
