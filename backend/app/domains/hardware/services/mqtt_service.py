import asyncio
import json
import logging
from typing import Callable

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

logger = logging.getLogger(__name__)


class MQTTIntegrationService:
    def __init__(
        self,
        broker_url: str = "localhost",
        port: int = 1883,
        topic: str = "iot/telemetry/#",
    ):
        self.broker_url = broker_url
        self.port = port
        self.topic = topic
        self._client = None
        self._on_message_callback = None
        self._loop = asyncio.get_event_loop()

    def start(self, on_message_callback: Callable):
        self._on_message_callback = on_message_callback
        if not mqtt:
            logger.warning(
                "paho-mqtt not installed, running mock MQTT broker integration."
            )
            return

        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        try:
            self._client.connect(self.broker_url, self.port, 60)
            self._client.loop_start()
            logger.info(
                f"MQTT Service started, listening on {self.broker_url}:{self.port}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to MQTT Broker: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker. Subscribing to topic: {self.topic}")
            client.subscribe(self.topic)
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            device_id = str(msg.topic).split("/")[-1]

            # Using loop.call_soon_threadsafe to interact with async components if needed
            if self._on_message_callback:
                self._loop.call_soon_threadsafe(
                    self._on_message_callback, device_id, payload
                )
        except json.JSONDecodeError:
            logger.error(f"Failed to decode MQTT payload: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def stop(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT Service stopped.")
