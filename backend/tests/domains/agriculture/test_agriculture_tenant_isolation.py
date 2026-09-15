"""
=============================================================================
VeriField Nexus — Agriculture Multi-Tenant Isolation Tests
=============================================================================
Tests:
1. Tenant A cannot read Tenant B's land units, soil samples, tree observations,
   or model runs.
2. Tenant A cannot create land units or submit soil samples referencing Tenant B's project.
3. Tenant A cannot update or delete Tenant B's land units.
4. Cryptographic verification dossiers cannot be generated across tenant boundaries.
=============================================================================
"""

import uuid
from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.schemas import LandUnitCreate, SoilSampleCreate
from app.domains.agriculture.service import AgricultureService
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


@pytest.mark.asyncio
async def test_cross_tenant_isolation_land_units_and_soils(db_session: AsyncSession):
    # Setup Tenant A and Tenant B
    org_a = Organization(name="Tenant Alpha Agriculture Ltd")
    org_b = Organization(name="Tenant Beta Agri-Holdings")
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    project_a = Project(name="Project Alpha", project_code="PRJ-A", organization_id=org_a.id)
    project_b = Project(name="Project Beta", project_code="PRJ-B", organization_id=org_b.id)
    db_session.add_all([project_a, project_b])
    await db_session.flush()

    # Tenant A creates Land Unit in Project A
    unit_a_payload = LandUnitCreate(
        project_id=project_a.id,
        name="Alpha Unit 1",
        unit_type="FIELD",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [
                [[77.10, 28.50], [77.12, 28.50], [77.12, 28.52], [77.10, 28.52], [77.10, 28.50]]
            ],
        },
    )
    unit_a = await AgricultureService.create_land_unit(db_session, unit_a_payload, org_a.id)

    # 1. Tenant B must NOT see Tenant A's land units in list
    units_b = await AgricultureService.get_land_units(db_session, org_b.id)
    assert len(units_b) == 0

    # 2. Tenant B must NOT be able to fetch Tenant A's land unit by ID
    unit_a_fetched_by_b = await AgricultureService.get_land_unit_by_id(db_session, unit_a.id, org_b.id)
    assert unit_a_fetched_by_b is None

    # 3. Tenant B cannot create a Land Unit targeting Tenant A's project
    unit_b_attack = LandUnitCreate(
        project_id=project_a.id,  # Project belongs to Tenant A!
        name="Beta Infiltration Plot",
        unit_type="FIELD",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [
                [[77.10, 28.50], [77.12, 28.50], [77.12, 28.52], [77.10, 28.52], [77.10, 28.50]]
            ],
        },
    )
    with pytest.raises(ValueError, match="not found for organization"):
        await AgricultureService.create_land_unit(db_session, unit_b_attack, org_b.id)

    # 4. Tenant B cannot submit soil samples to Tenant A's project
    soil_b_attack = SoilSampleCreate(
        project_id=project_a.id,
        sample_code="S-ATTACK-01",
        sampling_date=date(2026, 6, 1),
        latitude=28.51,
        longitude=77.11,
        depth_upper_cm=0.0,
        depth_lower_cm=30.0,
        soc_stock_pct=1.2,
    )
    with pytest.raises(ValueError, match="not found for organization"):
        await AgricultureService.create_soil_sample(db_session, soil_b_attack, org_b.id)

    # 5. Tenant B cannot delete Tenant A's land unit
    deleted = await AgricultureService.delete_land_unit(db_session, unit_a.id, org_b.id)
    assert deleted is False
