import uuid
from typing import Any, Dict, List
import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.hardware.models.device import Device


class HardwareProvisioningService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_to_inventory(self, serial_number: str, hardware_type: str, manufacturer: str, model: str) -> Device:
        device = Device(
            serial_number=serial_number,
            device_type=hardware_type,
            manufacturer=manufacturer,
            model=model,
            status="Inventory"
        )
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def transition_state(self, device_id: uuid.UUID, new_status: str, metadata: Dict[str, Any] = None) -> Device:
        """
        Transitions a device through the lifecycle:
        Inventory -> Commission -> Provision -> Assign -> Calibrate -> Activate -> Monitor -> Maintenance -> Retire
        """
        device = await self.db.get(Device, device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found.")

        # Log event history
        history = list(device.event_history) if device.event_history else []
        history.append({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "from_status": device.status,
            "to_status": new_status,
            "metadata": metadata or {}
        })
        
        device.status = new_status
        device.event_history = history
        
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def provision_device(self, device_id: uuid.UUID, public_key: str, certificate: str) -> Device:
        """Cryptographically provision a device for secure comms."""
        device = await self.db.get(Device, device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found.")
            
        device.public_key = public_key
        device.certificate = certificate
        device.provision_token = uuid.uuid4().hex
        
        return await self.transition_state(device.id, "Provision")

    async def list_devices(self) -> List[Device]:
        result = await self.db.execute(select(Device))
        return result.scalars().all()

class HardwareFleetService(HardwareProvisioningService):
    """Legacy alias for backward compatibility with api.py."""
    
    async def provision_device(self, serial_number: str, hardware_type: str, metadata_config: Dict[str, Any] = None) -> Device:
        """Alias that matches the api.py signature."""
        device = await self.add_to_inventory(
            serial_number=serial_number, 
            hardware_type=hardware_type, 
            manufacturer=metadata_config.get("manufacturer", "Unknown") if metadata_config else "Unknown",
            model=metadata_config.get("model", "Unknown") if metadata_config else "Unknown"
        )
        return await self.transition_state(device.id, "Provision", metadata_config)
        
    async def deactivate_device(self, device_id: uuid.UUID) -> Device:
        """Alias for deactivating a device."""
        return await self.transition_state(device_id, "Retire")
