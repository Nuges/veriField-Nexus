import uuid
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.hardware.models.device import Device


class HardwareFleetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def provision_device(
        self, serial_number: str, hardware_type: str, metadata_config: Dict[str, Any]
    ) -> Device:
        """
        Provisions a new hardware device into the fleet and optionally
        links it to a digital twin.
        """
        # Check if exists
        result = await self.db.execute(
            select(Device).where(Device.serial_number == serial_number)
        )
        device = result.scalars().first()

        if not device:
            device = Device(
                id=uuid.uuid4(),
                serial_number=serial_number,
                device_type=hardware_type,
                capabilities=metadata_config,
                status="provisioned",
            )
            self.db.add(device)
            await self.db.commit()
            await self.db.refresh(device)

        return device

    async def list_devices(self) -> List[Device]:
        result = await self.db.execute(select(Device))
        return result.scalars().all()

    async def deactivate_device(self, device_id: uuid.UUID) -> Device:
        device = await self.db.get(Device, device_id)
        if device:
            device.status = "deactivated"
            await self.db.commit()
            await self.db.refresh(device)
        return device
