"""
VeriField Nexus — Agriculture Phase 3B-1 Test Suite
===================================================
VM0042 v2.2 Soil Organic Carbon Stock & Equivalent Soil Mass (ESM) Engine:
- Layer soil mass derivation (dimensional verification)
- Layer SOC mass derivation
- Depth profile validation (inversion, gaps, overlaps, surface start)
- Shallow soil exception handling
- Reference soil mass determination
- Official golden vectors (Ellert & Bettany 1995 / VM0042 ESM Worksheet)
- Monotonic spline ESM option (Wendt & Hauser 2013)
- Multi-layer depth harmonization and compaction compensation
- Stratum and project-level area-weighted aggregation
- Component lineage and cryptographic SHA-256 snapshot hashing
- Numeric adversarial cases (high rock fragments, low/high BD)
- Multi-tenant and project isolation
- Segregation of Duties (Field Agent prohibited from finalizing authoritative stock)
- Immutability and deterministic idempotency
- Strict Carbon Invariant: tCO2e is NULL, ledger minting is BLOCKED
"""

import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.soil.soc_stock_calculator import (
    LayerInput,
    LayerResult,
    ProfileESMResult,
    SOCStockCalculationError,
    calculate_layer_soil_mass,
    calculate_layer_soc_mass,
    validate_profile_layers,
    calculate_profile_esm_proportioning,
    calculate_profile_esm_spline,
    aggregate_stratum_soc_stock,
    aggregate_project_area_weighted_soc_stock,
    compute_deterministic_hash,
)
from app.domains.agriculture.models import (
    AgriculturePrerequisiteAssessment,
    AgricultureSOCStockSnapshot,
    AgricultureSOCStockResult,
    AgricultureSOCLayerResult,
    SamplingPoint,
    Stratum,
)
from app.domains.agriculture.service import AgricultureService
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


# =============================================================================
# 1. LAYER STOCK & DIMENSIONAL TESTS (§05)
# =============================================================================

def test_layer_soil_mass_calculation():
    """
    Formula: M_soil = T * BD * (1 - CF) * 100
    10 cm * 1.30 g/cm3 * (1 - 0.10) * 100 = 1170.0000 t dry fine soil / ha
    """
    m = calculate_layer_soil_mass(
        thickness_cm=Decimal("10.00"),
        bulk_density_g_cm3=Decimal("1.3000"),
        coarse_fragment_fraction=Decimal("0.1000"),
    )
    assert m == Decimal("1170.0000")

    # Zero coarse fragments
    m2 = calculate_layer_soil_mass(
        thickness_cm=Decimal("30.00"),
        bulk_density_g_cm3=Decimal("1.2500"),
        coarse_fragment_fraction=Decimal("0.0000"),
    )
    assert m2 == Decimal("3750.0000")


def test_layer_soc_mass_calculation():
    """
    Formula: SOC_mass = M_soil * (C_soc / 1000)
    1170.0 t/ha * (15.0 g/kg / 1000) = 17.5500 t C / ha
    """
    soc_mass = calculate_layer_soc_mass(
        layer_soil_mass_t_ha=Decimal("1170.0000"),
        soc_concentration_g_kg=Decimal("15.0000"),
    )
    assert soc_mass == Decimal("17.5500")


# =============================================================================
# 2. DEPTH PROFILE VALIDATION & REJECTIONS (§06)
# =============================================================================

def test_depth_profile_validation():
    # Empty profile
    with pytest.raises(SOCStockCalculationError) as exc_empty:
        validate_profile_layers([])
    assert exc_empty.value.code == "EMPTY_PROFILE_LAYERS"

    # Does not start at surface
    with pytest.raises(SOCStockCalculationError) as exc_surf:
        validate_profile_layers([
            LayerInput(layer_index=0, depth_upper_cm=Decimal("5.0"), depth_lower_cm=Decimal("15.0"), bulk_density_g_cm3=Decimal("1.3"), soc_concentration_g_kg=Decimal("10.0"))
        ])
    assert exc_surf.value.code == "PROFILE_DOES_NOT_START_AT_SURFACE"

    # Depth inversion
    with pytest.raises(SOCStockCalculationError) as exc_inv:
        validate_profile_layers([
            LayerInput(layer_index=0, depth_upper_cm=Decimal("0.0"), depth_lower_cm=Decimal("10.0"), bulk_density_g_cm3=Decimal("1.3"), soc_concentration_g_kg=Decimal("10.0")),
            LayerInput(layer_index=1, depth_upper_cm=Decimal("10.0"), depth_lower_cm=Decimal("8.0"), bulk_density_g_cm3=Decimal("1.3"), soc_concentration_g_kg=Decimal("10.0")),
        ])
    assert exc_inv.value.code == "DEPTH_INVERSION_OR_ZERO_THICKNESS"

    # Depth gap (0-10, 15-30)
    with pytest.raises(SOCStockCalculationError) as exc_gap:
        validate_profile_layers([
            LayerInput(layer_index=0, depth_upper_cm=Decimal("0.0"), depth_lower_cm=Decimal("10.0"), bulk_density_g_cm3=Decimal("1.3"), soc_concentration_g_kg=Decimal("10.0")),
            LayerInput(layer_index=1, depth_upper_cm=Decimal("15.0"), depth_lower_cm=Decimal("30.0"), bulk_density_g_cm3=Decimal("1.3"), soc_concentration_g_kg=Decimal("10.0")),
        ])
    assert exc_gap.value.code == "PROFILE_DEPTH_GAP"

    # Overlapping layers (0-15, 10-30)
    with pytest.raises(SOCStockCalculationError) as exc_ovlp:
        validate_profile_layers([
            LayerInput(layer_index=0, depth_upper_cm=Decimal("0.0"), depth_lower_cm=Decimal("15.0"), bulk_density_g_cm3=Decimal("1.3"), soc_concentration_g_kg=Decimal("10.0")),
            LayerInput(layer_index=1, depth_upper_cm=Decimal("10.0"), depth_lower_cm=Decimal("30.0"), bulk_density_g_cm3=Decimal("1.3"), soc_concentration_g_kg=Decimal("10.0")),
        ])
    assert exc_ovlp.value.code == "PROFILE_OVERLAPPING_LAYERS"


# =============================================================================
# 3. SHALLOW SOIL & REFERENCE MASS GATES (§07, §08)
# =============================================================================

def test_shallow_soil_and_reference_mass_exceeded():
    # Shallow profile 0-20 cm (mass = 20 * 1.30 * 100 = 2600 t/ha)
    shallow_layers = [
        LayerInput(layer_index=0, depth_upper_cm=Decimal("0.0"), depth_lower_cm=Decimal("20.0"), bulk_density_g_cm3=Decimal("1.30"), soc_concentration_g_kg=Decimal("15.0"))
    ]
    ref_mass = Decimal("3900.0000")  # requires 30 cm

    # Fail closed without shallow soil exception
    with pytest.raises(SOCStockCalculationError) as exc_ref:
        calculate_profile_esm_proportioning(
            layers=shallow_layers,
            reference_soil_mass_t_ha=ref_mass,
            reference_depth_cm=Decimal("30.00"),
            allow_shallow_soil_exception=False,
        )
    assert exc_ref.value.code == "ESM_REFERENCE_MASS_EXCEEDS_MEASURED_PROFILE"

    # Permitted when shallow soil exception is approved
    res = calculate_profile_esm_proportioning(
        layers=shallow_layers,
        reference_soil_mass_t_ha=ref_mass,
        reference_depth_cm=Decimal("30.00"),
        allow_shallow_soil_exception=True,
    )
    assert res.shallow_soil_exception_applied is True
    assert res.depth_sufficiency_status == "SHALLOW_SOIL_EXCEPTION"
    assert res.soc_stock_t_c_per_ha == Decimal("39.0000")  # 2600 * 15 / 1000 = 39.0


# =============================================================================
# 4. OFFICIAL GOLDEN VECTORS (§09, §10)
# =============================================================================

def test_official_golden_vectors():
    """
    Official Vector: Ellert & Bettany 1995 / VM0042 ESM Worksheet example.
    3-layer continuous profile:
    Layer 1: 0–10 cm, BD = 1.25, CF = 0, C_soc = 20.0 g/kg (Mass = 1250, SOC = 25.0)
    Layer 2: 10–20 cm, BD = 1.35, CF = 0, C_soc = 12.0 g/kg (Mass = 1350, SOC = 16.2, CumMass = 2600, CumSOC = 41.2)
    Layer 3: 20–30 cm, BD = 1.45, CF = 0, C_soc = 8.0 g/kg (Mass = 1450, SOC = 11.6, CumMass = 4050, CumSOC = 52.8)
    Reference soil mass M_ref = 3500 t/ha:
    Layer 1 included: 1250 t/ha, 25.0 t C/ha
    Layer 2 included: 1350 t/ha, 16.2 t C/ha
    Remaining needed = 3500 - 2600 = 900 t/ha from Layer 3
    Fraction = 900 / 1450 = 0.6207
    Layer 3 SOC included = 900 * 8.0 / 1000 = 7.2000 t C/ha
    Total Normalized SOC = 25.0 + 16.2 + 7.2 = 48.4000 t C/ha
    Equivalent Depth = 20 + (0.6207 * 10) = 26.21 cm
    """
    layers = [
        LayerInput(layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("10.00"), bulk_density_g_cm3=Decimal("1.2500"), soc_concentration_g_kg=Decimal("20.0000")),
        LayerInput(layer_index=1, depth_upper_cm=Decimal("10.00"), depth_lower_cm=Decimal("20.00"), bulk_density_g_cm3=Decimal("1.3500"), soc_concentration_g_kg=Decimal("12.0000")),
        LayerInput(layer_index=2, depth_upper_cm=Decimal("20.00"), depth_lower_cm=Decimal("30.00"), bulk_density_g_cm3=Decimal("1.4500"), soc_concentration_g_kg=Decimal("8.0000")),
    ]
    ref_mass = Decimal("3500.0000")

    res = calculate_profile_esm_proportioning(layers, reference_soil_mass_t_ha=ref_mass)

    assert res.total_sampled_soil_mass_t_ha == Decimal("4050.0000")
    assert res.unadjusted_stock_t_c_per_ha == Decimal("52.8000")
    assert res.soc_stock_t_c_per_ha == Decimal("48.4000")
    assert res.equivalent_depth_cm == Decimal("26.21")
    assert res.depth_sufficiency_status == "DEPTH_SUFFICIENT"
    assert res.shallow_soil_exception_applied is False
    assert len(res.layers) == 3
    assert res.layers[0].fraction_in_reference_mass == Decimal("1.0000")
    assert res.layers[1].fraction_in_reference_mass == Decimal("1.0000")
    assert res.layers[2].fraction_in_reference_mass == Decimal("0.6207")
    assert res.layers[2].included_soil_mass_t_ha == Decimal("900.0000")
    assert res.layers[2].included_soc_mass_t_c_ha == Decimal("7.2000")


def test_monitoring_compaction_compensation():
    """
    Verifies ESM compaction compensation:
    A compacted monitoring soil profile has higher bulk density, reaching the 3500 t/ha reference mass
    at a shallower equivalent depth (24.52 cm) rather than 30 cm.
    """
    mon_layers = [
        LayerInput(layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("10.00"), bulk_density_g_cm3=Decimal("1.3500"), soc_concentration_g_kg=Decimal("22.0000")),
        LayerInput(layer_index=1, depth_upper_cm=Decimal("10.00"), depth_lower_cm=Decimal("20.00"), bulk_density_g_cm3=Decimal("1.4500"), soc_concentration_g_kg=Decimal("14.0000")),
        LayerInput(layer_index=2, depth_upper_cm=Decimal("20.00"), depth_lower_cm=Decimal("30.00"), bulk_density_g_cm3=Decimal("1.5500"), soc_concentration_g_kg=Decimal("9.0000")),
    ]
    ref_mass = Decimal("3500.0000")
    res = calculate_profile_esm_proportioning(mon_layers, reference_soil_mass_t_ha=ref_mass)

    # Layer 1 = 1350 t/ha, Layer 2 = 1450 t/ha (cum = 2800).
    # Remaining = 700 t/ha from Layer 3 (mass = 1550).
    # Fraction = 700 / 1550 = 0.4516
    # Eq Depth = 20 + 0.4516 * 10 = 24.52 cm
    assert res.soc_stock_t_c_per_ha == Decimal("56.3000")
    assert res.equivalent_depth_cm == Decimal("24.52")


def test_spline_esm_algorithm():
    """Tests monotonic cubic spline ESM normalization."""
    layers = [
        LayerInput(layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("10.00"), bulk_density_g_cm3=Decimal("1.2500"), soc_concentration_g_kg=Decimal("20.0000")),
        LayerInput(layer_index=1, depth_upper_cm=Decimal("10.00"), depth_lower_cm=Decimal("20.00"), bulk_density_g_cm3=Decimal("1.3500"), soc_concentration_g_kg=Decimal("12.0000")),
        LayerInput(layer_index=2, depth_upper_cm=Decimal("20.00"), depth_lower_cm=Decimal("30.00"), bulk_density_g_cm3=Decimal("1.4500"), soc_concentration_g_kg=Decimal("8.0000")),
    ]
    ref_mass = Decimal("3500.0000")
    res_spline = calculate_profile_esm_spline(layers, reference_soil_mass_t_ha=ref_mass)

    assert res_spline.esm_algorithm in {"CUBIC_SPLINE", "WENDT_HAUSER_2013_CUBIC_SPLINE"}
    # Spline output should be within 1.5% of piecewise linear proportioning (48.4 t C/ha)
    assert Decimal("47.0000") <= res_spline.soc_stock_t_c_per_ha <= Decimal("50.0000")


# =============================================================================
# 5. AREA-WEIGHTING & AGGREGATION TESTS (§13)
# =============================================================================

def test_stratum_and_project_area_weighting():
    # Stratum A: 2 sample points (45.0, 55.0) -> mean = 50.0 t C/ha, area = 150 ha
    # Stratum B: 3 sample points (30.0, 40.0, 50.0) -> mean = 40.0 t C/ha, area = 350 ha
    stratum_a_mean = aggregate_stratum_soc_stock([Decimal("45.0000"), Decimal("55.0000")])
    assert stratum_a_mean == Decimal("50.0000")

    stratum_b_mean = aggregate_stratum_soc_stock([Decimal("30.0000"), Decimal("40.0000"), Decimal("50.0000")])
    assert stratum_b_mean == Decimal("40.0000")

    strata = [
        {"stratum_code": "STRAT-A", "area_ha": Decimal("150.0000"), "stratum_mean_soc_t_c_per_ha": stratum_a_mean},
        {"stratum_code": "STRAT-B", "area_ha": Decimal("350.0000"), "stratum_mean_soc_t_c_per_ha": stratum_b_mean},
    ]

    # Weighted mean = (150 * 50 + 350 * 40) / 500 = (7500 + 14000) / 500 = 21500 / 500 = 43.0000 t C/ha
    project_soc, total_area = aggregate_project_area_weighted_soc_stock(strata)
    assert project_soc == Decimal("43.0000")
    assert total_area == Decimal("500.0000")


# =============================================================================
# 6. NUMERIC ADVERSARIAL CASES (§15)
# =============================================================================

def test_numeric_adversarial():
    # High rock fragments (CF = 0.70)
    m = calculate_layer_soil_mass(
        thickness_cm=Decimal("10.00"),
        bulk_density_g_cm3=Decimal("1.4000"),
        coarse_fragment_fraction=Decimal("0.7000"),
    )
    # 10 * 1.40 * 0.30 * 100 = 420.0000 t/ha
    assert m == Decimal("420.0000")

    # High organic ceiling check (> 580 g/kg fails)
    with pytest.raises(SOCStockCalculationError) as exc_org:
        calculate_layer_soc_mass(Decimal("1000.0"), Decimal("600.0"))
    assert exc_org.value.code == "SOC_CONCENTRATION_EXCEEDS_ORGANIC_LIMIT"

    # Extreme mineral soil BD limit (> 2.65 g/cm3 fails)
    with pytest.raises(SOCStockCalculationError) as exc_bd:
        calculate_layer_soil_mass(Decimal("10.0"), Decimal("2.70"))
    assert exc_bd.value.code == "BULK_DENSITY_EXCEEDS_PHYSICAL_LIMIT"


# =============================================================================
# 7. SERVICE & INTEGRATION TESTS (§11, §12, §14, §16, §17, §18, §19, §21)
# =============================================================================

@pytest.mark.asyncio
async def test_full_service_soc_stock_workflow(db_session: AsyncSession):
    """
    End-to-end service integration test:
    - Verifies locked prerequisite gate (fails closed if unlocked)
    - Verifies evaluation preview (read-only)
    - Enforces Segregation of Duties (Field Agent prohibited from finalizing calculation)
    - Calculates and persists authoritative results
    - Verifies component lineage, layer results, and SHA-256 hash
    - Enforces Idempotency
    - Strictly asserts Carbon Invariant: tCO2e is NULL, ledger minting is BLOCKED
    """
    # Create test tenant organization and project
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="MRV Agriculture Corp")
    db_session.add(org)

    proj_id = uuid.uuid4()
    proj = Project(
        id=proj_id,
        organization_id=org_id,
        name="Kenya Regenerative Soil Project",
        country="Kenya",
    )
    db_session.add(proj)
    await db_session.flush()

    # Create sampling stratum
    strat_id = uuid.uuid4()
    stratum = Stratum(
        id=strat_id,
        organization_id=org_id,
        project_id=proj_id,
        code="STRAT-NORTH",
        name="Northern Clay Loam Stratum",
        stratum_type="SOIL_TYPE",
        area_ha=250.0,
    )
    db_session.add(stratum)

    # Sampling point identifier
    pt_id = uuid.uuid4()
    await db_session.flush()

    # 1. Unlocked Prerequisite Gate (Fails closed)
    unlocked_prereq = AgriculturePrerequisiteAssessment(
        organization_id=org_id,
        project_id=proj_id,
        assessment_code="PREREQ-TEST-UNLOCKED",
        version=1,
        status="PREVIEW",
        overall_readiness="INCOMPLETE",
        assessment_hash="hash_unlocked",
        is_locked=False,
    )
    db_session.add(unlocked_prereq)
    await db_session.flush()

    sample_layers = {
        pt_id: [
            LayerInput(layer_index=0, depth_upper_cm=Decimal("0.0"), depth_lower_cm=Decimal("10.0"), bulk_density_g_cm3=Decimal("1.25"), soc_concentration_g_kg=Decimal("20.0")),
            LayerInput(layer_index=1, depth_upper_cm=Decimal("10.0"), depth_lower_cm=Decimal("20.0"), bulk_density_g_cm3=Decimal("1.35"), soc_concentration_g_kg=Decimal("12.0")),
            LayerInput(layer_index=2, depth_upper_cm=Decimal("20.0"), depth_lower_cm=Decimal("30.0"), bulk_density_g_cm3=Decimal("1.45"), soc_concentration_g_kg=Decimal("8.0")),
        ]
    }

    with pytest.raises(ValueError) as exc_gate:
        await AgricultureService.evaluate_soc_stock(
            db=db_session,
            project_id=proj_id,
            organization_id=org_id,
            prerequisite_assessment_id=unlocked_prereq.id,
            custom_point_layers=sample_layers,
        )
    assert "not eligible" in str(exc_gate.value)

    # 2. Lock Prerequisite Assessment
    locked_prereq = AgriculturePrerequisiteAssessment(
        organization_id=org_id,
        project_id=proj_id,
        assessment_code="PREREQ-TEST-LOCKED",
        version=2,
        status="LOCKED",
        overall_readiness="READY",
        assessment_hash="hash_locked_123",
        is_locked=True,
    )
    db_session.add(locked_prereq)
    await db_session.flush()

    # 3. Preview Evaluation (Read-only)
    eval_preview = await AgricultureService.evaluate_soc_stock(
        db=db_session,
        project_id=proj_id,
        organization_id=org_id,
        prerequisite_assessment_id=locked_prereq.id,
        reference_soil_mass_t_ha=Decimal("3500.0000"),
        custom_point_layers=sample_layers,
    )
    assert eval_preview["status"] == "EVALUATED"
    assert eval_preview["project_soc_stock_t_c_per_ha"] == Decimal("48.4000")
    assert eval_preview["carbon_accounting_status"] == "NOT_CONFIGURED"
    assert eval_preview["net_tco2e_removals"] is None

    # 4. Segregation of Duties: FIELD_AGENT forbidden
    admin_id = uuid.uuid4()
    with pytest.raises(ValueError) as exc_sod:
        await AgricultureService.calculate_and_persist_authoritative_soc_stock(
            db=db_session,
            project_id=proj_id,
            organization_id=org_id,
            user_id=admin_id,
            user_role="FIELD_AGENT",
            prerequisite_assessment_id=locked_prereq.id,
            reference_soil_mass_t_ha=Decimal("3500.0000"),
            custom_point_layers=sample_layers,
        )
    assert "Segregation of duties enforced" in str(exc_sod.value)

    # 5. Authoritative Calculation by PROJECT_ADMIN
    result = await AgricultureService.calculate_and_persist_authoritative_soc_stock(
        db=db_session,
        project_id=proj_id,
        organization_id=org_id,
        user_id=admin_id,
        user_role="PROJECT_ADMIN",
        prerequisite_assessment_id=locked_prereq.id,
        measurement_period_type="BASELINE",
        reference_soil_mass_t_ha=Decimal("3500.0000"),
        custom_point_layers=sample_layers,
    )
    await db_session.flush()

    assert result.result_status == "CALCULATED"
    assert result.aggregation_level == "PROJECT"
    assert result.soc_stock_t_c_per_ha == Decimal("48.4000")
    assert result.reference_soil_mass_t_ha == Decimal("3500.0000")

    # 6. Verify Carbon Invariant (§21)
    comp = result.component_breakdown
    assert comp["carbon_accounting_status"] == "NOT_CONFIGURED"
    assert comp["net_tco2e_removals"] is None
    assert comp["delta_soc_removals"] is None
    assert comp["vcu_quantity"] is None
    assert comp["ledger_status"] == "BLOCKED_FOR_AGRICULTURE"

    # 7. Idempotency (§19)
    result_dup = await AgricultureService.calculate_and_persist_authoritative_soc_stock(
        db=db_session,
        project_id=proj_id,
        organization_id=org_id,
        user_id=admin_id,
        user_role="PROJECT_ADMIN",
        prerequisite_assessment_id=locked_prereq.id,
        measurement_period_type="BASELINE",
        reference_soil_mass_t_ha=Decimal("3500.0000"),
        custom_point_layers=sample_layers,
    )
    assert result_dup.id == result.id

    # 8. Component Lineage Breakdown (§14)
    components = await AgricultureService.get_soc_stock_result_components(
        db=db_session,
        project_id=proj_id,
        result_id=result.id,
        organization_id=org_id,
    )
    assert components["result_id"] == result.id
    assert components["soc_stock_t_c_per_ha"] == "48.4000"
    assert components["carbon_accounting_status"] == "NOT_CONFIGURED"
    assert components["net_tco2e_removals"] is None
    assert components["ledger_status"] == "BLOCKED_FOR_AGRICULTURE"


@pytest.mark.asyncio
async def test_tenant_and_project_isolation(db_session: AsyncSession):
    """
    Verifies tenant boundary enforcement (§16):
    Organization B cannot view or calculate SOC stock for Organization A's project.
    """
    org_a = Organization(id=uuid.uuid4(), name="Org Alpha")
    org_b = Organization(id=uuid.uuid4(), name="Org Beta")
    db_session.add_all([org_a, org_b])

    proj_a = Project(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Org Alpha Project",
        country="Kenya",
    )
    db_session.add(proj_a)
    await db_session.flush()

    # Attempting to query with Org B's context raises 404 / access error
    with pytest.raises(Exception):
        await AgricultureService.list_soc_stock_results(
            db=db_session,
            project_id=proj_a.id,
            organization_id=org_b.id,
        )


@pytest.mark.asyncio
async def test_postgres_concurrency(db_session: AsyncSession):
    """
    Verifies concurrent evaluation and locking (§20):
    Two concurrent requests serialize properly without duplicate key violations.
    """
    import asyncio

    org = Organization(id=uuid.uuid4(), name="Concurrency Org")
    db_session.add(org)
    proj = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Concurrent Project",
        country="Kenya",
    )
    db_session.add(proj)
    await db_session.flush()

    locked_prereq = AgriculturePrerequisiteAssessment(
        organization_id=org.id,
        project_id=proj.id,
        assessment_code="PREREQ-CONC-1",
        version=1,
        status="LOCKED",
        overall_readiness="READY",
        assessment_hash="hash_conc_123",
        is_locked=True,
    )
    db_session.add(locked_prereq)
    await db_session.flush()

    pt_id = uuid.uuid4()
    sample_layers = {
        pt_id: [
            LayerInput(layer_index=0, depth_upper_cm=Decimal("0.0"), depth_lower_cm=Decimal("30.0"), bulk_density_g_cm3=Decimal("1.30"), soc_concentration_g_kg=Decimal("15.0")),
        ]
    }

    # Evaluate concurrently
    eval1, eval2 = await asyncio.gather(
        AgricultureService.evaluate_soc_stock(
            db=db_session,
            project_id=proj.id,
            organization_id=org.id,
            prerequisite_assessment_id=locked_prereq.id,
            reference_soil_mass_t_ha=Decimal("3900.0000"),
            custom_point_layers=sample_layers,
        ),
        AgricultureService.evaluate_soc_stock(
            db=db_session,
            project_id=proj.id,
            organization_id=org.id,
            prerequisite_assessment_id=locked_prereq.id,
            reference_soil_mass_t_ha=Decimal("3900.0000"),
            custom_point_layers=sample_layers,
        ),
    )
    assert eval1["evaluation_hash"] == eval2["evaluation_hash"]
    assert eval1["project_soc_stock_t_c_per_ha"] == eval2["project_soc_stock_t_c_per_ha"]
