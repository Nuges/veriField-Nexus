"""
=============================================================================
VeriField Nexus — VM0047 Tree Observations & Allometric Model Registry Tests
=============================================================================
Methodology: VM0047 v1.1 / BM FR05.002
Tests:
1. AllometricModelRegistry registration, lookup, metadata, and filtering by pool & methodology.
2. Strict separation of ABOVEGROUND_BIOMASS (AGB) and BELOWGROUND_BIOMASS (BGB):
   - Chave et al. (2014) pantropical AGB alone (BGB remains None, not inferred).
   - Chave et al. (2014) with height vs without height.
   - Cairns et al. (1997) root-to-shoot BGB model explicitly configured.
   - IPCC (2019 Refinement) default root-to-shoot BGB model explicitly configured.
   - IPCC (2006) / Brown (1997) tropical hardwood AGB model.
3. Validation and error handling for invalid or mismatched pool model IDs.
4. End-to-end database persistence and service lifecycle for tree observations:
   - Raw measurements intact (DBH, height, species, health, wood density).
   - Derived pools accurately calculated and stored.
=============================================================================
"""

import uuid
from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.allometrics import (
    AllometricModelDefinition,
    AllometricModelRegistry,
    BiomassPoolType,
    ModelReviewStatus,
    estimate_tree_biomass_pools,
)
from app.domains.agriculture.calculators.vm0047 import VM0047CalculatorV11
from app.domains.agriculture.geospatial import BoundarySource
from app.domains.agriculture.models import LandUnit, TreeObservation
from app.domains.agriculture.schemas import LandUnitCreate, TreeObservationBase, TreeObservationCreate
from app.domains.agriculture.service import AgricultureService
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


def test_allometric_model_registry_and_filtering():
    # 1. Verify Chave 2014 model registration
    chave = AllometricModelRegistry.get("CHAVE_2014_PANTROPICAL_AGB")
    assert chave is not None
    assert chave.pool_type == BiomassPoolType.ABOVEGROUND_BIOMASS
    assert chave.review_status == ModelReviewStatus.APPROVED
    assert "VM0047" in chave.methodology_compatibility
    assert "dbh_cm" in chave.required_inputs
    assert "wood_density_g_cm3" in chave.required_inputs

    # 2. Verify Cairns 1997 root-to-shoot model registration
    cairns = AllometricModelRegistry.get("CAIRNS_1997_ROOT_SHOOT_BGB")
    assert cairns is not None
    assert cairns.pool_type == BiomassPoolType.BELOWGROUND_BIOMASS
    assert cairns.review_status == ModelReviewStatus.APPROVED
    assert "agb_kg" in cairns.required_inputs

    # 3. Verify IPCC 2019 model registration
    ipcc2019 = AllometricModelRegistry.get("IPCC_2019_DEFAULT_ROOT_SHOOT_BGB")
    assert ipcc2019 is not None
    assert ipcc2019.pool_type == BiomassPoolType.BELOWGROUND_BIOMASS

    # 4. Verify pool type filtering
    agb_models = AllometricModelRegistry.list_models(pool_type=BiomassPoolType.ABOVEGROUND_BIOMASS)
    agb_ids = [m.model_id for m in agb_models]
    assert "CHAVE_2014_PANTROPICAL_AGB" in agb_ids
    assert "IPCC_2006_TROPICAL_HARDWOOD_AGB" in agb_ids
    assert "CAIRNS_1997_ROOT_SHOOT_BGB" not in agb_ids

    bgb_models = AllometricModelRegistry.list_models(pool_type=BiomassPoolType.BELOWGROUND_BIOMASS)
    bgb_ids = [m.model_id for m in bgb_models]
    assert "CAIRNS_1997_ROOT_SHOOT_BGB" in bgb_ids
    assert "IPCC_2019_DEFAULT_ROOT_SHOOT_BGB" in bgb_ids
    assert "CHAVE_2014_PANTROPICAL_AGB" not in bgb_ids

    # 5. Verify methodology filtering
    vm0047_models = AllometricModelRegistry.list_models(methodology="VM0047")
    vm0047_ids = [m.model_id for m in vm0047_models]
    assert "CHAVE_2014_PANTROPICAL_AGB" in vm0047_ids
    assert "CAIRNS_1997_ROOT_SHOOT_BGB" in vm0047_ids


def test_chave_allometric_biomass_derivations_strict_separation():
    # Tree with height measured: DBH=30cm, H=15m, wood_density=0.65 g/cm3
    res_with_h = VM0047CalculatorV11.calculate_tree_biomass(
        dbh_cm=30.0,
        height_m=15.0,
        wood_density_g_cm3=0.65,
    )
    # AGB is calculated
    assert res_with_h["agb_kg"] > 0
    # Strict VM0047 rule: BGB is NOT automatically inferred without an approved BGB model
    assert res_with_h["bgb_kg"] is None
    # Total biomass reflects measured pools only
    assert res_with_h["total_biomass_kg"] == res_with_h["agb_kg"]
    assert res_with_h["carbon_stock_t_co2e"] > 0
    assert res_with_h["provenance"]["bgb_model"] is None
    assert res_with_h["provenance"]["height_measured"] is True

    # Tree without height measured: uses Chave 2014 non-height equation
    res_no_h = VM0047CalculatorV11.calculate_tree_biomass(
        dbh_cm=30.0,
        height_m=None,
        wood_density_g_cm3=0.65,
    )
    assert res_no_h["agb_kg"] > 0
    assert res_no_h["bgb_kg"] is None
    assert res_no_h["carbon_stock_t_co2e"] > 0
    assert res_no_h["provenance"]["height_measured"] is False


def test_explicit_belowground_allometric_models():
    # 1. Chave 2014 AGB + Cairns 1997 BGB model
    res_cairns = VM0047CalculatorV11.calculate_tree_biomass(
        dbh_cm=28.0,
        height_m=12.0,
        wood_density_g_cm3=0.62,
        agb_model_id="CHAVE_2014_PANTROPICAL_AGB",
        bgb_model_id="CAIRNS_1997_ROOT_SHOOT_BGB",
    )
    assert res_cairns["agb_kg"] > 0
    assert res_cairns["bgb_kg"] is not None
    assert res_cairns["bgb_kg"] > 0
    assert res_cairns["total_biomass_kg"] == round(res_cairns["agb_kg"] + res_cairns["bgb_kg"], 2)
    assert res_cairns["provenance"]["bgb_model"]["model_id"] == "CAIRNS_1997_ROOT_SHOOT_BGB"

    # 2. Chave 2014 AGB + IPCC 2019 Refinement Default BGB model
    res_ipcc = VM0047CalculatorV11.calculate_tree_biomass(
        dbh_cm=28.0,
        height_m=12.0,
        wood_density_g_cm3=0.62,
        agb_model_id="CHAVE_2014_PANTROPICAL_AGB",
        bgb_model_id="IPCC_2019_DEFAULT_ROOT_SHOOT_BGB",
    )
    assert res_ipcc["agb_kg"] > 0
    assert res_ipcc["bgb_kg"] is not None
    # IPCC default ratio is 0.235
    assert res_ipcc["bgb_kg"] == round(res_ipcc["agb_kg"] * 0.235, 2)
    assert res_ipcc["provenance"]["bgb_model"]["model_id"] == "IPCC_2019_DEFAULT_ROOT_SHOOT_BGB"


def test_ipcc_2006_tropical_hardwood_agb():
    res = estimate_tree_biomass_pools(
        dbh_cm=25.0,
        agb_model_id="IPCC_2006_TROPICAL_HARDWOOD_AGB",
    )
    assert res["agb_kg"] > 0
    assert res["bgb_kg"] is None
    assert res["provenance"]["agb_model"]["model_id"] == "IPCC_2006_TROPICAL_HARDWOOD_AGB"


def test_allometric_model_pool_mismatch_and_invalid_ids():
    # Unknown AGB model
    with pytest.raises(ValueError, match="Invalid or unapproved AGB allometric model"):
        estimate_tree_biomass_pools(dbh_cm=20.0, agb_model_id="UNKNOWN_AGB_MODEL")

    # BGB model passed as AGB model
    with pytest.raises(ValueError, match="Invalid or unapproved AGB allometric model"):
        estimate_tree_biomass_pools(dbh_cm=20.0, agb_model_id="CAIRNS_1997_ROOT_SHOOT_BGB")

    # Unknown BGB model
    with pytest.raises(ValueError, match="Invalid or unapproved BGB allometric model"):
        estimate_tree_biomass_pools(
            dbh_cm=20.0,
            agb_model_id="CHAVE_2014_PANTROPICAL_AGB",
            bgb_model_id="UNKNOWN_BGB_MODEL",
        )

    # AGB model passed as BGB model
    with pytest.raises(ValueError, match="Invalid or unapproved BGB allometric model"):
        estimate_tree_biomass_pools(
            dbh_cm=20.0,
            agb_model_id="CHAVE_2014_PANTROPICAL_AGB",
            bgb_model_id="CHAVE_2014_PANTROPICAL_AGB",
        )


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

    # Batch create tree observations (one with AGB only, one with explicit BGB model)
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
            allometric_model_id="CHAVE_2014_PANTROPICAL_AGB",
            # belowground_model_id not set -> BGB remains None
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
            allometric_model_id="CHAVE_2014_PANTROPICAL_AGB",
            belowground_model_id="CAIRNS_1997_ROOT_SHOOT_BGB",
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

    # Tree 1: AGB only
    t1 = next(t for t in saved_trees if t.tag_number == "TREE-001")
    assert t1.derived_aboveground_biomass_kg is not None
    assert t1.derived_aboveground_biomass_kg > 0
    assert t1.derived_belowground_biomass_kg is None  # Strict VM0047 separation
    assert t1.derived_carbon_stock_t_co2e is not None
    assert t1.derived_carbon_stock_t_co2e > 0
    assert t1.dbh_cm == 24.5  # Raw measurement intact

    # Tree 2: AGB + Cairns 1997 BGB
    t2 = next(t for t in saved_trees if t.tag_number == "TREE-002")
    assert t2.derived_aboveground_biomass_kg is not None
    assert t2.derived_aboveground_biomass_kg > 0
    assert t2.derived_belowground_biomass_kg is not None
    assert t2.derived_belowground_biomass_kg > 0
    assert t2.derived_carbon_stock_t_co2e is not None
    assert t2.derived_carbon_stock_t_co2e > 0
    assert t2.belowground_model_id == "CAIRNS_1997_ROOT_SHOOT_BGB"
    assert t2.dbh_cm == 18.2  # Raw measurement intact
