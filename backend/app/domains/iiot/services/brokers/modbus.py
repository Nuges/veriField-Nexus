import logging
import uuid
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class ModbusGateway:
    """
    Abstractions for polling edge devices via Modbus TCP / RTU.
    """

    def __init__(
        self, ingestion_callback: Callable[[uuid.UUID, str, list], Awaitable[Any]]
    ):
        self.ingestion_callback = ingestion_callback

    async def poll_device(
        self, device_id: uuid.UUID, ip_address: str, port: int, registers: list
    ):
        """
        Polls a Modbus TCP device for specified registers and routes to ingestion engine.
        """
        logger.info(f"Polling Modbus TCP device {device_id} at {ip_address}:{port}")

        # Simulated Modbus read
        payload = []
        for reg in registers:
            payload.append({"local_identifier": str(reg), "value": 0.0})  # Placeholder

        await self.ingestion_callback(device_id, "modbus_tcp", payload)
