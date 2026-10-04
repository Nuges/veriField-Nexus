"""
VeriField Nexus — Agriculture Phase 3B-2 Test Suite
===================================================
VM0042 v2.2 + 11 June 2026 C&C:
- Equations (44) & (45): Baseline and project scenario annual SOC stock changes (t C/ha/yr).
- Equations (46) & (47): Stoichiometric 44/12 conversion & area-weighted CO2 stock changes (tCO2e/yr).
- Equations (70) & (71): Sampling variance and covariance sensitivity.
- Laboratory measurement error router (proficient dry combustion = negligible, unverified = fail closed).
- Equation (74): Student's t uncertainty deduction (p = 0.667) with 15% threshold and zero/negative denominator safety.
- Ledger gate: Ledger blocks credit issuance for AgricultureSOCChangeResult.
- Segregation of duties: FIELD_AGENT cannot finalize authoritative calculations.
- Concurrency & Idempotency: Duplicate submissions return deterministic existing result.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.domains.agriculture.soil.soc_change_calculator import (
    StratumInputData,
    StratumChangeOutput,
    UncertaintyDeductionOutput,
    ProjectSOCChangeOutput,
    SOCChangeCalculationError,
    aggregate_project_qa2_soc_change,
    calculate_student_t_0667,
    calculate_stratum_soc_change_and_variance,
    calculate_vm0042_eq74_uncertainty_deduction,
    route_measurement_error,
    CO2_TO_C_RATIO,
    EQ44_EQ45_PARTIALLY_CONFIGURED_SOC_ONLY,
    DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR,
)
from app.domains.agriculture.models import (
    AgricultureSOCStockResult,
    AgricultureSOCChangeResult,
    AgriculturePrerequisiteAssessment,
    Stratum,
)
from app.domains.projects.models import Project
from app.domains.organizations.models import Organization
from app.domains.authentication.models import User


# =============================================================================
# 1. SCIENTIFIC ARITHMETIC & HAND-VECTOR GOLDEN TESTS
# =============================================================================

class TestVM0042SOCChangeArithmetic:
    """Rigorous mathematical parity tests for VM0042 v2.2 Equations (44), (45), (46), (47), (70), (71), (74)."""

    def test_vm0042_equations_44_45_annualized_rate(self):
        """Tests rate of SOC stock change per hectare (t C/ha/yr)."""
        # Baseline: initial 32.5000 t C/ha, static control 32.5000 t C/ha over 5 years -> 0.0000 t C/ha/yr
        # Project: initial 32.5000 t C/ha, monitoring 38.7500 t C/ha over 5 years
        # Delta = (38.7500 - 32.5000) / 5 = 6.25 / 5 = 1.2500 t C/ha/yr
        s = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="STRAT-01",
            area_ha=Decimal("150.0000"),
            baseline_mean_soc_t_c_per_ha=Decimal("32.5000"),
            monitoring_mean_soc_t_c_per_ha=Decimal("38.7500"),
            sample_count_project=10,
            sample_count_baseline=10,
            sample_variance_project_t1=Decimal("3.2000"),
            sample_variance_project_t2=Decimal("3.8000"),
            paired_covariance_project=Decimal("1.5000"),
        )
        res = calculate_stratum_soc_change_and_variance(s, elapsed_years=Decimal("5.0000"))

        assert res.delta_soc_project_t_c_ha_yr == Decimal("1.2500")
        assert res.delta_soc_baseline_t_c_ha_yr == Decimal("0.0000")
        assert res.delta_soc_net_t_c_ha_yr == Decimal("1.2500")

    def test_exact_stoichiometric_44_12_ratio(self):
        """Verifies exact Decimal 44/12 stoichiometric conversion factor."""
        expected_ratio = Decimal("44") / Decimal("12")
        assert CO2_TO_C_RATIO == expected_ratio
        # 1.0000 t C * (44/12) = 3.666666... -> rounded to 4 decimals: 3.6667
        c_mass = Decimal("1.0000")
        co2_mass = (c_mass * CO2_TO_C_RATIO).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        assert co2_mass == Decimal("3.6667")

    def test_equations_46_47_area_weighted_aggregation(self):
        """
        Verifies Equation (46) & (47) area-weighted aggregation across project strata:
        Stratum 1: 100 ha, Delta_SOC_net = 1.0000 t C/ha/yr -> Total CO2 = 100 * 1.0 * (44/12) = 366.67 tCO2e/yr
        Stratum 2: 200 ha, Delta_SOC_net = 0.5000 t C/ha/yr -> Total CO2 = 200 * 0.5 * (44/12) = 366.67 tCO2e/yr
        Total Project Net CO2 = 733.34 tCO2e/yr
        Total Area = 300 ha, Area-weighted Delta_SOC_net = (100*1.0 + 200*0.5) / 300 = 200 / 300 = 0.6667 t C/ha/yr
        """
        s1 = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="STRAT-A",
            area_ha=Decimal("100.0000"),
            baseline_mean_soc_t_c_per_ha=Decimal("40.0000"),
            monitoring_mean_soc_t_c_per_ha=Decimal("44.0000"),
            sample_count_project=8,
            sample_count_baseline=8,
            sample_variance_project_t1=Decimal("2.0"),
            sample_variance_project_t2=Decimal("2.0"),
            paired_covariance_project=Decimal("1.0"),
        )
        s2 = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="STRAT-B",
            area_ha=Decimal("200.0000"),
            baseline_mean_soc_t_c_per_ha=Decimal("35.0000"),
            monitoring_mean_soc_t_c_per_ha=Decimal("37.0000"),
            sample_count_project=8,
            sample_count_baseline=8,
            sample_variance_project_t1=Decimal("2.0"),
            sample_variance_project_t2=Decimal("2.0"),
            paired_covariance_project=Decimal("1.0"),
        )

        out = aggregate_project_qa2_soc_change(
            strata_inputs=[s1, s2],
            elapsed_years=Decimal("4.0000"),
        )

        assert out.total_project_area_ha == Decimal("300.0000")
        assert out.delta_soc_net_t_c_ha_yr == Decimal("0.6667")
        assert out.total_net_delta_co2_tco2e_yr == Decimal("733.3300")

    def test_equation_71_stratum_variance_and_covariance_sensitivity(self):
        """
        Demonstrates Equation (71) covariance sensitivity:
        Paired repeated measurements with positive covariance cov(t1, t2) > 0
        strictly reduce sampling variance compared to independent cores (cov = 0).
        """
        s_paired = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="PAIRED",
            area_ha=Decimal("50.0"),
            baseline_mean_soc_t_c_per_ha=Decimal("30.0"),
            monitoring_mean_soc_t_c_per_ha=Decimal("34.0"),
            sample_count_project=10,
            sample_count_baseline=10,
            sample_variance_project_t1=Decimal("5.0"),
            sample_variance_project_t2=Decimal("5.0"),
            paired_covariance_project=Decimal("3.0"),  # Positive correlation between visits
        )
        res_paired = calculate_stratum_soc_change_and_variance(s_paired, elapsed_years=Decimal("2.0"))

        s_independent = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="INDEPENDENT",
            area_ha=Decimal("50.0"),
            baseline_mean_soc_t_c_per_ha=Decimal("30.0"),
            monitoring_mean_soc_t_c_per_ha=Decimal("34.0"),
            sample_count_project=10,
            sample_count_baseline=10,
            sample_variance_project_t1=Decimal("5.0"),
            sample_variance_project_t2=Decimal("5.0"),
            paired_covariance_project=Decimal("0.0"),  # Zero covariance
        )
        res_indep = calculate_stratum_soc_change_and_variance(s_independent, elapsed_years=Decimal("2.0"))

        # For paired: [5 + 5 - 2*3] / (2^2 * 10) = 4 / 40 = 0.1000
        # For indep:  [5 + 5 - 0]   / (2^2 * 10) = 10 / 40 = 0.2500
        assert res_paired.variance_delta_soc_proj == Decimal("0.10000000")
        assert res_indep.variance_delta_soc_proj == Decimal("0.25000000")
        assert res_paired.variance_delta_soc_proj < res_indep.variance_delta_soc_proj

    def test_student_t_distribution_0667_critical_values(self):
        """Verifies Student's t distribution at one-sided 66.7% confidence level."""
        t1 = calculate_student_t_0667(1)
        t5 = calculate_student_t_0667(5)
        t10 = calculate_student_t_0667(10)
        t30 = calculate_student_t_0667(30)
        t100 = calculate_student_t_0667(100)

        assert t1 == Decimal("0.5787")
        assert t5 == Decimal("0.4583")
        assert t10 == Decimal("0.4447")
        assert t30 == Decimal("0.4359")
        assert t100 == Decimal("0.4329")

        # Monotonically decreasing with degrees of freedom toward z_0.667 = 0.4316
        assert t1 > t5 > t10 > t30 > t100 > Decimal("0.4316")

    def test_eq74_small_nonzero_uncertainty_produces_small_nonzero_deduction(self):
        """
        CRITICAL VM0042 RULE: Zero Deadband.
        A small nonzero uncertainty (e.g. U = 0.5833%) produces an exact deduction of 0.5833%, NOT 0.0000%.
        """
        unc = calculate_vm0042_eq74_uncertainty_deduction(
            mean_net_removal_tco2e_yr=Decimal("1000.0000"),
            total_project_area_ha=Decimal("100.0000"),
            total_variance_delta_soc=Decimal("0.00010000"),
            degrees_of_freedom=20,
        )
        assert Decimal("0.0000") < unc.relative_uncertainty_pct < Decimal("15.0000")
        assert unc.uncertainty_deduction_pct == unc.relative_uncertainty_pct
        assert unc.uncertainty_deduction_fraction > Decimal("0.000000")
        assert unc.deduction_applied is True
        assert unc.uncertainty_status == "EXACT_EQ74_DEDUCTION_APPLIED"
        assert unc.allowable_uncertainty_pct == Decimal("0.0000")
        expected_adj = (Decimal("1000.0000") * (Decimal("1.000000") - unc.uncertainty_deduction_fraction)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        assert unc.adjusted_net_delta_co2_tco2e_yr == expected_adj

    def test_eq74_large_uncertainty_produces_corresponding_deduction(self):
        """
        CRITICAL VM0042 RULE: Exact Deduction.
        When U% = 25.40%, deduction is exactly 25.40%, NOT (25.40% - 15% = 10.40%).
        """
        unc = calculate_vm0042_eq74_uncertainty_deduction(
            mean_net_removal_tco2e_yr=Decimal("100.0000"),
            total_project_area_ha=Decimal("100.0000"),
            total_variance_delta_soc=Decimal("0.08000000"),
            degrees_of_freedom=10,
        )
        assert unc.relative_uncertainty_pct > Decimal("15.0000")
        assert unc.uncertainty_deduction_pct == unc.relative_uncertainty_pct
        assert unc.deduction_applied is True
        assert unc.uncertainty_status == "EXACT_EQ74_DEDUCTION_APPLIED"

    def test_eq74_zero_variance_produces_zero_deduction(self):
        """When sampling variance is zero, uncertainty is 0% and deduction is 0%."""
        unc = calculate_vm0042_eq74_uncertainty_deduction(
            mean_net_removal_tco2e_yr=Decimal("500.0000"),
            total_project_area_ha=Decimal("100.0000"),
            total_variance_delta_soc=Decimal("0.00000000"),
            degrees_of_freedom=10,
        )
        assert unc.relative_uncertainty_pct == Decimal("0.0000")
        assert unc.uncertainty_deduction_pct == Decimal("0.0000")
        assert unc.uncertainty_deduction_fraction == Decimal("0.000000")
        assert unc.adjusted_net_delta_co2_tco2e_yr == Decimal("500.0000")
        assert unc.deduction_applied is False
        assert unc.uncertainty_status == "ZERO_VARIANCE_ZERO_DEDUCTION"

    def test_eq74_probability_of_exceedance_formula_exact(self):
        """
        Verifies exact hand-calculation of Equation (74):
        UNC = (sqrt(s^2) / Mean * 100) * t_0.667
        """
        unc = calculate_vm0042_eq74_uncertainty_deduction(
            mean_net_removal_tco2e_yr=Decimal("50.0000"),
            total_project_area_ha=Decimal("10.0000"),
            total_variance_delta_soc=Decimal("0.04000000"),
            degrees_of_freedom=10,
        )
        assert unc.student_t_value_0667 == Decimal("0.4447")
        assert unc.relative_uncertainty_pct == Decimal("6.5222")
        assert unc.uncertainty_deduction_pct == Decimal("6.5222")
        assert unc.uncertainty_deduction_fraction == Decimal("0.065222")
        assert unc.adjusted_net_delta_co2_tco2e_yr == Decimal("46.7389")

    def test_eq74_zero_mean_removal_fails_closed(self):
        """When mean net removal is 0.0000 with nonzero variance, fails closed deterministically."""
        with pytest.raises(SOCChangeCalculationError) as exc_info:
            calculate_vm0042_eq74_uncertainty_deduction(
                mean_net_removal_tco2e_yr=Decimal("0.0000"),
                total_project_area_ha=Decimal("100.0000"),
                total_variance_delta_soc=Decimal("0.01000000"),
                degrees_of_freedom=10,
            )
        assert exc_info.value.code == "ZERO_MEAN_REMOVAL_UNDEFINED_UNCERTAINTY"

    def test_equations_44_45_sign_indicator_branches(self):
        """
        Tests sign indicator I(ΔCO2_soil_t):
        Branch 1 (Net positive removal): I = +1, factor = (1 - fraction) <= 1.0 (reduces credited removals)
        Branch 2 (Net negative removal/loss): I = -1, factor = (1 + fraction) >= 1.0 (increases loss magnitude)
        """
        # Branch 1: Positive removal
        unc_pos = calculate_vm0042_eq74_uncertainty_deduction(
            mean_net_removal_tco2e_yr=Decimal("100.0000"),
            total_project_area_ha=Decimal("10.0000"),
            total_variance_delta_soc=Decimal("0.01000000"),
            degrees_of_freedom=10,
        )
        assert unc_pos.sign_indicator == 1
        assert unc_pos.adjusted_net_delta_co2_tco2e_yr < Decimal("100.0000")

        # Branch 2: Negative removal (loss)
        unc_neg = calculate_vm0042_eq74_uncertainty_deduction(
            mean_net_removal_tco2e_yr=Decimal("-100.0000"),
            total_project_area_ha=Decimal("10.0000"),
            total_variance_delta_soc=Decimal("0.01000000"),
            degrees_of_freedom=10,
        )
        assert unc_neg.sign_indicator == -1
        assert unc_neg.adjusted_net_delta_co2_tco2e_yr < Decimal("-100.0000")
        assert abs(unc_neg.adjusted_net_delta_co2_tco2e_yr) > abs(Decimal("-100.0000"))

    def test_equation_46_baseline_soc_stock_change_exact(self):
        """Verifies VM0042 Equation (46) Baseline Scenario SOC Stock Change: ΔCO2_soil_bsl,t."""
        s = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="BSL-TEST",
            area_ha=Decimal("100.0000"),
            baseline_mean_soc_t_c_per_ha=Decimal("30.0000"),
            monitoring_mean_soc_t_c_per_ha=Decimal("35.0000"),
            baseline_delta_soc_t_c_ha_yr=Decimal("-0.2000"),
            sample_count_project=10,
            sample_count_baseline=10,
        )
        res = calculate_stratum_soc_change_and_variance(s, elapsed_years=Decimal("2.0000"))
        assert res.delta_soc_baseline_t_c_ha_yr == Decimal("-0.2000")
        assert res.baseline_soc_change_tco2e_yr == Decimal("-73.3300")

    def test_equation_47_project_soc_change_exact(self):
        """Verifies VM0042 Equation (47) Project Scenario SOC Stock Change: ΔCO2_soil_wp,t."""
        s = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="PROJ-TEST",
            area_ha=Decimal("100.0000"),
            baseline_mean_soc_t_c_per_ha=Decimal("30.0000"),
            monitoring_mean_soc_t_c_per_ha=Decimal("35.0000"),
            sample_count_project=10,
            sample_count_baseline=10,
        )
        res = calculate_stratum_soc_change_and_variance(s, elapsed_years=Decimal("2.0000"))
        assert res.delta_soc_project_t_c_ha_yr == Decimal("2.5000")
        assert res.project_soc_change_tco2e_yr == Decimal("916.6700")

    def test_qa2_net_soc_effect_naming_and_separation(self):
        """Verifies that QA2 comparative net effect is strictly Project (Eq. 47) - Baseline (Eq. 46)."""
        s = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="QA2-TEST",
            area_ha=Decimal("100.0000"),
            baseline_mean_soc_t_c_per_ha=Decimal("30.0000"),
            monitoring_mean_soc_t_c_per_ha=Decimal("35.0000"),
            baseline_delta_soc_t_c_ha_yr=Decimal("-0.5000"),
            sample_count_project=10,
            sample_count_baseline=10,
        )
        res = calculate_stratum_soc_change_and_variance(s, elapsed_years=Decimal("2.0000"))
        assert res.qa2_net_soc_effect_tco2e_yr == Decimal("1100.0000")
        assert res.qa2_net_soc_effect_tco2e_yr == (res.project_soc_change_tco2e_yr - res.baseline_soc_change_tco2e_yr).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

    def test_default_stratified_random_df_estimator_classification(self):
        """Verifies df estimator is DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR and Eq 44/45 is PARTIALLY_CONFIGURED_SOC_ONLY."""
        s = StratumInputData(
            stratum_id=uuid.uuid4(),
            stratum_code="STRAT-01",
            area_ha=Decimal("100.0000"),
            baseline_mean_soc_t_c_per_ha=Decimal("30.0000"),
            monitoring_mean_soc_t_c_per_ha=Decimal("32.0000"),
            sample_count_project=5,
            sample_count_baseline=5,
        )
        out = aggregate_project_qa2_soc_change(
            strata_inputs=[s],
            elapsed_years=Decimal("2.0000"),
        )
        assert out.df_estimator == DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR
        assert out.eq44_eq45_status == EQ44_EQ45_PARTIALLY_CONFIGURED_SOC_ONLY
        assert out.uncertainty.df_estimator == DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR


# =============================================================================
# 2. MEASUREMENT ERROR ROUTER TESTS
# =============================================================================

class TestMeasurementErrorRouter:
    """Verifies laboratory measurement error routing under VM0042 QA2."""

    def test_dry_combustion_proficient_classified_negligible(self):
        status, router, var = route_measurement_error(
            laboratory_method="DRY_COMBUSTION",
            lab_qa_verified=True,
            active_lab_proficiency=True,
        )
        assert status == "NEGLIGIBLE_PER_VM0042_CONDITIONS"
        assert router == "CONVENTIONAL_DRY_COMBUSTION"
        assert var == Decimal("0.00000000")

    def test_unverified_lab_proficiency_fails_closed(self):
        with pytest.raises(SOCChangeCalculationError) as exc_info:
            route_measurement_error(
                laboratory_method="DRY_COMBUSTION",
                lab_qa_verified=False,
                active_lab_proficiency=False,
            )
        assert exc_info.value.code == "LAB_PROFICIENCY_EVIDENCE_INCOMPLETE"

    def test_alternative_sensor_fails_closed(self):
        with pytest.raises(SOCChangeCalculationError) as exc_info:
            route_measurement_error(
                laboratory_method="VIS_NIR",
                lab_qa_verified=True,
                active_lab_proficiency=True,
            )
        assert exc_info.value.code == "QA2_ALTERNATIVE_MEASUREMENT_UNCERTAINTY_NOT_CONFIGURED"


# =============================================================================
# 3. DATABASE PERSISTENCE, API & CONCURRENCY TESTS (REAL POSTGRESQL)
# =============================================================================

@pytest.mark.asyncio
class TestAgricultureSOCChangeEngineDatabaseAndAPI:
    """Tests full stack PostgreSQL persistence, API endpoints, ABAC, and idempotency."""

    @pytest_asyncio.fixture
    async def test_user(self, db_session):
        from app.core.security import get_password_hash
        tag = uuid.uuid4().hex[:8]
        org = Organization(
            id=uuid.uuid4(),
            name=f"Agriculture Test Org {tag}",
            org_type="DEVELOPER",
            status="ACTIVE",
        )
        db_session.add(org)
        await db_session.flush()

        user = User(
            id=uuid.uuid4(),
            email=f"user.{tag}@verifield.test",
            password_hash=get_password_hash("TestPass123!"),
            full_name="Lead MRV Specialist",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        db_session.add(user)
        await db_session.flush()
        return user

    async def _setup_prerequisite_and_stocks(self, db, org_id, user_id):
        """Helper to create realistic baseline & monitoring project stock results."""
        # 1. Project
        tag = uuid.uuid4().hex[:6]
        proj = Project(
            id=uuid.uuid4(),
            organization_id=org_id,
            name=f"VM0042 Grassland Soil Project {tag}",
            project_code=f"PRJ-{tag}",
        )
        db.add(proj)
        await db.flush()

        # 2. Prerequisite Assessment
        prereq = AgriculturePrerequisiteAssessment(
            organization_id=org_id,
            project_id=proj.id,
            assessment_code=f"PREREQ-{tag}",
            version=1,
            status="LOCKED",
            overall_readiness="READY",
            methodology_code="VM0042",
            methodology_version="2.2",
            corrections_clarifications_version="2026-06-11",
            rule_set_version="VM0042_V2.2_RULES_CC20260611_V1.0",
            assessment_hash="hash_" + uuid.uuid4().hex[:12],
            is_locked=True,
        )
        db.add(prereq)
        await db.flush()

        # 3. Stratum
        stratum = Stratum(
            organization_id=org_id,
            project_id=proj.id,
            code="STRAT-01",
            name="Sandy Loam Management Unit",
            area_ha=100.0,
        )
        db.add(stratum)
        await db.flush()

        # 4. Baseline Project Stock Result (t_start)
        t_start = datetime.now(timezone.utc) - timedelta(days=365 * 3)
        bsl_stock = AgricultureSOCStockResult(
            organization_id=org_id,
            project_id=proj.id,
            prerequisite_assessment_id=prereq.id,
            result_code=f"SOC-PROJ-BSL-{uuid.uuid4().hex[:6]}",
            measurement_period_type="BASELINE",
            aggregation_level="PROJECT",
            methodology_version="2.2",
            corrections_clarifications_version="2026-06-11",
            calculation_engine_version="VM0042_V2_2_ESM_ENGINE_V1.0",
            esm_algorithm="WENDT_HAUSER_2013_CUBIC_SPLINE",
            reference_soil_mass_t_ha=Decimal("1950.0000"),
            reference_depth_cm=Decimal("30.00"),
            soc_stock_t_c_per_ha=Decimal("35.0000"),
            area_ha=Decimal("100.0000"),
            sample_count=10,
            component_breakdown={
                "strata_results": [
                    {
                        "stratum_id": str(stratum.id),
                        "stratum_code": stratum.code,
                        "area_ha": "100.0000",
                        "stratum_mean_soc_t_c_per_ha": "35.0000",
                        "sample_count": 10,
                        "sample_variance": "2.50000000",
                    }
                ]
            },
            result_status="CALCULATED",
            calculation_hash="hash_bsl_" + uuid.uuid4().hex[:12],
            input_snapshot_hash="hash_bsl_in_" + uuid.uuid4().hex[:12],
            created_at=t_start,
            updated_at=t_start,
        )
        db.add(bsl_stock)
        await db.flush()

        # 5. Monitoring Project Stock Result (t_final)
        t_final = datetime.now(timezone.utc)
        mon_stock = AgricultureSOCStockResult(
            organization_id=org_id,
            project_id=proj.id,
            prerequisite_assessment_id=prereq.id,
            result_code=f"SOC-PROJ-MON-{uuid.uuid4().hex[:6]}",
            measurement_period_type="MONITORING",
            aggregation_level="PROJECT",
            methodology_version="2.2",
            corrections_clarifications_version="2026-06-11",
            calculation_engine_version="VM0042_V2_2_ESM_ENGINE_V1.0",
            esm_algorithm="WENDT_HAUSER_2013_CUBIC_SPLINE",
            reference_soil_mass_t_ha=Decimal("1950.0000"),
            reference_depth_cm=Decimal("30.00"),
            soc_stock_t_c_per_ha=Decimal("41.0000"),  # Gained 6 t C/ha over 3 years -> 2.0 t C/ha/yr
            area_ha=Decimal("100.0000"),
            sample_count=10,
            component_breakdown={
                "strata_results": [
                    {
                        "stratum_id": str(stratum.id),
                        "stratum_code": stratum.code,
                        "area_ha": "100.0000",
                        "stratum_mean_soc_t_c_per_ha": "41.0000",
                        "sample_count": 10,
                        "sample_variance": "2.80000000",
                    }
                ]
            },
            result_status="CALCULATED",
            calculation_hash="hash_mon_" + uuid.uuid4().hex[:12],
            input_snapshot_hash="hash_mon_in_" + uuid.uuid4().hex[:12],
            created_at=t_final,
            updated_at=t_final,
        )
        db.add(mon_stock)
        await db.flush()

        return proj, prereq, bsl_stock, mon_stock

    async def test_evaluate_soc_stock_change_preview(self, db_session, test_user):
        """Tests non-mutating preview evaluation endpoint."""
        proj, prereq, bsl, mon = await self._setup_prerequisite_and_stocks(
            db_session, test_user.organization_id, test_user.id
        )

        from app.domains.agriculture.service import AgricultureService
        preview = await AgricultureService.evaluate_soc_stock_change(
            db=db_session,
            project_id=proj.id,
            organization_id=test_user.organization_id,
            baseline_stock_result_id=bsl.id,
            monitoring_stock_result_id=mon.id,
            prerequisite_assessment_id=prereq.id,
        )

        assert preview["status"] == "EVALUATED"
        assert Decimal(preview["delta_soc_net_t_c_ha_yr"]) > Decimal("0.0")
        assert Decimal(preview["total_net_delta_co2_tco2e_yr"]) > Decimal("0.0")
        assert preview["measurement_error_status"] == "NEGLIGIBLE_PER_VM0042_CONDITIONS"
        assert len(preview["strata_results"]) == 1

    async def test_finalize_soc_stock_change_authoritative(self, db_session, test_user):
        """Tests authoritative persistence of AgricultureSOCChangeResult to real PostgreSQL."""
        proj, prereq, bsl, mon = await self._setup_prerequisite_and_stocks(
            db_session, test_user.organization_id, test_user.id
        )

        from app.domains.agriculture.service import AgricultureService
        res = await AgricultureService.finalize_soc_stock_change(
            db=db_session,
            project_id=proj.id,
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            user_role="PROJECT_MANAGER",
            baseline_stock_result_id=bsl.id,
            monitoring_stock_result_id=mon.id,
            prerequisite_assessment_id=prereq.id,
        )

        assert res.id is not None
        assert res.result_status == "CALCULATED"
        assert res.carbon_accounting_status == "NOT_CONFIGURED"
        assert res.ledger_status == "BLOCKED_FOR_AGRICULTURE"
        assert res.total_net_delta_co2_tco2e_yr > Decimal("0.0")
        assert res.adjusted_net_delta_co2_tco2e_yr > Decimal("0.0")

        # Verify DB query
        persisted = await db_session.get(AgricultureSOCChangeResult, res.id)
        assert persisted is not None
        assert persisted.result_code.startswith("SOC-CHG-")
        assert persisted.baseline_soc_change_tco2e_yr == res.baseline_soc_change_tco2e_yr
        assert persisted.project_soc_change_tco2e_yr == res.project_soc_change_tco2e_yr
        assert persisted.qa2_net_soc_effect_tco2e_yr == res.qa2_net_soc_effect_tco2e_yr
        assert persisted.uncertainty_adjusted_soc_effect_tco2e_yr == res.uncertainty_adjusted_soc_effect_tco2e_yr
        assert persisted.sign_indicator == 1
        assert persisted.eq44_eq45_status == "PARTIALLY_CONFIGURED_SOC_ONLY"
        assert persisted.df_estimator == "DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR"
        assert persisted.allowable_uncertainty_pct == Decimal("0.0000")

    async def test_unfavorable_soc_change_conservative_sign(self, db_session, test_user):
        """Verifies that an unfavorable SOC change (monitoring < baseline) applies I = -1 conservatively."""
        proj, prereq, bsl, mon = await self._setup_prerequisite_and_stocks(
            db_session, test_user.organization_id, test_user.id
        )
        mon.soc_stock_t_c_per_ha = Decimal("30.0000")  # bsl is 35.0000 -> loss
        mon_strata = [
            {
                "stratum_id": str(uuid.uuid4()),
                "stratum_code": "STRAT-01",
                "area_ha": "100.0000",
                "stratum_mean_soc_t_c_per_ha": "30.0000",
                "sample_count": 10,
                "sample_variance": "2.80000000",
            }
        ]
        mon.component_breakdown = {"strata_results": mon_strata}
        await db_session.flush()

        from app.domains.agriculture.service import AgricultureService
        res = await AgricultureService.finalize_soc_stock_change(
            db=db_session,
            project_id=proj.id,
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            user_role="PROJECT_MANAGER",
            baseline_stock_result_id=bsl.id,
            monitoring_stock_result_id=mon.id,
            prerequisite_assessment_id=prereq.id,
        )
        assert res.sign_indicator == -1
        assert res.qa2_net_soc_effect_tco2e_yr < Decimal("0.0")
        assert abs(res.uncertainty_adjusted_soc_effect_tco2e_yr) >= abs(res.qa2_net_soc_effect_tco2e_yr)

    async def test_idempotency_and_concurrency(self, db_session, test_user):
        """Verifies duplicate finalize calls with identical inputs return existing record."""
        proj, prereq, bsl, mon = await self._setup_prerequisite_and_stocks(
            db_session, test_user.organization_id, test_user.id
        )

        from app.domains.agriculture.service import AgricultureService
        first = await AgricultureService.finalize_soc_stock_change(
            db=db_session,
            project_id=proj.id,
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            user_role="PROJECT_MANAGER",
            baseline_stock_result_id=bsl.id,
            monitoring_stock_result_id=mon.id,
            prerequisite_assessment_id=prereq.id,
        )

        second = await AgricultureService.finalize_soc_stock_change(
            db=db_session,
            project_id=proj.id,
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            user_role="PROJECT_MANAGER",
            baseline_stock_result_id=bsl.id,
            monitoring_stock_result_id=mon.id,
            prerequisite_assessment_id=prereq.id,
        )

        assert first.id == second.id
        assert first.calculation_hash == second.calculation_hash

    async def test_field_agent_sod_enforcement(self, db_session, test_user):
        """Verifies FIELD_AGENT role cannot finalize authoritative calculations (403)."""
        proj, prereq, bsl, mon = await self._setup_prerequisite_and_stocks(
            db_session, test_user.organization_id, test_user.id
        )

        from app.domains.agriculture.service import AgricultureService
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await AgricultureService.finalize_soc_stock_change(
                db=db_session,
                project_id=proj.id,
                organization_id=test_user.organization_id,
                user_id=test_user.id,
                user_role="FIELD_AGENT",
                baseline_stock_result_id=bsl.id,
                monitoring_stock_result_id=mon.id,
                prerequisite_assessment_id=prereq.id,
            )
        assert exc_info.value.status_code == 403

    async def test_cross_tenant_isolation(self, db_session, test_user):
        """Verifies that accessing a baseline result from another organization fails closed."""
        proj, prereq, bsl, mon = await self._setup_prerequisite_and_stocks(
            db_session, test_user.organization_id, test_user.id
        )
        other_org_id = uuid.uuid4()

        from app.domains.agriculture.service import AgricultureService
        with pytest.raises(Exception):
            await AgricultureService.evaluate_soc_stock_change(
                db=db_session,
                project_id=proj.id,
                organization_id=other_org_id,  # Foreign tenant
                baseline_stock_result_id=bsl.id,
                monitoring_stock_result_id=mon.id,
                prerequisite_assessment_id=prereq.id,
            )

    async def test_esm_reference_mass_mismatch_fails_closed(self, db_session, test_user):
        """Verifies that mismatched reference soil mass between baseline and monitoring is rejected."""
        proj, prereq, bsl, mon = await self._setup_prerequisite_and_stocks(
            db_session, test_user.organization_id, test_user.id
        )
        mon.reference_soil_mass_t_ha = Decimal("2100.0000")  # Changed from 1950.0000
        await db_session.flush()

        from app.domains.agriculture.service import AgricultureService
        with pytest.raises(SOCChangeCalculationError) as exc_info:
            await AgricultureService.evaluate_soc_stock_change(
                db=db_session,
                project_id=proj.id,
                organization_id=test_user.organization_id,
                baseline_stock_result_id=bsl.id,
                monitoring_stock_result_id=mon.id,
                prerequisite_assessment_id=prereq.id,
            )
        assert exc_info.value.code == "ESM_REFERENCE_MASS_MISMATCH"

    async def test_ledger_rejects_soc_change_minting(self, db_session, test_user):
        """Verifies that the digital ledger minting endpoint fails closed on Phase 3B-2 results."""
        proj, prereq, bsl, mon = await self._setup_prerequisite_and_stocks(
            db_session, test_user.organization_id, test_user.id
        )

        from app.domains.agriculture.service import AgricultureService
        change_res = await AgricultureService.finalize_soc_stock_change(
            db=db_session,
            project_id=proj.id,
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            user_role="PROJECT_MANAGER",
            baseline_stock_result_id=bsl.id,
            monitoring_stock_result_id=mon.id,
            prerequisite_assessment_id=prereq.id,
        )

        from app.domains.ledger.api import execute_carbon_minting, MintRequest
        from fastapi import HTTPException
        mint_req = MintRequest(
            project_id=proj.id,
            calculation_id=change_res.id,  # Pass Phase 3B-2 calculation ID!
        )

        # Ledger must fail closed: NO eligible carbon calculation found for this ID
        with pytest.raises(HTTPException) as exc_info:
            await execute_carbon_minting(
                data=mint_req,
                db=db_session,
                current_user=test_user,
            )
        # Should raise 400 or 404 (calculation not found in CarbonCalculation table)
        assert exc_info.value.status_code in (400, 404)
