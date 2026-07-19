import asyncio
import logging
from typing import Callable, Optional

try:
    from pymodbus.client import AsyncModbusTcpClient
except ImportError:
    AsyncModbusTcpClient = None

logger = logging.getLogger(__name__)


class ModbusPollingService:
    def __init__(
        self, host: str = "127.0.0.1", port: int = 502, poll_interval: int = 5
    ):
        self.host = host
        self.port = port
        self.poll_interval = poll_interval
        self._task: Optional[asyncio.Task] = None

    def start(self, on_data_callback: Callable):
        self._task = asyncio.create_task(self._poll_loop(on_data_callback))

    async def _poll_loop(self, on_data_callback: Callable):
        if not AsyncModbusTcpClient:
            logger.error("pymodbus not installed. Modbus polling disabled.")
            return

        client = AsyncModbusTcpClient(self.host, port=self.port)
        await client.connect()
        try:
            while True:
                if client.connected:
                    result = await client.read_holding_registers(0x00, count=3, slave=1)
                    if not result.isError():
                        payload = {
                            "message_id": f"modbus_{asyncio.get_event_loop().time()}",
                            "registers": result.registers,
                        }
                        on_data_callback("modbus_device_1", payload)
                    else:
                        logger.error(f"Modbus read error: {result}")
                else:
                    await client.connect()
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            pass
        finally:
            client.close()

    def stop(self):
        if self._task:
            self._task.cancel()
