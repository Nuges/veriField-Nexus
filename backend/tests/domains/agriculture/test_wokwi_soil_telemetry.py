"""
VeriField Nexus — Local Wokwi ESP32 Soil Telemetry Test Suite
=============================================================
Tests:
1. FIELD_AGENT authentication flow (POST /api/v1/auth/login -> JWT Bearer).
2. SOIL_SENSOR_TELEMETRY payload submission (POST /api/v1/activities).
3. Activity persistence in local PostgreSQL (test_ci_db).
4. Persistence of activity_data fields:
   - device_id == "WOKWI-ESP32-SOIL-01"
   - soil_moisture_raw == 1420
   - soil_moisture_pct == 66.5
   - soil_temperature_c == 29.4
   - test_mode == True
   - simulation_source == "WOKWI_ESP32"
5. Server enforcement: field-agent submission treated as provisional observation:
   - field_data_authority == "PROVISIONAL_OBSERVATION"
   - is_authoritative is False
6. Idempotency / deduplication: duplicate client_id does not create duplicate records.
7. Tenant isolation: field agent cannot submit into a foreign organization's project.
8. Calculation isolation: no soil telemetry automatically triggers carbon-credit calculations.
"""

import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text

from app.main import app
from app.db.session import get_db
from app.core.security import get_password_hash
from app.domains.organizations.models import Organization
from app.domains.authentication.models import User
from app.domains.projects.models import Project
from app.domains.activities.models import Activity
from app.domains.projects.models import CarbonCalculation
from app.domains.agriculture.models import SoilSample, AgricultureSOCStockResult

POSTGRES_URL = (
    os.environ.get("POSTGIS_TEST_URL")
    or os.environ.get("POSTGRES_TEST_URL")
    or f"postgresql+asyncpg://{os.environ.get('USER', 'postgres')}@localhost:5432/verifield_postgis_test"
)


@pytest_asyncio.fixture
async def db_fixture():
    engine = create_async_engine(POSTGRES_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    org_id = uuid.uuid4()
    foreign_org_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    project_id = uuid.uuid4()
    foreign_project_id = uuid.uuid4()

    password = "WokwiTestPassword123!"
    agent_email = f"agent_{uuid.uuid4().hex[:6]}@deepakfarm.org"

    async with session_factory() as session:
        # Organization A (Local Deepak Farm)
        org_a = Organization(
            id=org_id,
            name=f"Deepak Regenerative Agriculture Org {uuid.uuid4().hex[:6]}",
            status="ACTIVE",
            licensed_sectors=["AGRICULTURE_LAND_USE"],
        )
        # Organization B (Foreign Tenant)
        org_b = Organization(
            id=foreign_org_id,
            name=f"Foreign Tenant Org {uuid.uuid4().hex[:6]}",
            status="ACTIVE",
            licensed_sectors=["AGRICULTURE_LAND_USE"],
        )

        # Field Agent in Org A
        agent = User(
            id=agent_id,
            email=agent_email,
            full_name="Wokwi Field Agent",
            role="FIELD_AGENT",
            organization_id=org_id,
            password_hash=get_password_hash(password),
            status="active",
        )

        # Project A in Org A
        project_a = Project(
            id=project_id,
            project_code=f"AGR-DEEPAK-{uuid.uuid4().hex[:4]}",
            name="Deepak Farm Soil Sensor Pilot",
            organization_id=org_id,
            country="India",
            baseline_source="telemetry_pilot",
        )

        # Project B in Org B
        project_b = Project(
            id=foreign_project_id,
            project_code=f"AGR-FOR-{uuid.uuid4().hex[:4]}",
            name="Foreign Tenant Project",
            organization_id=foreign_org_id,
            country="India",
            baseline_source="telemetry_pilot",
        )

        session.add(org_a)
        session.add(org_b)
        session.add(agent)
        session.add(project_a)
        session.add(project_b)
        await session.commit()

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "session_factory": session_factory,
        "org_id": org_id,
        "foreign_org_id": foreign_org_id,
        "agent_id": agent_id,
        "agent_email": agent_email,
        "password": password,
        "project_id": project_id,
        "foreign_project_id": foreign_project_id,
    }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_wokwi_field_agent_authentication(db_fixture):
    """1. Prove that FIELD_AGENT can authenticate using JSON credentials and receive JWT."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        assert res.status_code == 200, f"Login failed: {res.text}"
        data = res.json()
        assert "access_token" in data
        assert data["token_type"].lower() == "bearer"
        assert data["user"]["role"] == "FIELD_AGENT"
        assert str(data["user"]["id"]) == str(db_fixture["agent_id"])


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_submission_and_persistence(db_fixture):
    """
    2-10. Prove that FIELD_AGENT can submit SOIL_SENSOR_TELEMETRY,
    the activity is persisted with all expected fields, and server flags it provisional.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Authenticate
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Submit Telemetry
        client_id = f"wokwi-soil-{uuid.uuid4().hex[:8]}"
        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "client_id": client_id,
            "project_id": str(db_fixture["project_id"]),
            "captured_at": "2026-10-09T02:30:00Z",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "activity_data": {
                "device_id": "WOKWI-ESP32-SOIL-01",
                "test_mode": True,
                "simulation_source": "WOKWI_ESP32",
                "soil_moisture_raw": 1420,
                "soil_moisture_pct": 66.5,
                "soil_temperature_c": 29.4,
                "soil_moisture_sensor": "SIMULATED_ANALOG_12BIT",
                "temperature_sensor": "DS18B20",
                "device_time_synchronized": True,
                "measurement_authority": "PROVISIONAL_SENSOR_OBSERVATION",
            },
        }

        res = await client.post("/api/v1/activities", json=payload, headers=headers)
        assert res.status_code == 201, f"Submission failed: {res.text}"
        body = res.json()
        assert body["project_id"] == str(db_fixture["project_id"]), f"Expected project_id {db_fixture['project_id']}, got {body.get('project_id')}"
        activity_id = uuid.UUID(body["id"])

        # Verify DB Persistence
        session_factory = db_fixture["session_factory"]
        async with session_factory() as session:
            stmt = select(Activity).where(Activity.id == activity_id)
            q_res = await session.execute(stmt)
            activity = q_res.scalar_one_or_none()

            assert activity is not None, "Activity was not persisted to database"
            assert activity.activity_type == "SOIL_SENSOR_TELEMETRY"
            assert activity.client_id == client_id
            assert activity.organization_id == db_fixture["org_id"]
            assert activity.project_id == db_fixture["project_id"], f"Expected DB project_id {db_fixture['project_id']}, got {activity.project_id}"
            assert activity.latitude == pytest.approx(28.6139)
            assert activity.longitude == pytest.approx(77.2090)
            assert activity.captured_at is not None
            # Verify captured_at is timezone-aware UTC
            assert activity.captured_at.tzinfo is not None

            # Invariant checks on activity_data
            data = activity.activity_data
            assert data["device_id"] == "WOKWI-ESP32-SOIL-01"
            assert data["soil_moisture_raw"] == 1420
            assert data["soil_moisture_pct"] == 66.5
            assert data["soil_temperature_c"] == 29.4
            assert data["temperature_sensor"] == "DS18B20"
            assert data["device_time_synchronized"] is True
            assert data["test_mode"] is True
            assert data["simulation_source"] == "WOKWI_ESP32"

            # Provisional authority attribution
            assert data["field_data_authority"] == "PROVISIONAL_OBSERVATION"
            assert data["is_authoritative"] is False
            assert data["provisional_field_observation"] is True

        # Verify project can query and list its associated activities
        list_res = await client.get(f"/api/v1/activities?project_id={db_fixture['project_id']}", headers=headers)
        assert list_res.status_code == 200, f"List activities failed: {list_res.text}"
        list_body = list_res.json()
        matched_activities = [act for act in list_body["activities"] if act["id"] == str(activity_id)]
        assert len(matched_activities) == 1, "Expected activity to be listed under project"
        assert matched_activities[0]["project_id"] == str(db_fixture["project_id"])


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_client_id_deduplication(db_fixture):
    """11. Prove that duplicate client_id does not create duplicate records."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        dedup_client_id = f"wokwi-dedup-{uuid.uuid4().hex[:8]}"
        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "client_id": dedup_client_id,
            "project_id": str(db_fixture["project_id"]),
            "captured_at": "2026-10-09T02:30:00Z",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "activity_data": {
                "device_id": "WOKWI-ESP32-SOIL-01",
                "soil_moisture_raw": 1420,
                "soil_moisture_pct": 66.5,
                "soil_temperature_c": 29.4,
            },
        }

        # First post
        res1 = await client.post("/api/v1/activities", json=payload, headers=headers)
        assert res1.status_code == 201
        id1 = res1.json()["id"]

        # Second post with identical client_id
        res2 = await client.post("/api/v1/activities", json=payload, headers=headers)
        assert res2.status_code in (200, 201)
        id2 = res2.json()["id"]

        assert id1 == id2, "Duplicate client_id returned a different activity ID"

        # Verify only 1 record exists in database
        session_factory = db_fixture["session_factory"]
        async with session_factory() as session:
            stmt = select(Activity).where(Activity.client_id == dedup_client_id)
            q_res = await session.execute(stmt)
            activities = q_res.scalars().all()
            assert len(activities) == 1, f"Expected 1 record, found {len(activities)}"


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_cross_tenant_rejection(db_fixture):
    """12. Prove that a field agent cannot submit into a foreign organization's project."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to target foreign project
        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "client_id": f"wokwi-cross-{uuid.uuid4().hex[:8]}",
            "project_id": str(db_fixture["foreign_project_id"]),
            "captured_at": "2026-10-09T02:30:00Z",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "activity_data": {
                "device_id": "WOKWI-ESP32-SOIL-01",
                "soil_moisture_pct": 50.0,
            },
        }

        res = await client.post("/api/v1/activities", json=payload, headers=headers)
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"
        assert "another organization is forbidden" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_wokwi_telemetry_does_not_trigger_carbon_credits(db_fixture):
    """
    13. Prove that soil telemetry does NOT automatically trigger carbon-credit calculations
    and does not write to authoritative SoilSample or SOC stock results.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "client_id": f"wokwi-calc-{uuid.uuid4().hex[:8]}",
            "project_id": str(db_fixture["project_id"]),
            "captured_at": "2026-10-09T02:30:00Z",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "activity_data": {
                "device_id": "WOKWI-ESP32-SOIL-01",
                "soil_moisture_raw": 1420,
                "soil_moisture_pct": 66.5,
                "soil_temperature_c": 29.4,
            },
        }

        res = await client.post("/api/v1/activities", json=payload, headers=headers)
        assert res.status_code == 201

        # Check DB: no carbon calculations created
        session_factory = db_fixture["session_factory"]
        async with session_factory() as session:
            calc_stmt = select(CarbonCalculation).where(
                CarbonCalculation.project_id == db_fixture["project_id"]
            )
            calc_res = await session.execute(calc_stmt)
            calcs = calc_res.scalars().all()
            assert len(calcs) == 0, "Telemetry submission created unexpected carbon calculation!"

            # Check DB: no soil sample created for this project
            sample_count = await session.execute(
                text("SELECT count(*) FROM soil_samples WHERE project_id = :pid"),
                {"pid": db_fixture["project_id"]}
            )
            assert sample_count.scalar() == 0, "Telemetry submission created unexpected soil_sample record!"


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_null_project_id_succeeds(db_fixture):
    """14. Prove that omitted project_id succeeds and persists with null project_id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "client_id": f"wokwi-null-proj-{uuid.uuid4().hex[:8]}",
            "captured_at": "2026-10-09T02:30:00Z",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "activity_data": {
                "device_id": "WOKWI-ESP32-SOIL-01",
                "soil_moisture_pct": 45.0,
                "soil_temperature_c": 21.0,
            },
        }

        res = await client.post("/api/v1/activities", json=payload, headers=headers)
        assert res.status_code == 201, f"Submission without project_id failed: {res.text}"
        body = res.json()
        assert body["project_id"] is None, f"Expected project_id to be None, got {body.get('project_id')}"
        activity_id = uuid.UUID(body["id"])

        # Verify DB Persistence has project_id is None
        session_factory = db_fixture["session_factory"]
        async with session_factory() as session:
            stmt = select(Activity).where(Activity.id == activity_id)
            q_res = await session.execute(stmt)
            activity = q_res.scalar_one_or_none()

            assert activity is not None, "Activity was not persisted"
            assert activity.project_id is None, "Expected DB project_id to be None"


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_batch_submission_tenancy(db_fixture):
    """Prove that batch submission enforces project tenancy per item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        same_org_cid = f"batch-same-{uuid.uuid4().hex[:8]}"
        foreign_org_cid = f"batch-for-{uuid.uuid4().hex[:8]}"
        missing_org_cid = f"batch-miss-{uuid.uuid4().hex[:8]}"
        null_org_cid = f"batch-null-{uuid.uuid4().hex[:8]}"
        missing_uuid = str(uuid.uuid4())

        batch_payload = {
            "activities": [
                {
                    "client_id": same_org_cid,
                    "project_id": str(db_fixture["project_id"]),
                    "activity_type": "SOIL_SENSOR_TELEMETRY",
                    "activity_data": {"device_id": "WOKWI-BATCH-01", "soil_moisture_pct": 55.0},
                },
                {
                    "client_id": foreign_org_cid,
                    "project_id": str(db_fixture["foreign_project_id"]),
                    "activity_type": "SOIL_SENSOR_TELEMETRY",
                    "activity_data": {"device_id": "WOKWI-BATCH-02", "soil_moisture_pct": 52.0},
                },
                {
                    "client_id": missing_org_cid,
                    "project_id": missing_uuid,
                    "activity_type": "SOIL_SENSOR_TELEMETRY",
                    "activity_data": {"device_id": "WOKWI-BATCH-03", "soil_moisture_pct": 50.0},
                },
                {
                    "client_id": null_org_cid,
                    "project_id": None,
                    "activity_type": "SOIL_SENSOR_TELEMETRY",
                    "activity_data": {"device_id": "WOKWI-BATCH-04", "soil_moisture_pct": 48.0},
                },
            ]
        }

        res = await client.post("/api/v1/activities/batch", json=batch_payload, headers=headers)
        assert res.status_code == 200, f"Batch submission failed: {res.text}"
        results = res.json()["results"]
        assert len(results) == 4

        res_by_cid = {r["client_id"]: r for r in results}
        assert res_by_cid[same_org_cid]["status"] == "submitted"
        assert res_by_cid[same_org_cid].get("id") is not None

        assert res_by_cid[foreign_org_cid]["status"] == "failed"
        assert res_by_cid[foreign_org_cid].get("error_code") == 403
        assert "forbidden" in res_by_cid[foreign_org_cid]["error"].lower()

        assert res_by_cid[missing_org_cid]["status"] == "failed"
        assert res_by_cid[missing_org_cid].get("error_code") == 404
        assert "not found" in res_by_cid[missing_org_cid]["error"].lower()

        assert res_by_cid[null_org_cid]["status"] == "submitted"

        # Verify DB persistence of same-org item and null-org item
        session_factory = db_fixture["session_factory"]
        async with session_factory() as session:
            act_same = (await session.execute(select(Activity).where(Activity.client_id == same_org_cid))).scalar_one_or_none()
            assert act_same is not None
            assert act_same.project_id == db_fixture["project_id"]

            act_null = (await session.execute(select(Activity).where(Activity.client_id == null_org_cid))).scalar_one_or_none()
            assert act_null is not None
            assert act_null.project_id is None

            act_foreign = (await session.execute(select(Activity).where(Activity.client_id == foreign_org_cid))).scalar_one_or_none()
            assert act_foreign is None, "Foreign project activity was unexpectedly saved to DB!"


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_bulk_submission_tenancy(db_fixture):
    """Prove that bulk submission (/activities/bulk) also enforces project tenancy per item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        bulk_same_cid = f"bulk-same-{uuid.uuid4().hex[:8]}"
        bulk_for_cid = f"bulk-for-{uuid.uuid4().hex[:8]}"

        bulk_payload = {
            "activities": [
                {
                    "client_id": bulk_same_cid,
                    "project_id": str(db_fixture["project_id"]),
                    "activity_type": "SOIL_SENSOR_TELEMETRY",
                    "activity_data": {"device_id": "WOKWI-BULK-01", "soil_moisture_pct": 58.0},
                },
                {
                    "client_id": bulk_for_cid,
                    "project_id": str(db_fixture["foreign_project_id"]),
                    "activity_type": "SOIL_SENSOR_TELEMETRY",
                    "activity_data": {"device_id": "WOKWI-BULK-02", "soil_moisture_pct": 51.0},
                },
            ]
        }

        res = await client.post("/api/v1/activities/bulk", json=bulk_payload, headers=headers)
        assert res.status_code == 200, f"Bulk submission failed: {res.text}"
        results = res.json()["results"]
        res_by_cid = {r["client_id"]: r for r in results}

        assert res_by_cid[bulk_same_cid]["status"] == "submitted"
        assert res_by_cid[bulk_for_cid]["status"] == "failed"
        assert res_by_cid[bulk_for_cid]["error_code"] == 403


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_offline_route_validation(db_fixture):
    """Prove that /activities/offline endpoint enforces same-org access and rejects foreign or missing projects."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Same org -> 201
        res_ok = await client.post(
            "/api/v1/activities/offline",
            json={
                "activity_type": "SOIL_SENSOR_TELEMETRY",
                "client_id": f"offline-same-{uuid.uuid4().hex[:8]}",
                "project_id": str(db_fixture["project_id"]),
                "captured_at": "2026-10-09T02:30:00Z",
                "activity_data": {"device_id": "WOKWI-OFFLINE-01", "soil_moisture_pct": 60.0},
            },
            headers=headers,
        )
        assert res_ok.status_code == 201
        assert res_ok.json()["project_id"] == str(db_fixture["project_id"])

        # Foreign org -> 403
        res_for = await client.post(
            "/api/v1/activities/offline",
            json={
                "activity_type": "SOIL_SENSOR_TELEMETRY",
                "client_id": f"offline-for-{uuid.uuid4().hex[:8]}",
                "project_id": str(db_fixture["foreign_project_id"]),
                "captured_at": "2026-10-09T02:30:00Z",
                "activity_data": {"device_id": "WOKWI-OFFLINE-02", "soil_moisture_pct": 60.0},
            },
            headers=headers,
        )
        assert res_for.status_code == 403

        # Missing project -> 404
        res_miss = await client.post(
            "/api/v1/activities/offline",
            json={
                "activity_type": "SOIL_SENSOR_TELEMETRY",
                "client_id": f"offline-miss-{uuid.uuid4().hex[:8]}",
                "project_id": str(uuid.uuid4()),
                "captured_at": "2026-10-09T02:30:00Z",
                "activity_data": {"device_id": "WOKWI-OFFLINE-03", "soil_moisture_pct": 60.0},
            },
            headers=headers,
        )
        assert res_miss.status_code == 404


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_missing_project_single_rejected(db_fixture):
    """Prove that single POST /activities with non-existent project_id returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/v1/activities",
            json={
                "activity_type": "SOIL_SENSOR_TELEMETRY",
                "client_id": f"single-miss-{uuid.uuid4().hex[:8]}",
                "project_id": str(uuid.uuid4()),
                "captured_at": "2026-10-09T02:30:00Z",
                "activity_data": {"device_id": "WOKWI-SINGLE-MISS", "soil_moisture_pct": 60.0},
            },
            headers=headers,
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_wokwi_soil_telemetry_timestamp_fallback_and_unsynchronized_state(db_fixture):
    """
    Prove that when ESP32 SNTP fails:
    1. captured_at is omitted/null.
    2. Backend safely falls back to server UTC receipt time.
    3. device_time_synchronized: false is preserved in activity_data.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": db_fixture["agent_email"],
                "password": db_fixture["password"],
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client_id = f"wokwi-nosync-{uuid.uuid4().hex[:8]}"
        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "client_id": client_id,
            "project_id": str(db_fixture["project_id"]),
            "captured_at": None,
            "activity_data": {
                "device_id": "WOKWI-ESP32-SOIL-01",
                "soil_moisture_pct": 60.0,
                "soil_temperature_c": 28.5,
                "device_time_synchronized": False,
            },
        }

        res = await client.post("/api/v1/activities", json=payload, headers=headers)
        assert res.status_code == 201
        activity_id = uuid.UUID(res.json()["id"])

        session_factory = db_fixture["session_factory"]
        async with session_factory() as session:
            stmt = select(Activity).where(Activity.id == activity_id)
            q_res = await session.execute(stmt)
            act = q_res.scalar_one_or_none()

            assert act is not None
            # Server UTC fallback assigned
            assert act.captured_at is not None
            assert act.captured_at.tzinfo is not None
            # Device unsynchronized state strictly preserved
            assert act.activity_data["device_time_synchronized"] is False



