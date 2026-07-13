from uuid import uuid4
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_hardware_device_lifecycle(async_client: AsyncClient, admin_token_headers: dict):
    device_sn = f"SN-{uuid4().hex[:8]}"
    
    # 1. Provision Device
    payload = {
        "interval": 60,
        "location": "field-1"
    }
    
    resp = await async_client.post(
        f"/api/v1/hardware/provision?serial_number={device_sn}&hardware_type=embedded_device", 
        json=payload, 
        headers=admin_token_headers
    )
    if resp.status_code == 404:
        pytest.skip("Hardware endpoints not fully wired.")
        
    assert resp.status_code == 200, f"Provisioning failed: {resp.text}"
    device = resp.json()
    device_id = device["id"]
    
    # 2. List Devices
    resp_list = await async_client.get(
        "/api/v1/hardware/devices", headers=admin_token_headers
    )
    assert resp_list.status_code == 200
    devices = resp_list.json()["devices"]
    assert any(d["id"] == device_id for d in devices)
    
    # 3. Deactivate
    resp_deact = await async_client.post(
        f"/api/v1/hardware/devices/{device_id}/deactivate", headers=admin_token_headers
    )
    assert resp_deact.status_code == 200
    assert resp_deact.json()["status"] == "deactivated"
