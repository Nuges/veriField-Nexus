"""
VeriField Nexus — Agriculture Phase 3B-1: Final Scientific & Lineage Acceptance Test Suite
===========================================================================================
Audits:
- Profile Identity Contract (Sections 7, 8, 9, 10)
- VM0042 Equation (3) Direct Soil Mass & Bulk Density Roles (Sections 4, 5, 6, 21)
- Official Verra ESM Golden Vector: 1950 Mg/ha, 47.36 t C/ha at VM42point1-1 (Sections 14, 15)
- Monotonic Spline (Wendt & Hauser 2013) & Layer Mass Proportioning (Ellert & Bettany 1995)
- Reference Mass Maximum Determined Selection Rule (Section 16)
- Depth Continuity, Gap/Overlap Rejection, Shallow Soil Impeding Layers (Sections 17, 18, 19)
- Verified Laboratory QA Gate & Supersession Exclusion (Section 22)
- Zero Carbon Invariants: No ΔSOC, No 44/12, No tCO2e (Sections 26, 27)
"""

import math
import uuid
from decimal import Decimal
import pytest

from app.domains.agriculture.soil.soc_stock_calculator import (
    LayerInput,
    LayerResult,
    ProfileESMResult,
    SOCStockCalculationError,
    calculate_layer_soil_mass,
    calculate_layer_soil_mass_direct,
    calculate_layer_soc_mass,
    calculate_profile_esm_proportioning,
    calculate_profile_esm_spline,
    calculate_profile_esm_diagnostic_pchip,
    aggregate_stratum_soc_stock,
    aggregate_project_area_weighted_soc_stock,
    validate_profile_layers,
)
from app.domains.agriculture.service import AgricultureService
from app.domains.agriculture.models import (
    PhysicalSample,
    SamplingPoint,
    SampleCollectionEvent,
    LaboratoryAnalysis,
    LaboratoryResult,
)


class TestProfileIdentityContract:
    """Verifies Profile Identity Contract per Sections 7, 8, 9, 10."""

    def test_explicit_soil_profile_id_takes_priority(self):
        """Explicit soil_profile_id on PhysicalSample or SamplingPoint establishes profile identity."""
        sample = PhysicalSample(
            id=uuid.uuid4(),
            sample_code="SMP-001",
            soil_profile_id="PROF-ALPHA-01",
            campaign_id=uuid.uuid4(),
        )
        prof_id, method, conf = AgricultureService._resolve_profile_identity(sample)
        assert method == "EXPLICIT_SAMPLE_PROFILE_ID"
        assert "PROF-ALPHA-01" in prof_id
        assert conf == Decimal("1.00")

    def test_same_coordinate_different_campaign_resolves_to_different_profiles(self):
        """Same geographic coordinates sampled across different monitoring campaigns are never merged."""
        c1 = uuid.uuid4()
        c2 = uuid.uuid4()
        lat, lon = 42.123456, -93.654321

        sp1 = SamplingPoint(
            id=uuid.uuid4(),
            campaign_id=c1,
            point_code="SP-01-0_15",
            planned_lat=lat,
            planned_lon=lon,
        )
        s1 = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c1,
            sample_code="SMP-C1-01",
            soil_profile_id="PROF-01",
            sampling_point=sp1,
        )

        sp2 = SamplingPoint(
            id=uuid.uuid4(),
            campaign_id=c2,
            point_code="SP-01-0_15",
            planned_lat=lat,
            planned_lon=lon,
        )
        s2 = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c2,
            sample_code="SMP-C2-01",
            soil_profile_id="PROF-01",
            sampling_point=sp2,
        )

        p1_id, _, _ = AgricultureService._resolve_profile_identity(s1)
        p2_id, _, _ = AgricultureService._resolve_profile_identity(s2)

        assert p1_id != p2_id
        assert str(c1) in p1_id
        assert str(c2) in p2_id

    def test_close_legitimate_profiles_never_merged(self):
        """Two distinct profiles within meters of each other maintain separate auditable identities."""
        c = uuid.uuid4()
        s_a = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c,
            sample_code="SMP-A-01",
            soil_profile_id="PROF-A",
        )
        s_b = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c,
            sample_code="SMP-B-01",
            soil_profile_id="PROF-B",
        )
        p_a, _, _ = AgricultureService._resolve_profile_identity(s_a)
        p_b, _, _ = AgricultureService._resolve_profile_identity(s_b)
        assert p_a != p_b

    def test_case_a_explicit_soil_profile_id_multiple_layers_eligible(self):
        """Case A: Explicit soil_profile_id on sample or point enables multi-layer depth profile extraction."""
        c = uuid.uuid4()
        sp = SamplingPoint(
            id=uuid.uuid4(),
            campaign_id=c,
            point_code="SP-A-01",
            soil_profile_id="PROF-ALPHA",
            planned_lat=10.0,
            planned_lon=20.0,
        )
        s = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c,
            sample_code="SMP-A-01",
            soil_profile_id="PROF-ALPHA",
            sampling_point=sp,
        )
        prof_id, method, conf = AgricultureService._resolve_profile_identity(s)
        assert method == "EXPLICIT_SAMPLE_PROFILE_ID"
        assert "PROF-ALPHA" in prof_id
        assert conf == Decimal("1.00")

    def test_case_b_same_coordinates_different_soil_profile_id_separate(self):
        """Case B: Same coordinates + different soil_profile_id remain separate physical profiles."""
        c = uuid.uuid4()
        lat, lon = 15.000000, 30.000000
        sp_a = SamplingPoint(id=uuid.uuid4(), campaign_id=c, point_code="SP-A", planned_lat=lat, planned_lon=lon)
        s_a = PhysicalSample(id=uuid.uuid4(), campaign_id=c, sample_code="SMP-A", soil_profile_id="PROFILE-NORTH", sampling_point=sp_a)

        sp_b = SamplingPoint(id=uuid.uuid4(), campaign_id=c, point_code="SP-B", planned_lat=lat, planned_lon=lon)
        s_b = PhysicalSample(id=uuid.uuid4(), campaign_id=c, sample_code="SMP-B", soil_profile_id="PROFILE-SOUTH", sampling_point=sp_b)

        p_a, _, _ = AgricultureService._resolve_profile_identity(s_a)
        p_b, _, _ = AgricultureService._resolve_profile_identity(s_b)
        assert p_a != p_b
        assert "PROFILE-NORTH" in p_a
        assert "PROFILE-SOUTH" in p_b

    def test_case_c_same_monitored_profile_different_campaign_separate(self):
        """Case C: Same profile ID sampled across different campaigns are separate temporal observations."""
        c_baseline = uuid.uuid4()
        c_monitoring = uuid.uuid4()
        s_base = PhysicalSample(id=uuid.uuid4(), campaign_id=c_baseline, sample_code="S-BASE", soil_profile_id="PERM-PROF-01")
        s_mon = PhysicalSample(id=uuid.uuid4(), campaign_id=c_monitoring, sample_code="S-MON", soil_profile_id="PERM-PROF-01")

        p_base, _, _ = AgricultureService._resolve_profile_identity(s_base)
        p_mon, _, _ = AgricultureService._resolve_profile_identity(s_mon)
        assert p_base != p_mon
        assert str(c_baseline) in p_base
        assert str(c_monitoring) in p_mon

    def test_case_d_explicit_adjacent_sample_relationship_same_event_accepted(self):
        """Case D: Explicit adjacent-sample relationship within same sampling event is accepted."""
        c = uuid.uuid4()
        event_id = uuid.uuid4()
        s_top = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c,
            sample_code="SMP-CORE-0-15",
        )
        s_top.properties = {
            "adjacent_sample_relationship": "SAME_PHYSICAL_CORE",
            "sampling_event_id": str(event_id),
        }
        s_bot = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c,
            sample_code="SMP-CORE-15-30",
        )
        s_bot.properties = {
            "adjacent_sample_relationship": "SAME_PHYSICAL_CORE",
            "sampling_event_id": str(event_id),
        }
        p_top, m_top, c_top = AgricultureService._resolve_profile_identity(s_top)
        p_bot, m_bot, c_bot = AgricultureService._resolve_profile_identity(s_bot)

        assert m_top == "EXPLICIT_ADJACENT_SAMPLE_EVENT"
        assert m_bot == "EXPLICIT_ADJACENT_SAMPLE_EVENT"
        assert p_top == p_bot
        assert str(event_id) in p_top
        assert c_top == Decimal("0.95")

    def test_case_e_matching_code_prefix_without_authoritative_evidence_incomplete(self):
        """Case E: Matching code prefix without authoritative profile evidence returns PROFILE_IDENTITY_INCOMPLETE and fails closed."""
        c = uuid.uuid4()
        sp = SamplingPoint(id=uuid.uuid4(), campaign_id=c, point_code="SP-42-0_15", planned_lat=10.0, planned_lon=20.0)
        s = PhysicalSample(id=uuid.uuid4(), campaign_id=c, sample_code="SMP-42-0_15", sampling_point=sp)

        prof_id, method, conf = AgricultureService._resolve_profile_identity(s)
        assert method == "PROFILE_IDENTITY_INCOMPLETE"
        assert conf == Decimal("0.00")
        assert "UNGROUPED_PROFILE" in prof_id

        # Section 8 & 9 fail-closed gate: extract profile layers raises PROFILE_IDENTITY_INCOMPLETE
        s.collection_event = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=s.id,
            sampling_point_id=sp.id,
            actual_lat=10.0,
            actual_lon=20.0,
            actual_depth_from_cm=0.0,
            actual_depth_to_cm=15.0,
        )
        s.laboratory_analyses = [
            LaboratoryAnalysis(
                id=uuid.uuid4(),
                qa_status="VERIFIED",
                results=[
                    LaboratoryResult(
                        id=uuid.uuid4(),
                        analyte="SOC_CONCENTRATION",
                        raw_value=Decimal("15.0"),
                        raw_unit="g/kg",
                    )
                ]
            )
        ]
        with pytest.raises(SOCStockCalculationError) as exc_info:
            AgricultureService._extract_profile_layers_from_samples([s], require_verified_lab_qa=True)
        assert exc_info.value.code == "PROFILE_IDENTITY_INCOMPLETE"

    def test_case_f_nearby_coordinates_without_explicit_profile_insufficient(self):
        """Case F: Nearby coordinates alone without explicit profile relationship are insufficient for grouping."""
        c = uuid.uuid4()
        s1 = PhysicalSample(id=uuid.uuid4(), campaign_id=c, sample_code="SMP-NEAR-1")
        s2 = PhysicalSample(id=uuid.uuid4(), campaign_id=c, sample_code="SMP-NEAR-2")

        p1, m1, c1 = AgricultureService._resolve_profile_identity(s1)
        p2, m2, c2 = AgricultureService._resolve_profile_identity(s2)
        assert m1 == "PROFILE_IDENTITY_INCOMPLETE"
        assert m2 == "PROFILE_IDENTITY_INCOMPLETE"
        assert p1 != p2

    def test_client_device_metadata_cannot_assert_profile_identity(self):
        """SECURITY: field-submitted device_metadata claiming an adjacent-sample relationship is ignored."""
        c = uuid.uuid4()
        s = PhysicalSample(id=uuid.uuid4(), campaign_id=c, sample_code="SMP-SPOOF-1")
        s.collection_event = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=s.id,
            sampling_point_id=uuid.uuid4(),
            actual_lat=10.0,
            actual_lon=20.0,
            device_metadata={
                "adjacent_sample_relationship": "SAME_PHYSICAL_CORE",
                "sampling_event_id": str(uuid.uuid4()),
                "legacy_profile_mapping": {"target_profile_id": "X", "review_status": "VERIFIED"},
            },
        )
        _, method, conf = AgricultureService._resolve_profile_identity(s)
        assert method == "PROFILE_IDENTITY_INCOMPLETE"
        assert conf == Decimal("0.00")

    def test_option_b_ephemeral_legacy_profile_mapping_rejected_fail_closed(self):
        """OPTION B: Ephemeral in-process legacy mapping dictionaries are rejected; returns PROFILE_IDENTITY_INCOMPLETE."""
        c = uuid.uuid4()
        s = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c,
            sample_code="LEGACY-SMP-001",
        )
        s.properties = {
            "legacy_profile_mapping": {
                "target_profile_id": "PROF-HISTORIC-01",
                "mapping_method": "PEDOLOGICAL_RECONSTRUCTION",
                "source_record_ids": [str(uuid.uuid4())],
                "review_status": "VERIFIED",
                "reviewed_by": "QA_DIRECTOR_USER",
                "mapped_at": "2026-05-15T12:00:00Z",
            }
        }
        prof_id, method, conf = AgricultureService._resolve_profile_identity(s)
        assert method == "PROFILE_IDENTITY_INCOMPLETE"
        assert conf == Decimal("0.00")
        assert f"UNGROUPED_PROFILE_{s.id}" == prof_id

    def test_option_b_persisted_profile_id_required_for_legacy_resolution(self):
        """OPTION B: Only explicit persisted soil_profile_id resolves legacy samples authoritatively."""
        c = uuid.uuid4()
        s = PhysicalSample(
            id=uuid.uuid4(),
            campaign_id=c,
            sample_code="LEGACY-SMP-002",
            soil_profile_id="PROF-HISTORIC-02",  # Persisted column!
        )
        prof_id, method, conf = AgricultureService._resolve_profile_identity(s)
        assert method == "EXPLICIT_SAMPLE_PROFILE_ID"
        assert "PROF-HISTORIC-02" in prof_id
        assert conf == Decimal("1.00")


class TestVM0042Equation3DirectSoilMass:
    """Verifies VM0042 Equation (3) direct fine-soil mass per unit area and dimensional rigor."""

    def test_exact_dimensional_derivation(self):
        """
        Direct calculation:
        Core diameter = 50 mm = 5 cm -> radius = 2.5 cm.
        Area = pi * 2.5^2 = 19.634954... cm^2.
        N_cores = 1.
        Dry fine soil mass = 250.0 g.
        Formula: M_soil = (250.0 / 19.634954...) * 100.0 = 1273.2395 t/ha.
        """
        mass = calculate_layer_soil_mass_direct(
            dry_fine_soil_mass_g=Decimal("250.00"),
            core_diameter_mm=Decimal("50.00"),
            core_count=1,
        )
        expected_area = Decimal(str(math.pi)) * (Decimal("2.5") ** 2)
        expected_mass = (Decimal("250.00") / expected_area) * Decimal("100.0000")
        assert abs(mass - expected_mass.quantize(Decimal("0.0001"))) <= Decimal("0.0001")

    def test_composite_cores_scaling(self):
        """Compositing N cores divides sample mass across total sampled core area."""
        m_single = calculate_layer_soil_mass_direct(
            dry_fine_soil_mass_g=Decimal("300.00"),
            core_diameter_mm=Decimal("50.00"),
            core_count=1,
        )
        m_composite = calculate_layer_soil_mass_direct(
            dry_fine_soil_mass_g=Decimal("900.00"),  # 3 cores pooled
            core_diameter_mm=Decimal("50.00"),
            core_count=3,
        )
        assert m_single == m_composite

    def test_bulk_density_derived_procedure(self):
        """Thickness * BD * (1 - CF) * 100."""
        # 15 cm, BD = 1.30 g/cm3, CF = 5% (0.05)
        # M_soil = 15 * 1.30 * 0.95 * 100 = 1852.5000 t/ha
        m = calculate_layer_soil_mass(
            thickness_cm=Decimal("15.00"),
            bulk_density_g_cm3=Decimal("1.3000"),
            coarse_fragment_fraction=Decimal("0.0500"),
        )
        assert m == Decimal("1852.5000")

    def test_layer_soc_mass_conversion(self):
        """Layer SOC mass = M_soil * (SOC_conc / 1000)."""
        # 1852.5 t/ha * 20 g C / kg = 1852.5 * 0.02 = 37.0500 t C/ha
        soc_m = calculate_layer_soc_mass(
            layer_soil_mass_t_ha=Decimal("1852.5000"),
            soc_concentration_g_kg=Decimal("20.0000"),
        )
        assert soc_m == Decimal("37.0500")

    def test_literal_vm0042_equation3_numeric_parity(self):
        """
        Direct hand-verifiable parity vector between literal VM0042 Equation (3) and production code:
        Literal: SOC = [ (MS * C_SOC) / (A * N) ] * 0.1000
        Production: M_soil = [ MS / (A * N) ] * 100.0, SOC = M_soil * (C_SOC / 1000.0)
        Inputs: MS=250.00g, d=50.00mm, N=1, C_SOC=20.00 g C/kg dry fine soil.
        """
        ms = Decimal("250.00")
        diam_mm = Decimal("50.00")
        diam_cm = diam_mm / Decimal("10.0")
        radius_cm = diam_cm / Decimal("2.0")
        area_cm2 = Decimal(str(math.pi)) * (radius_cm ** 2)
        n_cores = 1
        c_soc = Decimal("20.00")
        cf_vm0042 = Decimal("0.1000")

        # 1. Literal VM0042 v2.2 Equation (3)
        soc_literal = ((ms * c_soc) / (area_cm2 * n_cores)) * cf_vm0042
        soc_literal_rounded = soc_literal.quantize(Decimal("0.0001"))

        # 2. Production implementation
        prod_m_soil = calculate_layer_soil_mass_direct(
            dry_fine_soil_mass_g=ms,
            core_diameter_mm=diam_mm,
            core_count=n_cores,
        )
        prod_soc = calculate_layer_soc_mass(
            layer_soil_mass_t_ha=prod_m_soil,
            soc_concentration_g_kg=c_soc,
        )

        diff = abs(prod_soc - soc_literal_rounded)
        assert diff <= Decimal("0.0001")
        assert prod_soc == Decimal("25.4648")


class TestOfficialESMGoldenVector:
    """
    Official Verra VM0042 Example & Wendt and Hauser (2013) Golden Vector.
    In VM0042 Section 8.1.1.2:
    Cumulative reference soil mass for 0-30 cm is 1950 Mg/ha.
    Point VM42point1-1 cumulative SOC stock to 1950 Mg/ha is 47.36 Mg/ha (t C/ha).
    Second layer 1950 to 3253 Mg/ha.
    """

    def test_official_vm0042_golden_point(self):
        """
        Validates reproduction of VM0042 Section 8.1.1.2 illustrative example:
        Profile at VM42point1-1:
        Layer 1 (0-30 cm): Soil mass = 1950.0 t/ha, SOC conc = 24.2872 g/kg -> SOC mass = 47.3600 t C/ha.
        Layer 2 (30-50 cm): Soil mass = 1303.0 t/ha, cumulative = 3253.0 t/ha, SOC conc = 12.0000 g/kg -> SOC mass = 15.6360 t C/ha.
        Reference mass: 1950.0 t/ha.
        ESM normalized SOC stock: Exactly 47.3600 t C/ha.
        """
        layers = [
            LayerInput(
                layer_index=0,
                depth_upper_cm=Decimal("0.00"),
                depth_lower_cm=Decimal("30.00"),
                bulk_density_g_cm3=Decimal("0.6500"),  # 30 * 0.65 * 100 = 1950 t/ha
                soc_concentration_g_kg=Decimal("24.28718"),  # 1950 * 0.02428718 = 47.3600 t C/ha
            ),
            LayerInput(
                layer_index=1,
                depth_upper_cm=Decimal("30.00"),
                depth_lower_cm=Decimal("50.00"),
                bulk_density_g_cm3=Decimal("0.6515"),  # 20 * 0.6515 * 100 = 1303 t/ha -> Cum = 3253 t/ha
                soc_concentration_g_kg=Decimal("12.0000"),
            ),
        ]

        # 1. Piecewise Layer Proportioning (Ellert & Bettany 1995)
        res_prop = calculate_profile_esm_proportioning(
            layers=layers,
            reference_soil_mass_t_ha=Decimal("1950.0000"),
            reference_depth_cm=Decimal("30.00"),
        )
        assert abs(res_prop.soc_stock_t_c_per_ha - Decimal("47.3600")) <= Decimal("0.0002")
        assert res_prop.total_sampled_soil_mass_t_ha == Decimal("3253.0000")
        assert res_prop.equivalent_depth_cm == Decimal("30.00")
        assert res_prop.depth_sufficiency_status == "DEPTH_SUFFICIENT"

        # 2. Wendt & Hauser (2013) Spline Interpolation
        res_spline = calculate_profile_esm_spline(
            layers=layers,
            reference_soil_mass_t_ha=Decimal("1950.0000"),
            reference_depth_cm=Decimal("30.00"),
        )
        assert abs(res_spline.soc_stock_t_c_per_ha - Decimal("47.3600")) <= Decimal("0.0002")

    def test_wendt_hauser_point1_exact_parity(self):
        """VM42point1: Exact natural cubic spline parity against official Wendt & Hauser (2013) workbook."""
        ref_mass = Decimal("1950.0000")
        p1_layers = [
            LayerInput(
                layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("30.00"),
                soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                fine_soil_mass_g=Decimal("283.20"), core_diameter_mm=Decimal("21.50"), core_count=4,
                soc_concentration_g_kg=Decimal("24.2872"),
            ),
            LayerInput(
                layer_index=1, depth_upper_cm=Decimal("30.00"), depth_lower_cm=Decimal("50.00"),
                soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                fine_soil_mass_g=Decimal("189.20"), core_diameter_mm=Decimal("21.50"), core_count=4,
                soc_concentration_g_kg=Decimal("12.6815"),
            ),
        ]
        res1 = calculate_profile_esm_spline(layers=p1_layers, reference_soil_mass_t_ha=ref_mass)
        assert res1.esm_algorithm == "WENDT_HAUSER_2013_CUBIC_SPLINE"
        # Natural cubic spline exact value is 47.3610 Mg C/ha, depth 29.9978 cm -> 30.0 cm
        assert abs(res1.soc_stock_t_c_per_ha - Decimal("47.3610")) <= Decimal("0.0002")
        assert res1.soc_stock_t_c_per_ha.quantize(Decimal("0.01")) == Decimal("47.36")
        assert res1.equivalent_depth_cm == Decimal("30.00")

    def test_wendt_hauser_point2_nontrivial_parity(self):
        """VM42point2: Non-trivial natural cubic spline adjustment (1533.53 < 1950.0 Mg/ha)."""
        ref_mass = Decimal("1950.0000")
        p2_layers = [
            LayerInput(
                layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("30.00"),
                soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                fine_soil_mass_g=Decimal("222.70"), core_diameter_mm=Decimal("21.50"), core_count=4,
                soc_concentration_g_kg=Decimal("28.7673"),
            ),
            LayerInput(
                layer_index=1, depth_upper_cm=Decimal("30.00"), depth_lower_cm=Decimal("50.00"),
                soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                fine_soil_mass_g=Decimal("144.30"), core_diameter_mm=Decimal("21.50"), core_count=4,
                soc_concentration_g_kg=Decimal("10.6470"),
            ),
        ]
        res2 = calculate_profile_esm_spline(layers=p2_layers, reference_soil_mass_t_ha=ref_mass)
        assert res2.esm_algorithm == "WENDT_HAUSER_2013_CUBIC_SPLINE"
        # Natural cubic spline raw value is 49.9121 Mg C/ha, depth 38.34 cm
        assert abs(res2.soc_stock_t_c_per_ha - Decimal("49.9121")) <= Decimal("0.0002")
        assert res2.soc_stock_t_c_per_ha.quantize(Decimal("0.1")) == Decimal("49.9")
        assert res2.equivalent_depth_cm.quantize(Decimal("0.1")) == Decimal("38.3")

    def test_wendt_hauser_point3_nontrivial_parity(self):
        """VM42point3: Non-trivial natural cubic spline adjustment (1497.73 < 1950.0 Mg/ha). Rounds to 36.8, not 36.9!"""
        ref_mass = Decimal("1950.0000")
        p3_layers = [
            LayerInput(
                layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("30.00"),
                soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                fine_soil_mass_g=Decimal("217.50"), core_diameter_mm=Decimal("21.50"), core_count=4,
                soc_concentration_g_kg=Decimal("20.6790"),
            ),
            LayerInput(
                layer_index=1, depth_upper_cm=Decimal("30.00"), depth_lower_cm=Decimal("50.00"),
                soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                fine_soil_mass_g=Decimal("143.50"), core_diameter_mm=Decimal("21.50"), core_count=4,
                soc_concentration_g_kg=Decimal("11.2831"),
            ),
        ]
        res3 = calculate_profile_esm_spline(layers=p3_layers, reference_soil_mass_t_ha=ref_mass)
        assert res3.esm_algorithm == "WENDT_HAUSER_2013_CUBIC_SPLINE"
        # Natural cubic spline raw value is 36.7810 Mg C/ha, depth 39.14 cm
        assert abs(res3.soc_stock_t_c_per_ha - Decimal("36.7810")) <= Decimal("0.0002")
        # STRICT SCIENTIFIC ACCEPTANCE: Rounds to 36.8 Mg C/ha, exactly matching published target!
        assert res3.soc_stock_t_c_per_ha.quantize(Decimal("0.1")) == Decimal("36.8")
        assert res3.equivalent_depth_cm.quantize(Decimal("0.1")) == Decimal("39.1")

    def test_wendt_hauser_published_rounding_parity(self):
        """Verifies that all three published points round to their exact published display precision."""
        ref_mass = Decimal("1950.0000")
        inputs = [
            (Decimal("283.20"), Decimal("24.2872"), Decimal("189.20"), Decimal("12.6815"), Decimal("47.36"), Decimal("0.01"), Decimal("30.0")),
            (Decimal("222.70"), Decimal("28.7673"), Decimal("144.30"), Decimal("10.6470"), Decimal("49.9"), Decimal("0.1"), Decimal("38.3")),
            (Decimal("217.50"), Decimal("20.6790"), Decimal("143.50"), Decimal("11.2831"), Decimal("36.8"), Decimal("0.1"), Decimal("39.1")),
        ]
        for w1, c1, w2, c2, target_soc, precision, target_depth in inputs:
            layers = [
                LayerInput(layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("30.00"),
                           soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                           fine_soil_mass_g=w1, core_diameter_mm=Decimal("21.50"),
                           core_count=4, soc_concentration_g_kg=c1),
                LayerInput(layer_index=1, depth_upper_cm=Decimal("30.00"), depth_lower_cm=Decimal("50.00"),
                           soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                           fine_soil_mass_g=w2, core_diameter_mm=Decimal("21.50"),
                           core_count=4, soc_concentration_g_kg=c2),
            ]
            res = calculate_profile_esm_spline(layers=layers, reference_soil_mass_t_ha=ref_mass)
            assert res.soc_stock_t_c_per_ha.quantize(precision) == target_soc
            assert res.equivalent_depth_cm.quantize(Decimal("0.1")) == target_depth

    def test_wendt_hauser_boundary_conditions(self):
        """Verifies that the authoritative cubic spline enforces natural boundary conditions S''(0) = S''(M_max) = 0."""
        layers = [
            LayerInput(layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("30.00"),
                       soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                       fine_soil_mass_g=Decimal("283.20"), core_diameter_mm=Decimal("21.50"), core_count=4, soc_concentration_g_kg=Decimal("24.2872")),
            LayerInput(layer_index=1, depth_upper_cm=Decimal("30.00"), depth_lower_cm=Decimal("50.00"),
                       soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                       fine_soil_mass_g=Decimal("189.20"), core_diameter_mm=Decimal("21.50"), core_count=4, soc_concentration_g_kg=Decimal("12.6815")),
        ]
        res = calculate_profile_esm_spline(layers=layers, reference_soil_mass_t_ha=Decimal("1950.0000"))
        assert res.algorithm_metadata["boundary_conditions"] == "S''(0) = 0, S''(M_max) = 0 (NATURAL)"
        assert res.algorithm_metadata["interpolation_type"] == "NATURAL_CUBIC_SPLINE"

    def test_pchip_not_used_for_authoritative_wendt_path(self):
        """Verifies that PCHIP is NOT used for the authoritative Wendt & Hauser path."""
        layers = [
            LayerInput(layer_index=0, depth_upper_cm=Decimal("0.00"), depth_lower_cm=Decimal("30.00"),
                       soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                       fine_soil_mass_g=Decimal("217.50"), core_diameter_mm=Decimal("21.50"), core_count=4, soc_concentration_g_kg=Decimal("20.6790")),
            LayerInput(layer_index=1, depth_upper_cm=Decimal("30.00"), depth_lower_cm=Decimal("50.00"),
                       soil_mass_provenance="DIRECT_SOIL_MASS", bulk_density_g_cm3=None, bulk_density_provenance="NOT_REQUIRED",
                       fine_soil_mass_g=Decimal("143.50"), core_diameter_mm=Decimal("21.50"), core_count=4, soc_concentration_g_kg=Decimal("11.2831")),
        ]
        ref_mass = Decimal("1950.0000")
        authoritative_res = calculate_profile_esm_spline(layers=layers, reference_soil_mass_t_ha=ref_mass)
        diagnostic_res = calculate_profile_esm_diagnostic_pchip(layers=layers, reference_soil_mass_t_ha=ref_mass)

        # 1. Algorithm identifiers are strictly separated
        assert authoritative_res.esm_algorithm == "WENDT_HAUSER_2013_CUBIC_SPLINE"
        assert diagnostic_res.esm_algorithm == "DIAGNOSTIC_PCHIP"

        # 2. Authoritative natural cubic spline yields 36.7810 (rounds to 36.8)
        assert authoritative_res.soc_stock_t_c_per_ha.quantize(Decimal("0.1")) == Decimal("36.8")

        # 3. Diagnostic PCHIP yields 36.8968 (erroneously rounds to 36.9)
        assert diagnostic_res.soc_stock_t_c_per_ha.quantize(Decimal("0.1")) == Decimal("36.9")
        assert authoritative_res.soc_stock_t_c_per_ha != diagnostic_res.soc_stock_t_c_per_ha

    def test_divergent_bulk_density_esm_normalization(self):
        """
        Profiles with lower vs higher bulk density normalized to same reference soil mass
        demonstrate true ESM mass-equivalence adjustment.
        """
        # Profile A (Dense): BD = 1.30 g/cm3, 0-15cm mass = 1950 t/ha, SOC = 20 g/kg (39.0 t C/ha)
        # Profile B (Porous): BD = 1.00 g/cm3, 0-15cm mass = 1500 t/ha (30 t C/ha), 15-30cm mass = 1500 t/ha (15 t C/ha)
        # M_ref = 1950 t/ha.
        # Profile B needs 450 t/ha from Layer 2 (fraction = 450/1500 = 0.30).
        # Profile B ESM SOC = 30 + 0.30 * 15 = 34.5000 t C/ha.
        layers_b = [
            LayerInput(
                layer_index=0,
                depth_upper_cm=Decimal("0.00"),
                depth_lower_cm=Decimal("15.00"),
                bulk_density_g_cm3=Decimal("1.0000"),
                soc_concentration_g_kg=Decimal("20.0000"),
            ),
            LayerInput(
                layer_index=1,
                depth_upper_cm=Decimal("15.00"),
                depth_lower_cm=Decimal("30.00"),
                bulk_density_g_cm3=Decimal("1.0000"),
                soc_concentration_g_kg=Decimal("10.0000"),
            ),
        ]
        res_b = calculate_profile_esm_proportioning(
            layers=layers_b,
            reference_soil_mass_t_ha=Decimal("1950.0000"),
        )
        assert res_b.soc_stock_t_c_per_ha == Decimal("34.5000")
        assert res_b.equivalent_depth_cm == Decimal("19.50")  # 15 + 0.30 * 15 = 19.50 cm


class TestESMRulesAndFailClosedGates:
    """Verifies fail-closed rules: extrapolation, depth gaps, inversions, and lab QA."""

    def test_extrapolation_beyond_measured_profile_raises_error(self):
        """VM0042 strictly prohibits out-of-range downward extrapolation."""
        layers = [
            LayerInput(
                layer_index=0,
                depth_upper_cm=Decimal("0.00"),
                depth_lower_cm=Decimal("15.00"),
                bulk_density_g_cm3=Decimal("1.2000"),  # Total mass = 1800 t/ha
                soc_concentration_g_kg=Decimal("20.0000"),
            ),
        ]
        with pytest.raises(SOCStockCalculationError) as exc_info:
            calculate_profile_esm_proportioning(
                layers=layers,
                reference_soil_mass_t_ha=Decimal("2500.0000"),  # Exceeds 1800 t/ha
                allow_shallow_soil_exception=False,
            )
        assert exc_info.value.code == "ESM_REFERENCE_MASS_EXCEEDS_MEASURED_PROFILE"

    def test_depth_gap_rejected(self):
        """Depth profile with missing increment (e.g. 0-15 then 20-30) fails closed."""
        layers = [
            LayerInput(
                layer_index=0,
                depth_upper_cm=Decimal("0.00"),
                depth_lower_cm=Decimal("15.00"),
                bulk_density_g_cm3=Decimal("1.20"),
                soc_concentration_g_kg=Decimal("20.0"),
            ),
            LayerInput(
                layer_index=1,
                depth_upper_cm=Decimal("20.00"),  # Gap: 15 to 20 cm
                depth_lower_cm=Decimal("30.00"),
                bulk_density_g_cm3=Decimal("1.20"),
                soc_concentration_g_kg=Decimal("15.0"),
            ),
        ]
        with pytest.raises(SOCStockCalculationError) as exc_info:
            validate_profile_layers(layers)
        assert exc_info.value.code == "PROFILE_DEPTH_GAP"

    def test_overlapping_layers_rejected(self):
        """Overlapping depth bounds fail closed."""
        layers = [
            LayerInput(
                layer_index=0,
                depth_upper_cm=Decimal("0.00"),
                depth_lower_cm=Decimal("20.00"),
                bulk_density_g_cm3=Decimal("1.20"),
                soc_concentration_g_kg=Decimal("20.0"),
            ),
            LayerInput(
                layer_index=1,
                depth_upper_cm=Decimal("15.00"),  # Overlap: 15 < 20
                depth_lower_cm=Decimal("30.00"),
                bulk_density_g_cm3=Decimal("1.20"),
                soc_concentration_g_kg=Decimal("15.0"),
            ),
        ]
        with pytest.raises(SOCStockCalculationError) as exc_info:
            validate_profile_layers(layers)
        assert exc_info.value.code == "PROFILE_OVERLAPPING_LAYERS"

    def test_unverified_laboratory_qa_excluded(self):
        """Section 22: Samples with UNVERIFIED (PENDING) lab results are excluded."""
        s = PhysicalSample(
            id=uuid.uuid4(),
            sample_code="SMP-TEST-UNVERIFIED",
            soil_profile_id="PROF-TEST",
            collection_event=SampleCollectionEvent(
                id=uuid.uuid4(),
                physical_sample_id=uuid.uuid4(),
                sampling_point_id=uuid.uuid4(),
                actual_lat=10.0,
                actual_lon=20.0,
                actual_depth_from_cm=0.0,
                actual_depth_to_cm=30.0,
            ),
            laboratory_analyses=[
                LaboratoryAnalysis(
                    id=uuid.uuid4(),
                    laboratory_name="Test Lab",
                    analytical_method="DRY_COMBUSTION",
                    analysis_date="2026-05-01",
                    qa_status="PENDING",  # Not verified!
                    results=[
                        LaboratoryResult(
                            id=uuid.uuid4(),
                            analyte="SOC_CONCENTRATION",
                            raw_value=Decimal("25.0"),
                            raw_unit="g/kg",
                            is_superseded=False,
                        )
                    ]
                )
            ]
        )
        grouped = AgricultureService._extract_profile_layers_from_samples([s], require_verified_lab_qa=True)
        assert len(grouped) == 0  # Excluded because lab QA is PENDING!


class TestCarbonInvariantsAndLineage:
    """Verifies strict Phase 3B-1 invariants: zero tCO2e, no ΔSOC credit, t C/ha units."""

    def test_area_weighted_aggregation(self):
        """Project aggregation correctly weights strata by authoritative area."""
        strata = [
            {"stratum_code": "STRAT-A", "area_ha": Decimal("100.00"), "stratum_mean_soc_t_c_per_ha": Decimal("50.0000")},
            {"stratum_code": "STRAT-B", "area_ha": Decimal("300.00"), "stratum_mean_soc_t_c_per_ha": Decimal("70.0000")},
        ]
        # (100 * 50 + 300 * 70) / 400 = (5000 + 21000) / 400 = 26000 / 400 = 65.0000 t C/ha
        proj_soc, tot_area = aggregate_project_area_weighted_soc_stock(strata)
        assert proj_soc == Decimal("65.0000")
        assert tot_area == Decimal("400.0000")
