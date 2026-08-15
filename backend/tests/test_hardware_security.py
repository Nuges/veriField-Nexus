"""
Security & Tenant Isolation Tests for Hardware Fleet Domain (P1-06 / P1-07)

Verifies:
1. Tenant-scoped device list:
   - Tenant A only sees devices linked to Tenant A
   - Tenant B only sees devices linked to Tenant B
   - Super Admin sees all devices
2. WebSocket Telemetry Ingestion Authentication:
   - Unauthenticated / missing token frame is rejected and closed
   - Invalid token is rejected with close code 4003
   - Valid token on active device authenticates successfully and processes telemetry
"""
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import get_current_user
from app.db.session import (
    get_db,
    _init_fallback_db,
    _get_fallback_session_factory,
)
from app.domains.assets.models import Asset
from app.domains.authentication.models import User
from app.domains.digital_twins.models.twin import DigitalTwin
from app.domains.hardware.models.device import Device
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


@pytest.mark.asyncio
async def test_hardware_fleet_tenant_scoping():
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()

    user_a = User(
        id=uuid.uuid4(),
        email=f"admin_a_{uuid.uuid4().hex[:6]}@tenant-a.com",
        full_name="Admin Tenant A",
        role="ORG_ADMIN",
        organization_id=org_a_id,
        status="active",
    )
    user_b = User(
        id=uuid.uuid4(),
        email=f"admin_b_{uuid.uuid4().hex[:6]}@tenant-b.com",
        full_name="Admin Tenant B",
        role="ORG_ADMIN",
        organization_id=org_b_id,
        status="active",
    )
    super_admin = User(
        id=uuid.uuid4(),
        email=f"superadmin_{uuid.uuid4().hex[:6]}@verifield.com",
        full_name="Super Admin",
        role="SUPER_ADMIN",
        organization_id=None,
        status="active",
    )

    org_a = Organization(id=org_a_id, name=f"Tenant A {uuid.uuid4().hex[:6]}", status="ACTIVE")
    org_b = Organization(id=org_b_id, name=f"Tenant B {uuid.uuid4().hex[:6]}", status="ACTIVE")

    project_a = Project(id=uuid.uuid4(), project_code=f"PRJ-A-{uuid.uuid4().hex[:4]}", name="Project A", organization_id=org_a_id)
    project_b = Project(id=uuid.uuid4(), project_code=f"PRJ-B-{uuid.uuid4().hex[:4]}", name="Project B", organization_id=org_b_id)

    asset_a = Asset(id=uuid.uuid4(), project_id=project_a.id, organization_id=org_a_id, name="Asset A", status="active")
    asset_b = Asset(id=uuid.uuid4(), project_id=project_b.id, organization_id=org_b_id, name="Asset B", status="active")

    device_a = Device(
        id=uuid.uuid4(),
        serial_number=f"SN-A-{uuid.uuid4().hex[:8]}",
        device_type="edge_cabinet",
        status="Activate",
        provision_token="token-a-secret-12345",
    )
    device_b = Device(
        id=uuid.uuid4(),
        serial_number=f"SN-B-{uuid.uuid4().hex[:8]}",
        device_type="edge_cabinet",
        status="Activate",
        provision_token="token-b-secret-67890",
    )

    twin_a = DigitalTwin(id=uuid.uuid4(), asset_id=asset_a.id, device_id=device_a.id, twin_status="online")
    twin_b = DigitalTwin(id=uuid.uuid4(), asset_id=asset_b.id, device_id=device_b.id, twin_status="online")

    async with factory() as session:
        session.add(org_a)
        session.add(org_b)
        session.add(user_a)
        session.add(user_b)
        session.add(super_admin)
        session.add(project_a)
        session.add(project_b)
        session.add(asset_a)
        session.add(asset_b)
        session.add(device_a)
        session.add(device_b)
        session.add(twin_a)
        session.add(twin_b)
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:

        # 1. Tenant A lists fleet devices -> only sees device_a
        app.dependency_overrides[get_current_user] = lambda: user_a
        res_a = await client.get("/api/v1/hardware/devices")
        assert res_a.status_code == 200
        device_ids_a = [d["id"] for d in res_a.json()["devices"]]
        assert str(device_a.id) in device_ids_a
        assert str(device_b.id) not in device_ids_a

        # 2. Tenant B lists fleet devices -> only sees device_b
        app.dependency_overrides[get_current_user] = lambda: user_b
        res_b = await client.get("/api/v1/hardware/devices")
        assert res_b.status_code == 200
        device_ids_b = [d["id"] for d in res_b.json()["devices"]]
        assert str(device_b.id) in device_ids_b
        assert str(device_a.id) not in device_ids_b

        # 3. Super Admin lists fleet devices -> sees both
        app.dependency_overrides[get_current_user] = lambda: super_admin
        res_sa = await client.get("/api/v1/hardware/devices")
        assert res_sa.status_code == 200
        device_ids_sa = [d["id"] for d in res_sa.json()["devices"]]
        assert str(device_a.id) in device_ids_sa
        assert str(device_b.id) in device_ids_sa

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_hardware_websocket_authentication():
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    device_id = uuid.uuid4()
    device = Device(
        id=device_id,
        serial_number=f"SN-WS-{uuid.uuid4().hex[:8]}",
        device_type="edge_cabinet",
        status="Activate",
        provision_token="device-valid-secret-token-777",
    )

    inactive_device_id = uuid.uuid4()
    inactive_device = Device(
        id=inactive_device_id,
        serial_number=f"SN-INACTIVE-{uuid.uuid4().hex[:8]}",
        device_type="edge_cabinet",
        status="Inventory",
        provision_token="inactive-token-111",
    )

    async with factory() as session:
        session.add(device)
        session.add(inactive_device)
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    # 1. Unknown device -> closed with 4001
    unknown_id = str(uuid.uuid4())
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/hardware/ws/telemetry/{unknown_id}") as ws:
            ws.send_text(json.dumps({"provision_token": "random_token"}))
            _ = ws.receive_text()
    assert exc.value.code == 4001

    # 2. Missing token frame -> closed with 4001
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/hardware/ws/telemetry/{device_id}") as ws:
            ws.send_text(json.dumps({"invalid_field": "no_token"}))
            _ = ws.receive_text()
    assert exc.value.code == 4001

    # 3. Invalid token -> closed with 4003
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/hardware/ws/telemetry/{device_id}") as ws:
            ws.send_text(json.dumps({"provision_token": "wrong-token"}))
            _ = ws.receive_text()
    assert exc.value.code == 4003

    # 4. Inactive device -> closed with 4003
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/hardware/ws/telemetry/{inactive_device_id}") as ws:
            ws.send_text(json.dumps({"provision_token": "inactive-token-111"}))
            _ = ws.receive_text()
    assert exc.value.code == 4003

    # 5. Valid device + valid token -> authenticated, receives confirmation and can send telemetry
    with client.websocket_connect(f"/api/v1/hardware/ws/telemetry/{device_id}") as ws:
        ws.send_text(json.dumps({"provision_token": "device-valid-secret-token-777"}))
        auth_ack = json.loads(ws.receive_text())
        assert auth_ack["status"] == "authenticated"

        # Send telemetry frame
        telemetry_payload = {
            "message_id": str(uuid.uuid4()),
            "sequence_number": 1,
            "sensor_readings": {"voltage": 48.2, "temperature": 25.4},
        }
        ws.send_text(json.dumps(telemetry_payload))
        telemetry_ack = json.loads(ws.receive_text())
        assert telemetry_ack["status"] == "received"

    app.dependency_overrides.clear()
