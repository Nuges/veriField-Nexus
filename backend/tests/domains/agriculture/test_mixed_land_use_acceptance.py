"""
=============================================================================
VeriField Nexus — Generic Mixed Land Use Acceptance Scenario
=============================================================================
Demonstrates end-to-end multi-management unit segregation and MRV screening:
- Scenario: mixed_land_use_acceptance_scenario
- Unit A: Established Cropland -> VM0042 Screening
- Unit B: Eligible Tree Planting -> VM0047 / BM FR05.002 Screening
- Unit C: Irrigated Paddy Rice -> VM0051 / BM AG04.002 Screening
- Unit D: Undetermined Land Cover -> Expert Review Flagged

Strict invariant: 100% generic synthetic test fixtures, zero client names.
=============================================================================
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.calculators import (
    VM0042CalculatorV22,
    VM0047CalculatorV11,
    VM0051CalculatorV11,
)
from app.domains.agriculture.geospatial import BoundarySource
from app.domains.agriculture.models import LandUnit, SoilSample, TreeObservation
from app.domains.agriculture.schemas import (
    LandUnitCreate,
    SoilSampleCreate,
    TreeObservationBase,
)
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.agriculture.service import AgricultureService
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


@pytest.mark.asyncio
async def test_mixed_land_use_acceptance_scenario(db_session: AsyncSession):
    """
    Executes the multi-management-unit acceptance scenario verifying
    clean domain segregation across diverse agricultural activities.
    """
    await seed_agriculture_methodologies(db_session)

    # 1. Organization & Project Setup
    org = Organization(name=f"Synthetic Agro-Ecological Systems {uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    project = Project(
        name="mixed_land_use_acceptance_scenario",
        project_code=f"AGR-MIXED-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        country="India",
        baseline_parameters={
            "locked_methodology_version": {
                "methodology_code": "VM0042",
                "version": "2.2",
                "status": "LOCKED",
            }
        },
    )
    db_session.add(project)
    await db_session.flush()

    # 2. Management Unit A: Established Cropland (VM0042)
    unit_a_payload = LandUnitCreate(
        project_id=project.id,
        name="Management Unit A - Cropland",
        code="MU-A-CROP",
        unit_type="FIELD",
        boundary_source="RTK_GNSS",
        land_use_category="CROPLAND",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [
                [[77.10, 28.50], [77.12, 28.50], [77.12, 28.52], [77.10, 28.52], [77.10, 28.50]]
            ],
        },
    )
    unit_a = await AgricultureService.create_land_unit(db_session, unit_a_payload, org.id)
    assert unit_a.area_ha > 0

    # Soil core sample in Unit A meeting VM0042 30 cm depth rule
    sample_a_payload = SoilSampleCreate(
        project_id=project.id,
        land_unit_id=unit_a.id,
        sample_code="SOIL-MU-A-01",
        sampling_date=date(2026, 5, 10),
        latitude=28.51,
        longitude=77.11,
        depth_upper_cm=0.0,
        depth_lower_cm=30.0,
        bulk_density_g_cm3=1.35,
        soc_stock_pct=1.42,
        lab_method="DRY_COMBUSTION",
        lab_name="Accredited Agronomy Laboratory",
        lab_accreditation="ISO_17025",
    )
    sample_a = await AgricultureService.create_soil_sample(db_session, sample_a_payload, org.id)
    assert sample_a.compliance_classification == "EX_POST_QUANTIFICATION_ELIGIBLE"
    assert sample_a.computed_soc_stock_t_c_ha is not None

    # 3. Management Unit B: Eligible Tree Planting (VM0047 / BM FR05.002)
    unit_b_payload = LandUnitCreate(
        project_id=project.id,
        name="Management Unit B - Agroforestry & Trees",
        code="MU-B-TREE",
        unit_type="FIELD",
        boundary_source="GNSS_SURVEY",
        land_use_category="AGROFORESTRY",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [
                [[77.13, 28.50], [77.15, 28.50], [77.15, 28.52], [77.13, 28.52], [77.13, 28.50]]
            ],
        },
    )
    unit_b = await AgricultureService.create_land_unit(db_session, unit_b_payload, org.id)

    # Ingest tree observations for Unit B
    trees_b = [
        TreeObservationBase(
            sampling_approach="AREA_BASED",
            tag_number="PLOT-B-T01",
            species_scientific="Dalbergia sissoo",
            species_common="Shisham",
            dbh_cm=22.0,
            height_m=10.5,
            health_status="HEALTHY",
            measurement_date=date(2026, 5, 15),
            wood_density_g_cm3=0.68,
        )
    ]
    saved_trees_b = await AgricultureService.batch_create_tree_observations(
        db=db_session,
        project_id=project.id,
        land_unit_id=unit_b.id,
        observations=trees_b,
        organization_id=org.id,
    )
    assert len(saved_trees_b) == 1
    assert saved_trees_b[0].derived_carbon_stock_t_co2e > 0

    # 4. Management Unit C: Irrigated Rice Cultivation (VM0051 / BM AG04.002)
    unit_c_payload = LandUnitCreate(
        project_id=project.id,
        name="Management Unit C - Irrigated Rice Paddy",
        code="MU-C-RICE",
        unit_type="FIELD",
        boundary_source="CADASTRAL",
        land_use_category="PADDY_RICE",
        properties={"water_regime": "ALTERNATE_WETTING_AND_DRYING", "drainage_days": 14},
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [
                [[77.16, 28.50], [77.18, 28.50], [77.18, 28.52], [77.16, 28.52], [77.16, 28.50]]
            ],
        },
    )
    unit_c = await AgricultureService.create_land_unit(db_session, unit_c_payload, org.id)
    assert unit_c.land_use_category == "PADDY_RICE"

    # 5. Management Unit D: Undetermined Land Cover (Requires Review)
    unit_d_payload = LandUnitCreate(
        project_id=project.id,
        name="Management Unit D - Undetermined Transitional Buffer",
        code="MU-D-REVIEW",
        unit_type="STRATUM",
        boundary_source="MANUALLY_DRAWN",
        land_use_category="FALLOW",
        properties={"expert_review_required": True, "reason": "Mixed vegetative canopy pending ground truth"},
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [
                [[77.19, 28.50], [77.20, 28.50], [77.20, 28.52], [77.19, 28.52], [77.19, 28.50]]
            ],
        },
    )
    unit_d = await AgricultureService.create_land_unit(db_session, unit_d_payload, org.id)
    assert unit_d.properties.get("expert_review_required") is True

    await db_session.commit()

    # 6. Verify Complete Segregation Across All 4 Units
    units = await AgricultureService.get_land_units(db_session, org.id, project_id=project.id)
    assert len(units) == 4
    categories = {u.code: u.land_use_category for u in units}
    assert categories["MU-A-CROP"] == "CROPLAND"
    assert categories["MU-B-TREE"] == "AGROFORESTRY"
    assert categories["MU-C-RICE"] == "PADDY_RICE"
    assert categories["MU-D-REVIEW"] == "FALLOW"

    # Verify fail-closed screening for Unit A (VM0042)
    calc42 = VM0042CalculatorV22()
    res42 = calc42.calculate_project_credits({"id": str(project.id)}, {})
    assert res42.status.value == "NOT_CONFIGURED"

    # Verify fail-closed screening for Unit B (VM0047)
    calc47 = VM0047CalculatorV11()
    res47 = calc47.calculate_project_credits({"id": str(project.id)}, {})
    assert res47.status.value == "NOT_CONFIGURED"

    # Verify fail-closed screening for Unit C (VM0051)
    calc51 = VM0051CalculatorV11()
    res51 = calc51.calculate_project_credits({"id": str(project.id)}, {})
    assert res51.status.value == "NOT_CONFIGURED"
