"""
=============================================================================
VeriField Nexus — VM0047 Tree Observations & Allometrics Tests
=============================================================================
Tests:
1. Separation of raw tree field measurements (DBH, height, species, health)
   from derived biomass calculations.
2. Pantropical allometric biomass derivation using Chave et al. (2014):
   - With height measured: AGB = 0.0673 * (rho * D^2 * H)^0.976
   - Without height: AGB = exp(-1.803 + 0.976*ln(rho) + 2.673*ln(D) - 0.0299*(ln(D))^2)
   - Root-to-shoot ratio belowground biomass (BGB).
   - Total carbon stock in t CO2e.
3. Tree observation batch ingestion and persistence.
=============================================================================
"""

import uuid
from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.calculators.vm0047 import VM0047CalculatorV11
from app.domains.agriculture.geospatial import BoundarySource
from app.domains.agriculture.models import LandUnit, TreeObservation
from app.domains.agriculture.schemas import LandUnitCreate, TreeObservationBase
from app.domains.agriculture.service import AgricultureService
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


def test_chave_allometric_biomass_derivations():
    # Tree with height measured: DBH=30cm, H=15m, wood_density=0.65 g/cm3
    res_with_h = VM0047CalculatorV11.calculate_tree_biomass(
        dbh_cm=30.0,
        height_m=15.0,
        wood_density_g_cm3=0.65,
    )
    assert res_with_h["agb_kg"] > 0
    assert res_with_h["bgb_kg"] > 0
    assert res_with_h["total_biomass_kg"] == round(res_with_h["agb_kg"] + res_with_h["bgb_kg"], 2)
    assert res_with_h["carbon_stock_t_co2e"] > 0

    # Tree without height measured
    res_no_h = VM0047CalculatorV11.calculate_tree_biomass(
        dbh_cm=30.0,
        height_m=None,
        wood_density_g_cm3=0.65,
    )
    assert res_no_h["agb_kg"] > 0
    assert res_no_h["carbon_stock_t_co2e"] > 0


@pytest.mark.asyncio
async def test_tree_observation_service_lifecycle(db_session: AsyncSession):
    org = Organization(name=f"Forest Carbon Developer {uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    project = Project(
        name="Community Agroforestry Initiative",
        project_code=f"AGR-TREE-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.flush()

    # Create land unit
    unit_payload = LandUnitCreate(
        project_id=project.id,
        name="Agroforestry Plot 1",
        unit_type="MONITORING_PLOT",
        boundary_source="GNSS_SURVEY",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [
                [[77.100, 28.600], [77.105, 28.600], [77.105, 28.605], [77.100, 28.605], [77.100, 28.600]]
            ],
        },
    )
    unit = await AgricultureService.create_land_unit(db_session, unit_payload, org.id)

    # Batch create tree observations
    trees_data = [
        TreeObservationBase(
            sampling_approach="CENSUS_BASED",
            tag_number="TREE-001",
            species_scientific="Tectona grandis",
            species_common="Teak",
            dbh_cm=24.5,
            height_m=11.2,
            health_status="HEALTHY",
            measurement_date=date(2026, 6, 1),
            wood_density_g_cm3=0.58,
        ),
        TreeObservationBase(
            sampling_approach="CENSUS_BASED",
            tag_number="TREE-002",
            species_scientific="Azadirachta indica",
            species_common="Neem",
            dbh_cm=18.2,
            height_m=8.5,
            health_status="HEALTHY",
            measurement_date=date(2026, 6, 1),
            wood_density_g_cm3=0.68,
        ),
    ]

    saved_trees = await AgricultureService.batch_create_tree_observations(
        db=db_session,
        project_id=project.id,
        land_unit_id=unit.id,
        observations=trees_data,
        organization_id=org.id,
    )
    await db_session.commit()

    assert len(saved_trees) == 2
    for t in saved_trees:
        assert t.derived_aboveground_biomass_kg is not None
        assert t.derived_aboveground_biomass_kg > 0
        assert t.derived_carbon_stock_t_co2e is not None
        assert t.derived_carbon_stock_t_co2e > 0
        assert t.dbh_cm in (24.5, 18.2)  # Raw measurement intact
