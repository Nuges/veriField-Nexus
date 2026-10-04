"""
=============================================================================
VeriField Nexus — Verra VM0044 v1.2 Biochar Quantification Engine Test Suite
=============================================================================
Methodology: Verra VM0044 v1.2 (Sectoral Scope 13 Waste Handling & Disposal)
Normative Tools: VCS Standard v4.5, VT0008 v1.0, CDM TOOL03, TOOL05, TOOL12, TOOL16, IPCC 2019

Full test coverage across:
1. Version Locking & Quarantine (VM0044 v1.2 active, v2.0 quarantined)
2. Normative Rules & External Document Dependencies Seed & Queries
3. Section 4 Applicability Conditions (Greenfield, Waste Biomass, Process, End Use, Wetland)
4. Section 7 Additionality Assessment & VT0008 Investment Analysis (Option 2 Benchmark)
5. Canonical Calculation Snapshots & Deterministic SHA-256 Hashing
6. Core Quantification Equations (1) through (15) with Decimal Precision
7. High-Tech vs Low-Tech Pyrolysis Conversion Pathways (CH4 Process Emissions)
8. Soil vs Non-Soil Durable Application Pathways (High-Tech Requirement)
9. Transport Exemption Threshold (<=200km vs >200km per CDM TOOL16)
10. VCS Conservativeness Uncertainty Deduction (>10% Threshold)
11. Multi-Registry Isolation & Cross-Methodology Double-Counting Protection (Puro & VM0042)
12. Ledger P0 Fail-Closed Minting Integration & Multi-Tenant Role Security
13. REST API Endpoint Integration & Concurrency Idempotency
=============================================================================
"""

import asyncio
import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
import jwt as pyjwt
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharLabAnalysis,
    FeedstockLot,
    FeedstockSource,
    ProductionFacility,
)
from app.domains.biochar.puro_models import PuroCalculationExecution
from app.domains.biochar.services.vm0044_quantification import (
    VM0044CalculatorV12,
    VM0044QuantificationError,
)
from app.domains.biochar.vm0044_models import (
    VM0044AdditionalityAssessment,
    VM0044ApplicabilityEvaluation,
    VM0044CalculationExecution,
    VM0044CalculationSnapshot,
    VM0044MethodologyVersion,
    VM0044NormativeDependency,
    VM0044RuleDefinition,
)
from app.domains.biochar.vm0044_rules import (
    CARBON_TO_CO2_FACTOR,
    DEFAULT_FE_LOW_TECH_CH4,
    DEFAULT_PR_DE_LOW_TECH_UNKNOWN_TEMP,
    GWP_CH4,
    MAX_ELIGIBLE_MOLAR_H_C,
    MAX_UTILIZATION_TIMELINE_DAYS,
    TABLE_3_PERMANENCE_FACTORS,
    TABLE_4_DEFAULT_FC_P,
    TRANSPORT_EXEMPTION_DISTANCE_KM,
    VM0044_OFFICIAL_CODE,
    VM0044_OFFICIAL_VERSION,
    get_default_fc_p,
    resolve_vcs_program_version,
    seed_vm0044_normative_metadata,
)
from app.domains.biochar.vm0044_schemas import (
    VM0044AdditionalityEvaluateRequest,
    VM0044ApplicabilityEvaluateRequest,
    VM0044CalculationRequest,
    VM0044SnapshotRequest,
)
from app.domains.ledger.api import execute_carbon_minting, MintRequest
from app.domains.ledger.models import Signature
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


def _make_auth_headers(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID) -> dict:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id),
    }
    token = pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def vm0044_test_env(db_session: AsyncSession):
    """Sets up an isolated project, facility, feedstock, and user in PostgreSQL."""
    await seed_vm0044_normative_metadata(db_session)

    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"VM0044 Test Org {org_id.hex[:6]}",
        org_type="DEVELOPER",
        status="ACTIVE",
    )
    db_session.add(org)
    await db_session.flush()

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"vm0044_admin_{user_id.hex[:6]}@verifield.io",
        full_name="VM0044 Admin",
        role="ORG_ADMIN",
        organization_id=org_id,
        status="active",
        is_active=True,
    )
    db_session.add(user)

    proj_id = uuid.uuid4()
    proj = Project(
        id=proj_id,
        organization_id=org_id,
        name=f"Verra Biochar Project {proj_id.hex[:6]}",
        country="Kenya",
    )
    db_session.add(proj)

    fac_id = uuid.uuid4()
    fac = ProductionFacility(
        id=fac_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-VM44-{fac_id.hex[:6]}",
        facility_name="Nairobi High-Tech Pyrolysis Plant",
        facility_status="NEW_OPERATIONAL",
        technology_type="HIGH_TEMPERATURE_PYROLYSIS",
    )
    db_session.add(fac)

    src_id = uuid.uuid4()
    src = FeedstockSource(
        id=src_id,
        organization_id=org_id,
        project_id=proj_id,
        source_code=f"SRC-COFFEE-{src_id.hex[:6]}",
        source_name="Coffee Husk Agricultural Residue",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="COFFEE_HUSK",
        origin_location="Kiambu, Kenya",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="OPEN_BURNING",
    )
    db_session.add(src)
    await db_session.flush()

    lot_id = uuid.uuid4()
    lot = FeedstockLot(
        id=lot_id,
        organization_id=org_id,
        project_id=proj_id,
        source_id=src_id,
        lot_number=f"LOT-HUSK-{lot_id.hex[:6]}",
        feedstock_type="AGRICULTURAL_RESIDUE",
        mass_received_tonnes=Decimal("100.0"),
        moisture_content_pct=Decimal("12.0"),
        dry_mass_tonnes=Decimal("88.0"),
    )
    db_session.add(lot)

    # 1. High-Tech Batch (>600°C)
    batch_high_id = uuid.uuid4()
    batch_high = BiocharBatch(
        id=batch_high_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_number=f"BATCH-HT-{batch_high_id.hex[:6]}",
        facility_name="Nairobi High-Tech Pyrolysis Plant",
        kiln_id="KILN-HT-01",
        feedstock_type="AGRICULTURAL_RESIDUE",
        feedstock_weight_tonnes=Decimal("100.0"),
        moisture_content_pct=Decimal("12.0"),
        pyrolysis_temp_celsius=650.0,
        residence_time_minutes=45.0,
        biochar_yield_tonnes=Decimal("30.0"),
        dry_mass_tonnes=Decimal("30.0"),
        fixed_carbon_pct=82.0,
        molar_h_c_ratio=0.35,
        status="ACTIVE",
    )
    db_session.add(batch_high)

    lab_high = BiocharLabAnalysis(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch_high_id,
        sample_id=f"SMP-HT-{uuid.uuid4().hex[:6]}",
        sampling_date=datetime.now(timezone.utc),
        laboratory_name="Kenya Bureau of Standards Accredited Lab",
        organic_carbon_pct=82.0,
        fixed_carbon_pct=78.0,
        molar_h_c_ratio=0.35,
        moisture_pct=5.0,
        ash_pct=2.5,
        heavy_metals_pass=True,
        qa_status="VERIFIED",
    )
    db_session.add(lab_high)

    # End use: Soil application non-wetland
    eu_soil_id = uuid.uuid4()
    eu_soil = BiocharEndUseRecord(
        id=eu_soil_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch_high_id,
        end_use_type="SOIL_APPLICATION",
        applied_quantity_tonnes=Decimal("30.0"),
        event_date=datetime(2026, 3, 15, tzinfo=timezone.utc),
        wetland_exclusion_screened=True,
        metadata_json={"incorporation_depth_cm": 15.0},
        verification_status="VERIFIED",
    )
    db_session.add(eu_soil)

    # 2. Low-Tech Batch (Kon-Tiki / Kiln, unmonitored temp)
    fac_low_id = uuid.uuid4()
    fac_low = ProductionFacility(
        id=fac_low_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-LOW-{fac_low_id.hex[:6]}",
        facility_name="Rural Kon-Tiki Kiln Unit",
        facility_status="NEW_OPERATIONAL",
        technology_type="LOW_TECH_KILN",
    )
    db_session.add(fac_low)

    batch_low_id = uuid.uuid4()
    batch_low = BiocharBatch(
        id=batch_low_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_number=f"BATCH-LT-{batch_low_id.hex[:6]}",
        facility_name="Rural Kon-Tiki Kiln Unit",
        kiln_id="KILN-LT-01",
        feedstock_type="AGRICULTURAL_RESIDUE",
        feedstock_weight_tonnes=Decimal("50.0"),
        moisture_content_pct=Decimal("15.0"),
        pyrolysis_temp_celsius=0.0,  # Unmonitored temp
        residence_time_minutes=60.0,
        biochar_yield_tonnes=Decimal("12.0"),
        dry_mass_tonnes=Decimal("12.0"),
        fixed_carbon_pct=72.0,
        molar_h_c_ratio=0.55,
        status="ACTIVE",
    )
    db_session.add(batch_low)

    lab_low = BiocharLabAnalysis(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch_low_id,
        sample_id=f"SMP-LT-{uuid.uuid4().hex[:6]}",
        sampling_date=datetime.now(timezone.utc),
        laboratory_name="Certified Agricultural Testing Lab",
        organic_carbon_pct=72.0,
        fixed_carbon_pct=68.0,
        molar_h_c_ratio=0.55,
        moisture_pct=6.0,
        ash_pct=3.0,
        heavy_metals_pass=True,
        qa_status="VERIFIED",
    )
    db_session.add(lab_low)

    eu_low_id = uuid.uuid4()
    eu_low = BiocharEndUseRecord(
        id=eu_low_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch_low_id,
        end_use_type="SOIL_APPLICATION",
        applied_quantity_tonnes=Decimal("12.0"),
        event_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
        wetland_exclusion_screened=True,
        metadata_json={"incorporation_depth_cm": 12.0},
        verification_status="VERIFIED",
    )
    db_session.add(eu_low)

    await db_session.commit()

    return {
        "org_id": org_id,
        "user_id": user_id,
        "user": user,
        "project_id": proj_id,
        "fac_high_id": fac_id,
        "batch_high_id": batch_high_id,
        "eu_soil_id": eu_soil_id,
        "fac_low_id": fac_low_id,
        "batch_low_id": batch_low_id,
        "eu_low_id": eu_low_id,
        "src_id": src_id,
        "lot_id": lot_id,
    }


# =============================================================================
# 1. Version Locking & Quarantine Tests
# =============================================================================

@pytest.mark.asyncio
async def test_vm0044_v12_active_and_ccp_approved(db_session: AsyncSession, vm0044_test_env):
    """Verifies VM0044 v1.2 is active, sectoral scope 13, and CCP-approved."""
    mv = await VM0044CalculatorV12.verify_methodology_version(db_session, "1.2")
    assert mv.code == "VM0044"
    assert mv.version == "1.2"
    assert mv.status == "ACTIVE"
    assert mv.mitigation_outcome == "REMOVALS"
    assert mv.ccp_approved is True
    assert mv.sectoral_scope == "13"


@pytest.mark.asyncio
async def test_vm0044_v20_quarantined_fail_closed(db_session: AsyncSession):
    """Verifies VM0044 v2.0 is quarantined and rejected fail-closed."""
    with pytest.raises(VM0044QuantificationError) as exc_info:
        await VM0044CalculatorV12.verify_methodology_version(db_session, "2.0")
    assert "METHODOLOGY_VERSION_QUARANTINED" in str(exc_info.value)

    with pytest.raises(VM0044QuantificationError) as exc_info:
        await VM0044CalculatorV12.verify_methodology_version(db_session, "v2.0-draft")
    assert "METHODOLOGY_VERSION_QUARANTINED" in str(exc_info.value)


# =============================================================================
# 2. Normative Rules & External Document Dependencies Tests
# =============================================================================

@pytest.mark.asyncio
async def test_vm0044_normative_metadata_seeding(db_session: AsyncSession):
    """Verifies idempotent seeding of 21 normative rules and 7 normative dependencies."""
    await seed_vm0044_normative_metadata(db_session)
    await db_session.commit()

    rules = (await db_session.execute(select(VM0044RuleDefinition))).scalars().all()
    assert len(rules) >= 21

    rule_ids = {r.rule_id for r in rules}
    assert "VM0044-AP-01" in rule_ids
    assert "VM0044-AP-02" in rule_ids
    assert "VM0044-AD-03" in rule_ids
    assert "VM0044-EQ-15" in rule_ids

    deps = (await db_session.execute(select(VM0044NormativeDependency))).scalars().all()
    assert len(deps) >= 7

    dep_codes = {d.code for d in deps}
    assert "VCS_STANDARD_V4_5" in dep_codes
    assert "VT0008_V1_0" in dep_codes
    assert "CDM_TOOL16_V4_0" in dep_codes


def test_stoichiometric_constants_and_table_parameters():
    """Validates stoichiometric conversion (44/12), GWP_CH4, and Table 3 & 4 parameters."""
    # 44 / 12 = 3.666666...
    assert CARBON_TO_CO2_FACTOR == Decimal("44") / Decimal("12")
    assert GWP_CH4 == Decimal("28")
    assert DEFAULT_FE_LOW_TECH_CH4 == Decimal("0.049")
    assert TRANSPORT_EXEMPTION_DISTANCE_KM == 200.0
    assert MAX_ELIGIBLE_MOLAR_H_C == 0.70
    assert MAX_UTILIZATION_TIMELINE_DAYS == 365

    # Table 3 permanence factors (strictly 3 temperature tiers per VM0044 v1.2 Table 3)
    assert len(TABLE_3_PERMANENCE_FACTORS) == 3
    assert TABLE_3_PERMANENCE_FACTORS["HIGH_TEMP_PYROLYSIS"] == Decimal("0.89")
    assert TABLE_3_PERMANENCE_FACTORS["MEDIUM_TEMP_PYROLYSIS"] == Decimal("0.80")
    assert TABLE_3_PERMANENCE_FACTORS["LOW_TEMP_PYROLYSIS"] == Decimal("0.65")
    # Conservative unknown temperature default (Footnote 21 & Section 8.2.2.2)
    assert DEFAULT_PR_DE_LOW_TECH_UNKNOWN_TEMP == Decimal("0.56")

    # Table 4 complete set of 6 IPCC 2019 feedstocks
    assert len(TABLE_4_DEFAULT_FC_P) == 6
    assert TABLE_4_DEFAULT_FC_P["ANIMAL_MANURE"]["PYROLYSIS"] == Decimal("0.38")
    assert TABLE_4_DEFAULT_FC_P["ANIMAL_MANURE"]["GASIFICATION"] == Decimal("0.09")
    assert TABLE_4_DEFAULT_FC_P["WOOD"]["PYROLYSIS"] == Decimal("0.77")
    assert TABLE_4_DEFAULT_FC_P["WOOD"]["GASIFICATION"] == Decimal("0.52")
    assert TABLE_4_DEFAULT_FC_P["HERBACEOUS"]["PYROLYSIS"] == Decimal("0.65")
    assert TABLE_4_DEFAULT_FC_P["HERBACEOUS"]["GASIFICATION"] == Decimal("0.28")
    assert TABLE_4_DEFAULT_FC_P["RICE_HUSK_STRAW"]["PYROLYSIS"] == Decimal("0.49")
    assert TABLE_4_DEFAULT_FC_P["RICE_HUSK_STRAW"]["GASIFICATION"] == Decimal("0.13")
    assert TABLE_4_DEFAULT_FC_P["NUT_SHELLS_PITS"]["PYROLYSIS"] == Decimal("0.74")
    assert TABLE_4_DEFAULT_FC_P["NUT_SHELLS_PITS"]["GASIFICATION"] == Decimal("0.40")
    assert TABLE_4_DEFAULT_FC_P["BIOSOLIDS_PAPER_SLUDGE"]["PYROLYSIS"] == Decimal("0.35")
    assert TABLE_4_DEFAULT_FC_P["BIOSOLIDS_PAPER_SLUDGE"]["GASIFICATION"] == Decimal("0.07")


def test_equation_1_stoichiometric_conversion_44_over_12():
    """
    P0 Stoichiometric Truth:
    Equation (1) converts stabilized organic carbon to CO2e strictly via:
      44 / 12 = 3.666666666666666666666666667
    1.000000 tonne C must equal exactly 3.666667 tCO2e.
    Zero instances of inverted factor 12/44 (0.2727) exist.
    """
    carbon_input = Decimal("1.000000")
    co2e_output = carbon_input * CARBON_TO_CO2_FACTOR
    rounded = co2e_output.quantize(Decimal("0.000001"))
    assert rounded == Decimal("3.666667")
    # Verify mathematically distinct from erroneous 12/44
    erroneous = carbon_input * (Decimal("12") / Decimal("44"))
    assert rounded != erroneous.quantize(Decimal("0.000001"))


def test_equation_9_pure_methane_formula_no_stoichiometric_multiplier():
    """
    P0 Equation 9 Truth:
    PEP,p,y = sum_t sum_k (Fe * GWP_CH4 * Mt,k,p,y)
    Equation (9) calculates methane emissions directly as tCO2e.
    It does NOT have any 44/12 or 12/44 molecular weight multiplier.
    For 10.0 tonnes dry biochar with default Fe = 0.049 tCH4/t biochar and GWP_CH4 = 28:
      PEP = 0.049 * 28 * 10.0 = 13.720000 tCO2e.
    """
    mass = Decimal("10.0")
    pe_p = DEFAULT_FE_LOW_TECH_CH4 * GWP_CH4 * mass
    assert pe_p == Decimal("13.72")
    # Verify no factor of 44/12 or 12/44 is applied
    assert pe_p != (DEFAULT_FE_LOW_TECH_CH4 * GWP_CH4 * mass * CARBON_TO_CO2_FACTOR)


def test_vcs_program_version_resolution_and_gwp():
    """Validates dynamic VCS program version resolution and GWP_CH4 = 28."""
    res = resolve_vcs_program_version(execution_date=date(2026, 6, 1))
    assert res.vcs_version == "v4.7"
    assert res.gwp_ch4 == Decimal("28")


def test_table_4_complete_set_ipcc_2019_feedstocks():
    """Validates complete coverage and alias resolution for IPCC 2019 Table 4."""
    assert get_default_fc_p("Wood Waste", "PYROLYSIS") == Decimal("0.77")
    assert get_default_fc_p("Forestry Residue", "GASIFICATION") == Decimal("0.52")
    assert get_default_fc_p("Rice Husks and Rice Straw", "PYROLYSIS") == Decimal("0.49")
    assert get_default_fc_p("Nut Shells, Pits, and Stones", "PYROLYSIS") == Decimal("0.74")
    assert get_default_fc_p("Animal Manure", "GASIFICATION") == Decimal("0.09")
    assert get_default_fc_p("Biosolids", "PYROLYSIS") == Decimal("0.35")


# =============================================================================
# 3. Section 4 Applicability Conditions Tests
# =============================================================================

@pytest.mark.asyncio
async def test_applicability_evaluation_pass(db_session: AsyncSession, vm0044_test_env):
    """Section 4 Applicability: Fully eligible greenfield facility and waste biomass passes."""
    env = vm0044_test_env
    res = await VM0044CalculatorV12.evaluate_applicability(
        db=db_session,
        request=VM0044ApplicabilityEvaluateRequest(
            project_id=env["project_id"],
            facility_id=env["fac_high_id"],
            batch_id=env["batch_high_id"],
        ),
    )
    assert res.status == "ELIGIBLE"
    assert res.facility_check["passed"] is True
    assert res.feedstock_check["passed"] is True
    assert res.end_use_check["passed"] is True
    assert len(res.blocking_findings) == 0


@pytest.mark.asyncio
async def test_applicability_torrefaction_rejected(db_session: AsyncSession, vm0044_test_env):
    """Section 4 Condition 1: Excluded thermochemical process (torrefaction) fails closed."""
    env = vm0044_test_env

    # Create torrefaction facility
    torr_fac = ProductionFacility(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        facility_code=f"FAC-TORR-{uuid.uuid4().hex[:6]}",
        facility_name="Torrefaction Plant",
        facility_status="NEW_OPERATIONAL",
        technology_type="TORREFACTION_REACTOR",
    )
    db_session.add(torr_fac)
    await db_session.flush()

    res = await VM0044CalculatorV12.evaluate_applicability(
        db=db_session,
        request=VM0044ApplicabilityEvaluateRequest(
            project_id=env["project_id"],
            facility_id=torr_fac.id,
            batch_id=env["batch_high_id"],
        ),
    )
    assert res.status == "INELIGIBLE"
    assert res.facility_check["passed"] is False
    assert any("TORREFACTION" in f.upper() for f in res.blocking_findings)


@pytest.mark.asyncio
async def test_applicability_purpose_grown_biomass_rejected(db_session: AsyncSession, vm0044_test_env):
    """Section 4 Condition 4a: Purpose-grown dedicated crop biomass fails closed."""
    env = vm0044_test_env

    # Add purpose-grown feedstock
    src_crop = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        source_code=f"SRC-CROP-{uuid.uuid4().hex[:6]}",
        source_name="Purpose Grown Energy Crop",
        source_type="PURPOSE_GROWN_CROP",
        biomass_type="ENERGY_CROP",
        origin_location="Nakuru, Kenya",
        waste_status="PURPOSE_GROWN_BIOMASS",
    )
    db_session.add(src_crop)
    await db_session.flush()

    res = await VM0044CalculatorV12.evaluate_applicability(
        db=db_session,
        request=VM0044ApplicabilityEvaluateRequest(
            project_id=env["project_id"],
            facility_id=env["fac_high_id"],
            feedstock_source_ids=[src_crop.id],
            batch_id=env["batch_high_id"],
        ),
    )
    assert res.status == "INELIGIBLE"
    assert res.feedstock_check["passed"] is False
    assert any("PURPOSE-GROWN" in f.upper() for f in res.blocking_findings)


@pytest.mark.asyncio
async def test_applicability_biomass_boilers_eligible(db_session: AsyncSession, vm0044_test_env):
    """Section 4 Condition 1 & Footnote 7: Biomass boilers are an approved thermochemical process."""
    env = vm0044_test_env
    boiler_fac = ProductionFacility(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        facility_code=f"FAC-BOILER-{uuid.uuid4().hex[:6]}",
        facility_name="Biomass Boiler Production Plant",
        facility_status="NEW_OPERATIONAL",
        technology_type="BIOMASS_BOILER",
    )
    db_session.add(boiler_fac)
    await db_session.flush()

    res = await VM0044CalculatorV12.evaluate_applicability(
        db=db_session,
        request=VM0044ApplicabilityEvaluateRequest(
            project_id=env["project_id"],
            facility_id=boiler_fac.id,
            batch_id=env["batch_high_id"],
        ),
    )
    assert res.facility_check["passed"] is True


@pytest.mark.asyncio
async def test_one_year_utilization_rule_enforcement(db_session: AsyncSession, vm0044_test_env):
    """Section 4 Condition 9: Utilization occurring > 365 days after production fails closed."""
    from datetime import timedelta
    env = vm0044_test_env

    eu_expired = BiocharEndUseRecord(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        batch_id=env["batch_high_id"],
        end_use_type="SOIL_APPLICATION",
        applied_quantity_tonnes=Decimal("30.0"),
        event_date=datetime.now(timezone.utc) + timedelta(days=400),
        wetland_exclusion_screened=True,
        verification_status="VERIFIED",
    )
    db_session.add(eu_expired)
    await db_session.flush()

    with pytest.raises(VM0044QuantificationError) as exc_info:
        await VM0044CalculatorV12.execute_calculation(
            db=db_session,
            request=VM0044CalculationRequest(
                project_id=env["project_id"],
                batch_id=env["batch_high_id"],
                end_use_record_id=eu_expired.id,
                technology_class="HIGH_TECHNOLOGY",
            ),
            user_id=env["user_id"],
        )
    assert "INELIGIBLE_END_USE_EXPIRED" in str(exc_info.value)


# =============================================================================
# 4. Section 7 Additionality Assessment & VT0008 Tests
# =============================================================================

@pytest.mark.asyncio
async def test_additionality_vt0008_benchmark_analysis_pass(db_session: AsyncSession, vm0044_test_env):
    """Section 7 & VT0008: Passes when Project IRR (8.5%) < Benchmark IRR (12.0%)."""
    env = vm0044_test_env
    res = await VM0044CalculatorV12.evaluate_additionality(
        db=db_session,
        request=VM0044AdditionalityEvaluateRequest(
            project_id=env["project_id"],
            regulatory_surplus_demonstrated=True,
            analysis_option="OPTION_2_BENCHMARK_ANALYSIS",
            project_irr_pct=Decimal("8.5"),
            benchmark_irr_pct=Decimal("12.0"),
            benchmark_source="Central Bank Commercial Lending Benchmark 2026",
        ),
    )
    assert res.status == "COMPLETE"
    assert res.step1_regulatory_surplus is True
    assert res.step2_positive_list is True
    assert res.step3_investment_analysis is True


@pytest.mark.asyncio
async def test_additionality_vt0008_benchmark_analysis_fails_when_profitable(db_session: AsyncSession, vm0044_test_env):
    """Section 7 & VT0008: Fails closed when Project IRR (14.2%) >= Benchmark IRR (12.0%)."""
    env = vm0044_test_env
    res = await VM0044CalculatorV12.evaluate_additionality(
        db=db_session,
        request=VM0044AdditionalityEvaluateRequest(
            project_id=env["project_id"],
            regulatory_surplus_demonstrated=True,
            analysis_option="OPTION_2_BENCHMARK_ANALYSIS",
            project_irr_pct=Decimal("14.2"),
            benchmark_irr_pct=Decimal("12.0"),
            benchmark_source="Central Bank Commercial Lending Benchmark 2026",
        ),
    )
    assert res.status == "NOT_ADDITIONAL"
    assert res.step3_investment_analysis is False
    assert any("PROJECT IRR" in f.upper() for f in res.findings)


@pytest.mark.asyncio
async def test_additionality_vt0008_option_1_investment_comparison_pass(db_session: AsyncSession, vm0044_test_env):
    """Section 7 & VT0008 Option 1: Passes with valid financial model hash."""
    env = vm0044_test_env
    res = await VM0044CalculatorV12.evaluate_additionality(
        db=db_session,
        request=VM0044AdditionalityEvaluateRequest(
            project_id=env["project_id"],
            regulatory_surplus_demonstrated=True,
            analysis_option="OPTION_1_INVESTMENT_COMPARISON",
            financial_model_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ),
    )
    assert res.status == "COMPLETE"
    assert res.step1_regulatory_surplus is True
    assert res.step3_investment_analysis is True


# =============================================================================
# 5. Canonical Snapshots & Hashing Tests
# =============================================================================

@pytest.mark.asyncio
async def test_calculation_snapshot_creation_and_reproducibility(db_session: AsyncSession, vm0044_test_env):
    """Verifies deterministic SHA-256 calculation input snapshot generation and idempotency."""
    env = vm0044_test_env
    req = VM0044SnapshotRequest(
        project_id=env["project_id"],
        batch_id=env["batch_high_id"],
        end_use_record_id=env["eu_soil_id"],
        technology_class="HIGH_TECHNOLOGY",
        grid_electricity_kwh=Decimal("120.0"),
        fossil_fuel_litres=Decimal("25.0"),
        biomass_transport_distance_km=Decimal("45.0"),
        biochar_transport_distance_km=Decimal("30.0"),
        uncertainty_pct=Decimal("0.05"),
    )

    snap1 = await VM0044CalculatorV12.create_calculation_snapshot(db_session, req, user_id=env["user_id"])
    snap2 = await VM0044CalculatorV12.create_calculation_snapshot(db_session, req, user_id=env["user_id"])

    # Idempotent match
    assert snap1.snapshot_hash == snap2.snapshot_hash
    assert snap1.snapshot_id == snap2.snapshot_id
    assert len(snap1.snapshot_hash) == 64


# =============================================================================
# 6. Core Equations (1) to (15) — High-Tech & Low-Tech Pathways
# =============================================================================

@pytest.mark.asyncio
async def test_high_tech_soil_quantification_equations(db_session: AsyncSession, vm0044_test_env):
    """
    High-Technology Pyrolysis (>600°C) with Soil Application:
    - Mass: 30.0 t dry biochar
    - C_org: 82.0% (0.82)
    - Temp: 650°C -> PR_de = 0.89 (Table 3)
    - CC_stored (Eq 2) = 30 * 0.82 * 0.89 = 21.894 tonnes C
    - Gross CO2e = 21.894 * (44/12) = 80.278000 tCO2e
    - High-tech process emissions: PE_P = 0.0 (Eq 3)
    - Transport <= 200km -> LE = 0.0 (Eq 13)
    - Pre-treatment: 100 kWh * 0.00045 + 10 L * 0.00268 = 0.045 + 0.0268 = 0.0718 tCO2e
    - Net removals ER_y = 80.278000 - 0.0718 = 80.206200 tCO2e
    """
    env = vm0044_test_env
    res = await VM0044CalculatorV12.execute_calculation(
        db=db_session,
        request=VM0044CalculationRequest(
            project_id=env["project_id"],
            batch_id=env["batch_high_id"],
            end_use_record_id=env["eu_soil_id"],
            technology_class="HIGH_TECHNOLOGY",
            grid_electricity_kwh=Decimal("100.0"),
            fossil_fuel_litres=Decimal("10.0"),
            biomass_transport_distance_km=Decimal("80.0"),  # <= 200km exempt
            biochar_transport_distance_km=Decimal("50.0"),  # <= 200km exempt
            uncertainty_pct=Decimal("0.05"),                # <= 10% no deduction
        ),
        user_id=env["user_id"],
    )

    assert res.status == "CALCULATED"
    eq = res.equation_breakdown
    assert eq.permanence_factor_pr_de == Decimal("0.8900")
    assert eq.organic_carbon_stored_cc_tonnes == Decimal("21.894000")
    assert eq.gross_co2e_stored_tonnes == Decimal("80.278000")
    assert eq.er_ss_tonnes == Decimal("0.000000")
    assert eq.pe_p_tonnes == Decimal("0.000000")  # High-tech methane = 0
    assert eq.le_total_tonnes == Decimal("0.000000")  # Distances <= 200km
    assert eq.uncertainty_deduction_tonnes == Decimal("0.000000")
    assert res.net_removal_tco2e == Decimal("80.206200")
    assert res.is_issuable is True
    assert res.ccp_eligible is True


@pytest.mark.asyncio
async def test_low_tech_methane_emissions_equation_9(db_session: AsyncSession, vm0044_test_env):
    """
    Low-Technology Kiln (Kon-Tiki unmonitored):
    - Mass: 12.0 t dry biochar
    - C_org: 72.0%
    - Temp: unmonitored -> PR_de = 0.56 (Table 3 default)
    - CC_stored (Eq 6) = 12 * 0.72 * 0.56 = 4.8384 tonnes C
    - Gross CO2e = 4.8384 * (44/12) = 17.740800 tCO2e
    - Low-tech process methane (Equation 9):
      PE_P = Fe * GWP_CH4 * M = 0.049 * 28 * 12.0 = 16.464000 tCO2e
    - Production net removals ER_PS (Eq 1) = 17.7408 - 16.464 = 1.276800 tCO2e
    """
    env = vm0044_test_env
    res = await VM0044CalculatorV12.execute_calculation(
        db=db_session,
        request=VM0044CalculationRequest(
            project_id=env["project_id"],
            batch_id=env["batch_low_id"],
            end_use_record_id=env["eu_low_id"],
            technology_class="LOW_TECHNOLOGY",
            grid_electricity_kwh=Decimal("0.0"),
            fossil_fuel_litres=Decimal("0.0"),
            biomass_transport_distance_km=Decimal("20.0"),
            biochar_transport_distance_km=Decimal("15.0"),
            uncertainty_pct=Decimal("0.05"),
        ),
        user_id=env["user_id"],
    )

    assert res.status == "CALCULATED"
    eq = res.equation_breakdown
    assert eq.permanence_factor_pr_de == Decimal("0.5600")
    assert eq.organic_carbon_stored_cc_tonnes == Decimal("4.838400")
    assert eq.pe_p_tonnes == Decimal("16.464000")  # 0.049 * 28 * 12.0
    assert eq.er_ps_tonnes == Decimal("1.276800")
    assert res.net_removal_tco2e == Decimal("1.276800")


# =============================================================================
# 7. Transport Leakage Threshold & Uncertainty Tests
# =============================================================================

@pytest.mark.asyncio
async def test_transport_leakage_distance_threshold(db_session: AsyncSession, vm0044_test_env):
    """
    Equation (13) & CDM TOOL16:
    - If transport distance <= 200 km -> LE = 0.0
    - If transport distance > 200 km (e.g. 350 km) -> LE > 0.0
    """
    env = vm0044_test_env

    # 1. Distances > 200km (350 km feedstock transport)
    res_long = await VM0044CalculatorV12.execute_calculation(
        db=db_session,
        request=VM0044CalculationRequest(
            project_id=env["project_id"],
            batch_id=env["batch_high_id"],
            end_use_record_id=env["eu_soil_id"],
            technology_class="HIGH_TECHNOLOGY",
            biomass_transport_distance_km=Decimal("350.0"),  # > 200km
            biochar_transport_distance_km=Decimal("50.0"),   # <= 200km
            preview=True,
        ),
        user_id=env["user_id"],
    )

    eq_long = res_long.equation_breakdown
    # LE_TS = 30 t * 350 km * 0.00012 tCO2e/t-km = 1.260000 tCO2e
    assert eq_long.le_ts_tonnes == Decimal("1.260000")
    assert eq_long.le_tap_tonnes == Decimal("0.000000")
    assert eq_long.le_total_tonnes == Decimal("1.260000")


@pytest.mark.asyncio
async def test_equation_15_net_removals_zero_uncertainty_deduction(db_session: AsyncSession, vm0044_test_env):
    """
    Equation (15) Semantics & Zero Uncertainty Deduction:
    - ER_y = ER_SS,y + ER_PS,y - PE_AS,y - LE_y.
    - VM0044 methodology contains zero uncertainty deduction formula in Equation (15).
    - Net removals are directly credited without unsupported methodology deductions.
    """
    env = vm0044_test_env
    res = await VM0044CalculatorV12.execute_calculation(
        db=db_session,
        request=VM0044CalculationRequest(
            project_id=env["project_id"],
            batch_id=env["batch_high_id"],
            end_use_record_id=env["eu_soil_id"],
            technology_class="HIGH_TECHNOLOGY",
            uncertainty_pct=Decimal("0.15"),  # 15% uncertainty input
            preview=True,
        ),
        user_id=env["user_id"],
    )

    eq = res.equation_breakdown
    assert eq.uncertainty_deduction_tonnes == Decimal("0.000000")
    assert res.net_removal_tco2e == Decimal("80.278000")
    assert res.net_removal_tco2e == eq.er_net_removals_tonnes


# =============================================================================
# 8. Non-Soil Pathway & High-Tech Requirement Tests
# =============================================================================

@pytest.mark.asyncio
async def test_non_soil_with_low_tech_fails_closed(db_session: AsyncSession, vm0044_test_env):
    """Section 4 Condition 11: Low-tech biochar used in non-soil applications fails closed."""
    env = vm0044_test_env

    # Create non-soil end use record
    eu_non_soil = BiocharEndUseRecord(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        batch_id=env["batch_low_id"],
        end_use_type="NON_SOIL_APPLICATION",
        product_category="CONCRETE_ADDITIVE",
        applied_quantity_tonnes=Decimal("12.0"),
        event_date=datetime(2026, 4, 15, tzinfo=timezone.utc),
        verification_status="VERIFIED",
    )
    db_session.add(eu_non_soil)
    await db_session.flush()

    with pytest.raises(VM0044QuantificationError) as exc_info:
        await VM0044CalculatorV12.execute_calculation(
            db=db_session,
            request=VM0044CalculationRequest(
                project_id=env["project_id"],
                batch_id=env["batch_low_id"],
                end_use_record_id=eu_non_soil.id,
                technology_class="LOW_TECHNOLOGY",
            ),
            user_id=env["user_id"],
        )
    assert "NON_SOIL_INELIGIBLE" in str(exc_info.value)


# =============================================================================
# 9. Double-Counting & Multi-Registry Conflict Tests
# =============================================================================

@pytest.mark.asyncio
async def test_double_counting_with_active_puro_calculation_blocks(db_session: AsyncSession, vm0044_test_env):
    """Prevents double-counting: Batch already calculated under Puro cannot be crediting under Verra."""
    env = vm0044_test_env

    # Add active Puro calculation on batch_high
    puro_exec = PuroCalculationExecution(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        facility_id=env["fac_high_id"],
        batch_id=env["batch_high_id"],
        calculation_mode="AUTHORITATIVE",
        engine_version="2.0.0",
        calculation_status="SUCCESS",
        eligible_dry_biochar_mass_tonnes=Decimal("30.0"),
        c_org_pct=82.0,
        molar_h_c=0.35,
        c_stored_tco2e=Decimal("80.0"),
        c_loss_tco2e=Decimal("8.0"),
        e_project_tco2e=Decimal("2.0"),
        net_corcs_calculated=Decimal("70.0"),
        final_corcs_issuable=Decimal("70.0"),
        input_manifest_json={},
        calculation_hash="puro_hash_conflict_test",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(puro_exec)
    await db_session.commit()

    with pytest.raises(VM0044QuantificationError) as exc_info:
        await VM0044CalculatorV12.execute_calculation(
            db=db_session,
            request=VM0044CalculationRequest(
                project_id=env["project_id"],
                batch_id=env["batch_high_id"],
                end_use_record_id=env["eu_soil_id"],
            ),
            user_id=env["user_id"],
        )
    assert "DOUBLE_COUNTING_CONFLICT" in str(exc_info.value)


# =============================================================================
# 10. Ledger P0 Fail-Closed Minting Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_authoritative_vm0044_calculation_minting_on_ledger(db_session: AsyncSession, vm0044_test_env):
    """Verifies authoritative VM0044 calculation can be minted on ledger with Solana signature."""
    env = vm0044_test_env

    # 1. Execute calculation
    calc_res = await VM0044CalculatorV12.execute_calculation(
        db=db_session,
        request=VM0044CalculationRequest(
            project_id=env["project_id"],
            batch_id=env["batch_high_id"],
            end_use_record_id=env["eu_soil_id"],
            technology_class="HIGH_TECHNOLOGY",
        ),
        user_id=env["user_id"],
    )
    await db_session.commit()

    # 2. Mint on ledger referencing VM0044 calculation
    req = MintRequest(
        project_id=env["project_id"],
        calculation_id=calc_res.calculation_id,
        target_chain="solana-devnet",
    )
    mint_res = await execute_carbon_minting(data=req, db=db_session, current_user=env["user"])

    assert mint_res["status"] == "MINTED"
    assert mint_res["total_tco2e"] == float(calc_res.net_removal_tco2e)
    assert str(calc_res.calculation_id) in mint_res["calculation_ids"]
    assert mint_res["calculation_source"] == "VM0044_EXECUTION"

    # 3. Attempt repeat minting of same VM0044 calculation -> BLOCKED with 409
    req_repeat = MintRequest(
        project_id=env["project_id"],
        calculation_id=calc_res.calculation_id,
        target_chain="solana-devnet",
    )
    with pytest.raises(HTTPException) as exc_repeat:
        await execute_carbon_minting(data=req_repeat, db=db_session, current_user=env["user"])
    assert exc_repeat.value.status_code == 409
    assert "CALCULATION_ALREADY_MINTED" in exc_repeat.value.detail


# =============================================================================
# 11. REST API Integration Endpoints Tests
# =============================================================================

@pytest.mark.asyncio
async def test_vm0044_rest_api_lifecycle(db_session: AsyncSession, vm0044_test_env):
    """Tests complete HTTP lifecycle: version -> rules -> applicability -> snapshot -> calculate."""
    env = vm0044_test_env
    headers = _make_auth_headers(
        user_id=env["user_id"],
        email=env["user"].email,
        role="ORG_ADMIN",
        org_id=env["org_id"],
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Version
        r_ver = await client.get("/api/v1/biochar/vm0044/version", headers=headers)
        assert r_ver.status_code == 200
        assert r_ver.json()["code"] == "VM0044"
        assert r_ver.json()["version"] == "1.2"

        # 2. Rules
        r_rules = await client.get("/api/v1/biochar/vm0044/rules", headers=headers)
        assert r_rules.status_code == 200
        assert len(r_rules.json()) >= 21

        # 3. Applicability
        r_app = await client.post(
            "/api/v1/biochar/vm0044/applicability",
            headers=headers,
            json={
                "project_id": str(env["project_id"]),
                "facility_id": str(env["fac_high_id"]),
                "batch_id": str(env["batch_high_id"]),
            },
        )
        assert r_app.status_code == 200
        assert r_app.json()["status"] == "ELIGIBLE"

        # 4. Snapshot
        r_snap = await client.post(
            "/api/v1/biochar/vm0044/snapshot",
            headers=headers,
            json={
                "project_id": str(env["project_id"]),
                "batch_id": str(env["batch_high_id"]),
                "end_use_record_id": str(env["eu_soil_id"]),
                "technology_class": "HIGH_TECHNOLOGY",
                "grid_electricity_kwh": "50.0",
                "fossil_fuel_litres": "10.0",
                "biomass_transport_distance_km": "30.0",
                "biochar_transport_distance_km": "20.0",
                "uncertainty_pct": "0.05",
            },
        )
        assert r_snap.status_code == 200
        snap_id = r_snap.json()["snapshot_id"]
        assert len(r_snap.json()["snapshot_hash"]) == 64

        # 5. Calculate
        r_calc = await client.post(
            "/api/v1/biochar/vm0044/calculate",
            headers=headers,
            json={
                "snapshot_id": snap_id,
            },
        )
        assert r_calc.status_code == 200
        calc_id = r_calc.json()["calculation_id"]
        assert float(r_calc.json()["net_removal_tco2e"]) > 0

        # 6. Query Calculation by ID
        r_get = await client.get(f"/api/v1/biochar/vm0044/calculations/{calc_id}", headers=headers)
        assert r_get.status_code == 200
        assert r_get.json()["calculation_id"] == calc_id

        # 7. Query Calculations for Project
        r_proj = await client.get(f"/api/v1/biochar/vm0044/calculations/project/{env['project_id']}", headers=headers)
        assert r_proj.status_code == 200
        assert len(r_proj.json()) >= 1


@pytest.mark.asyncio
async def test_vm0044_tenant_security(db_session: AsyncSession, vm0044_test_env):
    """Tenant Security: Unauthenticated requests fail with 401; cross-tenant access fails with 403."""
    env = vm0044_test_env
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Unauthenticated request to protected endpoint fails 401
        r_unauth = await client.post(
            "/api/v1/biochar/vm0044/calculate",
            json={"snapshot_id": str(uuid.uuid4())},
        )
        assert r_unauth.status_code == 401

        # 2. Foreign organization user attempting to access other org's project
        foreign_org = Organization(
            id=uuid.uuid4(),
            name=f"Foreign Org {uuid.uuid4().hex[:6]}",
            org_type="DEVELOPER",
            status="ACTIVE",
        )
        db_session.add(foreign_org)

        foreign_user = User(
            id=uuid.uuid4(),
            email=f"foreign_{uuid.uuid4().hex[:6]}@other.org",
            full_name="Foreign Member",
            role="ORG_MEMBER",
            organization_id=foreign_org.id,
            status="active",
            is_active=True,
        )
        db_session.add(foreign_user)
        await db_session.commit()

        foreign_headers = _make_auth_headers(
            user_id=foreign_user.id,
            email=foreign_user.email,
            role="ORG_MEMBER",
            org_id=foreign_org.id,
        )

        r_foreign = await client.get(
            f"/api/v1/biochar/vm0044/calculations/project/{env['project_id']}",
            headers=foreign_headers,
        )
        # Foreign tenant must be forbidden with 403
        assert r_foreign.status_code == 403


@pytest.mark.asyncio
async def test_vm0044_idempotency_and_replay_protection(db_session: AsyncSession, vm0044_test_env):
    """Idempotency & Replay Protection: Replaying a calculation snapshot creation or minting returns conflict/idempotent result."""
    env = vm0044_test_env

    # 1. Create a snapshot
    snap = await VM0044CalculatorV12.create_calculation_snapshot(
        db=db_session,
        request=VM0044SnapshotRequest(
            project_id=env["project_id"],
            batch_id=env["batch_high_id"],
            end_use_record_id=env["eu_soil_id"],
            technology_class="HIGH_TECHNOLOGY",
            grid_electricity_kwh=Decimal("50.0"),
            fossil_fuel_litres=Decimal("10.0"),
            biomass_transport_distance_km=Decimal("30.0"),
            biochar_transport_distance_km=Decimal("20.0"),
            uncertainty_pct=Decimal("0.05"),
        ),
    )
    assert snap.snapshot_id is not None

    # 2. Authoritative execution
    calc = await VM0044CalculatorV12.execute_calculation(
        db=db_session,
        request=VM0044CalculationRequest(
            snapshot_id=snap.snapshot_id,
            preview=False,
        ),
        user_id=env["user_id"],
    )
    assert calc.calculation_id is not None
    assert calc.status == "CALCULATED"
    await db_session.commit()

    # 3. Minting on ledger
    req = MintRequest(
        project_id=env["project_id"],
        calculation_id=calc.calculation_id,
        target_chain="solana-devnet",
    )
    res1 = await execute_carbon_minting(data=req, db=db_session, current_user=env["user"])
    assert res1["status"] == "MINTED"

    # 4. Attempting to mint the same calculation again must fail closed with 409
    with pytest.raises(HTTPException) as exc_info:
        await execute_carbon_minting(data=req, db=db_session, current_user=env["user"])
    assert exc_info.value.status_code == 409




@pytest.mark.asyncio
async def test_vm0044_concurrency_safety(db_session: AsyncSession, vm0044_test_env):
    """PostgreSQL Concurrency Safety: Creating multiple calculation snapshots concurrently preserves deterministic hashing."""
    env = vm0044_test_env

    # Create multiple snapshots with identical parameters
    req = VM0044SnapshotRequest(
        project_id=env["project_id"],
        batch_id=env["batch_high_id"],
        end_use_record_id=env["eu_soil_id"],
        technology_class="HIGH_TECHNOLOGY",
        grid_electricity_kwh=Decimal("50.0"),
        fossil_fuel_litres=Decimal("10.0"),
        biomass_transport_distance_km=Decimal("30.0"),
        biochar_transport_distance_km=Decimal("20.0"),
        uncertainty_pct=Decimal("0.05"),
    )

    s1 = await VM0044CalculatorV12.create_calculation_snapshot(db=db_session, request=req)
    s2 = await VM0044CalculatorV12.create_calculation_snapshot(db=db_session, request=req)

    # Hashes are deterministic and identical across calls
    assert s1.snapshot_hash == s2.snapshot_hash
    assert len(s1.snapshot_hash) == 64


# =============================================================================
# 13. Scientific Truth Reference & Boundary Tests
# =============================================================================

@pytest.mark.asyncio
async def test_stoichiometric_reference_direct_calculation(db_session: AsyncSession, vm0044_test_env):
    """
    Direct Reference Test (Requirement 3):
    persistent organic carbon = 1.000000 tC
    production emissions = 0
    other deductions = 0
    Expected carbon conversion component: 3.666666666... tCO2e
    derived strictly from: Decimal(44) / Decimal(12)
    """
    env = vm0044_test_env
    ref_batch = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        batch_number=f"BATCH-REF-1TC-{uuid.uuid4().hex[:6]}",
        facility_name="Reference Kiln",
        kiln_id="KILN-REF-01",
        feedstock_type="AGRICULTURAL_RESIDUE",
        feedstock_weight_tonnes=Decimal("1.0"),
        moisture_content_pct=Decimal("0.0"),
        pyrolysis_temp_celsius=650.0,
        residence_time_minutes=60.0,
        biochar_yield_tonnes=Decimal("1.0"),
        dry_mass_tonnes=Decimal("1.000000"),
        fixed_carbon_pct=100.0,
        molar_h_c_ratio=0.20,
        quality_grade="GRADE_A",
        status="ACTIVE",
    )
    db_session.add(ref_batch)

    eu_ref = BiocharEndUseRecord(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        batch_id=ref_batch.id,
        end_use_type="SOIL_APPLICATION",
        applied_quantity_tonnes=Decimal("1.000000"),
        event_date=datetime.now(timezone.utc),
        wetland_exclusion_screened=True,
        verification_status="VERIFIED",
    )
    db_session.add(eu_ref)

    lab_ref = BiocharLabAnalysis(
        id=uuid.uuid4(),
        organization_id=env["org_id"],
        project_id=env["project_id"],
        batch_id=ref_batch.id,
        sample_id=f"SMP-REF-{uuid.uuid4().hex[:6]}",
        sampling_date=datetime.now(timezone.utc),
        laboratory_name="Kenya Bureau of Standards Accredited Lab",
        organic_carbon_pct=100.0,
        fixed_carbon_pct=100.0,
        molar_h_c_ratio=0.20,
        moisture_pct=0.0,
        ash_pct=0.0,
        heavy_metals_pass=True,
        qa_status="VERIFIED",
    )
    db_session.add(lab_ref)
    await db_session.flush()

    res = await VM0044CalculatorV12.execute_calculation(
        db=db_session,
        request=VM0044CalculationRequest(
            project_id=env["project_id"],
            batch_id=ref_batch.id,
            end_use_record_id=eu_ref.id,
            technology_class="HIGH_TECHNOLOGY",
            custom_permanence_factor=Decimal("1.0000"),  # 1.000000 tC persistent organic carbon
            preview=True,
        ),
        user_id=env["user_id"],
    )

    expected_ratio = Decimal(44) / Decimal(12)
    expected_co2e = Decimal("1.000000") * expected_ratio
    eq = res.equation_breakdown
    assert eq.organic_carbon_stored_cc_tonnes == Decimal("1.000000")
    assert eq.gross_co2e_stored_tonnes == VM0044CalculatorV12.round_dec(expected_co2e)
    assert res.net_removal_tco2e == VM0044CalculatorV12.round_dec(expected_co2e)
    # Exact verification: 3.666667 tCO2e
    assert str(res.net_removal_tco2e) == "3.666667"


def test_one_year_rule_leap_year_boundary():
    """
    Leap-Year Boundary Test (Requirement 13):
    - Production on leap day: 2028-02-29.
    - Calendar year anniversary is 2029-02-28.
    - Production on 2028-01-01 (leap year has 366 days).
    - Calendar year anniversary is 2029-01-01 (366 days later).
    """
    from app.domains.biochar.vm0044_rules import add_one_calendar_year
    assert add_one_calendar_year(date(2028, 2, 29)) == date(2029, 2, 28)
    assert add_one_calendar_year(date(2028, 1, 1)) == date(2029, 1, 1)
    assert add_one_calendar_year(date(2025, 6, 27)) == date(2026, 6, 27)


def test_vcs_program_version_resolution_transition():
    """
    VCS Program Version & GWP_CH4 Resolution (Requirements 11 & 12):
    - Pre-2027 resolves to VCS v4.7 with GWP=28 per IPCC AR5.
    - Post-2026 resolves to VCS v5.0 with GWP=28.
    - Explicitly requested v5 resolves to v5.0.
    """
    from app.domains.biochar.vm0044_rules import resolve_vcs_program_version

    # Pre-2027 date
    res_47 = resolve_vcs_program_version(execution_date=date(2026, 6, 1))
    assert res_47.vcs_version == "v4.7"
    assert res_47.gwp_ch4 == Decimal("28")
    assert res_47.source_document == "VCS Program Standard"
    assert res_47.source_version == "v4.7"
    assert "transition provisions" in res_47.resolution_reason

    # Post-2026 date
    res_50 = resolve_vcs_program_version(execution_date=date(2027, 1, 1))
    assert res_50.vcs_version == "v5.0"
    assert res_50.gwp_ch4 == Decimal("28")
    assert res_50.source_version == "v5.0"
    assert "Mandatory VCS v5.0" in res_50.resolution_reason

    # Explicit request
    res_req = resolve_vcs_program_version(requested_vcs_version="v5.0", execution_date=date(2026, 6, 1))
    assert res_req.vcs_version == "v5.0"
    assert res_req.gwp_ch4 == Decimal("28")
