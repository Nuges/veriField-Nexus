"""
VeriField Nexus — Agriculture Phase 3B-3 Net GHG & VCU Readiness Engine Tests
=============================================================================
Comprehensive unit and integration test suite verifying:
- Table 5 Applicability Router and fail-closed integrity
- Baseline and Project Emissions by source (fossil fuel, liming, N2O, etc.)
- Woody biomass pool status and Equations 44 & 45 completion
- Leakage accounting (11 June 2026 C&C production decline, activity, livestock, residue)
- VM0042 Equations 37–43:
  - Eq. 37 Gross Reductions (ER)
  - Eq. 38 Net Reductions (ERNET)
  - Eq. 39 Leakage Allocation to Reductions (LKER)
  - Eq. 40 Gross Removals (CR)
  - Eq. 41 Net Removals (CRNET)
  - Eq. 42 Leakage Allocation to Removals (LKCR)
  - Eq. 43 Total Net GHG Benefit (ERRNET)
- Section 8.7 VCU Readiness (Eqs. 75–79):
  - NPR buffer gate
  - Eq. 75 Reduction buffer deduction
  - Eq. 76 Removal buffer deduction
  - Eq. 77 Reduction VCU quantity
  - Eq. 78 Removal VCU quantity
  - Eq. 79 Total internal VCU eligible quantity
- Multi-Year Vintage Accounting
- Tenant security & Segregation of Duties (Field Agent blocked)
- Immutability, Idempotency, and Supersession
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select

from app.domains.agriculture.quantification.net_ghg_calculator import (
    ApplicabilityStatus,
    ActivityDataStatus,
    QuantificationApproach,
    SourceApplicabilityItem,
    FossilFuelActivity,
    LimingActivity,
    FertilizerN2OActivity,
    NitrogenFixingActivity,
    ManureDepositionActivity,
    EntericFermentationActivity,
    BiomassBurningActivity,
    SoilMethanogenesisActivity,
    WoodyBiomassPoolData,
    LeakageInputData,
    NPRRiskAssessmentInput,
    GWPConfig,
    AnnualVintageGHGResult,
    NetGHGProjectOutput,
    NetGHGCalculationError,
    VMD0054Version,
    resolve_vmd0054_version,
    evaluate_single_vintage_net_ghg,
    validate_table_5_applicability,
    aggregate_verification_period_net_ghg,
    calculate_fossil_fuel_emissions,
    calculate_liming_emissions,
    calculate_fertilizer_n2o_emissions,
    calculate_manure_deposition_emissions,
    calculate_enteric_fermentation_emissions,
    calculate_biomass_burning_emissions,
    calculate_total_leakage,
    calculate_equation_37_gross_reductions,
    calculate_equation_38_net_reductions,
    calculate_equation_39_leakage_allocation_er,
    calculate_equation_40_gross_removals,
    calculate_equation_41_net_removals,
    calculate_equation_42_leakage_allocation_cr,
    allocate_leakage_eq39_eq42,
    calculate_equation_43_total_net,
    calculate_equation_75_buffer_reductions,
    calculate_equation_76_buffer_removals,
    calculate_equation_77_vcu_reductions,
    calculate_equation_78_vcu_removals,
    calculate_equation_79_total_vcu,
    calculate_vmd0054_v11_equation_11_delta_cs,
    calculate_vmd0054_v11_equation_13_cumulative_leakage,
    calculate_vmd0054_v10_equation_10_cumulative_leakage,
    calculate_vm0042_equation_36_market_leakage,
    VerraTransitionRequestCategory,
    VerraVerificationSubtype,
)
from app.domains.agriculture.models import (
    AgricultureNetGHGResult,
    AgricultureVintageGHGResult,
    AgriculturePrerequisiteAssessment,
    AgricultureSOCChangeResult,
    LandUnit,
)
from app.domains.agriculture.service import AgricultureService
from app.domains.projects.models import Project
from app.domains.organizations.models import Organization
from app.domains.authentication.models import User
from fastapi import HTTPException


# =============================================================================
# 1. Component Calculators Unit Tests
# =============================================================================

def test_fossil_fuel_emissions_calculation():
    """Verifies fossil fuel emissions with exact factors."""
    acts = [
        FossilFuelActivity(
            fuel_type="DIESEL",
            quantity=Decimal("10000.0000"),
            unit="LITERS",
            emission_factor_tco2e_per_unit=Decimal("0.00268"),
            factor_source="IPCC_2006",
        ),
        FossilFuelActivity(
            fuel_type="GASOLINE",
            quantity=Decimal("5000.0000"),
            unit="LITERS",
            emission_factor_tco2e_per_unit=Decimal("0.00231"),
            factor_source="IPCC_2006",
        ),
    ]
    total = calculate_fossil_fuel_emissions(acts)
    # 10000 * 0.00268 = 26.8000, 5000 * 0.00231 = 11.5500 -> Total = 38.3500
    assert total == Decimal("38.3500")


def test_liming_emissions_stoichiometry():
    """Verifies calcitic and dolomite liming with exact 44/12 stoichiometry."""
    act = LimingActivity(
        calcitic_limestone_tonnes=Decimal("100.0000"),
        dolomite_tonnes=Decimal("50.0000"),
    )
    total = calculate_liming_emissions(act)
    # Calcitic: 100 * 0.12 * 44/12 = 44.0000
    # Dolomite: 50 * 0.13 * 44/12 = 23.8333
    # Total = 67.8333
    assert total == Decimal("67.8333")


def test_fertilizer_n2o_direct_and_indirect():
    """Verifies fertilizer direct and indirect N2O emissions."""
    acts = [
        FertilizerN2OActivity(
            fertilizer_type="SYNTHETIC_UREA",
            mass_kg=Decimal("10000.0000"),
            n_fraction=Decimal("0.4600"),  # 4600 kg N
            ef1_direct=Decimal("0.0100"),  # 46 kg N2O-N direct
            frac_gasm_volatilization=Decimal("0.1000"),  # 460 kg N volatilized
            ef4_volatilization=Decimal("0.0100"),  # 4.6 kg N2O-N indirect volat
            frac_leach=Decimal("0.3000"),  # 1380 kg N leached
            ef5_leaching=Decimal("0.0075"),  # 10.35 kg N2O-N indirect leach
        )
    ]
    # Total N2O-N = 46 + 4.6 + 10.35 = 60.95 kg N2O-N
    # Total N2O = 60.95 * (44/28) = 95.77857 kg N2O
    # GWP_N2O = 265 -> tCO2e = 95.77857 * 0.001 * 265 = 25.3813 tCO2e
    total = calculate_fertilizer_n2o_emissions(acts, gwp_n2o=Decimal("265"))
    assert total == Decimal("25.3813")


# =============================================================================
# 2. Table 5 Applicability Router Tests
# =============================================================================

def test_table_5_router_blocks_unconfigured_applicable_source():
    """Ensures fail-closed behavior when an applicable source is not configured."""
    items = [
        SourceApplicabilityItem(
            source_category="CO2_SOC",
            gas="CO2",
            status=ApplicabilityStatus.APPLICABLE_CONFIGURED,
            quantification_approach=QuantificationApproach.QA2_MEASURE_AND_REMEASURE,
            activity_data_status=ActivityDataStatus.MEASURED,
            rationale="SOC direct sampling.",
        ),
        SourceApplicabilityItem(
            source_category="CO2_FOSSIL_FUEL",
            gas="CO2",
            status=ApplicabilityStatus.APPLICABLE_NOT_CONFIGURED,
            quantification_approach=QuantificationApproach.QA3_ACTIVITY_METHOD,
            activity_data_status=ActivityDataStatus.NOT_CONFIGURED,
            rationale="Machinery used but activity data unconfigured.",
        ),
    ]
    is_valid, reason, _ = validate_table_5_applicability(items)
    assert not is_valid
    assert "APPLICABLE but NOT_CONFIGURED" in reason


def test_table_5_router_blocks_qa2_on_methanogenesis():
    """Ensures QA2 cannot be falsely assigned to CH4 soil methanogenesis."""
    # Test 1: QA2 on methanogenesis fails closed (QA2 is strictly for SOC)
    items_qa2 = [
        SourceApplicabilityItem(
            source_category="CH4_SOIL_METHANOGENESIS",
            gas="CH4",
            status=ApplicabilityStatus.APPLICABLE_CONFIGURED,
            quantification_approach=QuantificationApproach.QA2_MEASURE_AND_REMEASURE,
            activity_data_status=ActivityDataStatus.MEASURED,
            rationale="Attempted QA2 on methanogenesis.",
        ),
    ]
    is_valid_qa2, reason_qa2, _ = validate_table_5_applicability(items_qa2)
    assert not is_valid_qa2
    assert "permits QA2 strictly for Soil Organic Carbon (SOC)" in reason_qa2

    # Test 2: QA3 on methanogenesis fails closed (methanogenesis permits strictly QA1)
    items_qa3 = [
        SourceApplicabilityItem(
            source_category="CH4_SOIL_METHANOGENESIS",
            gas="CH4",
            status=ApplicabilityStatus.APPLICABLE_CONFIGURED,
            quantification_approach=QuantificationApproach.QA3_ACTIVITY_METHOD,
            activity_data_status=ActivityDataStatus.MEASURED,
            rationale="Attempted QA3 on methanogenesis.",
        ),
    ]
    is_valid_qa3, reason_qa3, _ = validate_table_5_applicability(items_qa3)
    assert not is_valid_qa3
    assert "permits strictly QA1 biogeochemical model for soil methanogenesis" in reason_qa3


def test_table_5_router_verified_zero_accepted():
    """Proves that verified zero activity is accepted and does not block."""
    items = [
        SourceApplicabilityItem(
            source_category="CO2_SOC",
            gas="CO2",
            status=ApplicabilityStatus.APPLICABLE_CONFIGURED,
            quantification_approach=QuantificationApproach.QA2_MEASURE_AND_REMEASURE,
            activity_data_status=ActivityDataStatus.MEASURED,
            rationale="SOC measured.",
        ),
        SourceApplicabilityItem(
            source_category="CO2_FOSSIL_FUEL",
            gas="CO2",
            status=ApplicabilityStatus.APPLICABLE_CONFIGURED,
            quantification_approach=QuantificationApproach.QA3_ACTIVITY_METHOD,
            activity_data_status=ActivityDataStatus.VERIFIED_ACTIVITY_ZERO,
            rationale="Farm is 100% manual labor and solar; zero fossil fuel combustion verified.",
        ),
    ]
    is_valid, reason, _ = validate_table_5_applicability(items)
    assert is_valid
    assert reason is None


# =============================================================================
# 3. Hand-Calculated Reference Project (Positive Net GHG + NPR Buffer)
# =============================================================================

def test_hand_calculated_positive_reference_project():
    """
    Independent hand calculation verifying exact numbers:
    - SOC QA2: 40.0000 tCO2e/yr removal (cumulative project stock > 0)
    - Fossil fuel: baseline 50.0000, project 30.0000 -> 20.0000 tCO2e reduction
    - Fertilizer N2O: baseline 10.0000, project 6.0000 -> 4.0000 tCO2e reduction
    - Total source reductions: 24.0000 tCO2e/yr
    - Woody biomass: NOT_APPLICABLE (0.0000)
    - Eq. 44 baseline stock change = 0.0000
    - Eq. 45 project stock change = 40.0000
    - Eq. 37 Gross Reductions (ER) = 24.0000
    - Eq. 40 Gross Removals (CR) = 40.0000
    - Total Gross Benefit = 64.0000 tCO2e/yr
    - Leakage: production decline = 4.0000 tCO2e/yr
    - Eq. 39 LKER = 4.0000 * (24 / 64) = 1.5000 tCO2e/yr
    - Eq. 42 LKCR = 4.0000 * (40 / 64) = 2.5000 tCO2e/yr
    - Eq. 38 ERNET = 24.0000 - 1.5000 = 22.5000 tCO2e/yr
    - Eq. 41 CRNET = 40.0000 - 2.5000 = 37.5000 tCO2e/yr
    - Eq. 43 ERRNET = 22.5000 + 37.5000 = 60.0000 tCO2e/yr
    - NPR = 15%:
      - BUF_ER = 0.0000 (all ER from non-stock fossil/fertilizer)
      - BUF_CR = 0.15 * 40.0000 = 6.0000 tCO2e/yr (Eq. 76: based on gross CR before leakage)
      - Total Buffer = 6.0000 tCO2e/yr
      - Eq. 77 VCU_ER = 22.5000 tCO2e/yr
      - Eq. 78 VCU_CR = 37.5000 - 6.0000 = 31.5000 tCO2e/yr
      - Eq. 79 VCU_Total = 22.5000 + 31.5000 = 54.0000 tCO2e/yr
    """
    ff_bsl = [FossilFuelActivity("DIESEL", Decimal("50000.0000"), "LITERS", Decimal("0.001"), "S")]
    ff_wp = [FossilFuelActivity("DIESEL", Decimal("30000.0000"), "LITERS", Decimal("0.001"), "S")]

    lime_bsl = LimingActivity(is_verified_zero=True)
    lime_wp = LimingActivity(is_verified_zero=True)

    # Fertilizer N2O: direct only for exact calibration (N input 1000 vs 600 kg)
    # Using ef1=0.01, N2O_TO_N=44/28, GWP=265 / (44/28 * 265 * 0.001 * 0.01) to hit exactly 10.0 and 6.0
    fert_bsl = [
        FertilizerN2OActivity(
            fertilizer_type="SYNTHETIC_UREA",
            mass_kg=Decimal("10000.0000"),
            n_fraction=Decimal("0.2401344"),
            ef1_direct=Decimal("0.0100"),
            frac_gasm_volatilization=Decimal("0.0000"),
            frac_leach=Decimal("0.0000"),
        )
    ]
    fert_wp = [
        FertilizerN2OActivity(
            fertilizer_type="SYNTHETIC_UREA",
            mass_kg=Decimal("6000.0000"),
            n_fraction=Decimal("0.2401344"),
            ef1_direct=Decimal("0.0100"),
            frac_gasm_volatilization=Decimal("0.0000"),
            frac_leach=Decimal("0.0000"),
        )
    ]

    woody_pool = WoodyBiomassPoolData(is_verified_zero=True)
    leakage = LeakageInputData(production_decline_leakage_tco2e_yr=Decimal("4.0000"))
    npr_input = NPRRiskAssessmentInput(
        npr_rating_pct=Decimal("15.0000"),
        risk_assessment_id=uuid.uuid4(),
        approval_status="APPROVED",
        effective_date="2026-10-01",
    )

    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=ff_bsl,
        fossil_fuel_wp=ff_wp,
        liming_bsl=lime_bsl,
        liming_wp=lime_wp,
        fertilizer_bsl=fert_bsl,
        fertilizer_wp=fert_wp,
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("40.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=woody_pool,
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=leakage,
        npr_input=npr_input,
    )

    assert res.e_fossil_fuel_bsl == Decimal("50.0000")
    assert res.e_fossil_fuel_wp == Decimal("30.0000")
    assert abs(res.e_fert_n2o_bsl - Decimal("10.0000")) <= Decimal("0.0001")
    assert abs(res.e_fert_n2o_wp - Decimal("6.0000")) <= Decimal("0.0001")
    assert res.total_emission_reductions_from_sources_tco2e == Decimal("24.0000")

    # Stock changes
    assert res.eq44_baseline_total_carbon_stock_change_tco2e == Decimal("0.0000")
    assert res.eq45_project_total_carbon_stock_change_tco2e == Decimal("40.0000")
    assert res.i_delta_co2_wp == 1

    # Gross Reductions and Removals
    assert res.gross_reductions_er_tco2e == Decimal("24.0000")
    assert res.gross_removals_cr_tco2e == Decimal("40.0000")

    # Leakage Allocation
    assert res.total_leakage_tco2e == Decimal("4.0000")
    assert res.leakage_allocation_er_lker_tco2e == Decimal("1.5000")
    assert res.leakage_allocation_cr_lkcr_tco2e == Decimal("2.5000")
    assert res.leakage_allocation_er_lker_tco2e + res.leakage_allocation_cr_lkcr_tco2e == Decimal("4.0000")

    # Net Reductions and Removals
    assert res.net_reductions_ernet_tco2e == Decimal("22.5000")
    assert res.net_removals_crnet_tco2e == Decimal("37.5000")
    assert res.total_net_ghg_errnet_tco2e == Decimal("60.0000")

    # Section 8.7 VCU Readiness (Eq. 76: based on Gross CR 40.0 * 15% = 6.0000)
    assert res.buffer_deduction_reductions_tco2e == Decimal("0.0000")
    assert res.buffer_deduction_removals_tco2e == Decimal("6.0000")
    assert res.total_buffer_deduction_tco2e == Decimal("6.0000")
    assert res.internal_vcu_eligible_reductions_tco2e == Decimal("22.5000")
    assert res.internal_vcu_eligible_removals_tco2e == Decimal("31.5000")
    assert res.internal_vcu_eligible_total_tco2e == Decimal("54.0000")
    assert res.vcu_readiness_status == "CALCULATED"


# =============================================================================
# 4. Pure Removals vs Pure Reductions Cases
# =============================================================================

def test_pure_removals_case():
    """Proves pure removals scenario where no non-stock reductions occur."""
    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=[],
        fossil_fuel_wp=[],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("50.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=LeakageInputData(activity_displacement_tco2e_yr=Decimal("5.0000")),
        npr_input=NPRRiskAssessmentInput(Decimal("10.0000"), uuid.uuid4(), "APPROVED", "2026-10-01"),
    )
    assert res.gross_reductions_er_tco2e == Decimal("0.0000")
    assert res.gross_removals_cr_tco2e == Decimal("50.0000")
    assert res.leakage_allocation_er_lker_tco2e == Decimal("0.0000")
    assert res.leakage_allocation_cr_lkcr_tco2e == Decimal("5.0000")
    assert res.net_reductions_ernet_tco2e == Decimal("0.0000")
    assert res.net_removals_crnet_tco2e == Decimal("45.0000")
    assert res.total_net_ghg_errnet_tco2e == Decimal("45.0000")
    # Eq. 76: Gross removals 50.0 * 10% = 5.0000 (NOT CRNET 45 * 10% = 4.5)
    assert res.buffer_deduction_removals_tco2e == Decimal("5.0000")
    assert res.internal_vcu_eligible_total_tco2e == Decimal("40.0000")


def test_pure_reductions_case():
    """Proves avoided-emissions / pure reductions scenario without removals."""
    ff_bsl = [FossilFuelActivity("DIESEL", Decimal("40000.0000"), "LITERS", Decimal("0.001"), "S")]
    ff_wp = [FossilFuelActivity("DIESEL", Decimal("10000.0000"), "LITERS", Decimal("0.001"), "S")]

    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=ff_bsl,
        fossil_fuel_wp=ff_wp,
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("0.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=LeakageInputData(activity_displacement_tco2e_yr=Decimal("3.0000")),
        npr_input=NPRRiskAssessmentInput(Decimal("10.0000"), uuid.uuid4(), "APPROVED", "2026-10-01"),
    )
    assert res.gross_reductions_er_tco2e == Decimal("30.0000")
    assert res.gross_removals_cr_tco2e == Decimal("0.0000")
    assert res.leakage_allocation_er_lker_tco2e == Decimal("3.0000")
    assert res.leakage_allocation_cr_lkcr_tco2e == Decimal("0.0000")
    assert res.net_reductions_ernet_tco2e == Decimal("27.0000")
    assert res.net_removals_crnet_tco2e == Decimal("0.0000")
    assert res.total_net_ghg_errnet_tco2e == Decimal("27.0000")
    # Buffer deduction is 0 for non-stock reductions
    assert res.total_buffer_deduction_tco2e == Decimal("0.0000")
    assert res.internal_vcu_eligible_total_tco2e == Decimal("27.0000")


# =============================================================================
# 5. Adverse Project Case & Zero-Denominator Safety
# =============================================================================

def test_adverse_project_case():
    """Tests project where emissions increase and carbon is lost."""
    ff_bsl = [FossilFuelActivity("DIESEL", Decimal("10000.0000"), "LITERS", Decimal("0.001"), "S")]
    ff_wp = [FossilFuelActivity("DIESEL", Decimal("25000.0000"), "LITERS", Decimal("0.001"), "S")]

    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=ff_bsl,
        fossil_fuel_wp=ff_wp,
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("-10.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.050000"),
        soc_sign_indicator=-1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=LeakageInputData(activity_displacement_tco2e_yr=Decimal("0.0000")),
    )
    # Literal unclamped VM0042 Eq. 37 preserves adverse annual performance (does not clamp to zero)
    assert res.gross_reductions_er_tco2e == Decimal("-25.5000")
    assert res.gross_removals_cr_tco2e == Decimal("0.0000")
    assert res.total_net_ghg_errnet_tco2e == Decimal("-25.5000")


def test_zero_denominator_leakage_safety():
    """Tests that when ER + CR == 0 and leakage > 0, division by zero is prevented and fails closed."""
    with pytest.raises(NetGHGCalculationError) as exc_info:
        evaluate_single_vintage_net_ghg(
            vintage_year=2024,
            fossil_fuel_bsl=[],
            fossil_fuel_wp=[],
            liming_bsl=LimingActivity(is_verified_zero=True),
            liming_wp=LimingActivity(is_verified_zero=True),
            fertilizer_bsl=[],
            fertilizer_wp=[],
            nfixing_bsl=[],
            nfixing_wp=[],
            manure_bsl=[],
            manure_wp=[],
            enteric_bsl=[],
            enteric_wp=[],
            burning_bsl=[],
            burning_wp=[],
            methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
            methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
            soc_stock_change_bsl_tco2e=Decimal("0.0000"),
            soc_stock_change_wp_tco2e=Decimal("0.0000"),
            soc_uncertainty_deduction_fraction=Decimal("0.000000"),
            soc_sign_indicator=1,
            woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
            prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
            leakage=LeakageInputData(activity_displacement_tco2e_yr=Decimal("10.0000")),
        )
    assert exc_info.value.code == "LEAKAGE_ALLOCATION_UNDEFINED"
    assert exc_info.value.details.get("status") == "AUTHORITATIVE_NET_GHG_BLOCKED"


# =============================================================================
# 6. Service Integration, DB Persistence, Concurrency & Security Tests
# =============================================================================

@pytest.mark.asyncio
async def test_net_ghg_service_evaluate_and_finalize_lifecycle(db_session):
    """
    Full database workflow test:
    - Prepares project, prerequisite assessment, and SOC change result
    - Evaluates Net GHG preview
    - Finalizes authoritative record
    - Verifies relational persistence of net GHG result and annual vintages
    - Verifies immutability & idempotency
    """
    # 1. Setup Tenant and Project
    org = Organization(
        id=uuid.uuid4(),
        name=f"VeriField Agriculture QA Corp {uuid.uuid4().hex[:4]}",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(org)

    project = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Midwest Maize Regenerative Pilot",
        project_code=f"PRJ-{uuid.uuid4().hex[:6]}",
        country="USA",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)

    # 2. Prerequisite Assessment
    prereq = AgriculturePrerequisiteAssessment(
        id=uuid.uuid4(),
        organization_id=org.id,
        project_id=project.id,
        assessment_code=f"PREREQ-{uuid.uuid4().hex[:6]}",
        version=1,
        status="LOCKED",
        overall_readiness="READY",
        methodology_code="VM0042",
        methodology_version="2.2",
        corrections_clarifications_version="2026-06-11",
        rule_set_version="VM0042_V2.2_RULES_CC20260611_V1.0",
        vcs_standard_version="4.7",
        vcs_resolution_metadata={"transition_status": "V4_7_GOVERNED"},
        quantification_route_map={"selected_route": "APPROACH_2_ESM_DIRECT"},
        esm_input_dossier={"algorithm": "WENDT_HAUSER_2013_CUBIC_SPLINE"},
        sampling_design_assessment={"design_sufficiency": "SUFFICIENT"},
        uncertainty_input_readiness={"status": "READY"},
        baseline_monitoring_pairing={"status": "PAIRED"},
        dimensions={},
        blocking_reasons=[],
        advisory_notes=[],
        assessment_hash="hash_prereq_test",
        is_locked=True,
        locked_at=datetime.now(timezone.utc),
    )
    db_session.add(prereq)
    await db_session.flush()

    # 3. Evaluate Net GHG Preview
    eval_res = await AgricultureService.evaluate_net_ghg_reductions_and_removals(
        db=db_session,
        project_id=project.id,
        organization_id=org.id,
        prerequisite_assessment_id=prereq.id,
        verification_period_start=date(2023, 1, 1),
        verification_period_end=date(2024, 12, 31),
        fossil_fuel_activities_bsl=[{"quantity": 40000, "emission_factor_tco2e_per_unit": 0.001}],
        fossil_fuel_activities_wp=[{"quantity": 20000, "emission_factor_tco2e_per_unit": 0.001}],
        leakage_data={"production_decline_leakage_tco2e_yr": 2.0},
        npr_rating_pct=Decimal("15.0000"),
    )

    assert eval_res["status"] == "EVALUATED"
    assert eval_res["total_baseline_emissions_tco2e"] == Decimal("80.0000")  # 2 years * 40/yr
    assert eval_res["total_project_emissions_tco2e"] == Decimal("40.0000")   # 2 years * 20/yr
    assert eval_res["gross_reductions_er_tco2e"] == Decimal("40.0000")  # 2 years * 20/yr
    assert eval_res["total_leakage_tco2e"] == Decimal("4.0000")        # 2 years * 2/yr
    assert eval_res["net_reductions_ernet_tco2e"] == Decimal("36.0000")
    assert eval_res["vcu_readiness_status"] == "CALCULATED"
    assert len(eval_res["vintages"]) == 2

    # 4. Finalize Authoritative Record
    final_res = await AgricultureService.finalize_net_ghg_reductions_and_removals(
        db=db_session,
        project_id=project.id,
        organization_id=org.id,
        user_id=None,
        user_role="PROJECT_MANAGER",
        prerequisite_assessment_id=prereq.id,
        verification_period_start=date(2023, 1, 1),
        verification_period_end=date(2024, 12, 31),
        fossil_fuel_activities_bsl=[{"quantity": 40000, "emission_factor_tco2e_per_unit": 0.001}],
        fossil_fuel_activities_wp=[{"quantity": 20000, "emission_factor_tco2e_per_unit": 0.001}],
        leakage_data={"production_decline_leakage_tco2e_yr": 2.0},
        npr_rating_pct=Decimal("15.0000"),
    )

    assert final_res.id is not None
    assert final_res.result_status == "CALCULATED"
    assert final_res.total_net_ghg_errnet_tco2e == Decimal("36.0000")
    assert len(final_res.vintages) == 2
    assert final_res.vintages[0].vintage_year in (2023, 2024)

    # 5. Idempotency Check: Calling finalize again with identical parameters returns existing record
    idempotent_res = await AgricultureService.finalize_net_ghg_reductions_and_removals(
        db=db_session,
        project_id=project.id,
        organization_id=org.id,
        user_id=None,
        user_role="PROJECT_MANAGER",
        prerequisite_assessment_id=prereq.id,
        verification_period_start=date(2023, 1, 1),
        verification_period_end=date(2024, 12, 31),
        fossil_fuel_activities_bsl=[{"quantity": 40000, "emission_factor_tco2e_per_unit": 0.001}],
        fossil_fuel_activities_wp=[{"quantity": 20000, "emission_factor_tco2e_per_unit": 0.001}],
        leakage_data={"production_decline_leakage_tco2e_yr": 2.0},
        npr_rating_pct=Decimal("15.0000"),
    )
    assert idempotent_res.id == final_res.id

    # 6. Segregation of Duties: FIELD_AGENT cannot finalize Net GHG
    with pytest.raises(HTTPException) as exc_info:
        await AgricultureService.finalize_net_ghg_reductions_and_removals(
            db=db_session,
            project_id=project.id,
            organization_id=org.id,
            user_id=None,
            user_role="FIELD_AGENT",
            prerequisite_assessment_id=prereq.id,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_tenant_isolation_adversarial_rejection(db_session):
    """Proves that supplying a prerequisite assessment from a foreign tenant fails closed."""
    org_a = Organization(id=uuid.uuid4(), name=f"Org A {uuid.uuid4().hex[:4]}")
    org_b = Organization(id=uuid.uuid4(), name=f"Org B {uuid.uuid4().hex[:4]}")
    db_session.add_all([org_a, org_b])

    project_a = Project(id=uuid.uuid4(), organization_id=org_a.id, name="Project A", project_code=f"PRJ-A-{uuid.uuid4().hex[:4]}", country="USA")
    project_b = Project(id=uuid.uuid4(), organization_id=org_b.id, name="Project B", project_code=f"PRJ-B-{uuid.uuid4().hex[:4]}", country="USA")
    db_session.add_all([project_a, project_b])

    prereq_foreign = AgriculturePrerequisiteAssessment(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        project_id=project_b.id,
        assessment_code="PREREQ-B",
        version=1,
        status="LOCKED",
        overall_readiness="READY",
        methodology_code="VM0042",
        methodology_version="2.2",
        corrections_clarifications_version="2026-06-11",
        rule_set_version="VM0042_V2.2_RULES_CC20260611_V1.0",
        vcs_standard_version="4.7",
        vcs_resolution_metadata={},
        quantification_route_map={},
        esm_input_dossier={},
        sampling_design_assessment={},
        uncertainty_input_readiness={},
        baseline_monitoring_pairing={},
        dimensions={},
        blocking_reasons=[],
        advisory_notes=[],
        assessment_hash="foreign_hash",
        is_locked=True,
    )
    db_session.add(prereq_foreign)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await AgricultureService.evaluate_net_ghg_reductions_and_removals(
            db=db_session,
            project_id=project_a.id,
            organization_id=org_a.id,
            prerequisite_assessment_id=prereq_foreign.id,
        )
    assert exc_info.value.status_code == 404


# =============================================================================
# 7. Targeted Unit Tests for VM0042 Equations 37–43 & Section 8.7 (Eqs 75–79)
# =============================================================================

def test_eq37_exact_identity():
    """
    VM0042 v2.2 Equation 37: Gross GHG emission reductions before leakage.
    ER_t = sum(Delta_E_sources,t) + (1 - I(Delta_CO2_wp))*(Delta_CO2_wp,t - Delta_CO2_bsl,t)
           + I(Delta_CO2_wp)*max(0, -Delta_CO2_bsl,t)
    Verifies:
    1. Pure sources: Delta_E_sources = 40.0, Delta_CO2_wp = 1833.34, Delta_CO2_bsl = 0, I = 1
       -> ER_t = 40.0 + 1 * max(0, -0) = 40.0000 tCO2e/yr.
    2. Depleting baseline: Delta_E_sources = 10.0, Delta_CO2_bsl = -15.0, Delta_CO2_wp = 20.0, I = 1
       -> ER_t = 10.0 + max(0, -(-15.0)) = 10.0 + 15.0 = 25.0000 tCO2e/yr (avoided baseline loss).
    3. Negative cumulative project stock (I = 0): Delta_E_sources = 10.0, Delta_CO2_bsl = -20.0, Delta_CO2_wp = -5.0, I = 0
       -> ER_t = 10.0 + (-5.0 - (-20.0)) = 10.0 + 15.0 = 25.0000 tCO2e/yr.
    4. Proves ER_t is NOT a simple baseline emissions - project emissions.
    """
    # Case 1: Standard canonical reference
    er1, stock_term1 = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("40.0000"),
        eq44_bsl_total_tco2e=Decimal("0.0000"),
        eq45_wp_total_tco2e=Decimal("1833.3400"),
        i_delta_co2_wp=1,
    )
    assert er1 == Decimal("40.0000")
    assert stock_term1 == Decimal("0.0000")

    # Case 2: Depleting baseline with I = 1 (avoided baseline stock loss)
    er2, stock_term2 = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("10.0000"),
        eq44_bsl_total_tco2e=Decimal("-15.0000"),
        eq45_wp_total_tco2e=Decimal("20.0000"),
        i_delta_co2_wp=1,
    )
    assert er2 == Decimal("25.0000")
    assert stock_term2 == Decimal("15.0000")

    # Case 3: Negative cumulative project stock (I = 0)
    er3, stock_term3 = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("10.0000"),
        eq44_bsl_total_tco2e=Decimal("-20.0000"),
        eq45_wp_total_tco2e=Decimal("-5.0000"),
        i_delta_co2_wp=0,
    )
    assert er3 == Decimal("25.0000")
    assert stock_term3 == Decimal("15.0000")


def test_eq38_is_net_reductions():
    """
    VM0042 v2.2 Equation 38: Net GHG emission reductions ERNET_t = ER_t - LKER_t.
    ER = 40.0000, LKER = 0.0854 -> ERNET = 39.9146.
    """
    ernet = calculate_equation_38_net_reductions(
        er_gross=Decimal("40.0000"),
        lker=Decimal("0.0854"),
    )
    assert ernet == Decimal("39.9146")


def test_eq39_leakage_to_reductions():
    """
    VM0042 v2.2 Equation 39: Leakage allocated to emission reductions.
    LKER_t = TOTAL_LEAKAGE * ER_t / (ER_t + CR_t).
    For total_leakage = 4.0000, ER = 40.0000, CR = 1833.3400:
    LKER = 4.0000 * 40.0000 / 1873.3400 = 0.0854.
    """
    lker = calculate_equation_39_leakage_allocation_er(
        total_leakage=Decimal("4.0000"),
        er_gross=Decimal("40.0000"),
        cr_gross=Decimal("1833.3400"),
    )
    assert lker == Decimal("0.0854")


def test_eq40_is_gross_removals():
    """
    VM0042 v2.2 Equation 40: Gross carbon dioxide removals before leakage.
    CR_t = I(Delta_CO2_wp) * max(0, max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t)).
    1. Active cumulative project carbon stock (I = 1):
       Delta_CO2_wp = 1833.3400, Delta_CO2_bsl = 0.0000 -> CR = 1833.3400.
    2. Inactive cumulative project carbon stock (I = 0):
       Even if annual stock change is +50.0000, cumulative project stock <= 0 (I = 0)
       forces CR_t = 0.0000 (stock gain is accounted in Eq. 37 until cumulative deficit is overcome).
    """
    # Active removal state (I = 1)
    cr_active = calculate_equation_40_gross_removals(
        eq44_bsl_total_tco2e=Decimal("0.0000"),
        eq45_wp_total_tco2e=Decimal("1833.3400"),
        i_delta_co2_wp=1,
    )
    assert cr_active == Decimal("1833.3400")

    # Inactive removal state (I = 0)
    cr_inactive = calculate_equation_40_gross_removals(
        eq44_bsl_total_tco2e=Decimal("0.0000"),
        eq45_wp_total_tco2e=Decimal("1833.3400"),
        i_delta_co2_wp=0,
    )
    assert cr_inactive == Decimal("0.0000")


def test_eq41_is_net_removals():
    """
    VM0042 v2.2 Equation 41: Net carbon dioxide removals CRNET_t = CR_t - LKCR_t.
    CR = 1833.3400, LKCR = 3.9146 -> CRNET = 1829.4254.
    """
    crnet = calculate_equation_41_net_removals(
        cr_gross=Decimal("1833.3400"),
        lkcr=Decimal("3.9146"),
    )
    assert crnet == Decimal("1829.4254")


def test_eq42_leakage_to_removals():
    """
    VM0042 v2.2 Equation 42: Leakage allocated to removals.
    LKCR_t = TOTAL_LEAKAGE * CR_t / (ER_t + CR_t).
    For total_leakage = 4.0000, ER = 40.0000, CR = 1833.3400:
    LKCR = 4.0000 * 1833.3400 / 1873.3400 = 3.9146.
    """
    lkcr = calculate_equation_42_leakage_allocation_cr(
        total_leakage=Decimal("4.0000"),
        er_gross=Decimal("40.0000"),
        cr_gross=Decimal("1833.3400"),
    )
    assert lkcr == Decimal("3.9146")


def test_eq43_total_net_reconciliation():
    """
    VM0042 v2.2 Equation 43: Total Net GHG Reductions and Removals ERRNET_t = ERNET_t + CRNET_t.
    ERNET = 39.9146, CRNET = 1829.4254 -> ERRNET = 1869.3400.
    Reconciles exactly to (ER + CR) - TOTAL_LEAKAGE = 1873.3400 - 4.0000 = 1869.3400.
    """
    ernet = Decimal("39.9146")
    crnet = Decimal("1829.4254")
    errnet = calculate_equation_43_total_net(ernet=ernet, crnet=crnet)
    assert errnet == Decimal("1869.3400")

    er_gross = Decimal("40.0000")
    cr_gross = Decimal("1833.3400")
    total_leakage = Decimal("4.0000")
    assert errnet == (er_gross + cr_gross) - total_leakage


def test_cc20260611_lkdisp_included_in_eq39():
    """
    11 June 2026 C&C: Eq. 39 must include production decline leakage LKdisp,t via VMD0054 Eq. 10.
    TOTAL_LEAKAGE = LEOA + LKdisp + LEBR.
    LEOA = 1.0, LKdisp = 2.0, LEBR = 1.0 -> TOTAL_LEAKAGE = 4.0.
    LKER = 4.0 * (40 / (40 + 1833.34)) = 0.0854.
    """
    leakage = LeakageInputData(
        leoa_tco2e_yr=Decimal("1.0000"),
        production_decline_leakage_tco2e_yr=Decimal("2.0000"),
        biomass_residue_diversion_tco2e_yr=Decimal("1.0000"),
        vmd0054_version="1.0",
        production_decline_status="CALCULATED_VMD0054_EQ10",
    )
    tot, leoa, lkdisp, lebr = calculate_total_leakage(leakage)
    assert tot == Decimal("4.0000")
    assert lkdisp == Decimal("2.0000")

    lker = calculate_equation_39_leakage_allocation_er(
        total_leakage=tot,
        er_gross=Decimal("40.0000"),
        cr_gross=Decimal("1833.3400"),
    )
    assert lker == Decimal("0.0854")


def test_cc20260611_lkdisp_included_in_eq42():
    """
    11 June 2026 C&C: Eq. 42 must include production decline leakage LKdisp,t.
    LKCR = 4.0 * (1833.34 / (40 + 1833.34)) = 3.9146.
    """
    leakage = LeakageInputData(
        leoa_tco2e_yr=Decimal("1.0000"),
        production_decline_leakage_tco2e_yr=Decimal("2.0000"),
        biomass_residue_diversion_tco2e_yr=Decimal("1.0000"),
        vmd0054_version="1.0",
    )
    tot, _, lkdisp, _ = calculate_total_leakage(leakage)
    assert tot == Decimal("4.0000")
    assert lkdisp == Decimal("2.0000")

    lkcr = calculate_equation_42_leakage_allocation_cr(
        total_leakage=tot,
        er_gross=Decimal("40.0000"),
        cr_gross=Decimal("1833.3400"),
    )
    assert lkcr == Decimal("3.9146")


def test_zero_denominator_no_50_50_fallback():
    """
    Proves that when ER + CR == 0, the system NEVER performs an arbitrary 50/50 fallback.
    - If total_leakage == 0: returns (0, 0, 'NO_BENEFIT_NO_LEAKAGE').
    - If total_leakage > 0: raises NetGHGCalculationError with LEAKAGE_ALLOCATION_UNDEFINED.
    """
    # Case 1: 0 benefit, 0 leakage
    lker, lkcr, status = allocate_leakage_eq39_eq42(
        total_leakage=Decimal("0.0000"),
        er_gross=Decimal("0.0000"),
        cr_gross=Decimal("0.0000"),
    )
    assert lker == Decimal("0.0000")
    assert lkcr == Decimal("0.0000")
    assert status == "NO_BENEFIT_NO_LEAKAGE"

    # Case 2: 0 benefit, positive leakage
    with pytest.raises(NetGHGCalculationError) as exc_info:
        allocate_leakage_eq39_eq42(
            total_leakage=Decimal("10.0000"),
            er_gross=Decimal("0.0000"),
            cr_gross=Decimal("0.0000"),
        )
    assert exc_info.value.code == "LEAKAGE_ALLOCATION_UNDEFINED"
    assert exc_info.value.details.get("status") == "AUTHORITATIVE_NET_GHG_BLOCKED"


def test_zero_benefit_zero_leakage_safe():
    """
    Proves that a project with ER=0, CR=0, and TOTAL_LEAKAGE=0 is handled safely
    as an explicit NO_BENEFIT_NO_LEAKAGE degenerate state without numerical error.
    """
    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=[],
        fossil_fuel_wp=[],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("0.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=LeakageInputData(activity_displacement_tco2e_yr=Decimal("0.0000")),
    )
    assert res.gross_reductions_er_tco2e == Decimal("0.0000")
    assert res.gross_removals_cr_tco2e == Decimal("0.0000")
    assert res.total_leakage_tco2e == Decimal("0.0000")
    assert res.leakage_allocation_er_lker_tco2e == Decimal("0.0000")
    assert res.leakage_allocation_cr_lkcr_tco2e == Decimal("0.0000")
    assert res.leakage_allocation_status == "NO_BENEFIT_NO_LEAKAGE"
    assert res.total_net_ghg_errnet_tco2e == Decimal("0.0000")


def test_zero_benefit_positive_leakage_blocks():
    """
    Proves that a project with ER=0, CR=0, and TOTAL_LEAKAGE > 0 fails closed
    and blocks calculation as LEAKAGE_ALLOCATION_UNDEFINED.
    """
    with pytest.raises(NetGHGCalculationError) as exc_info:
        evaluate_single_vintage_net_ghg(
            vintage_year=2024,
            fossil_fuel_bsl=[],
            fossil_fuel_wp=[],
            liming_bsl=LimingActivity(is_verified_zero=True),
            liming_wp=LimingActivity(is_verified_zero=True),
            fertilizer_bsl=[],
            fertilizer_wp=[],
            nfixing_bsl=[],
            nfixing_wp=[],
            manure_bsl=[],
            manure_wp=[],
            enteric_bsl=[],
            enteric_wp=[],
            burning_bsl=[],
            burning_wp=[],
            methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
            methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
            soc_stock_change_bsl_tco2e=Decimal("0.0000"),
            soc_stock_change_wp_tco2e=Decimal("0.0000"),
            soc_uncertainty_deduction_fraction=Decimal("0.000000"),
            soc_sign_indicator=1,
            woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
            prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
            leakage=LeakageInputData(activity_displacement_tco2e_yr=Decimal("5.0000")),
        )
    assert exc_info.value.code == "LEAKAGE_ALLOCATION_UNDEFINED"
    assert exc_info.value.details.get("status") == "AUTHORITATIVE_NET_GHG_BLOCKED"


def test_eq75_exact_buffer_reductions():
    """
    VM0042 Section 8.7 Eq. 75: Buffer deduction for emission reductions.
    BuER,t is based on qualifying carbon-stock-change reduction terms and NPR%.
    It is NOT a percentage of generic net emission reductions (e.g. fossil fuel).
    - If stock reduction term = 0: BuER = 0.
    - If stock reduction term = 20.0 and NPR = 15%: BuER = 20.0 * 0.15 = 3.0000 tCO2e/yr.
    """
    # Non-stock emission reductions -> 0 buffer
    bu_er_zero = calculate_equation_75_buffer_reductions(
        stock_reductions_term=Decimal("0.0000"),
        npr_fraction=Decimal("0.1500"),
    )
    assert bu_er_zero == Decimal("0.0000")

    # Qualifying stock reduction -> NPR applies
    bu_er_stock = calculate_equation_75_buffer_reductions(
        stock_reductions_term=Decimal("20.0000"),
        npr_fraction=Decimal("0.1500"),
    )
    assert bu_er_stock == Decimal("3.0000")


def test_eq76_exact_buffer_removals():
    """
    VM0042 Section 8.7 Eq. 76: Buffer deduction for removals.
    BuCR,t = I(Delta_CO2_wp) * [max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t)] * NPR% = CR_t * NPR%.
    Based on gross removals CR_t before leakage, NOT CRNET * NPR%.
    For CR = 1833.3400 and NPR = 15%:
    BuCR = 1833.3400 * 0.15 = 275.0010 tCO2e/yr.
    (Proves correction from erroneous CRNET * 15% = 1829.4254 * 0.15 = 274.4138).
    """
    bu_cr = calculate_equation_76_buffer_removals(
        cr_gross=Decimal("1833.3400"),
        npr_fraction=Decimal("0.1500"),
    )
    assert bu_cr == Decimal("275.0010")
    # Assert it does NOT equal the incorrect CRNET basis
    incorrect_crnet_basis = (Decimal("1829.4254") * Decimal("0.1500")).quantize(Decimal("0.0001"))
    assert bu_cr != incorrect_crnet_basis


def test_eq77_reduction_vcu_ready():
    """
    VM0042 Section 8.7 Eq. 77: Reduction-side VCU eligible quantity.
    VCUER,t = ERNET_t - BuER,t.
    ERNET = 39.9146, BuER = 0.0000 -> VCUER = 39.9146.
    """
    vcu_er = calculate_equation_77_vcu_reductions(
        ernet=Decimal("39.9146"),
        bu_er=Decimal("0.0000"),
    )
    assert vcu_er == Decimal("39.9146")


def test_eq78_removal_vcu_ready():
    """
    VM0042 Section 8.7 Eq. 78: Removal-side VCU eligible quantity.
    VCUCR,t = CRNET_t - BuCR,t.
    CRNET = 1829.4254, BuCR = 275.0010 -> VCUCR = 1554.4244.
    """
    vcu_cr = calculate_equation_78_vcu_removals(
        crnet=Decimal("1829.4254"),
        bu_cr=Decimal("275.0010"),
    )
    assert vcu_cr == Decimal("1554.4244")


def test_eq79_total_vcu_ready():
    """
    VM0042 Section 8.7 Eq. 79: Total internal VCU eligible quantity.
    VCU_t = VCUER,t + VCUCR,t.
    VCUER = 39.9146, VCUCR = 1554.4244 -> VCU_total = 1594.3390.
    Reconciles exactly to ERRNET - Total_Buffer = 1869.3400 - 275.0010 = 1594.3390.
    """
    vcu_tot = calculate_equation_79_total_vcu(
        vcu_er=Decimal("39.9146"),
        vcu_cr=Decimal("1554.4244"),
    )
    assert vcu_tot == Decimal("1594.3390")
    errnet = Decimal("1869.3400")
    tot_buf = Decimal("275.0010")
    assert vcu_tot == errnet - tot_buf


def test_npr_not_defaulted():
    """
    Proves fail-closed behavior when NPR is not configured:
    NPR% must NEVER default to 15%. When omitted, vcu_readiness_status must be
    NOT_CONFIGURED_MISSING_NPR and buffer/VCU values must be None.
    """
    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("40000.0000"), "LITERS", Decimal("0.001"), "S")],
        fossil_fuel_wp=[FossilFuelActivity("DIESEL", Decimal("20000.0000"), "LITERS", Decimal("0.001"), "S")],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("40.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=LeakageInputData(production_decline_leakage_tco2e_yr=Decimal("2.0000")),
        npr_input=None,  # Explicitly omitted
    )
    assert res.npr_rating_pct is None
    assert res.buffer_deduction_reductions_tco2e is None
    assert res.buffer_deduction_removals_tco2e is None
    assert res.total_buffer_deduction_tco2e is None
    assert res.internal_vcu_eligible_total_tco2e is None
    assert res.vcu_readiness_status == "NOT_CONFIGURED_MISSING_NPR"


def test_year_specific_vintage_inputs():
    """
    VM0042 Section 8: Multi-year verification periods must quantify reductions and removals
    by year using explicit year-specific activity data, rather than uniform calendar-day proration.
    Vintage 2023: Fuel reduction = 10 tCO2e, SOC removal = 800 tCO2e, Leakage = 1.0 tCO2e.
    Vintage 2024: Fuel reduction = 30 tCO2e, SOC removal = 1033.34 tCO2e, Leakage = 3.0 tCO2e.
    """
    npr = NPRRiskAssessmentInput(Decimal("15.0000"), uuid.uuid4(), "APPROVED", "2026-10-01")

    # Vintage 2023
    v2023 = evaluate_single_vintage_net_ghg(
        vintage_year=2023,
        fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("30000.0000"), "LITERS", Decimal("0.001"), "S")],
        fossil_fuel_wp=[FossilFuelActivity("DIESEL", Decimal("20000.0000"), "LITERS", Decimal("0.001"), "S")],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("800.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=LeakageInputData(production_decline_leakage_tco2e_yr=Decimal("1.0000")),
        npr_input=npr,
    )
    assert v2023.gross_reductions_er_tco2e == Decimal("10.0000")
    assert v2023.gross_removals_cr_tco2e == Decimal("800.0000")
    assert v2023.total_leakage_tco2e == Decimal("1.0000")

    # Vintage 2024
    v2024 = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("50000.0000"), "LITERS", Decimal("0.001"), "S")],
        fossil_fuel_wp=[FossilFuelActivity("DIESEL", Decimal("20000.0000"), "LITERS", Decimal("0.001"), "S")],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("1033.3400"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("800.0000"),
        leakage=LeakageInputData(production_decline_leakage_tco2e_yr=Decimal("3.0000")),
        npr_input=npr,
    )
    assert v2024.gross_reductions_er_tco2e == Decimal("30.0000")
    assert v2024.gross_removals_cr_tco2e == Decimal("1033.3400")
    assert v2024.total_leakage_tco2e == Decimal("3.0000")


def test_vintage_sum_reconciles_to_period():
    """
    Proves that the sum of discrete annual vintage quantifications reconciles exactly
    to the verification period totals across every single component.
    """
    npr = NPRRiskAssessmentInput(Decimal("15.0000"), uuid.uuid4(), "APPROVED", "2026-10-01")

    v2023 = evaluate_single_vintage_net_ghg(
        vintage_year=2023,
        fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("30000.0000"), "LITERS", Decimal("0.001"), "S")],
        fossil_fuel_wp=[FossilFuelActivity("DIESEL", Decimal("20000.0000"), "LITERS", Decimal("0.001"), "S")],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("800.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=LeakageInputData(production_decline_leakage_tco2e_yr=Decimal("1.0000")),
        npr_input=npr,
    )

    v2024 = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("50000.0000"), "LITERS", Decimal("0.001"), "S")],
        fossil_fuel_wp=[FossilFuelActivity("DIESEL", Decimal("20000.0000"), "LITERS", Decimal("0.001"), "S")],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("1033.3400"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("800.0000"),
        leakage=LeakageInputData(production_decline_leakage_tco2e_yr=Decimal("3.0000")),
        npr_input=npr,
    )

    agg = aggregate_verification_period_net_ghg(
        project_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        start_date=date(2023, 1, 1),
        end_date=date(2024, 12, 31),
        annual_vintages=[v2023, v2024],
        applicability_report={},
        npr_input=npr,
    )

    # Component-by-component reconciliation
    assert agg.gross_reductions_er_tco2e == v2023.gross_reductions_er_tco2e + v2024.gross_reductions_er_tco2e
    assert agg.gross_removals_cr_tco2e == v2023.gross_removals_cr_tco2e + v2024.gross_removals_cr_tco2e
    assert agg.total_leakage_tco2e == v2023.total_leakage_tco2e + v2024.total_leakage_tco2e
    assert agg.leakage_allocation_er_lker_tco2e == v2023.leakage_allocation_er_lker_tco2e + v2024.leakage_allocation_er_lker_tco2e
    assert agg.leakage_allocation_cr_lkcr_tco2e == v2023.leakage_allocation_cr_lkcr_tco2e + v2024.leakage_allocation_cr_lkcr_tco2e
    assert agg.net_reductions_ernet_tco2e == v2023.net_reductions_ernet_tco2e + v2024.net_reductions_ernet_tco2e
    assert agg.net_removals_crnet_tco2e == v2023.net_removals_crnet_tco2e + v2024.net_removals_crnet_tco2e
    assert agg.total_net_ghg_errnet_tco2e == v2023.total_net_ghg_errnet_tco2e + v2024.total_net_ghg_errnet_tco2e
    assert agg.total_buffer_deduction_tco2e == v2023.total_buffer_deduction_tco2e + v2024.total_buffer_deduction_tco2e
    assert agg.internal_vcu_eligible_total_tco2e == v2023.internal_vcu_eligible_total_tco2e + v2024.internal_vcu_eligible_total_tco2e


# =============================================================================
# Targeted Tests: VM0042 Eq. 37, Eq. 75 & VMD0054 Resolution Closure
# =============================================================================

def test_eq37_i1_current_year_project_loss_exact():
    """
    VM0042 v2.2 Eq. 37 Critical Branch Test:
    Cumulative project stock change > 0, therefore I(Delta_CO2_wp) = 1.
    Current-year project stock change is negative: Delta_CO2_wp,t = -5.0000.
    Baseline stock change: Delta_CO2_bsl,t = -10.0000.
    Ignoring other source reductions (Delta_E_sources = 0):
    Official stock reduction term:
        min(0, -5) - min(0, -10) = -5 - (-10) = +5.0000 tCO2e/yr.
    The simplified implementation:
        max(0, -(-10)) = +10.0000 tCO2e/yr is WRONG (ignored project loss).
    Production must return the official result (+5.0000).
    """
    er, stock_term = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("0.0000"),
        eq44_bsl_total_tco2e=Decimal("-10.0000"),
        eq45_wp_total_tco2e=Decimal("-5.0000"),
        i_delta_co2_wp=1,
    )
    assert stock_term == Decimal("5.0000")
    assert er == Decimal("5.0000")
    # Explicitly prove production rejected the erroneous simplified form (+10.0000)
    assert stock_term != Decimal("10.0000")


def test_eq37_i0_exact_branch():
    """
    VM0042 v2.2 Eq. 37 I=0 Branch Test:
    When I(Delta_CO2_wp) = 0, official stock-change reduction term is:
        [min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t)]
        + [max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t)]
    Which algebraically equals Delta_CO2_wp,t - Delta_CO2_bsl,t for this branch.
    """
    # Vector A: Both negative losses: wp = -5, bsl = -20
    # min(-5) - min(-20) = 15; max(-5) - max(-20) = 0 -> 15.0000
    er_a, stock_term_a = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("10.0000"),
        eq44_bsl_total_tco2e=Decimal("-20.0000"),
        eq45_wp_total_tco2e=Decimal("-5.0000"),
        i_delta_co2_wp=0,
    )
    assert stock_term_a == Decimal("15.0000")
    assert er_a == Decimal("25.0000")

    # Vector B: Project positive, Baseline negative: wp = 15, bsl = -10
    # min(0, 15) - min(0, -10) = 0 - (-10) = 10; max(0, 15) - max(0, -10) = 15 - 0 = 15 -> 25.0000
    er_b, stock_term_b = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("0.0000"),
        eq44_bsl_total_tco2e=Decimal("-10.0000"),
        eq45_wp_total_tco2e=Decimal("15.0000"),
        i_delta_co2_wp=0,
    )
    assert stock_term_b == Decimal("25.0000")
    assert er_b == Decimal("25.0000")


def test_eq37_literal_formula_parity():
    """
    Verifies full parity of official Eq. 37 formula with canonical positive reference:
    Delta_CO2_wp = 1833.3400, Delta_CO2_bsl = 0.0000, I = 1.
    min(0, 1833.34) - min(0, 0) = 0.0000.
    With Delta_E_sources = 40.0000 -> ER = 40.0000 tCO2e/yr.
    Preserves 100% of approved Phase 3B-3 quantification benchmark numbers.
    """
    er, stock_term = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("40.0000"),
        eq44_bsl_total_tco2e=Decimal("0.0000"),
        eq45_wp_total_tco2e=Decimal("1833.3400"),
        i_delta_co2_wp=1,
    )
    assert stock_term == Decimal("0.0000")
    assert er == Decimal("40.0000")


def test_eq75_literal_i1_branch():
    """
    VM0042 Section 8.7 Eq. 75 literal I=1 branch:
    BuER,t = I(Delta_CO2_wp) * [min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t)] * NPR%.
    For I=1, Delta_CO2_wp = 0, Delta_CO2_bsl = -10, NPR = 15%:
    Stock term = min(0, 0) - min(0, -10) = 0 - (-10) = 10.0000.
    BuER = 10.0000 * 0.15 = 1.5000 tCO2e/yr.
    """
    bu_er_direct = calculate_equation_75_buffer_reductions(
        stock_reductions_term=Decimal("10.0000"),
        npr_fraction=Decimal("0.1500"),
    )
    assert bu_er_direct == Decimal("1.5000")

    bu_er_keyword = calculate_equation_75_buffer_reductions(
        eq44_bsl_total_tco2e=Decimal("-10.0000"),
        eq45_wp_total_tco2e=Decimal("0.0000"),
        i_delta_co2_wp=1,
        npr_fraction=Decimal("0.1500"),
    )
    assert bu_er_keyword == Decimal("1.5000")


def test_eq75_literal_i0_branch():
    """
    VM0042 Section 8.7 Eq. 75 literal I=0 branch:
    BuER,t = (1 - I) * [min(0, wp) - min(0, bsl) + max(0, wp) - max(0, bsl)] * NPR%.
    For I=0, Delta_CO2_wp = -5, Delta_CO2_bsl = -20, NPR = 15%:
    Stock term = 15.0000.
    BuER = 15.0000 * 0.15 = 2.2500 tCO2e/yr.
    """
    bu_er = calculate_equation_75_buffer_reductions(
        eq44_bsl_total_tco2e=Decimal("-20.0000"),
        eq45_wp_total_tco2e=Decimal("-5.0000"),
        i_delta_co2_wp=0,
        npr_fraction=Decimal("0.1500"),
    )
    assert bu_er == Decimal("2.2500")


def test_eq75_no_outer_zero_clamp():
    """
    VM0042 Section 8.7 Eq. 75 Adverse Vector Test:
    Removes outer MAX(0, ...).
    I = 1, Delta_CO2_wp,t = -10.0000, Delta_CO2_bsl,t = -2.0000, NPR = 15%.
    Official stock term:
        min(0, -10) - min(0, -2) = -10 - (-2) = -8.0000.
    BuER,t = -8.0000 * 0.15 = -1.2000 tCO2e/yr.
    Proves production reproduces the literal Eq. 75 result and does NOT clamp to zero.
    """
    bu_er = calculate_equation_75_buffer_reductions(
        eq44_bsl_total_tco2e=Decimal("-2.0000"),
        eq45_wp_total_tco2e=Decimal("-10.0000"),
        i_delta_co2_wp=1,
        npr_fraction=Decimal("0.1500"),
    )
    assert bu_er == Decimal("-1.2000")
    assert bu_er != Decimal("0.0000")


def test_vmd0054_v11_current_route():
    """
    VMD0054 v1.1 Current Active Route:
    Resolves to VMD0054_1_1_CURRENT, uses source equation VMD0054_V1.1_EQ13,
    and executes authoritative pipeline with calculation hash and persisted metadata.
    """
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input=VMD0054Version.VMD0054_1_1_CURRENT,
    )
    assert ver == VMD0054Version.VMD0054_1_1_CURRENT
    assert eq == "VMD0054_V1.1_EQ13"
    assert ruleset == "VMD0054_V1.1_ACTIVE"

    # Pipeline execution
    npr = NPRRiskAssessmentInput(
        npr_rating_pct=Decimal("15.0000"),
        risk_assessment_id=uuid.uuid4(),
        approval_status="APPROVED",
        effective_date="2025-01-01",
    )
    leakage = LeakageInputData(
        production_decline_leakage_tco2e_yr=Decimal("2.0000"),
        vmd0054_version=VMD0054Version.VMD0054_1_1_CURRENT,
    )
    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("10000.0000"), "LITERS", Decimal("0.001"), "S")],
        fossil_fuel_wp=[],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("50.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=leakage,
        npr_input=npr,
    )
    assert res.vmd0054_version == "VMD0054_1_1_CURRENT"
    assert res.vmd0054_source_equation == "VMD0054_V1.1_EQ13"
    assert res.vmd0054_effective_ruleset == "VMD0054_V1.1_ACTIVE"
    assert res.vcu_readiness_status == "CALCULATED"


def test_vmd0054_v10_transition_route():
    """
    VMD0054 v1.0 Transition Route:
    Project meeting Verra submission deadlines / transition conditions
    resolves to VMD0054_1_0_TRANSITION_ELIGIBLE, uses source equation VMD0054_V1.0_EQ10,
    and executes VM0042 Eq. 36 integration.
    """
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 12, 1),
        project_request_type="REGISTRATION",
        verra_request_id="VERRA_PRE_2027_SUBMISSION_REQ_001",
        transition_document_id="VERRA_TRANSITION_DOC_8849",
        transition_evidence="VERRA_TRANSITION_DOC_8849",
    )
    assert ver == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert eq == "VMD0054_V1.0_EQ10"
    assert "REGISTRATION" in basis
    assert ruleset == "VMD0054_V1.0_TRANSITION"

    npr = NPRRiskAssessmentInput(
        npr_rating_pct=Decimal("15.0000"),
        risk_assessment_id=uuid.uuid4(),
        approval_status="APPROVED",
        effective_date="2025-01-01",
    )
    leakage = LeakageInputData(
        production_decline_leakage_tco2e_yr=Decimal("2.0000"),
        vmd0054_version="1.0",
        submission_date=date(2026, 12, 1),
        project_request_type="REGISTRATION",
        verra_request_id="VERRA_PRE_2027_SUBMISSION_REQ_001",
        transition_document_id="VERRA_TRANSITION_DOC_8849",
        transition_evidence="VERRA_TRANSITION_DOC_8849",
    )
    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("10000.0000"), "LITERS", Decimal("0.001"), "S")],
        fossil_fuel_wp=[],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("0.0000"),
        soc_stock_change_wp_tco2e=Decimal("50.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
        leakage=leakage,
        npr_input=npr,
    )
    assert res.vmd0054_version == "VMD0054_1_0_TRANSITION_ELIGIBLE"
    assert res.vmd0054_source_equation == "VMD0054_V1.0_EQ10"
    assert "REGISTRATION" in res.vmd0054_transition_basis
    assert res.vmd0054_effective_ruleset == "VMD0054_V1.0_TRANSITION"


def test_vmd0054_unresolved_transition_blocks():
    """
    VMD0054 Unresolved Transition Fail-Closed Test:
    When a project requests v1.0 but transition eligibility cannot be determined,
    it resolves to VMD0054_VERSION_UNRESOLVED and authoritative leakage calculation
    must block (AUTHORITATIVE_NET_GHG_BLOCKED). Does not default to v1.0.
    """
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        transition_eligible=None,
        transition_basis=None,
    )
    assert ver == VMD0054Version.VMD0054_VERSION_UNRESOLVED
    assert eq == "UNRESOLVED"

    # In authoritative leakage check, must raise NetGHGCalculationError
    leakage = LeakageInputData(
        production_decline_leakage_tco2e_yr=Decimal("2.0000"),
        vmd0054_version="1.0",
        vmd0054_transition_eligible=None,
        vmd0054_transition_basis=None,
    )
    with pytest.raises(NetGHGCalculationError) as exc_info:
        calculate_total_leakage(leakage, authoritative=True)
    assert exc_info.value.code == "VMD0054_VERSION_UNRESOLVED"
    assert exc_info.value.details.get("status") == "AUTHORITATIVE_NET_GHG_BLOCKED"

    # In full evaluate_single_vintage_net_ghg, must also fail closed
    npr = NPRRiskAssessmentInput(
        npr_rating_pct=Decimal("15.0000"),
        risk_assessment_id=uuid.uuid4(),
        approval_status="APPROVED",
        effective_date="2025-01-01",
    )
    with pytest.raises(NetGHGCalculationError) as exc_info:
        evaluate_single_vintage_net_ghg(
            vintage_year=2024,
            fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("10000.0000"), "LITERS", Decimal("0.001"), "S")],
            fossil_fuel_wp=[],
            liming_bsl=LimingActivity(is_verified_zero=True),
            liming_wp=LimingActivity(is_verified_zero=True),
            fertilizer_bsl=[],
            fertilizer_wp=[],
            nfixing_bsl=[],
            nfixing_wp=[],
            manure_bsl=[],
            manure_wp=[],
            enteric_bsl=[],
            enteric_wp=[],
            burning_bsl=[],
            burning_wp=[],
            methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
            methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
            soc_stock_change_bsl_tco2e=Decimal("0.0000"),
            soc_stock_change_wp_tco2e=Decimal("50.0000"),
            soc_uncertainty_deduction_fraction=Decimal("0.000000"),
            soc_sign_indicator=1,
            woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
            prior_cumulative_project_stock_change_tco2e=Decimal("0.0000"),
            leakage=leakage,
            npr_input=npr,
        )
    assert exc_info.value.code == "VMD0054_VERSION_UNRESOLVED"
    assert exc_info.value.details.get("status") == "AUTHORITATIVE_NET_GHG_BLOCKED"


# =============================================================================
# 7. Agriculture Phase 3B-3 Final Closure Targeted Tests
# - VM0042 Eq. 37 Literal Unclamped Formulation (Negative Result Preservation)
# - VMD0054 v1.1 Eq. 11 (ΔCS in t C/ha) vs. Eq. 13 (LK_t in tCO2e)
# - VMD0054 v1.0 Eq. 10 Cumulative LK_t (Transition Route)
# - VM0042 Eq. 36 LKdisp,t Integration and Unit Preservation
# - Transition Governance Submission Deadline & Evidence Enforcement
# - Direct Numeric Hand-Calculation Parity
# =============================================================================

def test_eq37_negative_result_not_clamped():
    """
    Proves that when the official VM0042 Eq. 37 formula evaluates to a negative value,
    the production calculator preserves that negative value rather than forcing ER_t = 0.
    Protects against silently discarding adverse annual performance.
    """
    # 1. Direct Unit Test of calculate_equation_37_gross_reductions
    # When I(Delta_CO2_wp) = 1:
    # ER_t = sum(Delta_E_sources,t) + [min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t)]
    # With:
    # Delta_E_sources = 0.0000 (no source reductions)
    # Delta_CO2_wp = -10.0000
    # Delta_CO2_bsl = -2.0000
    # min(0, -10.0) - min(0, -2.0) = -10.0 - (-2.0) = -8.0000
    # ER_t = 0.0 + (-8.0000) = -8.0000 tCO2e
    er_gross, stock_term = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("0.0000"),
        eq44_bsl_total_tco2e=Decimal("-2.0000"),
        eq45_wp_total_tco2e=Decimal("-10.0000"),
        i_delta_co2_wp=1,
    )
    assert stock_term == Decimal("-8.0000")
    assert er_gross == Decimal("-8.0000"), "Production must not clamp negative ER_t to 0.0000"
    assert er_gross < Decimal("0.0000")

    # 2. Integration Test through evaluate_single_vintage_net_ghg
    # Same inputs through full vintage evaluation pipeline
    res = evaluate_single_vintage_net_ghg(
        vintage_year=2024,
        fossil_fuel_bsl=[FossilFuelActivity("DIESEL", Decimal("1000.0000"), "LITERS", Decimal("0.001"), "S")],
        fossil_fuel_wp=[FossilFuelActivity("DIESEL", Decimal("1000.0000"), "LITERS", Decimal("0.001"), "S")],
        liming_bsl=LimingActivity(is_verified_zero=True),
        liming_wp=LimingActivity(is_verified_zero=True),
        fertilizer_bsl=[],
        fertilizer_wp=[],
        nfixing_bsl=[],
        nfixing_wp=[],
        manure_bsl=[],
        manure_wp=[],
        enteric_bsl=[],
        enteric_wp=[],
        burning_bsl=[],
        burning_wp=[],
        methanogenesis_bsl=SoilMethanogenesisActivity(is_verified_zero=True),
        methanogenesis_wp=SoilMethanogenesisActivity(is_verified_zero=True),
        soc_stock_change_bsl_tco2e=Decimal("-2.0000"),
        soc_stock_change_wp_tco2e=Decimal("-10.0000"),
        soc_uncertainty_deduction_fraction=Decimal("0.000000"),
        soc_sign_indicator=1,
        woody_pool=WoodyBiomassPoolData(is_verified_zero=True),
        prior_cumulative_project_stock_change_tco2e=Decimal("100.0000"),  # ensures I = 1
        leakage=LeakageInputData(activity_displacement_tco2e_yr=Decimal("0.0000")),
    )
    assert res.total_emission_reductions_from_sources_tco2e == Decimal("0.0000")
    assert res.gross_reductions_er_tco2e == Decimal("-8.0000")
    assert res.gross_removals_cr_tco2e == Decimal("0.0000")
    assert res.net_reductions_ernet_tco2e == Decimal("-8.0000")
    assert res.total_net_ghg_errnet_tco2e == Decimal("-8.0000")


def test_eq37_no_outer_max():
    """
    Tests both branches of VM0042 Eq. 37 to verify neither has an outer MAX(0, ...).
    Branch 1: I(Delta_CO2_wp) = 1
    Branch 2: I(Delta_CO2_wp) = 0
    """
    # Branch 1 (I=1):
    # Delta_E_sources = 5.0, Delta_CO2_wp = -15.0, Delta_CO2_bsl = 0.0
    # stock_term = min(0, -15) - min(0, 0) = -15.0
    # ER_t = 5.0 + (-15.0) = -10.0000 tCO2e
    er1, stock1 = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("5.0000"),
        eq44_bsl_total_tco2e=Decimal("0.0000"),
        eq45_wp_total_tco2e=Decimal("-15.0000"),
        i_delta_co2_wp=1,
    )
    assert er1 == Decimal("-10.0000")
    assert stock1 == Decimal("-15.0000")

    # Branch 2 (I=0):
    # Delta_E_sources = 5.0, Delta_CO2_wp = 10.0, Delta_CO2_bsl = 30.0
    # min(0, 10) - min(0, 30) = 0 - 0 = 0.0
    # max(0, 10) - max(0, 30) = 10 - 30 = -20.0
    # stock_term = 0.0 + (-20.0) = -20.0000
    # ER_t = 5.0 + (-20.0000) = -15.0000 tCO2e
    er0, stock0 = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=Decimal("5.0000"),
        eq44_bsl_total_tco2e=Decimal("30.0000"),
        eq45_wp_total_tco2e=Decimal("10.0000"),
        i_delta_co2_wp=0,
    )
    assert er0 == Decimal("-15.0000")
    assert stock0 == Decimal("-20.0000")


def test_vmd0054_v11_eq11_is_delta_cs_not_leakage():
    """
    VMD0054 v1.1 Equation 11:
    Delta_CS = Delta_C_biomass + Delta_SOC (t C/ha)
    Proves that Eq. 11 calculates carbon stock density difference on converted land,
    NOT cumulative market leakage tCO2e.
    """
    delta_c_biomass = Decimal("1.2500")  # t C/ha
    delta_soc = Decimal("2.7500")        # t C/ha
    delta_cs = calculate_vmd0054_v11_equation_11_delta_cs(
        delta_c_biomass_tc_ha=delta_c_biomass,
        delta_soc_tc_ha=delta_soc,
    )
    assert delta_cs == Decimal("4.0000")
    # Eq. 11 output is in t C/ha, cannot be equated with tCO2e or LK_t
    assert delta_cs != Decimal("14.6667")


def test_vmd0054_v11_eq13_is_cumulative_leakage():
    """
    VMD0054 v1.1 Equation 13:
    LK_t = AL_t * Delta_CS * (44/12) + ELM_t (tCO2e)
    Proves that Eq. 13 calculates cumulative market leakage in tCO2e.
    """
    al_t = Decimal("100.0000")          # ha
    delta_cs = Decimal("3.0000")        # t C/ha
    elm_t = Decimal("100.0000")         # tCO2e
    lk_t = calculate_vmd0054_v11_equation_13_cumulative_leakage(
        al_t_ha=al_t,
        delta_cs_tc_ha=delta_cs,
        elm_t_tco2e=elm_t,
    )
    # AL_t * Delta_CS * (44/12) = 100 * 3 * 3.666666... = 1100.0000 tCO2e
    # LK_t = 1100.0000 + 100.0000 = 1200.0000 tCO2e
    assert lk_t == Decimal("1200.0000")


def test_vmd0054_v10_eq10_is_cumulative_leakage():
    """
    VMD0054 v1.0 Equation 10 (Transition Route):
    LK_t = cumulative leakage up to year t (tCO2e).
    """
    al_t = Decimal("100.0000")          # ha
    delta_cs = Decimal("3.0000")        # t C/ha
    elm_t = Decimal("100.0000")         # tCO2e
    lk_t = calculate_vmd0054_v10_equation_10_cumulative_leakage(
        al_t_ha=al_t,
        delta_cs_tc_ha=delta_cs,
        elm_t_tco2e=elm_t,
    )
    assert lk_t == Decimal("1200.0000")


def test_vm0042_eq36_uses_correct_versioned_lk_output():
    """
    VM0042 Corrected Eq. 36 (11 June 2026 C&C):
    LKdisp,t = MAX(0, LK_t - LK_prior) / years (tCO2e/yr)
    Preserves units:
    LK_t = tCO2e
    LK_prior = tCO2e
    LKdisp,t = tCO2e/yr
    """
    # 1. Normal positive increment
    lkdisp = calculate_vm0042_equation_36_market_leakage(
        lk_t_tco2e=Decimal("1200.0000"),
        lk_prior_tco2e=Decimal("200.0000"),
        verification_period_years=Decimal("2.0000"),
    )
    # (1200 - 200) / 2 = 500.0000 tCO2e/yr
    assert lkdisp == Decimal("500.0000")

    # 2. Cumulative leakage decreased or unchanged: no negative market leakage deduction
    lkdisp_zero = calculate_vm0042_equation_36_market_leakage(
        lk_t_tco2e=Decimal("150.0000"),
        lk_prior_tco2e=Decimal("200.0000"),
        verification_period_years=Decimal("1.0000"),
    )
    assert lkdisp_zero == Decimal("0.0000")

    # 3. Invalid zero or negative years fail closed
    with pytest.raises(NetGHGCalculationError) as exc_info:
        calculate_vm0042_equation_36_market_leakage(
            lk_t_tco2e=Decimal("1200.0000"),
            lk_prior_tco2e=Decimal("200.0000"),
            verification_period_years=Decimal("0.0000"),
        )
    assert exc_info.value.code == "INVALID_PERIOD"


def test_vmd0054_transition_deadline_evidence():
    """
    Tests Verra transition governance rules:
    - Submission on or before 31 January 2027 with valid request type and documentary evidence -> ELIGIBLE (v1.0 Eq. 10).
    - Submission after 31 January 2027 -> INELIGIBLE / UNRESOLVED.
    - Invalid request type -> INELIGIBLE / UNRESOLVED.
    - Missing documentary evidence -> INELIGIBLE / UNRESOLVED.
    - Generic boolean alone does not bypass governance.
    """
    # Case A: Valid submission on deadline date
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2027, 1, 31),
        project_request_type="REGISTRATION_REQUEST",
        transition_evidence="VERRA_REGISTRY_SUBMISSION_DOC_REF_20270131_8849",
    )
    assert ver == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert eq == "VMD0054_V1.0_EQ10"
    assert ruleset == "VMD0054_V1.0_TRANSITION"

    # Case B: Submission past deadline (1 February 2027) -> BLOCKED
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2027, 2, 1),
        project_request_type="REGISTRATION_REQUEST",
        transition_evidence="VERRA_LATE_SUBMISSION_DOC",
    )
    assert ver == VMD0054Version.VMD0054_VERSION_UNRESOLVED
    assert eq == "UNRESOLVED"
    assert "EXCEEDS_DEADLINE" in basis

    # Case C: Invalid request type
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 11, 1),
        project_request_type="INFORMAL_INQUIRY",
        transition_evidence="EMAIL_QUERY",
    )
    assert ver == VMD0054Version.VMD0054_VERSION_UNRESOLVED
    assert "INVALID_PROJECT_REQUEST_TYPE" in basis

    # Case D: Missing evidence
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 11, 1),
        project_request_type="REGISTRATION_REQUEST",
        transition_evidence=None,
    )
    assert ver == VMD0054Version.VMD0054_VERSION_UNRESOLVED


def test_vmd0054_v11_hand_calculation_parity():
    """
    Direct Numeric VMD0054 Proof (Item 10 of User Specification):
    Build one hand-verifiable v1.1 case.
    Inputs:
        AL_t = 100.0000 ha
        Delta_C_biomass = 1.0000 t C/ha
        Delta_SOC = 2.0000 t C/ha
        ELM,t = 100.0000 tCO2e
        LK_prior = 200.0000 tCO2e
        years = 2.0000
    Hand Calculation:
        Delta_CS (Eq. 11) = 1.0000 + 2.0000 = 3.0000 t C/ha
        LK_t (Eq. 13)     = 100.0000 * 3.0000 * (44/12) + 100.0000 = 1100.0000 + 100.0000 = 1200.0000 tCO2e
        LKdisp,t (Eq. 36) = MAX(0, 1200.0000 - 200.0000) / 2.0000 = 1000.0000 / 2.0000 = 500.0000 tCO2e/yr
    Asserts production output equals hand calculation exactly.
    """
    # 1. Component functions
    delta_cs = calculate_vmd0054_v11_equation_11_delta_cs(
        delta_c_biomass_tc_ha=Decimal("1.0000"),
        delta_soc_tc_ha=Decimal("2.0000"),
    )
    assert delta_cs == Decimal("3.0000")

    lk_t = calculate_vmd0054_v11_equation_13_cumulative_leakage(
        al_t_ha=Decimal("100.0000"),
        delta_cs_tc_ha=delta_cs,
        elm_t_tco2e=Decimal("100.0000"),
    )
    assert lk_t == Decimal("1200.0000")

    lkdisp_t = calculate_vm0042_equation_36_market_leakage(
        lk_t_tco2e=lk_t,
        lk_prior_tco2e=Decimal("200.0000"),
        verification_period_years=Decimal("2.0000"),
    )
    assert lkdisp_t == Decimal("500.0000")

    # 2. End-to-end LeakageInputData and calculate_total_leakage execution
    leakage_input = LeakageInputData(
        vmd0054_version="1.1",
        al_t_ha=Decimal("100.0000"),
        delta_c_biomass_tc_ha=Decimal("1.0000"),
        delta_soc_tc_ha=Decimal("2.0000"),
        elm_t_tco2e=Decimal("100.0000"),
        vmd0054_prior_leakage_tco2e=Decimal("200.0000"),
        vmd0054_verification_period_years=Decimal("2.0000"),
    )
    total_lk, leoa, lkdisp, lebr = calculate_total_leakage(leakage_input, authoritative=True)
    assert lkdisp == Decimal("500.0000")
    assert total_lk == Decimal("500.0000")
    assert leakage_input.vmd0054_source_equation == "VMD0054_V1.1_EQ13"
    assert leakage_input.vmd0054_cumulative_leakage_tco2e == Decimal("1200.0000")
    assert leakage_input.production_decline_leakage_tco2e_yr == Decimal("500.0000")


# =============================================================================
# VMD0054 v1.0 Official Verra Transition Gate & Taxonomy Tests
# =============================================================================

def test_vmd0054_v10_registration_before_deadline_allowed():
    """
    Official Verra Transition Category: REGISTRATION submitted on or before 31 January 2027
    with valid reference ID and documentary evidence qualifies for VMD0054 v1.0 (Eq. 10).
    """
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2027, 1, 31),
        project_request_type="REGISTRATION",
        verra_request_id="VERRA-REG-2027-0091",
        transition_document_id="DOC-VMD0054-REG-TRANSITION-0091",
    )
    assert ver == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert eq == "VMD0054_V1.0_EQ10"
    assert ruleset == "VMD0054_V1.0_TRANSITION"
    assert "REGISTRATION" in basis


def test_vmd0054_v10_registration_after_deadline_blocked():
    """
    Official Verra Transition Category: REGISTRATION submitted AFTER 31 January 2027
    fails closed to VMD0054_VERSION_UNRESOLVED and NOT_ELIGIBLE.
    """
    res = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2027, 2, 1),
        project_request_type="REGISTRATION",
        verra_request_id="VERRA-REG-2027-0092",
        transition_document_id="DOC-VMD0054-REG-TRANSITION-0092",
    )
    assert res.version == VMD0054Version.VMD0054_VERSION_UNRESOLVED
    assert res.source_equation == "UNRESOLVED"
    assert "EXCEEDS_DEADLINE_2027-01-31" in res.transition_basis
    assert res.governance["eligibility_decision"] == "NOT_ELIGIBLE"


def test_vmd0054_v10_verification_baseline_reassessment_allowed():
    """
    Official Verra Transition Category: VERIFICATION_APPROVAL_BASELINE_REASSESSMENT
    qualifies for VMD0054 v1.0 when submitted by 31 January 2027 with valid documentary evidence.
    Tested via both explicit request type and via request type + subtype pair.
    """
    # Direct enum string
    res1 = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 8, 15),
        project_request_type="VERIFICATION_APPROVAL_BASELINE_REASSESSMENT",
        verra_request_id="VERRA-VBR-2026-0044",
        transition_document_id="DOC-BASELINE-REASSESSMENT-EVIDENCE",
    )
    assert res1.version == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert res1.source_equation == "VMD0054_V1.0_EQ10"
    assert res1.governance["verification_subtype"] == "BASELINE_REASSESSMENT"
    assert res1.governance["eligibility_decision"] == "ELIGIBLE"

    # Paired: VERIFICATION_APPROVAL with verification_subtype=BASELINE_REASSESSMENT
    res2 = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 9, 1),
        project_request_type="VERIFICATION_APPROVAL",
        verification_subtype="BASELINE_REASSESSMENT",
        verra_request_id="VERRA-VBR-2026-0045",
        transition_document_id="DOC-BASELINE-REASSESSMENT-EVIDENCE-2",
    )
    assert res2.version == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert res2.source_equation == "VMD0054_V1.0_EQ10"
    assert res2.governance["verification_subtype"] == "BASELINE_REASSESSMENT"
    assert res2.governance["eligibility_decision"] == "ELIGIBLE"


def test_vmd0054_v10_verification_pd_deviation_allowed():
    """
    Official Verra Transition Category: VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION
    qualifies for VMD0054 v1.0 when submitted by 31 January 2027 with valid documentary evidence.
    Tested via both explicit request type and via request type + subtype pair.
    """
    # Direct enum string
    res1 = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 10, 10),
        project_request_type="VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION",
        verra_request_id="VERRA-VPD-2026-0088",
        transition_document_id="DOC-PD-DEVIATION-EVIDENCE-0088",
    )
    assert res1.version == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert res1.source_equation == "VMD0054_V1.0_EQ10"
    assert res1.governance["verification_subtype"] == "METHODOLOGY_CHANGE_PD_DEVIATION"
    assert res1.governance["eligibility_decision"] == "ELIGIBLE"

    # Paired: VERIFICATION_APPROVAL with verification_subtype=METHODOLOGY_CHANGE_PD_DEVIATION
    res2 = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 11, 5),
        project_request_type="VERIFICATION_APPROVAL",
        verification_subtype="METHODOLOGY_CHANGE_PD_DEVIATION",
        verra_request_id="VERRA-VPD-2026-0089",
        transition_document_id="DOC-PD-DEVIATION-EVIDENCE-0089",
    )
    assert res2.version == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert res2.source_equation == "VMD0054_V1.0_EQ10"
    assert res2.governance["verification_subtype"] == "METHODOLOGY_CHANGE_PD_DEVIATION"
    assert res2.governance["eligibility_decision"] == "ELIGIBLE"


def test_vmd0054_v10_generic_verification_blocked():
    """
    Disallowed Category: A generic verification approval/request does NOT qualify
    unless explicitly accompanied by BASELINE_REASSESSMENT or METHODOLOGY_CHANGE_PD_DEVIATION.
    """
    # Case A: Generic VERIFICATION_APPROVAL with no subtype
    res1 = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 7, 20),
        project_request_type="VERIFICATION_APPROVAL",
        verification_subtype=None,
        verra_request_id="VERRA-VER-GENERIC-001",
        transition_document_id="DOC-VER-GENERIC-001",
    )
    assert res1.version == VMD0054Version.VMD0054_VERSION_UNRESOLVED
    assert res1.source_equation == "UNRESOLVED"
    assert res1.governance["eligibility_decision"] == "NOT_ELIGIBLE"
    assert "GENERIC_VERIFICATION_DOES_NOT_QUALIFY" in res1.transition_basis

    # Case B: Generic VERIFICATION_REQUEST with non-qualifying subtype
    res2 = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 7, 20),
        project_request_type="VERIFICATION_REQUEST",
        verification_subtype="STANDARD_PERIODIC_MONITORING",
        verra_request_id="VERRA-VER-GENERIC-002",
        transition_document_id="DOC-VER-GENERIC-002",
    )
    assert res2.version == VMD0054Version.VMD0054_VERSION_UNRESOLVED
    assert res2.source_equation == "UNRESOLVED"
    assert res2.governance["eligibility_decision"] == "NOT_ELIGIBLE"
    assert "GENERIC_VERIFICATION_DOES_NOT_QUALIFY" in res2.transition_basis


def test_vmd0054_v10_crediting_period_renewal_allowed():
    """
    Official Verra Transition Category: CREDITING_PERIOD_RENEWAL
    submitted on or before 31 January 2027 qualifies for VMD0054 v1.0.
    """
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2027, 1, 15),
        project_request_type="CREDITING_PERIOD_RENEWAL",
        verra_request_id="VERRA-CPR-2027-0100",
        transition_document_id="DOC-CPR-RENEWAL-0100",
    )
    assert ver == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert eq == "VMD0054_V1.0_EQ10"
    assert ruleset == "VMD0054_V1.0_TRANSITION"
    assert "CREDITING_PERIOD_RENEWAL" in basis


def test_vmd0054_v10_requantification_allowed():
    """
    Official Verra Transition Category: REQUANTIFICATION
    submitted on or before 31 January 2027 qualifies for VMD0054 v1.0.
    """
    ver, eq, basis, ruleset = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 12, 20),
        project_request_type="REQUANTIFICATION",
        verra_request_id="VERRA-REQ-2026-0333",
        transition_document_id="DOC-REQUANTIFICATION-0333",
    )
    assert ver == VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE
    assert eq == "VMD0054_V1.0_EQ10"
    assert ruleset == "VMD0054_V1.0_TRANSITION"
    assert "REQUANTIFICATION" in basis


def test_validation_listing_does_not_qualify():
    """
    Disallowed Category: VALIDATION_LISTING_REQUEST must NOT independently establish v1.0 eligibility.
    """
    res = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 6, 1),
        project_request_type="VALIDATION_LISTING_REQUEST",
        verra_request_id="VERRA-LISTING-001",
        transition_document_id="DOC-LISTING-001",
    )
    assert res.version == VMD0054Version.VMD0054_VERSION_UNRESOLVED
    assert res.source_equation == "UNRESOLVED"
    assert res.governance["eligibility_decision"] == "NOT_ELIGIBLE"
    assert "VALIDATION_LISTING_DOES_NOT_ESTABLISH_TRANSITION_ELIGIBILITY" in res.transition_basis


def test_generic_project_description_submission_does_not_qualify():
    """
    Disallowed Category: PROJECT_DESCRIPTION_SUBMISSION must NOT independently establish v1.0 eligibility.
    """
    res = resolve_vmd0054_version(
        vmd0054_version_input="1.0",
        submission_date=date(2026, 6, 1),
        project_request_type="PROJECT_DESCRIPTION_SUBMISSION",
        verra_request_id="VERRA-PDS-001",
        transition_document_id="DOC-PDS-001",
    )
    assert res.version == VMD0054Version.VMD0054_VERSION_UNRESOLVED
    assert res.source_equation == "UNRESOLVED"
    assert res.governance["eligibility_decision"] == "NOT_ELIGIBLE"
    assert "PROJECT_DESCRIPTION_SUBMISSION_DOES_NOT_ESTABLISH_TRANSITION_ELIGIBILITY" in res.transition_basis
