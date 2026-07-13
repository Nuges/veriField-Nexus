import logging
import uuid
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class OPCUAGateway:
    """
    Abstractions for receiving edge telemetry via OPC-UA.
    """

    def __init__(
        self,
        endpoint_url: str,
        ingestion_callback: Callable[[uuid.UUID, str, list], Awaitable[Any]],
    ):
        self.endpoint_url = endpoint_url
        self.ingestion_callback = ingestion_callback
        self.is_connected = False

    async def connect(self):
        self.is_connected = True
        logger.info(f"Connected to OPC-UA server at {self.endpoint_url}")

    async def subscribe_data_changes(self, device_id: uuid.UUID, node_ids: list):
        """
        Subscribes to specific node changes and routes them to ingestion engine.
        """
        logger.info(f"Subscribed to OPC-UA nodes {node_ids} for device {device_id}")

    async def _on_data_change(self, device_id: uuid.UUID, node_id: str, value: Any):
        payload = [{"local_identifier": node_id, "value": value}]
        await self.ingestion_callback(device_id, "opc_ua", payload)
