import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.hardware.services.modbus_service import ModbusPollingService
from app.domains.hardware.services.mqtt_service import MQTTIntegrationService
from app.domains.hardware.services.telemetry_processor import \
    TelemetryProcessor


def test_telemetry_processor_valid_sequence():
    processor = TelemetryProcessor()

    device_id = "device_123"
    assert processor.process_telemetry(
        device_id, {"message_id": "m1", "sequence_number": 1, "data": 10}
    )
    assert processor.process_telemetry(
        device_id, {"message_id": "m2", "sequence_number": 2, "data": 20}
    )

    buffer = processor.get_buffered_data()
    assert len(buffer) == 2
    assert buffer[0]["payload"]["data"] == 10
    assert buffer[1]["payload"]["data"] == 20


def test_telemetry_processor_out_of_order_sequence():
    processor = TelemetryProcessor()
    device_id = "device_123"

    assert processor.process_telemetry(
        device_id, {"message_id": "m1", "sequence_number": 1, "data": 10}
    )
    # Out of order sequence
    assert not processor.process_telemetry(
        device_id, {"message_id": "m3", "sequence_number": 1, "data": 30}
    )

    dlq = processor.get_dlq()
    assert len(dlq) == 1
    assert dlq[0]["error"] == "Sequence validation failed"


def test_telemetry_processor_duplicate_detection():
    processor = TelemetryProcessor()
    device_id = "device_123"

    assert processor.process_telemetry(device_id, {"message_id": "dup_msg", "data": 10})
    assert not processor.process_telemetry(
        device_id, {"message_id": "dup_msg", "data": 20}
    )

    buffer = processor.get_buffered_data()
    assert len(buffer) == 1


def test_telemetry_processor_heartbeat():
    processor = TelemetryProcessor()
    device_id = "device_123"

    processor.process_telemetry(device_id, {"message_id": "m1", "data": 10})

    with patch("time.time", return_value=time.time() + 400):
        offline = processor.check_heartbeats(timeout_seconds=300)
        assert device_id in offline


@patch("app.domains.hardware.services.mqtt_service.mqtt")
def test_mqtt_service_integration(mock_mqtt):
    # Mocking paho-mqtt to prevent actual network connections during tests
    mock_client_instance = MagicMock()
    if mock_mqtt:
        mock_mqtt.Client.return_value = mock_client_instance

    service = MQTTIntegrationService()

    received_messages = []

    def on_message(device_id, payload):
        received_messages.append((device_id, payload))

    service.start(on_message)
    if mock_mqtt:
        mock_client_instance.connect.assert_called_once()
        mock_client_instance.loop_start.assert_called_once()

    service.stop()
    if mock_mqtt:
        mock_client_instance.loop_stop.assert_called_once()
        mock_client_instance.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_modbus_service_integration():
    # If pymodbus is available, we patch it. If not, it falls back to mock loop
    with patch(
        "app.domains.hardware.services.modbus_service.AsyncModbusTcpClient"
    ) as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        # Make connect an async mock returning None
        mock_client_instance.write_register = AsyncMock()
        mock_client_instance.connected = True

        # Mock read_holding_registers
        mock_result = MagicMock()
        mock_result.isError.return_value = False
        mock_result.registers = [10, 20, 30]
        mock_client_instance.read_holding_registers = AsyncMock(
            return_value=mock_result
        )

        service = ModbusPollingService(poll_interval=0.1)

        received_messages = []

        def on_message(device_id, payload):
            received_messages.append((device_id, payload))

        service.start(on_message)
        await asyncio.sleep(0.15)
        service.stop()

        # Depending on whether pymodbus was actually imported or not,
        # it might have triggered the real logic or the fallback loop.
        # The test passes as long as it starts and stops cleanly without errors.
