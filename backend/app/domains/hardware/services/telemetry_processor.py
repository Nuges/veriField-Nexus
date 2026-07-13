import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class TelemetryProcessor:
    def __init__(self):
        self.edge_buffer: List[Dict[str, Any]] = []
        self.dead_letter_queue: List[Dict[str, Any]] = []

        # State for sequence validation and deduplication
        self.device_sequence_map: Dict[str, int] = {}
        self.device_last_seen: Dict[str, float] = {}
        self.processed_message_ids: set = set()

    def process_telemetry(self, device_id: str, payload: Dict[str, Any]) -> bool:
        """Processes incoming telemetry with IIoT edge validations."""
        # Heartbeat validation
        self.device_last_seen[device_id] = time.time()

        message_id = payload.get("message_id")
        seq_num = payload.get("sequence_number")

        # Duplicate packet detection
        if message_id and message_id in self.processed_message_ids:
            logger.warning(f"Duplicate message detected: {message_id}")
            return False

        if message_id:
            self.processed_message_ids.add(message_id)
            # Prevent memory leak in a real app
            if len(self.processed_message_ids) > 10000:
                # Remove an arbitrary item to keep size bounded
                self.processed_message_ids.pop()

        # Sequence validation
        if seq_num is not None:
            expected_seq = self.device_sequence_map.get(device_id, 0) + 1
            if seq_num < expected_seq:
                logger.error(
                    f"Out of order sequence for {device_id}. Expected {expected_seq}, got {seq_num}"
                )
                self.dead_letter_queue.append(
                    {
                        "device_id": device_id,
                        "payload": payload,
                        "error": "Sequence validation failed",
                    }
                )
                return False
            self.device_sequence_map[device_id] = seq_num

        # Edge buffering
        self.edge_buffer.append(
            {"device_id": device_id, "payload": payload, "timestamp": time.time()}
        )

        # Digital Twin Synchronization
        self._sync_digital_twin(device_id, payload)

        return True

    def _sync_digital_twin(self, device_id: str, payload: Dict[str, Any]):
        """Simulate Digital Twin Sync."""
        logger.info(f"Syncing Digital Twin for device {device_id} with data {payload}")
        # In a full implementation, this would publish to a message broker or call a Digital Twin service

    def get_buffered_data(self) -> List[Dict[str, Any]]:
        """Returns and clears the edge buffer."""
        data = self.edge_buffer.copy()
        self.edge_buffer.clear()
        return data

    def get_dlq(self) -> List[Dict[str, Any]]:
        return self.dead_letter_queue

    def check_heartbeats(self, timeout_seconds: float = 300.0) -> List[str]:
        """Returns a list of device IDs that missed their heartbeat."""
        current_time = time.time()
        offline_devices = []
        for device_id, last_seen in self.device_last_seen.items():
            if current_time - last_seen > timeout_seconds:
                offline_devices.append(device_id)
        return offline_devices


# Global instance for simplification in this scope
processor = TelemetryProcessor()
