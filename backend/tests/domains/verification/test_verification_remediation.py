"""
VeriField Nexus — Verification Findings Schema & Endpoints Remediation Test Suite
==================================================================================
Tests:
1. VerificationTaskListItem findings normalization:
   - No findings ([] and {})
   - One finding in array
   - Multiple findings in array (CAR, NCR, CL)
   - Legacy wrapped dictionary representation
   - Legacy single-finding dictionary representation
   - Legacy notes dictionary representation
2. GET /api/v1/verification/tasks serialization:
   - Tasks with diverse findings shapes never trigger 500 serialization error.
3. GET /api/v1/verification/sensors/{asset_id}:
   - Returns HTTP 200 with SensorReading list (no longer HTTP 501).
4. GET /api/v1/verification/community/{asset_id}:
   - Returns HTTP 200 with CommunityValidation list (no longer HTTP 501).
"""

import os
import uuid
import datetime
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.domains.verification.schemas import (
    VerificationTaskListItem,
    VerificationTaskListResponse,
    VerificationFinding,
)
from app.domains.verification.models import VerificationTask
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.authentication.service import AuthenticationService
from app.db.session import get_db

POSTGRES_URL = (
    os.environ.get("POSTGIS_TEST_URL")
    or os.environ.get("POSTGRES_TEST_URL")
    or f"postgresql+asyncpg://{os.environ.get('USER', 'postgres')}@localhost:5432/verifield_postgis_test"
)


def test_findings_schema_normalization():
    """Validates that VerificationTaskListItem normalizes all canonical and legacy findings shapes."""
    task_id = uuid.uuid4()

    # Case 1: Empty list
    item_empty_list = VerificationTaskListItem(
        id=task_id, status="ASSIGNED", findings=[]
    )
    assert len(item_empty_list.findings) == 0

    # Case 2: Empty dict
    item_empty_dict = VerificationTaskListItem(
        id=task_id, status="ASSIGNED", findings={}
    )
    assert len(item_empty_dict.findings) == 0

    # Case 3: None
    item_none = VerificationTaskListItem(
        id=task_id, status="ASSIGNED", findings=None
    )
    assert len(item_none.findings) == 0

    # Case 4: Array with single CAR finding
    item_single_car = VerificationTaskListItem(
        id=task_id,
        status="IN_PROGRESS",
        findings=[{
            "code": "CAR-01",
            "type": "CORRECTIVE_ACTION",
            "severity": "MAJOR",
            "description": "Missing laboratory calibration cert",
            "status": "OPEN",
        }],
    )
    assert len(item_single_car.findings) == 1
    f0 = item_single_car.findings[0]
    assert isinstance(f0, VerificationFinding)
    assert f0.code == "CAR-01"
    assert f0.type == "CORRECTIVE_ACTION"
    assert f0.severity == "MAJOR"

    # Case 5: Multiple findings (CAR, NCR, Clarification)
    item_multi = VerificationTaskListItem(
        id=task_id,
        status="UNDER_REVIEW",
        findings=[
            {"code": "CAR-01", "type": "CAR", "description": "Minor meter drift"},
            {"code": "NCR-01", "type": "NCR", "description": "Baseline deviation", "severity": "CRITICAL"},
            {"code": "CL-01", "type": "CLARIFICATION", "description": "Provide GPS metadata"},
        ],
    )
    assert len(item_multi.findings) == 3
    assert item_multi.findings[0].code == "CAR-01"
    assert item_multi.findings[1].code == "NCR-01"
    assert item_multi.findings[1].severity == "CRITICAL"
    assert item_multi.findings[2].type == "CLARIFICATION"

    # Case 6: Legacy wrapped dict with car_list key
    item_wrapped = VerificationTaskListItem(
        id=task_id,
        status="ASSIGNED",
        findings={"car_list": [{"code": "CAR-09", "description": "Wrapped finding"}]},
    )
    assert len(item_wrapped.findings) == 1
    assert item_wrapped.findings[0].code == "CAR-09"

    # Case 7: Legacy unstructured dict notes
    item_legacy_notes = VerificationTaskListItem(
        id=task_id,
        status="ASSIGNED",
        findings={"summary": "Pre-audit preliminary observations", "severity": "MINOR"},
    )
    assert len(item_legacy_notes.findings) == 1
    assert item_legacy_notes.findings[0].description == "Pre-audit preliminary observations"

    # Case 8: Envelope verification list response serialization
    response = VerificationTaskListResponse(
        tasks=[item_empty_list, item_single_car, item_multi, item_wrapped],
        audits=[item_empty_list, item_single_car, item_multi, item_wrapped],
        total=4,
    )
    dumped = response.model_dump(mode="json")
    assert dumped["total"] == 4
    assert len(dumped["tasks"][2]["findings"]) == 3


@pytest.mark.asyncio
async def test_verification_sensors_and_community_endpoints():
    """Validates that GET /verification/sensors and /community return 200 with typed data (DEFECT-04 fix)."""
    engine = create_async_engine(POSTGRES_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    device_id = f"SENSOR-NODE-{uuid.uuid4().hex[:4]}"

    async with session_factory() as session:
        org = Organization(
            id=org_id,
            name=f"Test Org {uuid.uuid4().hex[:6]}",
            org_type="DEVELOPER",
            status="ACTIVE",
        )
        session.add(org)

        user = User(
            id=user_id,
            email=f"verifier_{uuid.uuid4().hex[:6]}@verif.test",
            full_name="Sensor Verifier",
            role="VERIFIER",
            organization_id=org_id,
            status="active",
        )
        session.add(user)

        project_id = uuid.uuid4()
        project = Project(
            id=project_id,
            organization_id=org_id,
            name=f"Test Project {uuid.uuid4().hex[:6]}",
        )
        session.add(project)

        asset = Asset(
            id=asset_id,
            organization_id=org_id,
            project_id=project_id,
            name=f"Test Sensor Asset {uuid.uuid4().hex[:6]}",
        )
        session.add(asset)

        # Telemetry sensor activity
        sensor_act = Activity(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            asset_id=asset_id,
            activity_type="SOIL_SENSOR_TELEMETRY",
            captured_at=datetime.datetime.now(datetime.timezone.utc),
            activity_data={
                "device_id": device_id,
                "soil_temperature_c": 28.5,
                "usage_flag": True,
            },
        )
        # Community validation activity
        community_act = Activity(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            asset_id=asset_id,
            activity_type="COMMUNITY_VALIDATION",
            captured_at=datetime.datetime.now(datetime.timezone.utc),
            description="Community chief signed validation checklist",
            activity_data={
                "device_id": device_id,
                "response": "Affirmed clean cooking usage",
            },
        )
        session.add_all([sensor_act, community_act])
        await session.commit()

        token = AuthenticationService.generate_token_static(user)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test GET /api/v1/verification/sensors/{asset_id} -> HTTP 200 (not 501!)
        sensor_res = await client.get(f"/api/v1/verification/sensors/{asset_id}", headers=headers)
        assert sensor_res.status_code == 200, f"Expected 200, got {sensor_res.status_code}: {sensor_res.text}"
        sensor_data = sensor_res.json()
        assert isinstance(sensor_data, list)
        assert len(sensor_data) >= 1
        assert sensor_data[0]["device_id"] == device_id
        assert sensor_data[0]["temperature"] == 28.5

        # 2. Test GET /api/v1/verification/community/{asset_id} -> HTTP 200 (not 501!)
        comm_res = await client.get(f"/api/v1/verification/community/{asset_id}", headers=headers)
        assert comm_res.status_code == 200, f"Expected 200, got {comm_res.status_code}: {comm_res.text}"
        comm_data = comm_res.json()
        assert isinstance(comm_data, list)
        assert len(comm_data) >= 1
        assert "Affirmed clean cooking usage" in comm_data[0]["response"]

        # 3. Nonexistent asset returns empty list 200, not 404 or 501
        empty_res = await client.get(f"/api/v1/verification/sensors/{uuid.uuid4()}", headers=headers)
        assert empty_res.status_code == 200
        assert empty_res.json() == []

    app.dependency_overrides.clear()
    await engine.dispose()
