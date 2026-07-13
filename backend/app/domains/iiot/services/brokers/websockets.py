import logging
import uuid
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class WebSocketIngestion:
    """
    Abstractions for receiving edge telemetry via WebSockets & HTTP Push/Pull listeners.
    """

    def __init__(
        self, ingestion_callback: Callable[[uuid.UUID, str, list], Awaitable[Any]]
    ):
        self.ingestion_callback = ingestion_callback

    async def handle_websocket_message(self, device_id: uuid.UUID, data: dict):
        """
        Parses incoming WebSocket JSON payloads.
        """
        try:
            payload = data.get("payload", [])
            if not isinstance(payload, list):
                payload = [payload]

            await self.ingestion_callback(device_id, "websocket", payload)
        except Exception as e:
            logger.error(
                f"Failed to process WebSocket message for device {device_id}: {e}"
            )

    async def handle_http_push(self, device_id: uuid.UUID, data: dict):
        """
        Parses incoming HTTP Push JSON payloads.
        """
        try:
            payload = data.get("payload", [])
            if not isinstance(payload, list):
                payload = [payload]

            await self.ingestion_callback(device_id, "http_push", payload)
        except Exception as e:
            logger.error(
                f"Failed to process HTTP Push message for device {device_id}: {e}"
            )
