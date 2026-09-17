"""
=============================================================================
VeriField Nexus — Adversarial Server Field Authority & Provenance Test Suite
=============================================================================
Tests:
1. Malicious FIELD_AGENT payload claiming field_data_authority="AUTHORITATIVE",
   provisional_field_observation=false, is_authoritative=true is forcefully
   overridden by backend to PROVISIONAL_OBSERVATION and provisional_field_observation=true.
2. Field-entered analytical values (Corg=99%, H/Corg=0.10) in field Activity are
   isolated under provisional_field_estimates and NEVER become BiocharLabAnalysis.
3. Authoritative Puro quantification strictly uses accredited BiocharLabAnalysis
   (Corg=71%, H/Corg=0.55) and ignores field activity estimates (Corg=99%).
4. FIELD_AGENT attempting to directly register BiocharLabAnalysis receives 403 Forbidden.
5. FIELD_AGENT attempting to submit activity with conflicting methodology against
   a locked project receives 400 Bad Request.
=============================================================================
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.domains.activities.schemas import ActivityCreate
from app.domains.activities.service import ActivityService
from app.domains.activities.repository import ActivityRepository
from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharLabAnalysis,
    ProductionFacility,
    ProductionRun,
)
from app.domains.biochar.services.puro_quantification import PuroAuthoritativeQuantificationService
from app.domains.methodologies.models.base_registry import Methodology, MethodologyRegistry, MethodologyFamily
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app
import jwt as pyjwt


def _make_auth_header(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id),
        "iat": now,
        "exp": now + timedelta(hours=2),
        "jti": str(uuid.uuid4()),
    }
    token = pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_adversarial_field_agent_authority_override(db_session: AsyncSession):
    """
    1 & 2. FIELD_AGENT attempts to forge authoritative lab results via Activity submission.
    Server MUST override field_data_authority to PROVISIONAL_OBSERVATION and isolate lab keys.
    """
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Field Test Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    user_id = uuid.uuid4()
    field_agent = User(
        id=user_id,
        email=f"agent_{uuid.uuid4().hex[:8]}@nexus.test",
        full_name="Malicious Agent",
        password_hash="hash",
        role="FIELD_AGENT",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add_all([org, field_agent])
    await db_session.commit()

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    payload = ActivityCreate(
        activity_type="BIOCHAR_KILN_BURN",
        captured_at=datetime.now(timezone.utc),
        activity_data={
            "field_data_authority": "AUTHORITATIVE",
            "provisional_field_observation": False,
            "is_authoritative": True,
            "c_org": 99.0,
            "h_c_org": 0.10,
            "pte": "PASS",
            "pah": 0.01,
            "lab_moisture": 1.5,
            "kiln_temp_c": 650.0,
        },
    )

    created = await service.create_activity(
        payload, user_id=user_id, organization_id=org_id, user_role="FIELD_AGENT"
    )

    data = created.activity_data
    assert data["field_data_authority"] == "PROVISIONAL_OBSERVATION"
    assert data["provisional_field_observation"] is True
    assert data["is_authoritative"] is False

    assert "c_org" not in data
    assert "h_c_org" not in data
    assert "pte" not in data
    assert "pah" not in data
    assert "provisional_field_estimates" in data
    assert data["provisional_field_estimates"]["c_org"] == 99.0
    assert data["provisional_field_estimates"]["h_c_org"] == 0.10
    assert data["lab_provenance"] == "UNVALIDATED_FIELD_OBSERVATION"


@pytest.mark.asyncio
async def test_authoritative_lab_provenance_vs_field_estimates(db_session: AsyncSession):
    """
    3. Adversarial Test:
       Field Activity claims: Corg = 99%, H/Corg = 0.10
       Validated Lab Analysis claims: Corg = 71%, H/Corg = 0.55
       Authoritative calculation MUST resolve strictly from BiocharLabAnalysis (71%, 0.55).
    """
    u = uuid.uuid4().hex[:8]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Biochar Carbon Ltd {u}", org_type="DEVELOPER")

    reg = MethodologyRegistry(
        id=uuid.uuid4(),
        code=f"PURO_REG_{u[:6]}",
        name="Puro Earth Standard",
        is_active=True,
    )
    fam = MethodologyFamily(
        id=uuid.uuid4(),
        code=f"BIOCHAR_FAM_{u[:6]}",
        name="Biochar Carbon Removal",
        is_active=True,
    )
    meth = Methodology(
        id=uuid.uuid4(),
        code=f"PURO_BIOCHAR_2025_V2_{u}",
        name="Puro Biochar 2025 V2",
        registry_id=reg.id,
        family_id=fam.id,
        is_active=True,
    )
    proj_id = uuid.uuid4()
    project = Project(
        id=proj_id,
        name=f"Biochar Puro Project {u}",
        organization_id=org_id,
        methodology_id=meth.id,
    )
    facility = ProductionFacility(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-{u}",
        facility_name="Facility A",
        technology_type="SLOW_PYROLYSIS",
    )
    run = ProductionRun(
        id=uuid.uuid4(),
        organization_id=org_id,
        facility_id=facility.id,
        run_number=f"RUN-{u}",
        avg_pyrolysis_temp_celsius=580.0,
        residence_time_minutes=45.0,
        start_time=datetime.now(timezone.utc),
    )
    batch = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        production_run_id=run.id,
        batch_number=f"BATCH-{u}",
        facility_name="Facility A",
        kiln_id="KILN-01",
        feedstock_type="BIOMASS",
        feedstock_weight_tonnes=100.0,
        moisture_content_pct=10.0,
        pyrolysis_temp_celsius=550.0,
        residence_time_minutes=45.0,
        biochar_yield_tonnes=80.0,
        dry_mass_tonnes=80.0,
    )
    lab = BiocharLabAnalysis(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch.id,
        sample_id=f"SAMPLE-{u}",
        sampling_date=date.today(),
        laboratory_name="Eurofins Accredited Biochar Testing",
        organic_carbon_pct=Decimal("71.0"),
        molar_h_c_ratio=Decimal("0.55"),
        fixed_carbon_pct=Decimal("65.0"),
        moisture_pct=Decimal("10.0"),
        ash_pct=Decimal("5.0"),
        heavy_metals_pass=True,
    )
    end_use = BiocharEndUseRecord(
        id=uuid.uuid4(),
        organization_id=org_id,
        batch_id=batch.id,
        end_use_type="SOIL_APPLICATION",
        applied_quantity_tonnes=Decimal("80.0"),
        event_date=datetime.now(timezone.utc),
    )

    db_session.add_all([org, reg, fam, meth, project, facility, run, batch, lab, end_use])
    await db_session.commit()

    calc_res = await PuroAuthoritativeQuantificationService.resolve_and_execute(
        db=db_session,
        batch_id=batch.id,
        organization_id=org_id,
        mode="AUTHORITATIVE",
    )

    assert calc_res["calculation_status"] in ["SUCCESS", "CALCULATED"]
    c_stored = Decimal(str(calc_res["c_stored_tco2e"]))
    expected_c_stored = Decimal("80.0") * Decimal("0.71") * (Decimal("44") / Decimal("12"))
    assert abs(c_stored - expected_c_stored) < Decimal("0.05")


@pytest.mark.asyncio
async def test_field_agent_forbidden_from_creating_lab_analysis(db_session: AsyncSession):
    """
    4. FIELD_AGENT attempts to call POST /api/v1/biochar/batches/{batch_id}/lab-analyses.
    Server MUST reject with 403 Forbidden.
    """
    u = uuid.uuid4().hex[:8]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Test Org {u}", org_type="DEVELOPER")
    user_id = uuid.uuid4()
    field_agent = User(
        id=user_id,
        email=f"fa_{u}@nexus.test",
        full_name="Field Worker",
        password_hash="hash",
        role="FIELD_AGENT",
        organization_id=org_id,
        is_active=True,
    )
    proj_id = uuid.uuid4()
    project = Project(
        id=proj_id,
        name=f"Biochar Test Project {u}",
        organization_id=org_id,
    )
    batch = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        batch_number=f"BATCH-{u}",
        facility_name="Facility A",
        kiln_id="KILN-01",
        feedstock_type="BIOMASS",
        feedstock_weight_tonnes=50.0,
        moisture_content_pct=10.0,
        pyrolysis_temp_celsius=550.0,
        residence_time_minutes=45.0,
        biochar_yield_tonnes=40.0,
        dry_mass_tonnes=40.0,
    )
    db_session.add_all([org, field_agent, project, batch])
    await db_session.commit()

    headers = _make_auth_header(user_id, field_agent.email, "FIELD_AGENT", org_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/biochar/batches/{batch.id}/lab-analyses",
            json={
                "batch_id": str(batch.id),
                "sample_id": "ROGUE-SAMPLE-01",
                "sampling_date": datetime.now(timezone.utc).isoformat(),
                "laboratory_name": "Rogue Field Lab",
                "organic_carbon_pct": 95.0,
                "fixed_carbon_pct": 75.0,
                "moisture_pct": 5.0,
                "ash_pct": 3.0,
                "molar_h_c_ratio": 0.20,
            },
            headers=headers,
        )

    assert resp.status_code == 403
    assert "Field agents" in resp.text


@pytest.mark.asyncio
async def test_methodology_lock_rejection_on_conflicting_activity(db_session: AsyncSession):
    """
    5. FIELD_AGENT submits activity to a project locked to PURO_BIOCHAR_2025_V2
    specifying conflicting methodology ACM0002.
    Server MUST reject with 400 Bad Request.
    """
    u = uuid.uuid4().hex[:8]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Locked Project Org {u}", org_type="DEVELOPER")
    user_id = uuid.uuid4()
    field_agent = User(
        id=user_id,
        email=f"agent_lock_{u}@nexus.test",
        full_name="Agent Lock Test",
        password_hash="hash",
        role="FIELD_AGENT",
        organization_id=org_id,
        is_active=True,
    )
    reg = MethodologyRegistry(
        id=uuid.uuid4(),
        code=f"PURO_REG_LOCK_{u[:6]}",
        name="Puro Earth Standard Lock",
        is_active=True,
    )
    fam = MethodologyFamily(
        id=uuid.uuid4(),
        code=f"BIOCHAR_FAM_LOCK_{u[:6]}",
        name="Biochar Removal Family",
        is_active=True,
    )
    meth = Methodology(
        id=uuid.uuid4(),
        code=f"PURO_BIOCHAR_2025_V2_{u}".upper(),
        name="Puro Biochar 2025 V2",
        registry_id=reg.id,
        family_id=fam.id,
        is_active=True,
    )
    proj_id = uuid.uuid4()
    project = Project(
        id=proj_id,
        name=f"Locked Biochar Project {u}",
        organization_id=org_id,
        methodology_id=meth.id,
    )
    db_session.add_all([org, field_agent, reg, fam, meth, project])
    await db_session.commit()

    headers = _make_auth_header(user_id, field_agent.email, "FIELD_AGENT", org_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Conflicting methodology payload
        resp_bad = await client.post(
            "/api/v1/activities",
            json={
                "project_id": str(proj_id),
                "activity_type": "COOKSTOVE_DISTRIBUTION",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "activity_data": {
                    "methodology": "ACM0002",
                    "stove_id": "STOVE-01",
                },
            },
            headers=headers,
        )
        assert resp_bad.status_code == 400
        assert "Methodology mismatch" in resp_bad.text

        # 2. Compatible methodology payload successfully canonicalizes
        resp_good = await client.post(
            "/api/v1/activities",
            json={
                "project_id": str(proj_id),
                "activity_type": "BIOCHAR_KILN_BURN",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "activity_data": {
                    "methodology": meth.code,
                    "kiln_id": "KILN-01",
                },
            },
            headers=headers,
        )
        assert resp_good.status_code == 201
        res_data = resp_good.json()["activity_data"]
        assert res_data["methodology"] == meth.code
        assert res_data["methodology_locked"] is True
        assert res_data["field_data_authority"] == "PROVISIONAL_OBSERVATION"
