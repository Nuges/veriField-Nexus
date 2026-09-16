import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.biochar.services.puro_quantification import (
    PuroStoredCarbonCalculator,
    PuroBaselineRemovalCalculator,
    PuroStorageLossCalculator,
    PuroProjectEmissionsCalculator,
    PuroLeakageCalculator,
    PuroUncertaintyCalculator,
    PuroCORCCalculator,
    PuroAuthoritativeQuantificationService,
)
from app.domains.biochar.puro_rules import (
    CARBON_TO_CO2_FACTOR,
    MAX_ELIGIBLE_MOLAR_H_C,
    PURO_TABLE_6_1_REGRESSION_PARAMETERS,
    calculate_puro_persistence_fraction,
    resolve_puro_soil_temperature,
    PURO_TABLE_8_3_ILUC_FACTORS,
    seed_puro_biochar_normative_metadata,
)
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharLabAnalysis,
    FeedstockLot,
    FeedstockSource,
    ProductionFacility,
)
from app.domains.biochar.puro_models import (
    PuroCalculationExecution,
    PuroLCAModel,
    PuroCoProductAllocation,
)
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


# ==============================================================================
# Chapter 6: Table 6.1 Continuous Persistence Regressors & Provenance (Equation 6.4)
# ==============================================================================

def test_puro_rule_6_2_4_temperature_provenance_and_rounding():
    """
    Tests Rule 6.2.4 requirements:
    - Minimum soil temperature is conservatively floored at 7°C.
    - Temperature data rounded to closest upper integer (math.ceil).
    - Temperatures exceeding 40°C MUST NOT be silently clamped.
      Instead, return None with SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE.
    """
    # 1. Sub-7°C input floored at 7°C
    eff_temp, prov = resolve_puro_soil_temperature(4.2)
    assert eff_temp == 7
    assert prov["clamped_to_minimum_7c"] is True

    # 2. Non-integer input rounded up to upper integer
    eff_temp, prov = resolve_puro_soil_temperature(14.1)
    assert eff_temp == 15
    assert prov["rounded_upper_integer"] == 15

    # 3. Exact integer preserved
    eff_temp, prov = resolve_puro_soil_temperature(20.0)
    assert eff_temp == 20

    # 4. Above 40°C MUST NOT silently resolve to 40°C — must return None
    eff_temp, prov = resolve_puro_soil_temperature(43.5)
    assert eff_temp is None
    assert prov["status"] == "SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE"

    # 5. Exactly 40.0°C is within range (boundary)
    eff_temp, prov = resolve_puro_soil_temperature(40.0)
    assert eff_temp == 40

    # 6. 40.1°C rounds up to 41 → outside range
    eff_temp, prov = resolve_puro_soil_temperature(40.1)
    assert eff_temp is None
    assert prov["status"] == "SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE"


def test_puro_soil_temperature_41c_must_not_silently_resolve():
    """
    Gate Test: 41°C soil temperature must NOT silently resolve to 40°C.
    Must fail closed with SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE.
    This is a mandatory production gate per the user directive.
    """
    # Direct temperature resolution test
    eff_temp, prov = resolve_puro_soil_temperature(41.0)
    assert eff_temp is None, "41°C must NOT resolve to any integer temperature"
    assert prov["status"] == "SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE"
    assert prov["rounded_upper_integer"] == 41

    # Persistence fraction must also fail closed
    pf_res = calculate_puro_persistence_fraction(molar_h_c=0.35, soil_temp_celsius=41.0)
    assert pf_res["status"] == "SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE"
    assert pf_res["is_eligible"] is False
    assert pf_res["durability_class"] == "MANUAL_REVIEW_REQUIRED"
    assert pf_res["persistence_fraction_pf"] == 0.0


def test_puro_table_6_1_complete_coefficient_integrity():
    """
    Gate Test: Verifies ALL 34 temperature entries (7°C to 40°C) are present
    in the regression parameter table with valid M and a values.
    Every M must be positive, every a must be positive.
    M values must be monotonically decreasing from 7°C to 40°C.
    a values must be monotonically increasing from 7°C to 40°C.
    PF must be computable and in [0, 100] range for H/C = 0.35 at every temperature.
    """
    assert len(PURO_TABLE_6_1_REGRESSION_PARAMETERS) == 34

    prev_m = None
    prev_a = None
    for temp in range(7, 41):
        assert temp in PURO_TABLE_6_1_REGRESSION_PARAMETERS, f"Temperature {temp}°C missing from Table 6.1"
        m, a = PURO_TABLE_6_1_REGRESSION_PARAMETERS[temp]
        assert m > 0.0, f"M must be positive at {temp}°C"
        assert a > 0.0, f"a must be positive at {temp}°C"

        # Monotonicity: M decreasing, a increasing with temperature
        if prev_m is not None:
            assert m <= prev_m, f"M must be monotonically decreasing: {temp}°C ({m}) > {temp - 1}°C ({prev_m})"
        if prev_a is not None:
            assert a >= prev_a, f"a must be monotonically increasing: {temp}°C ({a}) < {temp - 1}°C ({prev_a})"
        prev_m = m
        prev_a = a

        # PF must be computable in valid range for a standard H/C ratio
        pf = m - (a * 0.35)
        assert 0.0 <= pf <= 100.0, f"PF out of range at {temp}°C: {pf}"


def test_puro_cstored_invariant_different_pf_same_gross():
    """
    Gate Test: Same Qbiochar + Corg with DIFFERENT Persistence Factors (different temperatures)
    must yield the SAME gross Cstored. PF affects Closs, NOT Cstored.
    """
    c_stored_15 = PuroStoredCarbonCalculator.calculate(
        eligible_dry_mass_tonnes=Decimal("10.0"),
        c_org_pct=Decimal("80.0"),
    )
    c_stored_30 = PuroStoredCarbonCalculator.calculate(
        eligible_dry_mass_tonnes=Decimal("10.0"),
        c_org_pct=Decimal("80.0"),
    )
    assert c_stored_15["status"] == "SUCCESS"
    assert c_stored_30["status"] == "SUCCESS"
    # Gross Cstored must be identical regardless of what PF/temperature will be used
    assert c_stored_15["c_stored_tco2e"] == c_stored_30["c_stored_tco2e"]

    # But Closs must differ when PF differs (different temperatures)
    loss_15 = PuroStorageLossCalculator.calculate(
        c_stored_tco2e=c_stored_15["c_stored_tco2e"],
        molar_h_c=0.35,
        soil_temperature_celsius=15.0,
    )
    loss_30 = PuroStorageLossCalculator.calculate(
        c_stored_tco2e=c_stored_30["c_stored_tco2e"],
        molar_h_c=0.35,
        soil_temperature_celsius=30.0,
    )
    assert loss_15["status"] == "SUCCESS"
    assert loss_30["status"] == "SUCCESS"
    # Higher temperature → lower PF → higher Closs
    assert loss_30["c_loss_tco2e"] > loss_15["c_loss_tco2e"]






# ==============================================================================
# Rule 3.5.1: Strict Carbonization Threshold Boundary Tests
# ==============================================================================

def test_puro_rule_3_5_1_molar_h_c_strict_boundary():
    """
    Tests Rule 3.5.1:
    - H/Corg < 0.70 is ELIGIBLE.
    - H/Corg >= 0.70 fails closed as INELIGIBLE.
    """
    # 1. Boundary pass: H/C = 0.699 (< 0.70)
    res_pass = calculate_puro_persistence_fraction(molar_h_c=0.699, soil_temp_celsius=15.0)
    assert res_pass["status"] == "SUCCESS"
    assert res_pass["is_eligible"] is True
    assert res_pass["durability_class"] == "CORC200+"
    assert res_pass["persistence_fraction_pf"] > 0.0

    # 2. Boundary fail: H/C = 0.700 (>= 0.70)
    res_fail_exact = calculate_puro_persistence_fraction(molar_h_c=0.700, soil_temp_celsius=15.0)
    assert res_fail_exact["status"] == "FAIL_CLOSED"
    assert res_fail_exact["is_eligible"] is False
    assert res_fail_exact["durability_class"] == "INELIGIBLE"
    assert res_fail_exact["persistence_fraction_pf"] == 0.0
    assert res_fail_exact["loss_fraction"] == 1.0

    # 3. Substantial fail: H/C = 0.750
    res_fail_high = calculate_puro_persistence_fraction(molar_h_c=0.750, soil_temp_celsius=15.0)
    assert res_fail_high["status"] == "FAIL_CLOSED"
    assert res_fail_high["durability_class"] == "INELIGIBLE"


def test_puro_non_soil_decay_equivalence():
    """
    Tests Rule 6.2.4 Remark:
    Non-soil applications (e.g. BE1 concrete filler) use the exact same soil decay
    equation (Equation 6.4) and receive durability class CORC200+.
    """
    loss_res = PuroStorageLossCalculator.calculate(
        c_stored_tco2e=Decimal("100.0"),
        molar_h_c=0.35,
        soil_temperature_celsius=15.0,
        is_non_soil_durable=True,
    )
    assert loss_res["status"] == "SUCCESS"
    assert loss_res["durability_class"] == "CORC200+"
    # Uses Table 6.1 Ts=15°C -> PF = 82.014% -> Closs = 100 * (100 - 82.014)/100 = 17.986 tCO2e
    assert abs(loss_res["c_loss_tco2e"] - Decimal("17.9860")) < Decimal("0.001")


# ==============================================================================
# Chapter 6: Stored Carbon & Storage Loss Quantification
# ==============================================================================

def test_puro_case_a_valid_new_facility():
    """
    Case A: Valid New Facility case with standard soil temperature and low H/C.
    10 tonnes dry biochar, 80% Corg, H/C = 0.35, Ts = 15°C.
    - Cstored = 10 * 0.80 * (44 / 12) = 29.333333 tCO2e
    - Ts = 15°C -> Table 6.1 (M=91.87, a=28.16) -> PF = 91.87 - (28.16 * 0.35) = 82.014%
    - Closs = 29.333333 * (100 - 82.014)/100 = 5.275893 tCO2e
    - Eops = 1.0 tCO2e, Eemb = 0.0, Eleakage = 0.0
    - Net CORCs = 29.333333 - 0 - 5.275893 - 1.0 = 23.057440 tCO2e
    """
    res = PuroCORCCalculator.execute_quantification(
        eligible_dry_mass_tonnes=Decimal("10.0"),
        c_org_pct=Decimal("80.0"),
        molar_h_c=0.35,
        baseline_scenario="NEW_FACILITY",
        historical_baseline_tco2e=Decimal("0.0"),
        soil_temperature_celsius=15.0,
        is_non_soil_durable=False,
        e_biomass=Decimal("0.5"),
        e_production=Decimal("0.3"),
        e_use=Decimal("0.2"),
        e_infra=Decimal("0.0"),
        e_dluc=Decimal("0.0"),
        is_leakage_mitigated=True,
        end_use_corc_point_eligible=True,
    )

    assert res["calculation_status"] == "SUCCESS"
    assert res["corc_point_status"] == "CORC_POINT_ELIGIBLE"
    assert res["durability_class"] == "CORC200+"
    assert float(res["c_baseline_tco2e"]) == 0.0

    expected_c_stored = Decimal("10.0") * Decimal("0.8") * (Decimal("44") / Decimal("12"))
    assert abs(res["c_stored_tco2e"] - expected_c_stored) < Decimal("0.0001")

    # Table 6.1 at 15°C: PF = 82.014% -> Loss fraction = 0.179860
    expected_c_loss = expected_c_stored * Decimal("0.179860")
    assert abs(res["c_loss_tco2e"] - expected_c_loss) < Decimal("0.001")

    # Final CORCs must match net_corcs_calculated (no deductible uncertainty)
    assert res["final_corcs_issuable"] == res["net_corcs_calculated"]
    assert res["deductible_uncertainty_pct"] == 0.0
    assert len(res["calculation_hash"]) == 64


def test_puro_retail_r3_reversal_discount_factor():
    """
    Tests Rule 6.1 requirement for Retail non-traceable end uses (R3):
    Requires Country Reversal Discount Factor (RDF).
    """
    # 1. Missing RDF for R3 fails closed
    res_no_rdf = PuroStoredCarbonCalculator.calculate(
        eligible_dry_mass_tonnes=Decimal("10.0"),
        c_org_pct=Decimal("80.0"),
        end_use_category_code="R3",
        reversal_discount_factor=None,
    )
    assert res_no_rdf["status"] == "DATA_REQUIRED"
    assert "reversal_discount_factor" in res_no_rdf["missing_inputs"]

    # 2. Valid RDF (e.g. 0.90) applied to Cstored
    res_rdf = PuroStoredCarbonCalculator.calculate(
        eligible_dry_mass_tonnes=Decimal("10.0"),
        c_org_pct=Decimal("80.0"),
        end_use_category_code="R3",
        reversal_discount_factor=Decimal("0.90"),
    )
    assert res_rdf["status"] == "SUCCESS"
    raw_c = Decimal("10.0") * Decimal("0.80") * (Decimal("44") / Decimal("12"))
    expected_c = raw_c * Decimal("0.90")
    assert abs(res_rdf["c_stored_tco2e"] - expected_c) < Decimal("0.0001")


# ==============================================================================
# Chapter 7: LCA Multi-Output Energy Allocation (Rule 7.5.2b)
# ==============================================================================

def test_puro_coproduct_lhv_energy_allocation():
    """
    Tests Rule 7.5.2b:
    Multi-output co-product allocation MUST be based on Lower Heating Value (LHV) energy content.
    Mass allocation is strictly prohibited.
    """
    # Biochar: 10 dry tonnes, LHV = 28.0 MJ/kg -> Energy = 10,000 kg * 28.0 = 280,000 MJ.
    # Co-product (Bio-oil): 6,000 kg, LHV = 20.0 MJ/kg -> Energy = 120,000 MJ.
    # Total energy = 400,000 MJ. Biochar share = 280,000 / 400,000 = 70.0%.
    # Total production emissions = 10.0 tCO2e.
    res = PuroProjectEmissionsCalculator.allocate_coproduct_emissions(
        total_production_emissions_tco2e=Decimal("10.0"),
        biochar_dry_mass_tonnes=Decimal("10.0"),
        biochar_lhv_mj_kg=Decimal("28.0"),
        coproduct_quantity=Decimal("6000.0"),
        coproduct_lhv_mj_unit=Decimal("20.0"),
        coproduct_name="BIO_OIL",
    )
    assert res["status"] == "SUCCESS"
    assert res["allocation_method"] == "ENERGY_LHV"
    assert abs(res["biochar_energy_share_pct"] - 70.0) < 0.001
    assert abs(res["allocated_biochar_emissions_tco2e"] - Decimal("7.0")) < Decimal("0.001")
    assert abs(res["allocated_coproduct_emissions_tco2e"] - Decimal("3.0")) < Decimal("0.001")


# ==============================================================================
# Chapter 8: Leakage & Table 8.3 iLUC Factors
# ==============================================================================

def test_puro_leakage_and_table_8_3_iluc():
    """
    Tests Chapter 8 Leakage:
    - Ecological Leakage (L_ECO) per Eq 8.1.
    - Market Activity Shifting (L_MA) = max(0, sum(Delta P * EF)) + iLUC per Eq 8.3.
    - Table 8.3 iLUC factors: Cereals and starch (0.012), Sugar crops (0.013),
      Oil crops (0.055 kgCO2e/MJ).
    """
    assert PURO_TABLE_8_3_ILUC_FACTORS["CEREALS_AND_STARCH_CROPS"] == 0.012
    assert PURO_TABLE_8_3_ILUC_FACTORS["SUGAR_CROPS"] == 0.013
    assert PURO_TABLE_8_3_ILUC_FACTORS["OIL_CROPS"] == 0.055

    # Biochar batch with 1.5 tCO2e direct market activity leakage, 0.5 tCO2e ecological leakage,
    # and feedstock iLUC from Sugar crops:
    # 10 tonnes dry feedstock, LHV = 18.0 MJ/kg -> 180,000 MJ.
    # iLUC factor = 0.013 kgCO2e/MJ -> 2,340 kgCO2e = 2.34 tCO2e.
    # L_MA = 1.5 + 2.34 = 3.84 tCO2e. Total E_leakage = 0.5 + 3.84 = 4.34 tCO2e.
    res = PuroLeakageCalculator.calculate(
        is_leakage_mitigated=False,
        ecological_leakage_tco2e=Decimal("0.5"),
        market_activity_shifting_tco2e=Decimal("1.5"),
        iluc_feedstock_category="SUGAR_CROPS",
        feedstock_quantity_dry_tonnes=Decimal("10.0"),
        feedstock_lhv_mj_kg=Decimal("18.0"),
    )
    assert res["status"] == "SUCCESS"
    assert res["ecological_leakage_tco2e"] == Decimal("0.5")
    assert abs(res["iluc_leakage_tco2e"] - Decimal("2.34")) < Decimal("0.001")
    assert abs(res["market_leakage_tco2e"] - Decimal("3.84")) < Decimal("0.001")
    assert abs(res["e_leakage_tco2e"] - Decimal("4.34")) < Decimal("0.001")


# ==============================================================================
# Section 10: Uncertainty Propagation & Reporting
# ==============================================================================

def test_puro_section_10_uncertainty_reporting_without_deduction():
    """
    Tests Section 10:
    Combined uncertainty is computed via ISO GUM propagation and reported on CORC
    certificates as (CORCs ± U%). Deductible uncertainty is strictly 0.0%.
    """
    # Net removal = 100.0 tCO2e.
    # Parameter uncertainties: u_mass=2.0%, u_c_org=3.0%, u_persistence=4.0%, u_emissions=5.0%
    # u_comb = sqrt(4 + 9 + 16 + 25) = sqrt(54) = 7.3485% -> 7.35%
    res = PuroUncertaintyCalculator.calculate(
        net_removal_tco2e=Decimal("100.0"),
        u_mass_pct=2.0,
        u_c_org_pct=3.0,
        u_persistence_pct=4.0,
        u_emissions_pct=5.0,
    )
    assert res["status"] == "SUCCESS"
    assert res["combined_uncertainty_pct"] == 7.35
    assert res["deductible_uncertainty_pct"] == 0.0
    assert res["deduction_tco2e"] == Decimal("0.0")
    assert "7.3%" in res["reported_uncertainty_text"] or "7.4%" in res["reported_uncertainty_text"]


# ==============================================================================
# Fail-Closed and Guardrail Scenarios
# ==============================================================================

def test_puro_missing_organic_carbon_fails_closed():
    """Missing organic carbon -> fail closed."""
    res = PuroCORCCalculator.execute_quantification(
        eligible_dry_mass_tonnes=Decimal("10.0"),
        c_org_pct=Decimal("0.0"),
        molar_h_c=0.35,
        baseline_scenario="NEW_FACILITY",
        soil_temperature_celsius=15.0,
        end_use_corc_point_eligible=True,
    )
    assert res["calculation_status"] == "FAIL_CLOSED"
    assert res["final_corcs_issuable"] == Decimal("0.0")


def test_puro_missing_eligible_end_use_blocks_corc_point():
    """Missing eligible end use -> no CORC point."""
    res = PuroCORCCalculator.execute_quantification(
        eligible_dry_mass_tonnes=Decimal("10.0"),
        c_org_pct=Decimal("80.0"),
        molar_h_c=0.35,
        end_use_corc_point_eligible=False,
    )
    assert res["calculation_status"] == "FAIL_CLOSED"
    assert res["corc_point_status"] == "CORC_POINT_NOT_REACHED"
    assert res["final_corcs_issuable"] == Decimal("0.0")


def test_puro_retrofit_missing_baseline_fails_closed():
    """Retrofit facility lacking historical baseline -> fail closed / data required."""
    res = PuroCORCCalculator.execute_quantification(
        eligible_dry_mass_tonnes=Decimal("10.0"),
        c_org_pct=Decimal("80.0"),
        molar_h_c=0.35,
        baseline_scenario="RETROFIT_FACILITY",
        historical_baseline_tco2e=None,
        soil_temperature_celsius=15.0,
        end_use_corc_point_eligible=True,
    )
    assert res["calculation_status"] in ("FAIL_CLOSED", "DATA_REQUIRED")
    assert res["final_corcs_issuable"] == Decimal("0.0")


def test_puro_reproducibility_identical_hash():
    """Identical evidence produces identical canonical SHA-256 hash."""
    params = {
        "eligible_dry_mass_tonnes": Decimal("12.5"),
        "c_org_pct": Decimal("78.5"),
        "molar_h_c": 0.36,
        "baseline_scenario": "NEW_FACILITY",
        "historical_baseline_tco2e": Decimal("0.0"),
        "soil_temperature_celsius": 14.0,
        "is_non_soil_durable": False,
        "e_biomass": Decimal("0.6"),
        "e_production": Decimal("0.4"),
        "e_use": Decimal("0.2"),
        "e_infra": Decimal("0.5"),
        "e_dluc": Decimal("0.0"),
        "is_leakage_mitigated": True,
        "end_use_corc_point_eligible": True,
    }

    res1 = PuroCORCCalculator.execute_quantification(**params)
    res2 = PuroCORCCalculator.execute_quantification(**params)

    assert res1["calculation_status"] == "SUCCESS"
    assert res1["final_corcs_issuable"] == res2["final_corcs_issuable"]
    assert res1["calculation_hash"] == res2["calculation_hash"]
    assert len(res1["calculation_hash"]) == 64


def test_puro_changed_evidence_creates_new_hash():
    """Altered evidence creates distinct calculation hash."""
    params1 = {
        "eligible_dry_mass_tonnes": Decimal("10.0"),
        "c_org_pct": Decimal("80.0"),
        "molar_h_c": 0.35,
        "end_use_corc_point_eligible": True,
    }
    params2 = {
        "eligible_dry_mass_tonnes": Decimal("10.5"),
        "c_org_pct": Decimal("80.0"),
        "molar_h_c": 0.35,
        "end_use_corc_point_eligible": True,
    }

    res1 = PuroCORCCalculator.execute_quantification(**params1)
    res2 = PuroCORCCalculator.execute_quantification(**params2)

    assert res1["calculation_hash"] != res2["calculation_hash"]


# ==============================================================================
# Authoritative DB Resolver & Legacy Superseding Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_puro_authoritative_resolver_and_legacy_superseding(db_session: AsyncSession):
    """
    Tests end-to-end authoritative resolver:
    - Resolves facility, lab assays, and verified delivery end-use from database.
    - Supersedes legacy v1.0.0 calculation execution records.
    - Saves authoritative v2.0.0 record with full LCA breakdown and Table 6.1 parameters.
    """
    await seed_puro_biochar_normative_metadata(db_session)

    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Puro Biochar Facility Org {uuid.uuid4().hex[:6]}",
        org_type="SUPPLIER",
    )
    db_session.add(org)

    proj_id = uuid.uuid4()
    proj = Project(
        id=proj_id,
        organization_id=org_id,
        name="Puro Biochar Carbon Facility",
    )
    db_session.add(proj)

    fac_id = uuid.uuid4()
    fac = ProductionFacility(
        id=fac_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-{uuid.uuid4().hex[:6]}",
        facility_name="Pyrolysis Unit Alpha",
        technology_type="SLOW_PYROLYSIS",
    )
    db_session.add(fac)

    # Add Biochar Batch
    batch_id = uuid.uuid4()
    batch = BiocharBatch(
        id=batch_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_number=f"BATCH-{uuid.uuid4().hex[:4]}",
        facility_name="Pyrolysis Unit Alpha",
        kiln_id="K-01",
        feedstock_type="FORESTRY_RESIDUES",
        feedstock_weight_tonnes=Decimal("50.0"),
        moisture_content_pct=Decimal("10.0"),
        pyrolysis_temp_celsius=550.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=Decimal("10.0"),
        dry_mass_tonnes=Decimal("10.0"),
        status="ACTIVE",
    )
    db_session.add(batch)

    # Add Certified Lab Analysis
    lab_id = uuid.uuid4()
    lab = BiocharLabAnalysis(
        id=lab_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch_id,
        sample_id=f"SAMPLE-{uuid.uuid4().hex[:4]}",
        sampling_date=datetime.now(timezone.utc),
        laboratory_name="Eurofins Accredited Carbon Lab",
        organic_carbon_pct=80.0,
        fixed_carbon_pct=75.0,
        molar_h_c_ratio=0.35,
        moisture_pct=5.0,
        ash_pct=3.0,
        qa_status="VERIFIED",
    )
    db_session.add(lab)

    # Add a legacy v1.0.0 execution record that must be superseded
    legacy_exec_id = uuid.uuid4()
    legacy_exec = PuroCalculationExecution(
        id=legacy_exec_id,
        batch_id=batch_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_id=fac_id,
        calculation_mode="AUTHORITATIVE",
        engine_version="1.0.0",
        calculation_status="SUCCESS",
        eligible_dry_biochar_mass_tonnes=Decimal("10.0"),
        c_org_pct=80.0,
        molar_h_c=0.35,
        c_stored_tco2e=Decimal("29.333"),
        c_loss_tco2e=Decimal("4.400"),
        e_project_tco2e=Decimal("1.200"),
        net_corcs_calculated=Decimal("25.000"),
        final_corcs_issuable=Decimal("25.000"),
        input_manifest_json={},
        calculation_hash="legacy_fake_hash_123",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(legacy_exec)
    await db_session.commit()

    # Execute authoritative quantification
    breakdown = await PuroAuthoritativeQuantificationService.resolve_and_execute(
        db=db_session,
        batch_id=batch_id,
        organization_id=org_id,
        mode="AUTHORITATIVE",
    )

    assert breakdown["calculation_status"] == "SUCCESS"
    assert breakdown["calculation_mode"] == "AUTHORITATIVE"
    assert breakdown["engine_version"] == "2.0.0"
    assert breakdown["durability_class"] == "CORC200+"
    assert breakdown["persistence_fraction_pf"] > 0.0
    assert breakdown["regression_m"] is not None
    assert breakdown["regression_a"] is not None
    assert breakdown["reported_uncertainty_text"] is not None

    # Check database: legacy record must be superseded
    stmt_leg = select(PuroCalculationExecution).where(PuroCalculationExecution.id == legacy_exec_id)
    res_leg = await db_session.execute(stmt_leg)
    updated_legacy = res_leg.scalar_one()
    assert updated_legacy.superseded_at is not None
    assert updated_legacy.replacement_engine_version == "2.0.0"

    # Check database: new authoritative record persisted
    stmt_new = select(PuroCalculationExecution).where(
        PuroCalculationExecution.batch_id == batch_id,
        PuroCalculationExecution.engine_version == "2.0.0",
    )
    res_new = await db_session.execute(stmt_new)
    persisted_new = res_new.scalar_one()
    assert persisted_new.calculation_mode == "AUTHORITATIVE"
    assert persisted_new.final_corcs_issuable == breakdown["final_corcs_issuable"]
    assert persisted_new.superseded_at is None
