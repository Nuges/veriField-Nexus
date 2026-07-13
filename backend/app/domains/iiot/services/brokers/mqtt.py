import asyncio
import json
import logging
import uuid
from typing import Any, Awaitable, Callable

import aiomqtt

logger = logging.getLogger("verifield.iiot.mqtt")


class MQTTBrokerIngestion:
    """
    Abstractions for receiving edge telemetry via MQTT.
    """

    def __init__(
        self,
        broker_url: str,
        port: int,
        ingestion_callback: Callable[[uuid.UUID, str, list], Awaitable[Any]],
    ):
        self.broker_url = broker_url
        self.port = port
        self.ingestion_callback = ingestion_callback
        self.is_connected = False
        self.client = aiomqtt.Client(hostname=self.broker_url, port=self.port)

    async def connect(self):
        """Starts the MQTT listener task."""
        asyncio.create_task(self._run_listener())

    async def _run_listener(self):
        while True:
            try:
                async with self.client as client:
                    self.is_connected = True
                    logger.info(
                        f"Connected to MQTT broker at {self.broker_url}:{self.port}"
                    )
                    await client.subscribe("nexus/telemetry/#")
                    logger.info("Subscribed to MQTT topics matching nexus/telemetry/#")

                    async for message in client.messages:
                        await self.handle_message(str(message.topic), message.payload)
            except aiomqtt.MqttError as error:
                self.is_connected = False
                logger.error(
                    f"MQTT connection error: {error}. Reconnecting in 5 seconds..."
                )
                await asyncio.sleep(5)
            except Exception as e:
                self.is_connected = False
                logger.error(f"Unexpected MQTT error: {e}")
                await asyncio.sleep(5)

    async def subscribe(self, topic_pattern: str):
        logger.debug(
            f"Ignoring manual subscribe to {topic_pattern} as client auto-subscribes in loop."
        )

    async def handle_message(self, topic: str, payload_bytes: bytes):
        """
        Parses incoming MQTT payloads and routes them to the main ingestion engine.
        Expected topic structure: nexus/telemetry/{device_id}
        """
        try:
            parts = topic.split("/")
            if len(parts) < 3 or parts[1] != "telemetry":
                return
            device_id_str = parts[2]
            device_id = uuid.UUID(device_id_str)

            payload_str = payload_bytes.decode("utf-8")
            payload_data = json.loads(payload_str)

            # Normalize to array of points if it's a single point
            if isinstance(payload_data, dict):
                payload_data = [payload_data]

            await self.ingestion_callback(device_id, "mqtt", payload_data)
        except Exception as e:
            logger.error(f"Failed to process MQTT message from topic {topic}: {e}")
