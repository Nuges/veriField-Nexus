"""
=============================================================================
VeriField Nexus — Agriculture MRV Phase 1: Operational Workflow Tests
=============================================================================
Comprehensive unit, integration, and API tests for:
1. Project Foundation Configuration & Methodology Lock
2. Authoritative Spatial Boundary Linking (PostGIS / WGS84 Geodesic)
3. Land Management Unit Structure & Hierarchies
4. Stratum & StratumMembership Lifecycle & Area Aggregation
5. Management Baseline & Historical Practice Records Tracking
6. Deterministic Foundation Readiness Evaluator (Categorical Invariants)
7. Multi-Tenant ABAC Isolation
=============================================================================
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.main import app
from app.domains.agriculture.models import (
    AgricultureManagementRecord,
    LandUnit,
    Stratum,
    StratumMembership,
)
from app.domains.agriculture.schemas import (
    LandUnitCreate,
    LinkBoundaryRequest,
    ManagementRecordCreate,
    ManagementRecordUpdate,
    StratumCreate,
    StratumMembershipItem,
    StratumUpdate,
)
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.agriculture.service import AgricultureService
from app.domains.authentication.models import User
from app.domains.earth_observation.models import ProjectBoundaryVersion
from app.domains.methodologies.models.base_registry import (
    Methodology,
    MethodologyFamily,
    MethodologyVersion,
)
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


# Test Polygon Geometry (WGS84 approx 433 ha)
VALID_POLYGON_A = {
    "type": "Polygon",
    "coordinates": [
        [[77.10, 28.50], [77.12, 28.50], [77.12, 28.52], [77.10, 28.52], [77.10, 28.50]]
    ],
}

VALID_POLYGON_B = {
    "type": "Polygon",
    "coordinates": [
        [[77.10, 28.50], [77.11, 28.50], [77.11, 28.51], [77.10, 28.51], [77.10, 28.50]]
    ],
}

VALID_POLYGON_C = {
    "type": "Polygon",
    "coordinates": [
        [[77.11, 28.50], [77.12, 28.50], [77.12, 28.51], [77.11, 28.51], [77.11, 28.50]]
    ],
}


async def create_agri_setup(db_session: AsyncSession):
    """Sets up an organization, methodology catalogue, and test user."""
    await seed_agriculture_methodologies(db_session)

    org = Organization(name=f"AgriTech Operations {uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        email=f"agri.lead.{uuid.uuid4().hex[:6]}@verifield.test",
        full_name="Agriculture MRV Lead",
        role="ORG_ADMIN",
        organization_id=org.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    fam_res = await db_session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE"))
    agri_family = fam_res.scalars().first()

    m42_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0042"))
    vm0042 = m42_res.scalars().first()

    v22_res = await db_session.execute(
        select(MethodologyVersion).where(
            MethodologyVersion.methodology_id == vm0042.id,
            MethodologyVersion.version == "2.2",
        )
    )
    v22 = v22_res.scalars().first()

    return {
        "org": org,
        "user": user,
        "family": agri_family,
        "methodology": vm0042,
        "version": v22,
    }


@pytest.mark.asyncio
async def test_project_foundation_and_methodology_lock(db_session: AsyncSession):
    """Verifies methodology version locking and immutable parameter snapshots."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    vm0042 = setup["methodology"]
    v22 = setup["version"]
    family = setup["family"]

    project = Project(
        name="Karnal Regenerative Agriculture Hub",
        project_code=f"AGR-KARNAL-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        sector_id=family.id if family else None,
        methodology_id=vm0042.id,
        methodology_version_id=v22.id,
        crediting_start=date(2025, 1, 1),
        crediting_end=date(2045, 12, 31),
        baseline_parameters={},
    )
    db_session.add(project)
    await db_session.commit()

    # 1. Check foundation prior to lock
    foundation = await AgricultureService.get_project_foundation(db_session, project.id, org.id)
    assert foundation["project_name"] == "Karnal Regenerative Agriculture Hub"
    assert foundation["methodology_lock_status"] == "UNLOCKED"
    assert foundation["locked_methodology_snapshot"] is None

    # 2. Lock methodology
    snapshot = await AgricultureService.lock_project_methodology(
        db=db_session,
        project_id=project.id,
        organization_id=org.id,
        user_id=setup["user"].id,
        notes="Official project validation baseline lock",
    )
    await db_session.commit()

    assert snapshot["status"] == "LOCKED"
    assert snapshot["methodology_code"] == "VM0042"
    assert snapshot["version"] == "2.2"
    assert "VT0014 digital soil mapping tool where applicable" in snapshot["canonical_designation"]

    # 3. Check foundation after lock
    foundation_locked = await AgricultureService.get_project_foundation(db_session, project.id, org.id)
    assert foundation_locked["methodology_lock_status"] == "LOCKED"
    assert foundation_locked["locked_methodology_snapshot"]["status"] == "LOCKED"


@pytest.mark.asyncio
async def test_authoritative_boundary_linking(db_session: AsyncSession):
    """Verifies authoritative spatial boundary linking and version incrementing."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]

    project = Project(
        name="Punjab Soil Carbon Initiative",
        project_code=f"AGR-PB-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        crediting_start=date(2024, 6, 1),
        crediting_end=date(2044, 5, 31),
    )
    db_session.add(project)
    await db_session.commit()

    # Version 1
    req1 = LinkBoundaryRequest(
        boundary_geojson=VALID_POLYGON_A,
        source="CADASTRAL",
        effective_date=date(2024, 6, 1),
        reason="Initial Cadastral Boundary",
    )
    pbv1 = await AgricultureService.link_project_boundary(
        db=db_session,
        project_id=project.id,
        organization_id=org.id,
        user_id=setup["user"].id,
        payload=req1,
    )
    await db_session.commit()

    assert pbv1.version_number == 1
    assert pbv1.area_ha > 400.0  # WGS84 geodesic calculation ~433.9 ha
    assert pbv1.source == "CADASTRAL"

    # Version 2 (amended boundary)
    req2 = LinkBoundaryRequest(
        boundary_geojson=VALID_POLYGON_B,
        source="GNSS_SURVEY",
        effective_date=date(2025, 1, 1),
        reason="Survey Revision",
    )
    pbv2 = await AgricultureService.link_project_boundary(
        db=db_session,
        project_id=project.id,
        organization_id=org.id,
        user_id=setup["user"].id,
        payload=req2,
    )
    await db_session.commit()

    assert pbv2.version_number == 2
    assert pbv2.area_ha < pbv1.area_ha

    # Check foundation reflects latest version
    foundation = await AgricultureService.get_project_foundation(db_session, project.id, org.id)
    assert foundation["authoritative_boundary"]["version_number"] == 2


@pytest.mark.asyncio
async def test_stratum_and_membership_lifecycle(db_session: AsyncSession):
    """Verifies analytical strata creation, land unit memberships, and area aggregation."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]

    project = Project(
        name="Haryana Agroforestry & Soil Carbon",
        project_code=f"AGR-HR-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.commit()

    # 1. Create two land units
    lu1 = await AgricultureService.create_land_unit(
        db_session,
        LandUnitCreate(
            project_id=project.id,
            name="Field North",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
            land_use_category="CROPLAND",
        ),
        org.id,
    )
    lu2 = await AgricultureService.create_land_unit(
        db_session,
        LandUnitCreate(
            project_id=project.id,
            name="Field South",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_C,
            land_use_category="CROPLAND",
        ),
        org.id,
    )
    await db_session.commit()

    # 2. Create Stratum
    stratum = await AgricultureService.create_stratum(
        db_session,
        StratumCreate(
            code="STRAT-SILT-LOAM",
            name="Silt Loam - No Till",
            stratum_type="SOIL_TEXTURE",
            description="Alluvial silt loam soils under continuous no-till",
        ),
        organization_id=org.id,
        project_id=project.id,
    )
    await db_session.commit()

    assert stratum.code == "STRAT-SILT-LOAM"
    assert stratum.area_ha == 0.0

    # 3. Add Memberships
    updated_stratum = await AgricultureService.add_stratum_memberships(
        db=db_session,
        stratum_id=stratum.id,
        organization_id=org.id,
        memberships=[
            StratumMembershipItem(
                land_unit_id=lu1.id,
                valid_from=date(2024, 1, 1),
                status="ACTIVE",
            ),
            StratumMembershipItem(
                land_unit_id=lu2.id,
                valid_from=date(2024, 1, 1),
                status="ACTIVE",
            ),
        ],
    )
    await db_session.commit()

    assert updated_stratum["member_count"] == 2
    assert updated_stratum["area_ha"] == round(lu1.area_ha + lu2.area_ha, 4)
    assert lu1.id in updated_stratum["land_unit_ids"]
    assert lu2.id in updated_stratum["land_unit_ids"]


@pytest.mark.asyncio
async def test_management_records_tracking(db_session: AsyncSession):
    """Verifies typed management history tracking with provenance sources."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]

    project = Project(
        name="Deccan Plateau Millet Hub",
        project_code=f"AGR-DEC-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.commit()

    lu = await AgricultureService.create_land_unit(
        db_session,
        LandUnitCreate(
            project_id=project.id,
            name="Plot 1A",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
        ),
        org.id,
    )
    await db_session.commit()

    # 1. Historical Baseline Record (Conventional Tillage)
    rec1 = await AgricultureService.create_management_record(
        db=db_session,
        payload=ManagementRecordCreate(
            record_type="TILLAGE",
            practice_category="BASELINE",
            event_date=date(2022, 5, 10),
            data_source="FIELD_INTERVIEW",
            details={"tillage_depth_cm": 25, "type": "CONVENTIONAL_DISC_PLOW"},
            land_unit_id=lu.id,
            qa_status="VERIFIED",
        ),
        organization_id=org.id,
        user_id=setup["user"].id,
        project_id=project.id,
    )

    # 2. Project Activity Record (Zero-Till Cover Cropping)
    rec2 = await AgricultureService.create_management_record(
        db=db_session,
        payload=ManagementRecordCreate(
            record_type="COVER_CROP",
            practice_category="PROJECT_ACTIVITY",
            event_date=date(2025, 6, 15),
            data_source="FIELD_OBSERVATION",
            details={"species": "Pearl Millet / Cowpea Mix", "seeding_rate_kg_ha": 35.0},
            land_unit_id=lu.id,
            qa_status="VERIFIED",
        ),
        organization_id=org.id,
        user_id=setup["user"].id,
        project_id=project.id,
    )
    await db_session.commit()

    assert rec1.record_type == "TILLAGE"
    assert rec1.practice_category == "BASELINE"
    assert rec2.record_type == "COVER_CROP"
    assert rec2.practice_category == "PROJECT_ACTIVITY"

    # Filter by practice_category
    baseline_records = await AgricultureService.get_management_records(
        db=db_session,
        organization_id=org.id,
        project_id=project.id,
        practice_category="BASELINE",
    )
    assert len(baseline_records) == 1
    assert baseline_records[0].record_type == "TILLAGE"


@pytest.mark.asyncio
async def test_deterministic_foundation_readiness_evaluator(db_session: AsyncSession):
    """
    Verifies that the Foundation Readiness Evaluator returns deterministic
    categorical statuses across the 6 components without percentage scores or fake credits.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    vm0042 = setup["methodology"]
    v22 = setup["version"]

    # 1. Empty unconfigured project
    project = Project(
        name="Pampa Regenerative Soil Pilot",
        project_code=f"AGR-PAMPA-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.commit()

    readiness = await AgricultureService.evaluate_foundation_readiness(db_session, project.id, org.id)
    assert readiness["overall_status"] == "INCOMPLETE"
    assert readiness["components"]["project_configuration"]["status"] == "INCOMPLETE"
    assert readiness["components"]["methodology_lock"]["status"] == "NOT_CONFIGURED"
    assert readiness["components"]["authoritative_boundary"]["status"] == "NOT_CONFIGURED"
    assert readiness["components"]["land_units"]["status"] == "INCOMPLETE"
    assert readiness["components"]["stratification"]["status"] == "NOT_CONFIGURED"
    assert readiness["components"]["management_baseline"]["status"] == "NOT_CONFIGURED"

    # Invariant: No carbon credits or tCO2e in readiness evaluation
    assert "credits" not in readiness
    assert "tco2e" not in readiness

    # 2. Add crediting period
    project.crediting_start = date(2025, 1, 1)
    project.crediting_end = date(2045, 12, 31)
    await db_session.commit()

    readiness = await AgricultureService.evaluate_foundation_readiness(db_session, project.id, org.id)
    assert readiness["components"]["project_configuration"]["status"] == "COMPLETE"

    # 3. Assign and lock methodology
    project.methodology_id = vm0042.id
    project.methodology_version_id = v22.id
    await AgricultureService.lock_project_methodology(db_session, project.id, org.id, setup["user"].id)
    await db_session.commit()

    readiness = await AgricultureService.evaluate_foundation_readiness(db_session, project.id, org.id)
    assert readiness["components"]["methodology_lock"]["status"] == "COMPLETE"

    # 4. Link authoritative boundary
    await AgricultureService.link_project_boundary(
        db_session,
        project.id,
        org.id,
        setup["user"].id,
        LinkBoundaryRequest(boundary_geojson=VALID_POLYGON_A),
    )
    await db_session.commit()

    readiness = await AgricultureService.evaluate_foundation_readiness(db_session, project.id, org.id)
    assert readiness["components"]["authoritative_boundary"]["status"] == "COMPLETE"

    # 5. Add land unit
    lu = await AgricultureService.create_land_unit(
        db_session,
        LandUnitCreate(
            project_id=project.id,
            name="Field 1",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
        ),
        org.id,
    )
    await db_session.commit()

    readiness = await AgricultureService.evaluate_foundation_readiness(db_session, project.id, org.id)
    assert readiness["components"]["land_units"]["status"] == "COMPLETE"

    # 6. Add stratum and membership
    stratum = await AgricultureService.create_stratum(
        db_session,
        StratumCreate(code="S-01", name="Stratum 1"),
        org.id,
        project.id,
    )
    await AgricultureService.add_stratum_memberships(
        db_session,
        stratum.id,
        org.id,
        [StratumMembershipItem(land_unit_id=lu.id, valid_from=date(2025, 1, 1))],
    )
    await db_session.commit()

    readiness = await AgricultureService.evaluate_foundation_readiness(db_session, project.id, org.id)
    assert readiness["components"]["stratification"]["status"] == "COMPLETE"

    # 7. Add baseline management record
    await AgricultureService.create_management_record(
        db_session,
        ManagementRecordCreate(
            record_type="TILLAGE",
            practice_category="BASELINE",
            event_date=date(2023, 4, 15),
            data_source="FIELD_INTERVIEW",
            details={"type": "CHISEL_PLOW"},
            land_unit_id=lu.id,
        ),
        org.id,
        project_id=project.id,
    )
    await db_session.commit()

    # Now all 6 components are COMPLETE
    readiness = await AgricultureService.evaluate_foundation_readiness(db_session, project.id, org.id)
    assert readiness["overall_status"] == "COMPLETE"
    for comp_name, comp_data in readiness["components"].items():
        assert comp_data["status"] == "COMPLETE", f"Expected {comp_name} to be COMPLETE, got {comp_data['status']}"


@pytest.mark.asyncio
async def test_multi_tenant_abac_isolation(db_session: AsyncSession):
    """Verifies that an organization cannot access another organization's agricultural entities."""
    setup = await create_agri_setup(db_session)
    org_a = setup["org"]

    org_b = Organization(name=f"Rival Agro Holdings {uuid.uuid4().hex[:8]}")
    db_session.add(org_b)
    await db_session.flush()

    project_a = Project(
        name="Org A Agriculture Project",
        project_code=f"AGR-A-{uuid.uuid4().hex[:6]}",
        organization_id=org_a.id,
    )
    db_session.add(project_a)
    await db_session.commit()

    stratum_a = await AgricultureService.create_stratum(
        db_session,
        StratumCreate(code="STRAT-A", name="Stratum Org A"),
        org_a.id,
        project_a.id,
    )
    await db_session.commit()

    # Org B attempts to retrieve project_a foundation -> raises ValueError
    with pytest.raises(ValueError, match="not found for organization"):
        await AgricultureService.get_project_foundation(db_session, project_a.id, org_b.id)

    # Org B attempts to retrieve stratum_a -> returns None
    res = await AgricultureService.get_stratum_by_id(db_session, stratum_a.id, org_b.id)
    assert res is None

    # Org B attempts to evaluate readiness -> raises ValueError
    with pytest.raises(ValueError, match="not found for organization"):
        await AgricultureService.evaluate_foundation_readiness(db_session, project_a.id, org_b.id)


def _create_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id) if org_id else None,
        "iat": now,
        "exp": now + timedelta(hours=2),
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_agriculture_phase1_api_endpoints(db_session: AsyncSession):
    """Verifies all Phase 1 REST API endpoints over HTTP."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    user = setup["user"]
    vm0042 = setup["methodology"]
    v22 = setup["version"]

    project = Project(
        name="API Test Agriculture Project",
        project_code=f"AGR-API-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        methodology_id=vm0042.id,
        methodology_version_id=v22.id,
        crediting_start=date(2025, 1, 1),
        crediting_end=date(2045, 12, 31),
    )
    db_session.add(project)
    await db_session.commit()

    token = _create_token(user.id, user.email, user.role, org.id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. GET /projects/{project_id}/foundation
        res = await client.get(f"/api/v1/agriculture/projects/{project.id}/foundation", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["project_name"] == "API Test Agriculture Project"
        assert data["methodology_lock_status"] == "UNLOCKED"

        # 2. POST /projects/{project_id}/lock-methodology
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/lock-methodology",
            json={"notes": "HTTP lock"},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        lock_data = res.json()
        assert lock_data["status"] == "LOCKED"
        assert lock_data["methodology_code"] == "VM0042"

        # 3. POST /projects/{project_id}/link-boundary
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/link-boundary",
            json={
                "boundary_geojson": VALID_POLYGON_A,
                "source": "GNSS_SURVEY",
                "reason": "Official Baseline Boundary",
            },
            headers=headers,
        )
        assert res.status_code == 201, res.text
        b_data = res.json()
        assert b_data["version_number"] == 1
        assert b_data["area_ha"] > 400.0

        # 4. POST /land-units
        res = await client.post(
            "/api/v1/agriculture/land-units",
            json={
                "project_id": str(project.id),
                "name": "API Test Field",
                "unit_type": "FIELD",
                "boundary_geojson": VALID_POLYGON_B,
            },
            headers=headers,
        )
        assert res.status_code == 201, res.text
        lu_data = res.json()
        lu_id = lu_data["id"]

        # 5. POST /projects/{project_id}/strata
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/strata",
            json={
                "code": "API-STRAT-1",
                "name": "API Stratum",
                "stratum_type": "MANAGEMENT_PRACTICE",
            },
            headers=headers,
        )
        assert res.status_code == 201, res.text
        strat_data = res.json()
        strat_id = strat_data["id"]

        # 6. POST /projects/{project_id}/strata/{stratum_id}/members
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/strata/{strat_id}/members",
            json={
                "memberships": [
                    {
                        "land_unit_id": lu_id,
                        "valid_from": "2025-01-01",
                        "status": "ACTIVE",
                    }
                ]
            },
            headers=headers,
        )
        assert res.status_code == 200, res.text
        member_data = res.json()
        assert member_data["member_count"] == 1

        # 7. POST /projects/{project_id}/management-records
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/management-records",
            json={
                "record_type": "FERTILIZER_ORGANIC",
                "practice_category": "BASELINE",
                "event_date": "2024-03-20",
                "data_source": "DOCUMENT",
                "details": {"compost_t_ha": 5.0},
                "land_unit_id": lu_id,
            },
            headers=headers,
        )
        assert res.status_code == 201, res.text
        mr_data = res.json()
        assert mr_data["record_type"] == "FERTILIZER_ORGANIC"

        # 8. GET /projects/{project_id}/foundation-readiness
        res = await client.get(
            f"/api/v1/agriculture/projects/{project.id}/foundation-readiness",
            headers=headers,
        )
        assert res.status_code == 200, res.text
        readiness_data = res.json()
        assert readiness_data["overall_status"] == "COMPLETE"
        assert readiness_data["components"]["project_configuration"]["status"] == "COMPLETE"
        assert readiness_data["components"]["methodology_lock"]["status"] == "COMPLETE"
        assert readiness_data["components"]["authoritative_boundary"]["status"] == "COMPLETE"
        assert readiness_data["components"]["land_units"]["status"] == "COMPLETE"
        assert readiness_data["components"]["stratification"]["status"] == "COMPLETE"
        assert readiness_data["components"]["management_baseline"]["status"] == "COMPLETE"


@pytest.mark.asyncio
async def test_stratum_temporal_preservation_and_deduplication(db_session: AsyncSession):
    """
    Verifies that multiple historical membership assignments for the same land unit
    are preserved across time, while stratum.area_ha deduplicates overlapping active units.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]

    project = Project(
        name="Stratum Dedup Project",
        project_code=f"AGR-DEDUP-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.commit()

    lu1 = await AgricultureService.create_land_unit(
        db_session,
        LandUnitCreate(
            project_id=project.id,
            name="Field Alpha",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
        ),
        org.id,
    )
    lu2 = await AgricultureService.create_land_unit(
        db_session,
        LandUnitCreate(
            project_id=project.id,
            name="Field Beta",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_C,
        ),
        org.id,
    )
    await db_session.commit()

    strat = await AgricultureService.create_stratum(
        db_session,
        StratumCreate(
            code="STR-TILL",
            name="No-Till Soil Stratum",
            stratum_type="MANAGEMENT_PRACTICE",
        ),
        org.id,
        project_id=project.id,
    )
    await db_session.commit()

    # Period 1: lu1 active in 2024
    await AgricultureService.add_stratum_memberships(
        db_session,
        strat.id,
        org.id,
        [
            StratumMembershipItem(
                land_unit_id=lu1.id,
                valid_from=date(2024, 1, 1),
                valid_to=date(2024, 12, 31),
                status="ACTIVE",
            )
        ],
    )
    await db_session.commit()

    # Period 2: lu1 active in 2025 (distinct valid_from preserves historical period)
    await AgricultureService.add_stratum_memberships(
        db_session,
        strat.id,
        org.id,
        [
            StratumMembershipItem(
                land_unit_id=lu1.id,
                valid_from=date(2025, 1, 1),
                valid_to=None,
                status="ACTIVE",
            )
        ],
    )
    await db_session.commit()

    # Query memberships directly from DB
    mems = (
        await db_session.execute(
            select(StratumMembership).where(StratumMembership.stratum_id == strat.id)
        )
    ).scalars().all()
    assert len(mems) == 2, "Both historical membership periods must be preserved"

    # Area deduplication: lu1 area must be counted only once, not twice
    s_updated = await AgricultureService.get_stratum_by_id(db_session, strat.id, org.id)
    assert abs(s_updated["area_ha"] - lu1.area_ha) < 0.001, (
        f"Stratum area ({s_updated['area_ha']}) must equal single land unit area ({lu1.area_ha}), not double"
    )

    # Add second land unit lu2
    await AgricultureService.add_stratum_memberships(
        db_session,
        strat.id,
        org.id,
        [
            StratumMembershipItem(
                land_unit_id=lu2.id,
                valid_from=date(2025, 1, 1),
                status="ACTIVE",
            )
        ],
    )
    await db_session.commit()

    s_final = await AgricultureService.get_stratum_by_id(db_session, strat.id, org.id)
    expected_area = round(lu1.area_ha + lu2.area_ha, 4)
    assert abs(s_final["area_ha"] - expected_area) < 0.001


@pytest.mark.asyncio
async def test_management_history_temporal_and_schema_validation(db_session: AsyncSession):
    """
    Verifies management history temporal validation:
    - event_date <= today
    - end_date >= event_date
    - permitted record_type, practice_category, data_source
    - foreign key isolation
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]

    project = Project(
        name="Temporal Mgmt Project",
        project_code=f"AGR-TM-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.commit()

    # 1. Future event_date rejected
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValueError, match="future"):
        ManagementRecordCreate(
            project_id=project.id,
            record_type="TILLAGE",
            practice_category="BASELINE",
            event_date=tomorrow,
            data_source="REPORTED",
        )

    # 2. end_date < event_date rejected
    with pytest.raises(ValueError, match="cannot precede event_date"):
        ManagementRecordCreate(
            project_id=project.id,
            record_type="TILLAGE",
            practice_category="BASELINE",
            event_date=date(2024, 6, 15),
            end_date=date(2024, 6, 10),
            data_source="REPORTED",
        )

    # 3. Invalid record_type rejected
    with pytest.raises(ValueError, match="Invalid record_type"):
        ManagementRecordCreate(
            project_id=project.id,
            record_type="MAGIC_FERTILIZER",
            practice_category="BASELINE",
            event_date=date(2024, 6, 15),
            data_source="REPORTED",
        )

    # 4. Valid record creation
    rec = await AgricultureService.create_management_record(
        db_session,
        ManagementRecordCreate(
            project_id=project.id,
            record_type="COVER_CROP",
            practice_category="BASELINE",
            event_date=date(2024, 5, 1),
            end_date=date(2024, 9, 30),
            data_source="FIELD_INTERVIEW",
            details={"species": "Rye grass"},
        ),
        org.id,
    )
    assert rec.record_type == "COVER_CROP"
    assert rec.event_date == date(2024, 5, 1)

    # 5. Update rejecting inverted dates
    with pytest.raises(ValueError, match="cannot precede event_date"):
        await AgricultureService.update_management_record(
            db_session,
            rec.id,
            ManagementRecordUpdate(end_date=date(2024, 4, 1)),
            org.id,
        )


@pytest.mark.asyncio
async def test_methodology_lock_immutability_and_preservation(db_session: AsyncSession):
    """
    Verifies:
    1. Second call to lock_project_methodology fails closed (rejects re-locking).
    2. Standard project updates via ProjectService preserve the locked methodology snapshot.
    3. Complete snapshot metadata keys exist.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    vm0042 = setup["methodology"]
    v22 = setup["version"]
    user = setup["user"]

    project = Project(
        name="Methodology Lock Immutability Project",
        project_code=f"AGR-LOCK-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        methodology_id=vm0042.id,
        methodology_version_id=v22.id,
        crediting_start=date(2025, 1, 1),
        crediting_end=date(2045, 12, 31),
    )
    db_session.add(project)
    await db_session.commit()

    # 1. Initial lock succeeds
    snapshot = await AgricultureService.lock_project_methodology(
        db_session,
        project.id,
        org.id,
        user.id,
        notes="Primary baseline lock",
    )
    await db_session.commit()

    assert snapshot["status"] == "LOCKED"
    assert snapshot["methodology_code"] == "VM0042"
    assert snapshot["version"] == "2.2"
    assert snapshot["version_status"] == "active"
    assert "rules_parameters_snapshot" in snapshot
    assert "canonical_designation" in snapshot
    assert snapshot["project_id"] == str(project.id)
    assert snapshot["organization_id"] == str(org.id)

    # 2. Second lock attempt must fail closed (immutability)
    with pytest.raises(ValueError, match="already locked.*immutable"):
        await AgricultureService.lock_project_methodology(
            db_session,
            project.id,
            org.id,
            user.id,
            notes="Malicious or erroneous overwrite attempt",
        )

    # 3. Standard project update preserves snapshot
    from app.domains.projects.repository import ProjectRepository
    from app.domains.projects.schemas import ProjectUpdate
    from app.domains.projects.service import ProjectService

    repo = ProjectRepository(db_session)
    proj_service = ProjectService(repo)

    await proj_service.update_project(
        project.id,
        ProjectUpdate(
            name="Renamed Project With Same Locked Methodology",
            baseline_parameters={"soil_depth_target": 30},
        ),
        org.id,
    )
    await db_session.commit()

    # Reload and verify snapshot is still present and unaltered
    refreshed = await repo.get_by_id(project.id, org.id)
    assert refreshed.name == "Renamed Project With Same Locked Methodology"
    assert "locked_methodology_version" in refreshed.baseline_parameters
    assert refreshed.baseline_parameters["locked_methodology_version"]["status"] == "LOCKED"
    assert refreshed.baseline_parameters["locked_methodology_version"]["version"] == "2.2"
    assert refreshed.baseline_parameters["soil_depth_target"] == 30


@pytest.mark.asyncio
async def test_rbac_and_separation_of_duties_auditor_restriction(db_session: AsyncSession):
    """
    Enforces Segregation of Duties (SoD):
    - AUDITOR cannot lock methodology (403)
    - AUDITOR cannot link boundary (403)
    - AUDITOR cannot create strata (403)
    - AUDITOR cannot create management records (403)
    - AUDITOR CAN inspect foundation & readiness (200)
    - FIELD_AGENT can log management records (201) but cannot lock methodology (403)
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    vm0042 = setup["methodology"]
    v22 = setup["version"]

    project = Project(
        name="SoD Enforcement Project",
        project_code=f"AGR-SOD-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        methodology_id=vm0042.id,
        methodology_version_id=v22.id,
        crediting_start=date(2025, 1, 1),
        crediting_end=date(2045, 12, 31),
    )
    db_session.add(project)
    await db_session.commit()

    # Users
    auditor_id = uuid.uuid4()
    field_agent_id = uuid.uuid4()
    pm_id = uuid.uuid4()

    auditor_email = f"auditor-{uuid.uuid4().hex[:6]}@vvb.org"
    agent_email = f"agent-{uuid.uuid4().hex[:6]}@field.org"
    pm_email = f"pm-{uuid.uuid4().hex[:6]}@company.org"

    auditor_user = User(
        id=auditor_id,
        email=auditor_email,
        full_name="Auditor User",
        role="AUDITOR",
        organization_id=org.id,
        is_active=True,
    )
    agent_user = User(
        id=field_agent_id,
        email=agent_email,
        full_name="Field Agent User",
        role="FIELD_AGENT",
        organization_id=org.id,
        is_active=True,
    )
    pm_user = User(
        id=pm_id,
        email=pm_email,
        full_name="Project Manager User",
        role="PROJECT_MANAGER",
        organization_id=org.id,
        is_active=True,
    )
    db_session.add_all([auditor_user, agent_user, pm_user])
    await db_session.commit()

    auditor_token = _create_token(auditor_id, auditor_email, "AUDITOR", org.id)
    agent_token = _create_token(field_agent_id, agent_email, "FIELD_AGENT", org.id)
    pm_token = _create_token(pm_id, pm_email, "PROJECT_MANAGER", org.id)

    auditor_headers = {"Authorization": f"Bearer {auditor_token}"}
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    pm_headers = {"Authorization": f"Bearer {pm_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Auditor attempts mutation: lock methodology -> 403 Forbidden
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/lock-methodology",
            json={"notes": "Auditor unauthorized lock"},
            headers=auditor_headers,
        )
        assert res.status_code == 403, f"Auditor must be forbidden from locking methodology: {res.text}"

        # 2. Auditor attempts mutation: link boundary -> 403 Forbidden
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/link-boundary",
            json={"boundary_geojson": VALID_POLYGON_A, "source": "SURVEY"},
            headers=auditor_headers,
        )
        assert res.status_code == 403, f"Auditor must be forbidden from linking boundary: {res.text}"

        # 3. Auditor attempts mutation: create stratum -> 403 Forbidden
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/strata",
            json={"code": "STR-AUDIT", "name": "Audit Stratum"},
            headers=auditor_headers,
        )
        assert res.status_code == 403, f"Auditor must be forbidden from creating strata: {res.text}"

        # 4. Auditor attempts mutation: create management record -> 403 Forbidden
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/management-records",
            json={
                "record_type": "TILLAGE",
                "practice_category": "BASELINE",
                "event_date": "2024-01-01",
            },
            headers=auditor_headers,
        )
        assert res.status_code == 403, f"Auditor must be forbidden from creating management records: {res.text}"

        # 5. Auditor read access: foundation & readiness -> 200 OK
        res = await client.get(
            f"/api/v1/agriculture/projects/{project.id}/foundation",
            headers=auditor_headers,
        )
        assert res.status_code == 200, f"Auditor must have read access: {res.text}"

        res = await client.get(
            f"/api/v1/agriculture/projects/{project.id}/foundation-readiness",
            headers=auditor_headers,
        )
        assert res.status_code == 200, f"Auditor must have readiness inspection access: {res.text}"

        # 6. Field Agent attempts mutation: create management record -> 201 Created
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/management-records",
            json={
                "record_type": "TILLAGE",
                "practice_category": "BASELINE",
                "event_date": "2024-01-01",
                "data_source": "FIELD_OBSERVATION",
            },
            headers=agent_headers,
        )
        assert res.status_code == 201, f"Field Agent must be authorized to create management records: {res.text}"

        # 7. Field Agent attempts lock methodology -> 403 Forbidden
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/lock-methodology",
            json={"notes": "Field agent unauthorized lock"},
            headers=agent_headers,
        )
        assert res.status_code == 403, f"Field Agent must be forbidden from locking methodology: {res.text}"

        # 8. Project Manager locks methodology -> 200 OK
        res = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/lock-methodology",
            json={"notes": "PM authorized baseline lock"},
            headers=pm_headers,
        )
        assert res.status_code == 200, f"Project Manager must be authorized to lock methodology: {res.text}"
        assert res.json()["status"] == "LOCKED"


@pytest.mark.asyncio
async def test_stratum_as_of_date_deterministic_query(db_session: AsyncSession):
    """
    Verifies deterministic as_of_date query semantics on strata:
    - active if valid_from <= as_of_date and (valid_to is None or valid_to >= as_of_date)
    - area aggregation sums distinct land units as-of-date once
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    project = Project(
        name="Temporal Stratification Test Project",
        project_code=f"AGR-TEMP-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        crediting_start=date(2023, 1, 1),
        crediting_end=date(2043, 12, 31),
    )
    db_session.add(project)
    await db_session.commit()

    # Create two land units
    u1 = await AgricultureService.create_land_unit(
        db=db_session,
        payload=LandUnitCreate(
            project_id=project.id,
            name="Field North 10ha",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
        ),
        organization_id=org.id,
    )
    u2 = await AgricultureService.create_land_unit(
        db=db_session,
        payload=LandUnitCreate(
            project_id=project.id,
            name="Field South 15ha",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_C,
        ),
        organization_id=org.id,
    )
    await db_session.commit()

    # Create Stratum A (Reduced Tillage) and Stratum B (No-Till) under MANAGEMENT_PRACTICE
    stratum_a = await AgricultureService.create_stratum(
        db=db_session,
        payload=StratumCreate(
            project_id=project.id,
            code="STR-RT",
            name="Reduced Tillage",
            stratum_type="MANAGEMENT_PRACTICE",
        ),
        organization_id=org.id,
    )
    stratum_b = await AgricultureService.create_stratum(
        db=db_session,
        payload=StratumCreate(
            project_id=project.id,
            code="STR-NT",
            name="No-Till Continuous",
            stratum_type="MANAGEMENT_PRACTICE",
        ),
        organization_id=org.id,
    )
    await db_session.commit()

    # Assign Unit 1 to Stratum A for 2023 (2023-01-01 to 2023-12-31)
    await AgricultureService.add_stratum_memberships(
        db=db_session,
        stratum_id=stratum_a.id,
        organization_id=org.id,
        memberships=[
            StratumMembershipItem(
                land_unit_id=u1.id,
                valid_from=date(2023, 1, 1),
                valid_to=date(2023, 12, 31),
                status="ACTIVE",
            )
        ],
    )
    # Transition Unit 1 to Stratum B for 2024 ongoing (2024-01-01 to None)
    await AgricultureService.add_stratum_memberships(
        db=db_session,
        stratum_id=stratum_b.id,
        organization_id=org.id,
        memberships=[
            StratumMembershipItem(
                land_unit_id=u1.id,
                valid_from=date(2024, 1, 1),
                valid_to=None,
                status="ACTIVE",
            )
        ],
    )
    # Assign Unit 2 to Stratum B for all time (2023-01-01 to None)
    await AgricultureService.add_stratum_memberships(
        db=db_session,
        stratum_id=stratum_b.id,
        organization_id=org.id,
        memberships=[
            StratumMembershipItem(
                land_unit_id=u2.id,
                valid_from=date(2023, 1, 1),
                valid_to=None,
                status="ACTIVE",
            )
        ],
    )
    await db_session.commit()

    # Query 1: As of 2023-06-15
    # Stratum A should have Unit 1 (member_count=1, area=u1.area_ha)
    # Stratum B should have Unit 2 (member_count=1, area=u2.area_ha)
    strata_2023 = await AgricultureService.get_strata(
        db=db_session,
        organization_id=org.id,
        project_id=project.id,
        as_of_date=date(2023, 6, 15),
    )
    s_a_2023 = next(s for s in strata_2023 if s["code"] == "STR-RT")
    s_b_2023 = next(s for s in strata_2023 if s["code"] == "STR-NT")

    assert s_a_2023["member_count"] == 1
    assert u1.id in s_a_2023["land_unit_ids"]
    assert s_a_2023["area_ha"] == round(u1.area_ha, 4)

    assert s_b_2023["member_count"] == 1
    assert u2.id in s_b_2023["land_unit_ids"]
    assert s_b_2023["area_ha"] == round(u2.area_ha, 4)

    # Query 2: As of 2024-06-15
    # Stratum A should have 0 active members (area=0)
    # Stratum B should have Unit 1 AND Unit 2 (member_count=2, area=u1.area_ha + u2.area_ha)
    strata_2024 = await AgricultureService.get_strata(
        db=db_session,
        organization_id=org.id,
        project_id=project.id,
        as_of_date=date(2024, 6, 15),
    )
    s_a_2024 = next(s for s in strata_2024 if s["code"] == "STR-RT")
    s_b_2024 = next(s for s in strata_2024 if s["code"] == "STR-NT")

    assert s_a_2024["member_count"] == 0
    assert s_a_2024["area_ha"] == 0.0

    assert s_b_2024["member_count"] == 2
    assert u1.id in s_b_2024["land_unit_ids"]
    assert u2.id in s_b_2024["land_unit_ids"]
    assert s_b_2024["area_ha"] == round(u1.area_ha + u2.area_ha, 4)

    # Query 3: Prior to project start (2022-01-01)
    # Both strata must return 0 members and 0.0 ha
    strata_2022 = await AgricultureService.get_strata(
        db=db_session,
        organization_id=org.id,
        project_id=project.id,
        as_of_date=date(2022, 1, 1),
    )
    for s in strata_2022:
        assert s["member_count"] == 0
        assert s["area_ha"] == 0.0


@pytest.mark.asyncio
async def test_stratum_temporal_overlap_rejection_same_dimension(db_session: AsyncSession):
    """
    Verifies that simultaneous overlapping active memberships for the same land unit
    within the SAME stratification dimension (stratum_type) are strictly rejected.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    project = Project(
        name="Overlap Rejection Project",
        project_code=f"AGR-OVL-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.commit()

    unit = await AgricultureService.create_land_unit(
        db=db_session,
        payload=LandUnitCreate(
            project_id=project.id,
            name="Field Alpha",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
        ),
        organization_id=org.id,
    )
    s1 = await AgricultureService.create_stratum(
        db=db_session,
        payload=StratumCreate(
            project_id=project.id,
            code="STR-M1",
            name="Management Practice 1",
            stratum_type="MANAGEMENT_PRACTICE",
        ),
        organization_id=org.id,
    )
    s2 = await AgricultureService.create_stratum(
        db=db_session,
        payload=StratumCreate(
            project_id=project.id,
            code="STR-M2",
            name="Management Practice 2",
            stratum_type="MANAGEMENT_PRACTICE",
        ),
        organization_id=org.id,
    )
    await db_session.commit()

    # Assign unit to s1 for 2024
    await AgricultureService.add_stratum_memberships(
        db=db_session,
        stratum_id=s1.id,
        organization_id=org.id,
        memberships=[
            StratumMembershipItem(
                land_unit_id=unit.id,
                valid_from=date(2024, 1, 1),
                valid_to=date(2024, 12, 31),
                status="ACTIVE",
            )
        ],
    )
    await db_session.commit()

    # Attempt overlapping assignment to s2 (2024-06-01 to 2025-06-01) -> MUST FAIL
    with pytest.raises(ValueError, match="Temporal overlap conflict"):
        await AgricultureService.add_stratum_memberships(
            db=db_session,
            stratum_id=s2.id,
            organization_id=org.id,
            memberships=[
                StratumMembershipItem(
                    land_unit_id=unit.id,
                    valid_from=date(2024, 6, 1),
                    valid_to=date(2025, 6, 1),
                    status="ACTIVE",
                )
            ],
        )

    # Attempt intra-batch overlapping assignment to s2 -> MUST FAIL
    with pytest.raises(ValueError, match="Temporal overlap conflict in submission"):
        await AgricultureService.add_stratum_memberships(
            db=db_session,
            stratum_id=s2.id,
            organization_id=org.id,
            memberships=[
                StratumMembershipItem(
                    land_unit_id=unit.id,
                    valid_from=date(2025, 1, 1),
                    valid_to=date(2025, 6, 30),
                    status="ACTIVE",
                ),
                StratumMembershipItem(
                    land_unit_id=unit.id,
                    valid_from=date(2025, 4, 1),
                    valid_to=date(2025, 12, 31),
                    status="ACTIVE",
                ),
            ],
        )

    # Non-overlapping sequential assignment (2025-01-01 to 2025-12-31) -> MUST SUCCEED
    res = await AgricultureService.add_stratum_memberships(
        db=db_session,
        stratum_id=s2.id,
        organization_id=org.id,
        memberships=[
            StratumMembershipItem(
                land_unit_id=unit.id,
                valid_from=date(2025, 1, 1),
                valid_to=date(2025, 12, 31),
                status="ACTIVE",
            )
        ],
    )
    assert res["member_count"] == 1
    assert unit.id in res["land_unit_ids"]


@pytest.mark.asyncio
async def test_stratum_orthogonal_dimensions_simultaneous_active_membership(db_session: AsyncSession):
    """
    Verifies that simultaneous active memberships across DIFFERENT stratification dimensions
    (e.g., MANAGEMENT_PRACTICE and SOIL_TYPE) are permitted without conflict.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    project = Project(
        name="Orthogonal Dimensions Project",
        project_code=f"AGR-ORTHO-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.commit()

    unit = await AgricultureService.create_land_unit(
        db=db_session,
        payload=LandUnitCreate(
            project_id=project.id,
            name="Field Beta",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
        ),
        organization_id=org.id,
    )
    mgmt_strat = await AgricultureService.create_stratum(
        db=db_session,
        payload=StratumCreate(
            project_id=project.id,
            code="STR-MGMT-CC",
            name="Cover Crop Rotation",
            stratum_type="MANAGEMENT_PRACTICE",
        ),
        organization_id=org.id,
    )
    soil_strat = await AgricultureService.create_stratum(
        db=db_session,
        payload=StratumCreate(
            project_id=project.id,
            code="STR-SOIL-CLAY",
            name="Heavy Clay Loam",
            stratum_type="SOIL_TYPE",
        ),
        organization_id=org.id,
    )
    await db_session.commit()

    # Assign unit to mgmt_strat for 2024
    await AgricultureService.add_stratum_memberships(
        db=db_session,
        stratum_id=mgmt_strat.id,
        organization_id=org.id,
        memberships=[
            StratumMembershipItem(
                land_unit_id=unit.id,
                valid_from=date(2024, 1, 1),
                valid_to=date(2024, 12, 31),
                status="ACTIVE",
            )
        ],
    )

    # Assign unit to soil_strat for the exact same period 2024 -> MUST SUCCEED (orthogonal dimension)
    res_soil = await AgricultureService.add_stratum_memberships(
        db=db_session,
        stratum_id=soil_strat.id,
        organization_id=org.id,
        memberships=[
            StratumMembershipItem(
                land_unit_id=unit.id,
                valid_from=date(2024, 1, 1),
                valid_to=date(2024, 12, 31),
                status="ACTIVE",
            )
        ],
    )
    await db_session.commit()

    assert res_soil["member_count"] == 1
    assert unit.id in res_soil["land_unit_ids"]


@pytest.mark.asyncio
async def test_management_record_field_semantics_and_data_provenance(db_session: AsyncSession):
    """
    Verifies management record field semantics:
    - record_type: specific practice (TILLAGE, COVER_CROP, etc.)
    - practice_category: BASELINE vs PROJECT_ACTIVITY
    - data_source: REPORTED, FIELD_INTERVIEW, DOCUMENT, FIELD_OBSERVATION, REMOTE_SENSING_CORROBORATED
    - Remote sensing is corroborative context, not carbon proof
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    project = Project(
        name="Management Semantics Project",
        project_code=f"AGR-MGMT-SEM-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.commit()

    unit = await AgricultureService.create_land_unit(
        db=db_session,
        payload=LandUnitCreate(
            project_id=project.id,
            name="Field Gamma",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
        ),
        organization_id=org.id,
    )
    await db_session.commit()

    # 1. Historical Baseline Record via Field Interview
    rec_baseline = await AgricultureService.create_management_record(
        db=db_session,
        payload=ManagementRecordCreate(
            project_id=project.id,
            land_unit_id=unit.id,
            record_type="TILLAGE",
            practice_category="BASELINE",
            event_date=date(2021, 5, 10),
            data_source="FIELD_INTERVIEW",
            details={"tillage_depth_cm": 25, "implements": "disc_plow"},
        ),
        organization_id=org.id,
        user_id=setup["user"].id,
    )
    assert rec_baseline.record_type == "TILLAGE"
    assert rec_baseline.practice_category == "BASELINE"
    assert rec_baseline.data_source == "FIELD_INTERVIEW"

    # 2. Project Activity Record Corroborated by Remote Sensing
    rec_project = await AgricultureService.create_management_record(
        db=db_session,
        payload=ManagementRecordCreate(
            project_id=project.id,
            land_unit_id=unit.id,
            record_type="COVER_CROP",
            practice_category="PROJECT_ACTIVITY",
            event_date=date(2024, 10, 15),
            data_source="REMOTE_SENSING_CORROBORATED",
            details={
                "species": "cereal_rye",
                "seeding_rate_kg_ha": 65,
                "satellite_scene_id": "S2A_MSIL2A_20241020T054711",
                "corroboration_notes": "Corroborated by high post-harvest NDVI; represents corroborative evidence only",
            },
        ),
        organization_id=org.id,
        user_id=setup["user"].id,
    )
    assert rec_project.record_type == "COVER_CROP"
    assert rec_project.practice_category == "PROJECT_ACTIVITY"
    assert rec_project.data_source == "REMOTE_SENSING_CORROBORATED"

    # 3. Invalid data_source rejection in schema validation
    with pytest.raises(Exception):
        ManagementRecordCreate(
            project_id=project.id,
            record_type="TILLAGE",
            event_date=date(2024, 1, 1),
            data_source="INVALID_SOURCE",
        )

    # 4. Invalid practice_category rejection in schema validation
    with pytest.raises(Exception):
        ManagementRecordCreate(
            project_id=project.id,
            record_type="TILLAGE",
            event_date=date(2024, 1, 1),
            practice_category="ESTIMATED_FUTURE",
        )
