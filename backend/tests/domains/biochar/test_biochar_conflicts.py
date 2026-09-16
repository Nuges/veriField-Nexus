import uuid
from datetime import datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.agriculture.models import LandUnit
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.authentication.models import User
from app.domains.methodologies.models.base_registry import Methodology
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


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
async def test_cross_sector_vm0044_vm0042_conflict_detection(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    # 1. Fetch VM0042 Methodology
    res_m = await db_session.execute(select(Methodology).where(Methodology.code == "VM0042"))
    vm0042 = res_m.scalars().first()
    assert vm0042 is not None

    # Fetch VM0044 Methodology
    res_m44 = await db_session.execute(select(Methodology).where(Methodology.code == "VM0044"))
    vm0044 = res_m44.scalars().first()
    assert vm0044 is not None

    # 2. Setup Multi-Tenant Org and User
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Cross Sector AgriBiochar Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"compliance_officer_{uuid.uuid4().hex[:6]}@synthetic-nexus.org",
        full_name="Synthetic Compliance Officer",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    # 3. Agriculture Project governed by VM0042 (with SOC pool quantification)
    ag_project_id = uuid.uuid4()
    ag_project = Project(
        id=ag_project_id,
        name="Synthetic Regenerative Cropland Project",
        project_code=f"AG-VM42-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        methodology_id=vm0042.id,
        country="India",
    )
    db_session.add(ag_project)

    # LandUnit under the Agriculture project
    land_unit_id = uuid.uuid4()
    land_unit = LandUnit(
        id=land_unit_id,
        organization_id=org_id,
        project_id=ag_project_id,
        name="Synthetic Cropland Parcel Alpha",
        unit_type="PARCEL",
        area_ha=45.0,
        boundary_geojson={"type": "Polygon", "coordinates": [[[77.1, 28.5], [77.2, 28.5], [77.2, 28.6], [77.1, 28.6], [77.1, 28.5]]]},
        is_active=True,
    )
    db_session.add(land_unit)

    # Independent LandUnit NOT under VM0042
    indep_project_id = uuid.uuid4()
    indep_project = Project(
        id=indep_project_id,
        name="Synthetic Non-VM0042 Forestry Project",
        project_code=f"FOR-GEN-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        country="India",
    )
    db_session.add(indep_project)

    indep_land_unit_id = uuid.uuid4()
    indep_land_unit = LandUnit(
        id=indep_land_unit_id,
        organization_id=org_id,
        project_id=indep_project_id,
        name="Synthetic Non-SOC Parcel Gamma",
        unit_type="PARCEL",
        area_ha=20.0,
        boundary_geojson={"type": "Polygon", "coordinates": [[[85.1, 25.5], [85.2, 25.5], [85.2, 25.6], [85.1, 25.6], [85.1, 25.5]]]},
        is_active=True,
    )
    db_session.add(indep_land_unit)

    # 4. Biochar Project governed by VM0044
    bio_project_id = uuid.uuid4()
    bio_project = Project(
        id=bio_project_id,
        name="Synthetic Pyrolysis Project Theta",
        project_code=f"BIO-VM44-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        methodology_id=vm0044.id,
        country="India",
    )
    db_session.add(bio_project)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. Proactive Conflict Check on the VM0042 LandUnit
        res_conf = await client.get(
            f"/api/v1/biochar/conflicts/land-units/{land_unit_id}?biochar_methodology=VM0044",
            headers=headers,
        )
        assert res_conf.status_code == 200, res_conf.text
        conf_data = res_conf.json()
        assert conf_data["has_conflict"] is True
        assert conf_data["conflict_code"] == "DOUBLE_COUNTING_VM0044_VM0042_SOC"
        assert conf_data["severity"] == "BLOCKING"
        assert conf_data["accounting_blocked"] is True
        assert conf_data["carbon_pool"] == "SOIL_ORGANIC_CARBON"
        assert "Methodology Conflict" in conf_data["message"]

        # B. Proactive Conflict Check on Independent LandUnit -> NO CONFLICT
        res_indep = await client.get(
            f"/api/v1/biochar/conflicts/land-units/{indep_land_unit_id}?biochar_methodology=VM0044",
            headers=headers,
        )
        assert res_indep.status_code == 200, res_indep.text
        assert res_indep.json()["has_conflict"] is False
        assert res_indep.json()["accounting_blocked"] is False

        # C. Create Biochar Batch with VM0044 claim
        batch_payload = {
            "project_id": str(bio_project_id),
            "batch_number": f"BATCH-CONF-{uuid.uuid4().hex[:6].upper()}",
            "facility_name": "Pyrolysis Facility Theta",
            "kiln_id": "KILN-THETA",
            "feedstock_type": "RICE_STRAW",
            "feedstock_weight_tonnes": 30.0,
            "moisture_content_pct": 10.0,
            "pyrolysis_temp_celsius": 550.0,
            "residence_time_minutes": 30.0,
            "biochar_yield_tonnes": 10.0,
            "fixed_carbon_pct": 78.0,
            "ash_content_pct": 5.0,
            "molar_h_c_ratio": 0.38,
            "carbon_claim_registry": "VERRA",
            "carbon_claim_methodology": "VM0044",
        }
        res_batch = await client.post("/api/v1/biochar/batches", json=batch_payload, headers=headers)
        assert res_batch.status_code == 201, res_batch.text
        batch_id = res_batch.json()["id"]

        # D. Attempt Soil End-Use on conflicting VM0042 LandUnit -> MUST BE BLOCKED with 400!
        eu_soil_conflict = {
            "project_id": str(bio_project_id),
            "batch_id": batch_id,
            "end_use_type": "SOIL_APPLICATION",
            "applied_quantity_tonnes": 5.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "source_land_unit_id": str(land_unit_id),
            "application_rate_tonnes_per_ha": 2.5,
            "area_hectares": 2.0,
            "crop_type": "PADDY_RICE",
        }
        res_block = await client.post("/api/v1/biochar/end-uses", json=eu_soil_conflict, headers=headers)
        assert res_block.status_code == 400, res_block.text
        assert "Methodology Conflict" in res_block.json()["detail"]
        assert "double-counting" in res_block.json()["detail"].lower()

        # E. Soil End-Use on Independent LandUnit -> SUCCEEDS without conflict
        eu_soil_safe = {
            "project_id": str(bio_project_id),
            "batch_id": batch_id,
            "end_use_type": "SOIL_APPLICATION",
            "applied_quantity_tonnes": 5.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "source_land_unit_id": str(indep_land_unit_id),
            "application_rate_tonnes_per_ha": 2.5,
            "area_hectares": 2.0,
            "crop_type": "ORCHARD_FRUIT",
        }
        res_safe = await client.post("/api/v1/biochar/end-uses", json=eu_soil_safe, headers=headers)
        assert res_safe.status_code == 201, res_safe.text

        # F. Non-Soil Application on the remaining 5.0 tonnes -> SUCCEEDS
        eu_nonsoil = {
            "project_id": str(bio_project_id),
            "batch_id": batch_id,
            "end_use_type": "NON_SOIL_APPLICATION",
            "applied_quantity_tonnes": 5.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "product_category": "BUILDING_PANEL",
            "recipient_organization": "Synthetic Green Panels Ltd",
        }
        res_ns = await client.post("/api/v1/biochar/end-uses", json=eu_nonsoil, headers=headers)
        assert res_ns.status_code == 201, res_ns.text


@pytest.mark.asyncio
async def test_cross_sector_spatial_polygon_overlap_conflict(db_session: AsyncSession):
    """
    Mandatory Section 48 & 49: Cross-Sector Spatial Geometry Conflict Test.
    Creates two different LandUnit records (different UUIDs):
    - Agriculture LandUnit A under VM0042
    - Biochar-linked LandUnit B under VM0044
    With overlapping polygons:
    - Expected: conflict detected with material spatial_overlap_hectares reported.
    - Non-soil end use: no conflict.
    - Non-overlapping polygon: no conflict.
    """
    await seed_agriculture_methodologies(db_session)

    res_m42 = await db_session.execute(select(Methodology).where(Methodology.code == "VM0042"))
    vm0042 = res_m42.scalars().first()
    res_m44 = await db_session.execute(select(Methodology).where(Methodology.code == "VM0044"))
    vm0044 = res_m44.scalars().first()

    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Spatial Biochar Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"spatial_officer_{uuid.uuid4().hex[:6]}@synthetic-nexus.org",
        full_name="Spatial Compliance Officer",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    # 1. Agriculture Project A under VM0042
    ag_project = Project(
        id=uuid.uuid4(),
        name="Spatial Agri Project A",
        project_code=f"AG-SPAT-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        methodology_id=vm0042.id,
        country="Kenya",
    )
    db_session.add(ag_project)

    # LandUnit A: [36.8, -1.2] to [37.0, -1.0]
    land_unit_a = LandUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=ag_project.id,
        name="Agri Parcel A (VM0042)",
        unit_type="PARCEL",
        area_ha=100.0,
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[36.8, -1.2], [37.0, -1.2], [37.0, -1.0], [36.8, -1.0], [36.8, -1.2]]],
        },
        is_active=True,
    )
    db_session.add(land_unit_a)

    # 2. Biochar Project B under VM0044
    bio_project = Project(
        id=uuid.uuid4(),
        name="Spatial Biochar Project B",
        project_code=f"BIO-SPAT-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        methodology_id=vm0044.id,
        country="Kenya",
    )
    db_session.add(bio_project)

    # LandUnit B: Different UUID, partially overlapping geometry [36.9, -1.15] to [37.1, -0.95]
    land_unit_b_overlap = LandUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=bio_project.id,
        name="Biochar Application Parcel B (Overlapping)",
        unit_type="PARCEL",
        area_ha=80.0,
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[36.9, -1.15], [37.1, -1.15], [37.1, -0.95], [36.9, -0.95], [36.9, -1.15]]],
        },
        is_active=True,
    )
    db_session.add(land_unit_b_overlap)

    # LandUnit C: Different UUID, non-overlapping geometry [38.0, 0.0] to [38.2, 0.2]
    land_unit_c_distinct = LandUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=bio_project.id,
        name="Biochar Application Parcel C (Non-overlapping)",
        unit_type="PARCEL",
        area_ha=50.0,
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[38.0, 0.0], [38.2, 0.0], [38.2, 0.2], [38.0, 0.2], [38.0, 0.0]]],
        },
        is_active=True,
    )
    db_session.add(land_unit_c_distinct)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. Evaluate Overlapping LandUnit B against VM0044
        res_overlap = await client.get(
            f"/api/v1/biochar/conflicts/land-units/{land_unit_b_overlap.id}?biochar_methodology=VM0044",
            headers=headers,
        )
        assert res_overlap.status_code == 200, res_overlap.text
        overlap_data = res_overlap.json()
        assert overlap_data["has_conflict"] is True
        assert overlap_data["conflict_code"] == "DOUBLE_COUNTING_SPATIAL_GEOMETRY_OVERLAP_SOC"
        assert overlap_data["accounting_blocked"] is True
        assert overlap_data["spatial_overlap_hectares"] > 0.0
        assert overlap_data["time_overlap_detected"] is True
        assert overlap_data["carbon_pool"] == "SOIL_ORGANIC_CARBON"

        # B. Evaluate Non-Overlapping LandUnit C against VM0044
        res_distinct = await client.get(
            f"/api/v1/biochar/conflicts/land-units/{land_unit_c_distinct.id}?biochar_methodology=VM0044",
            headers=headers,
        )
        assert res_distinct.status_code == 200, res_distinct.text
        distinct_data = res_distinct.json()
        assert distinct_data["has_conflict"] is False
        assert distinct_data["accounting_blocked"] is False
        assert distinct_data["spatial_overlap_hectares"] == 0.0

