"""
=============================================================================
VeriField Nexus — Puro Biochar 2026 Standards Closure Test Suite
=============================================================================
Methodology: Puro.earth Biochar Edition 2025 Version 2
General Rules: Version 4.3 (March 2026) / Version 4.4 (May 2026)
Biomass Sourcing Criteria: Version 1.3 (September 2026) & Transition Rules

Covers Requirements A through F:
- Standard / Version Resolution
- Biomass Sourcing Criteria v1.3 Compliance & Classification
- Counterfactual Storage Assessment (Path A Negligible & Path B Material)
- Transition Engine (Crediting Period Start Date >= 2029-01-01, Renewal, Early Adoption)
- Authoritative Calculation Gating & Net CORCs Deduction
- Ledger Fail-Closed Minting & Multi-Tenant Security
=============================================================================
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.activities.schemas import ActivityCreate
from app.domains.activities.service import ActivityService
from app.domains.activities.repository import ActivityRepository
from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharLabAnalysis,
    FeedstockLot,
    FeedstockSource,
    ProductionFacility,
    ProductionRun,
)
from app.domains.biochar.puro_models import (
    PuroBiomassSourceDeclaration,
    PuroCalculationExecution,
    PuroCounterfactualStorageAssessment,
    PuroCreditingPeriod,
    PuroEndUseCategory,
    PuroEndUseRecordLink,
    PuroMethodologyVersion,
    PuroNormativeDependency,
    PuroRuleDefinition,
)
from app.domains.biochar.puro_rules import (
    OFFICIAL_PURO_BIOCHAR_METHODOLOGY_CODE,
    OFFICIAL_PURO_GENERAL_RULES_V4_3,
    OFFICIAL_PURO_GENERAL_RULES_V4_4,
    OFFICIAL_PURO_BIOMASS_SOURCING_V1_3,
    PURO_V1_3_MANDATORY_CUTOFF_DATE,
    evaluate_biomass_sourcing_applicability,
    resolve_puro_standard_configuration,
    seed_puro_biochar_normative_metadata,
)
from app.domains.biochar.services.puro_quantification import (
    PuroAuthoritativeQuantificationService,
    PuroCORCCalculator,
)
from app.domains.biochar.services.puro_sourcing import (
    PuroBiomassSourcingEngine,
    PuroCounterfactualService,
)
from fastapi import HTTPException
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.ledger.api import execute_carbon_minting, MintRequest
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app
import jwt as pyjwt
from app.core.config import settings


def _make_auth_headers(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID) -> dict:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id),
    }
    token = pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# A. Standard & Version Resolution Tests
# =============================================================================

def test_puro_edition_2025_v2_resolution():
    """1. Correct Biochar Edition 2025 v2 resolution."""
    res = resolve_puro_standard_configuration(
        methodology_code="PURO_BIOCHAR_2025_V2",
        general_rules_version="4.3",
        crediting_period_start_date=date(2029, 6, 1),
    )
    assert res["status"] == "SUCCESS"
    assert res["is_valid"] is True
    assert res["methodology_code"] == OFFICIAL_PURO_BIOCHAR_METHODOLOGY_CODE
    assert res["methodology_edition"] == "Edition 2025 v2"
    assert res["general_rules_version"] == "4.3"
    assert res["sourcing_criteria_version"] == "1.3"


def test_puro_general_rules_v4_3_and_v4_4_resolution():
    """2. General Rules 4.3 and 4.4 resolution."""
    res_43 = resolve_puro_standard_configuration(
        methodology_code="PURO_BIOCHAR_2025_V2",
        general_rules_version="4.3",
        crediting_period_start_date=date(2027, 1, 1),
    )
    assert res_43["is_valid"] is True
    assert res_43["general_rules_version"] == "4.3"

    res_44 = resolve_puro_standard_configuration(
        methodology_code="PURO_BIOCHAR_2025_V2",
        general_rules_version="4.4",
        crediting_period_start_date=date(2027, 1, 1),
    )
    assert res_44["is_valid"] is True
    assert res_44["general_rules_version"] == "4.4"


def test_puro_missing_methodology_version_fails_closed():
    """3. Missing methodology version fails closed."""
    res = resolve_puro_standard_configuration(
        methodology_code=None,
        general_rules_version="4.3",
    )
    assert res["status"] == "FAIL_CLOSED"
    assert res["is_valid"] is False
    assert res["reason_code"] == "PURO_METHODOLOGY_VERSION_MISSING"


def test_puro_unsupported_methodology_version_fails_closed():
    """4. Unsupported methodology version fails closed."""
    res = resolve_puro_standard_configuration(
        methodology_code="PURO_BIOCHAR_V99",
        general_rules_version="4.3",
    )
    assert res["status"] == "FAIL_CLOSED"
    assert res["is_valid"] is False
    assert res["reason_code"] == "PURO_UNSUPPORTED_METHODOLOGY_VERSION"


# =============================================================================
# B. Biomass Sourcing Criteria v1.3 Tests
# =============================================================================

def test_valid_eligible_biomass_source_passes():
    """5. Valid eligible biomass source passes required criteria."""
    src = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_code="SRC-PINE-01",
        source_name="Pine Residue",
        source_type="FORESTRY_RESIDUE",
        biomass_type="WOOD_CHIPS",
        origin_location="Joensuu, Finland",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="OPEN_BURNING",
    )
    decl = PuroBiomassSourceDeclaration(
        id=uuid.uuid4(),
        organization_id=src.organization_id,
        feedstock_source_id=src.id,
        source_declaration_code="DECL-PINE-01",
        declared_validity_start=date(2026, 1, 1),
        declared_validity_end=date(2028, 1, 1),
        puro_category_ref="FORESTRY_RESIDUE",
        risk_classification="LOW_RISK",
        is_active=True,
    )
    eval_res = PuroBiomassSourcingEngine.evaluate_feedstock_source(
        source=src,
        declaration=decl,
        criteria_version="1.3",
        reference_date=date(2026, 6, 1),
    )
    assert eval_res["is_eligible"] is True
    assert eval_res["status"] == "COMPLIANT"
    assert eval_res["reason_code"] == "SOURCING_CRITERIA_SATISFIED"


def test_missing_biomass_category_fails():
    """6. Missing biomass category fails."""
    src = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_code="SRC-UNKNOWN",
        source_name="Unknown Biomass",
        source_type="INVALID_TYPE",
        biomass_type="UNSPECIFIED",
        origin_location="Unknown",
    )
    decl = PuroBiomassSourceDeclaration(
        id=uuid.uuid4(),
        organization_id=src.organization_id,
        feedstock_source_id=src.id,
        source_declaration_code="DECL-UNK",
        declared_validity_start=date(2026, 1, 1),
        declared_validity_end=date(2028, 1, 1),
        puro_category_ref="INVALID_TYPE",
        is_active=True,
    )
    eval_res = PuroBiomassSourcingEngine.evaluate_feedstock_source(src, decl)
    assert eval_res["is_eligible"] is False
    assert eval_res["status"] == "NON_COMPLIANT"


def test_prohibited_biomass_category_fails_closed():
    """7. Prohibited biomass categories fail closed immediately."""
    prohibited_types = [
        "MIXED_MUNICIPAL_SOLID_WASTE",
        "TREATED_WOOD_PRESERVED",
        "CONTAMINATED_WASTE",
        "HAZARDOUS_BIOMASS",
        "PRIMARY_FOREST_DEFORESTATION",
        "PEATLAND_DRAINAGE",
    ]
    for p_type in prohibited_types:
        src = FeedstockSource(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            source_code=f"SRC-{p_type}",
            source_name=f"Prohibited {p_type}",
            source_type=p_type,
            biomass_type="WOOD",
            origin_location="Location",
        )
        decl = PuroBiomassSourceDeclaration(
            id=uuid.uuid4(),
            organization_id=src.organization_id,
            feedstock_source_id=src.id,
            source_declaration_code=f"DECL-{p_type}",
            declared_validity_start=date(2026, 1, 1),
            declared_validity_end=date(2028, 1, 1),
            puro_category_ref=p_type,
            is_active=True,
        )
        eval_res = PuroBiomassSourcingEngine.evaluate_feedstock_source(src, decl)
        assert eval_res["is_eligible"] is False
        assert eval_res["reason_code"] == "PROHIBITED_FEEDSTOCK_CATEGORY"


def test_missing_sourcing_declaration_fails():
    """8. Missing mandatory declaration fails."""
    src = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_code="SRC-NO-DECL",
        source_name="Residue",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="RICE_HUSK",
        origin_location="Delhi, India",
    )
    eval_res = PuroBiomassSourcingEngine.evaluate_feedstock_source(source=src, declaration=None)
    assert eval_res["is_eligible"] is False
    assert eval_res["status"] == "DATA_REQUIRED"
    assert eval_res["reason_code"] == "SOURCING_DECLARATION_MISSING"


def test_invalid_expired_declaration_fails():
    """9. Expired declaration fails."""
    src = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_code="SRC-EXP",
        source_name="Residue",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="BAGASSE",
        origin_location="Brazil",
    )
    decl = PuroBiomassSourceDeclaration(
        id=uuid.uuid4(),
        organization_id=src.organization_id,
        feedstock_source_id=src.id,
        source_declaration_code="DECL-EXP",
        declared_validity_start=date(2024, 1, 1),
        declared_validity_end=date(2025, 1, 1),  # Expired
        puro_category_ref="AGRICULTURAL_RESIDUE",
        is_active=True,
    )
    eval_res = PuroBiomassSourcingEngine.evaluate_feedstock_source(
        source=src,
        declaration=decl,
        reference_date=date(2026, 6, 1),
    )
    assert eval_res["is_eligible"] is False
    assert any("expired" in b.lower() for b in eval_res["blockers"])


@pytest.mark.asyncio
async def test_cross_tenant_biomass_source_blocked(db_session: AsyncSession):
    """10. Source belonging to another tenant cannot be used."""
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()

    db_session.add(Organization(id=org1_id, name=f"Tenant 1 {uuid.uuid4().hex[:6]}", org_type="SUPPLIER"))
    db_session.add(Organization(id=org2_id, name=f"Tenant 2 {uuid.uuid4().hex[:6]}", org_type="SUPPLIER"))

    proj1 = Project(id=uuid.uuid4(), organization_id=org1_id, name="Proj 1")
    fac1 = ProductionFacility(id=uuid.uuid4(), organization_id=org1_id, project_id=proj1.id, facility_code=f"FAC-{uuid.uuid4().hex[:6]}", facility_name="Fac 1")
    batch1 = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=org1_id,
        project_id=proj1.id,
        batch_number=f"BATCH-T1-{uuid.uuid4().hex[:6]}",
        facility_name="Fac 1",
        kiln_id="K-1",
        feedstock_type="WOOD",
        feedstock_weight_tonnes=Decimal("10.0"),
        moisture_content_pct=Decimal("5.0"),
        pyrolysis_temp_celsius=500.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=Decimal("3.0"),
    )

    # Lot belongs to org2!
    src2 = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=org2_id,
        source_code=f"SRC-T2-{uuid.uuid4().hex[:6]}",
        source_name="Tenant 2 Source",
        source_type="FORESTRY_RESIDUE",
        biomass_type="WOOD",
    )
    lot2 = FeedstockLot(
        id=uuid.uuid4(),
        organization_id=org2_id,
        source_id=src2.id,
        lot_number=f"LOT-T2-{uuid.uuid4().hex[:6]}",
        feedstock_type="WOOD",
        mass_received_tonnes=Decimal("10.0"),
        moisture_content_pct=Decimal("5.0"),
        dry_mass_tonnes=Decimal("9.5"),
    )
    batch1.metadata_json = {"feedstock_lot_id": str(lot2.id)}

    db_session.add_all([proj1, fac1, batch1, src2, lot2])
    await db_session.commit()

    res = await PuroBiomassSourcingEngine.evaluate_batch_sourcing_compliance(
        db=db_session,
        batch=batch1,
        organization_id=org1_id,
    )
    assert res["is_compliant"] is False
    assert any("another tenant" in b.lower() for b in res["blockers"])


# =============================================================================
# C. Biomass Counterfactual Storage Assessment Tests (v1.3 Section 3)
# =============================================================================

def test_counterfactual_path_a_negligible_storage_with_verified_evidence():
    """11. Supported negligible-storage counterfactual + valid evidence passes."""
    assessment = PuroCounterfactualStorageAssessment(
        counterfactual_path="PATH_A_NEGLIGIBLE_STORAGE",
        baseline_fate="OPEN_BURNING",
        evidence_status="VERIFIED",
        evidence_reference="DOC-REF-OPEN-BURN-AFFIDAVIT",
        counterfactual_carbon_stored_tco2e=Decimal("0.0"),
    )
    eval_res = PuroCounterfactualService.evaluate_counterfactual(assessment)
    assert eval_res["is_compliant"] is True
    assert eval_res["status"] == "COMPLIANT"
    assert eval_res["deductible_counterfactual_tco2e"] == Decimal("0.0")
    assert eval_res["reason_code"] == "PURO_COUNTERFACTUAL_NEGLIGIBLE_VERIFIED"


def test_counterfactual_path_a_missing_evidence_fails_closed():
    """12. Negligible-storage assertion without verified evidence fails closed."""
    assessment = PuroCounterfactualStorageAssessment(
        counterfactual_path="PATH_A_NEGLIGIBLE_STORAGE",
        baseline_fate="OPEN_BURNING",
        evidence_status="PENDING",  # Not verified!
        counterfactual_carbon_stored_tco2e=Decimal("0.0"),
    )
    eval_res = PuroCounterfactualService.evaluate_counterfactual(assessment)
    assert eval_res["is_compliant"] is False
    assert eval_res["status"] == "EVIDENCE_REQUIRED"
    assert eval_res["reason_code"] == "PURO_COUNTERFACTUAL_EVIDENCE_REQUIRED"


def test_counterfactual_path_a_ineligible_fate_fails():
    """13. Attempting Path A with an ineligible baseline fate fails."""
    assessment = PuroCounterfactualStorageAssessment(
        counterfactual_path="PATH_A_NEGLIGIBLE_STORAGE",
        baseline_fate="LONG_TERM_WOOD_PRODUCTS",  # Material storage!
        evidence_status="VERIFIED",
    )
    eval_res = PuroCounterfactualService.evaluate_counterfactual(assessment)
    assert eval_res["is_compliant"] is False
    assert eval_res["reason_code"] == "PURO_INVALID_NEGLIGIBLE_FATE"


def test_counterfactual_path_b_material_storage_with_quantified_deduction():
    """14. Material counterfactual with quantified deduction passes."""
    assessment = PuroCounterfactualStorageAssessment(
        counterfactual_path="PATH_B_MATERIAL_STORAGE",
        baseline_fate="LONG_TERM_WOOD_PRODUCTS",
        evidence_status="VERIFIED",
        counterfactual_carbon_stored_tco2e=Decimal("12.450000"),
    )
    eval_res = PuroCounterfactualService.evaluate_counterfactual(assessment)
    assert eval_res["is_compliant"] is True
    assert eval_res["status"] == "COMPLIANT"
    assert eval_res["deductible_counterfactual_tco2e"] == Decimal("12.450000")
    assert eval_res["reason_code"] == "PURO_COUNTERFACTUAL_MATERIAL_QUANTIFIED"


def test_counterfactual_path_b_missing_or_zero_quantity_fails_closed():
    """15. Material counterfactual requiring quantification cannot pass with missing or zero quantity."""
    assessment = PuroCounterfactualStorageAssessment(
        counterfactual_path="PATH_B_MATERIAL_STORAGE",
        baseline_fate="DEEP_BURIAL_ANAEROBIC",
        evidence_status="VERIFIED",
        counterfactual_carbon_stored_tco2e=Decimal("0.0"),  # Zero!
    )
    eval_res = PuroCounterfactualService.evaluate_counterfactual(assessment)
    assert eval_res["is_compliant"] is False
    assert eval_res["status"] == "DEDUCTION_REQUIRED"
    assert eval_res["reason_code"] == "PURO_COUNTERFACTUAL_DEDUCTION_REQUIRED"


def test_counterfactual_deduction_subtracted_from_net_corcs():
    """16. Required deduction is propagated correctly into authoritative output."""
    c_stored = Decimal("100.0")
    c_baseline = Decimal("5.0")
    c_loss = Decimal("15.0")
    e_project = Decimal("10.0")
    e_leakage = Decimal("2.0")
    c_counterfactual = Decimal("12.0")

    # Net CORCs = max(0, 100 - 5 - 15 - 10 - 2 - 12) = 56.0
    net = PuroCORCCalculator.calculate_net_corcs(
        c_stored=c_stored,
        c_baseline=c_baseline,
        c_loss=c_loss,
        e_project=e_project,
        e_leakage=e_leakage,
        c_counterfactual=c_counterfactual,
    )
    assert net == Decimal("56.0")

    # If counterfactual is zero: Net CORCs = 68.0
    net_zero = PuroCORCCalculator.calculate_net_corcs(
        c_stored=c_stored,
        c_baseline=c_baseline,
        c_loss=c_loss,
        e_project=e_project,
        e_leakage=e_leakage,
        c_counterfactual=Decimal("0.0"),
    )
    assert net_zero == Decimal("68.0")
    assert net_zero - net == c_counterfactual


def test_missing_counterfactual_assessment_fails_closed():
    """17. Missing counterfactual assessment fails closed."""
    eval_res = PuroCounterfactualService.evaluate_counterfactual(assessment=None)
    assert eval_res["is_compliant"] is False
    assert eval_res["status"] == "DATA_REQUIRED"
    assert eval_res["reason_code"] == "PURO_COUNTERFACTUAL_ASSESSMENT_REQUIRED"


# =============================================================================
# D. Transition Engine Tests
# =============================================================================

def test_transition_post_2029_mandatory_v1_3():
    """18. Facility crediting period start date >= 2029-01-01 uses v1.3 as MANDATORY."""
    res = evaluate_biomass_sourcing_applicability(crediting_period_start_date=date(2029, 1, 1))
    assert res["status"] == "RESOLVED"
    assert res["applicable_version"] == "1.3"
    assert res["is_v1_3_mandatory"] is True
    assert res["transition_category"] == "MANDATORY_NEW_FACILITY"


def test_transition_crediting_period_renewal_mandatory_v1_3():
    """19. Earlier facility on renewal audit uses v1.3 as MANDATORY."""
    res = evaluate_biomass_sourcing_applicability(
        crediting_period_start_date=date(2026, 6, 1),
        is_renewal=True,
    )
    assert res["status"] == "RESOLVED"
    assert res["applicable_version"] == "1.3"
    assert res["is_v1_3_mandatory"] is True
    assert res["transition_category"] == "MANDATORY_ON_RENEWAL"


def test_transition_voluntary_early_adoption_v1_3():
    """20. Voluntary early adoption explicitly recorded."""
    res = evaluate_biomass_sourcing_applicability(
        crediting_period_start_date=date(2026, 6, 1),
        is_renewal=False,
        voluntary_early_adoption=True,
    )
    assert res["status"] == "RESOLVED"
    assert res["applicable_version"] == "1.3"
    assert res["is_v1_3_mandatory"] is False
    assert res["is_v1_3_applicable"] is True
    assert res["transition_category"] == "VOLUNTARY_EARLY_ADOPTION"


def test_transition_earlier_facility_not_yet_mandatory():
    """21. Earlier facility follows official transitional rule (2025 criteria until renewal)."""
    res = evaluate_biomass_sourcing_applicability(
        crediting_period_start_date=date(2026, 6, 1),
        is_renewal=False,
        voluntary_early_adoption=False,
    )
    assert res["status"] == "RESOLVED"
    assert res["applicable_version"] == "2025"
    assert res["is_v1_3_mandatory"] is False
    assert res["is_v1_3_applicable"] is False
    assert res["transition_category"] == "NOT_YET_MANDATORY"


def test_transition_missing_dates_fails_closed():
    """22. Missing crediting-period dates produces unresolved applicability."""
    res = evaluate_biomass_sourcing_applicability(crediting_period_start_date=None)
    assert res["status"] == "UNRESOLVED"
    assert res["applicable_version"] is None
    assert res["reason_code"] == "PURO_CREDITING_DATE_MISSING"


# =============================================================================
# E. Ledger Integration & Fail-Closed Gating Tests
# =============================================================================

@pytest.mark.asyncio
async def test_puro_calculation_with_failed_sourcing_criteria_cannot_mint(db_session: AsyncSession):
    """23. Puro calculation with failed sourcing criteria fails closed and cannot mint."""
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    fac_id = uuid.uuid4()
    batch_id = uuid.uuid4()

    db_session.add(Organization(id=org_id, name=f"Org Biochar {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
    db_session.add(Project(id=proj_id, organization_id=org_id, name="Biochar Project"))
    db_session.add(ProductionFacility(id=fac_id, organization_id=org_id, project_id=proj_id, facility_code=f"FAC-{uuid.uuid4().hex[:6]}", facility_name="Alpha"))

    # Crediting period present
    db_session.add(PuroCreditingPeriod(
        id=uuid.uuid4(),
        organization_id=org_id,
        facility_id=fac_id,
        sequence_number=1,
        start_date=date(2026, 1, 1),
        end_date=date(2036, 1, 1),
        crediting_duration_years=10,
        status="ACTIVE",
    ))

    # Batch with PROHIBITED feedstock
    src_prohibited = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        source_code=f"SRC-PROHIBITED-{uuid.uuid4().hex[:6]}",
        source_name="MSW Biomass",
        source_type="MIXED_MUNICIPAL_SOLID_WASTE",
        biomass_type="MSW",
    )
    lot_prohibited = FeedstockLot(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        source_id=src_prohibited.id,
        lot_number=f"LOT-PROHIBITED-{uuid.uuid4().hex[:6]}",
        feedstock_type="MSW",
        mass_received_tonnes=Decimal("10.0"),
        moisture_content_pct=Decimal("5.0"),
        dry_mass_tonnes=Decimal("9.0"),
    )
    batch = BiocharBatch(
        id=batch_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_number=f"BATCH-FAIL-SOURCING-{uuid.uuid4().hex[:6]}",
        facility_name="Alpha",
        kiln_id="K-1",
        feedstock_type="MSW",
        feedstock_weight_tonnes=Decimal("10.0"),
        moisture_content_pct=Decimal("5.0"),
        pyrolysis_temp_celsius=550.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=Decimal("3.0"),
        dry_mass_tonnes=Decimal("3.0"),
        metadata_json={"feedstock_lot_id": str(lot_prohibited.id)},
    )
    lab = BiocharLabAnalysis(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch_id,
        sample_id=f"SAMPLE-FAIL-SRC-{uuid.uuid4().hex[:6]}",
        sampling_date=date.today(),
        laboratory_name="Eurofins",
        organic_carbon_pct=Decimal("80.0"),
        fixed_carbon_pct=Decimal("75.0"),
        moisture_pct=Decimal("5.0"),
        ash_pct=Decimal("3.0"),
        molar_h_c_ratio=Decimal("0.35"),
    )

    db_session.add_all([src_prohibited, lot_prohibited, batch, lab])
    await db_session.commit()

    # Attempt authoritative execution
    exec_res = await PuroAuthoritativeQuantificationService.resolve_and_execute(
        db=db_session,
        batch_id=batch_id,
        organization_id=org_id,
        mode="AUTHORITATIVE",
    )

    # Must fail closed
    assert exec_res["calculation_status"] == "FAIL_CLOSED"
    assert exec_res["reason_code"] == "PURO_BIOMASS_SOURCING_REQUIRED"

    # Verify no SUCCESS calculation was saved
    stmt_chk = select(PuroCalculationExecution).where(
        PuroCalculationExecution.batch_id == batch_id,
        PuroCalculationExecution.calculation_status == "SUCCESS",
    )
    res_chk = await db_session.execute(stmt_chk)
    assert res_chk.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_fully_eligible_authoritative_puro_calculation_can_mint(db_session: AsyncSession):
    """24. Fully eligible authoritative Puro calculation can mint on ledger."""
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    fac_id = uuid.uuid4()
    batch_id = uuid.uuid4()

    db_session.add(Organization(id=org_id, name=f"Green Biochar Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
    db_session.add(Project(id=proj_id, organization_id=org_id, name="Green Biochar Proj"))
    db_session.add(ProductionFacility(id=fac_id, organization_id=org_id, project_id=proj_id, facility_code=f"FAC-KILN-{uuid.uuid4().hex[:6]}", facility_name="Green Kiln"))

    # 1. Crediting Period
    db_session.add(PuroCreditingPeriod(
        id=uuid.uuid4(),
        organization_id=org_id,
        facility_id=fac_id,
        sequence_number=1,
        start_date=date(2026, 1, 1),
        end_date=date(2036, 1, 1),
        crediting_duration_years=10,
        status="ACTIVE",
    ))

    # 2. Compliant Feedstock Source, Lot, Declaration
    src = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        source_code=f"SRC-CLEAN-PINE-{uuid.uuid4().hex[:6]}",
        source_name="Clean Pine",
        source_type="FORESTRY_RESIDUE",
        biomass_type="WOOD_CHIPS",
        origin_location="Kupio, Finland",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="OPEN_BURNING",
    )
    lot = FeedstockLot(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        source_id=src.id,
        lot_number=f"LOT-CLEAN-PINE-{uuid.uuid4().hex[:6]}",
        feedstock_type="WOOD_CHIPS",
        mass_received_tonnes=Decimal("20.0"),
        moisture_content_pct=Decimal("10.0"),
        dry_mass_tonnes=Decimal("18.0"),
        chain_of_custody_ref="COC-PINE-01",
    )
    decl = PuroBiomassSourceDeclaration(
        id=uuid.uuid4(),
        organization_id=org_id,
        feedstock_source_id=src.id,
        source_declaration_code=f"DECL-CLEAN-PINE-{uuid.uuid4().hex[:6]}",
        declared_validity_start=date(2025, 1, 1),
        declared_validity_end=date(2030, 1, 1),
        puro_category_ref="FORESTRY_RESIDUE",
        risk_classification="LOW_RISK",
        is_active=True,
    )
    db_session.add(src)
    await db_session.flush()
    db_session.add_all([lot, decl])
    await db_session.flush()

    # 3. Batch & Lab
    batch = BiocharBatch(
        id=batch_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_number=f"BATCH-CLEAN-{uuid.uuid4().hex[:6]}",
        facility_name="Green Kiln",
        kiln_id="K-01",
        feedstock_type="WOOD_CHIPS",
        feedstock_weight_tonnes=Decimal("20.0"),
        moisture_content_pct=Decimal("10.0"),
        pyrolysis_temp_celsius=580.0,
        residence_time_minutes=35.0,
        biochar_yield_tonnes=Decimal("6.0"),
        dry_mass_tonnes=Decimal("6.0"),
        metadata_json={"feedstock_lot_id": str(lot.id)},
    )
    lab = BiocharLabAnalysis(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch_id,
        sample_id=f"SAMPLE-CLEAN-{uuid.uuid4().hex[:6]}",
        sampling_date=date.today(),
        laboratory_name="Eurofins Accredited",
        organic_carbon_pct=Decimal("82.0"),
        fixed_carbon_pct=Decimal("75.0"),
        moisture_pct=Decimal("5.0"),
        ash_pct=Decimal("3.0"),
        molar_h_c_ratio=Decimal("0.32"),
    )
    db_session.add_all([batch, lab])

    # 4. Verified Counterfactual Storage Assessment (Path A)
    cf = PuroCounterfactualStorageAssessment(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        facility_id=fac_id,
        batch_id=batch_id,
        counterfactual_path="PATH_A_NEGLIGIBLE_STORAGE",
        baseline_fate="OPEN_BURNING",
        evidence_status="VERIFIED",
        counterfactual_carbon_stored_tco2e=Decimal("0.0"),
        assessment_status="COMPLIANT",
    )
    db_session.add(cf)
    await db_session.commit()

    # Execute Authoritative Quantification
    exec_res = await PuroAuthoritativeQuantificationService.resolve_and_execute(
        db=db_session,
        batch_id=batch_id,
        organization_id=org_id,
        mode="AUTHORITATIVE",
    )
    assert exec_res["calculation_status"] == "SUCCESS"
    calc_exec_id = uuid.UUID(exec_res["execution_id"])

    # Now mint via ledger endpoint
    user = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:6]}@verifield.test",
        role="SUPER_ADMIN",
        organization_id=org_id,
        full_name="Admin User",
    )
    req = MintRequest(project_id=proj_id)
    res_mint = await execute_carbon_minting(data=req, db=db_session, current_user=user)
    assert res_mint["status"] == "MINTED"
    assert res_mint["records_minted"] == 1
    assert str(calc_exec_id) in res_mint["calculation_ids"]
    assert float(res_mint["total_tco2e"]) > 0.0

    # Duplicate mint must be rejected
    with pytest.raises(HTTPException) as exc_dup:
        await execute_carbon_minting(data=req, db=db_session, current_user=user)
    assert exc_dup.value.status_code in (400, 409)


# =============================================================================
# F. API Endpoints Tests
# =============================================================================

@pytest.mark.asyncio
async def test_api_puro_standard_config(db_session: AsyncSession):
    """25. GET /api/v1/biochar/puro/standard-config endpoint returns valid configuration."""
    org_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email=f"user-{uuid.uuid4().hex[:6]}@test.org", role="SUPER_ADMIN", organization_id=org_id, full_name="Admin User")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(
                "/api/v1/biochar/puro/standard-config",
                params={
                    "methodology_code": "PURO_BIOCHAR_2025_V2",
                    "crediting_period_start_date": "2029-06-01",
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["methodology_code"] == "PURO_BIOCHAR_2025_V2"
            assert data["methodology_edition"] == "Edition 2025 v2"
            assert data["sourcing_criteria_version"] == "1.3"
            assert data["is_valid"] is True
            assert data["applicability"]["is_v1_3_mandatory"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_api_batch_sourcing_compliance(db_session: AsyncSession):
    """26. GET /api/v1/biochar/puro/batches/{batch_id}/sourcing-compliance endpoint."""
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    fac_id = uuid.uuid4()
    batch_id = uuid.uuid4()

    db_session.add(Organization(id=org_id, name=f"Test Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
    db_session.add(Project(id=proj_id, organization_id=org_id, name="Test Proj"))
    db_session.add(ProductionFacility(id=fac_id, organization_id=org_id, project_id=proj_id, facility_code=f"FAC-TEST-{uuid.uuid4().hex[:6]}", facility_name="Test Fac"))

    src = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        source_code=f"SRC-API-{uuid.uuid4().hex[:6]}",
        source_name="API Residue",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="RICE_HUSK",
        origin_location="Punjab, India",
    )
    lot = FeedstockLot(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        source_id=src.id,
        lot_number=f"LOT-API-{uuid.uuid4().hex[:6]}",
        feedstock_type="RICE_HUSK",
        mass_received_tonnes=Decimal("15.0"),
        moisture_content_pct=Decimal("8.0"),
        dry_mass_tonnes=Decimal("13.8"),
    )
    decl = PuroBiomassSourceDeclaration(
        id=uuid.uuid4(),
        organization_id=org_id,
        feedstock_source_id=src.id,
        source_declaration_code=f"DECL-API-{uuid.uuid4().hex[:6]}",
        declared_validity_start=date(2025, 1, 1),
        declared_validity_end=date(2030, 1, 1),
        puro_category_ref="AGRICULTURAL_RESIDUE",
        risk_classification="LOW_RISK",
        is_active=True,
    )
    batch = BiocharBatch(
        id=batch_id,
        organization_id=org_id,
        project_id=proj_id,
        batch_number=f"BATCH-API-{uuid.uuid4().hex[:6]}",
        facility_name="Test Fac",
        kiln_id="K-01",
        feedstock_type="RICE_HUSK",
        feedstock_weight_tonnes=Decimal("15.0"),
        moisture_content_pct=Decimal("8.0"),
        pyrolysis_temp_celsius=520.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=Decimal("4.5"),
        metadata_json={"feedstock_lot_id": str(lot.id)},
    )
    cf = PuroCounterfactualStorageAssessment(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        facility_id=fac_id,
        batch_id=batch_id,
        counterfactual_path="PATH_A_NEGLIGIBLE_STORAGE",
        baseline_fate="OPEN_BURNING",
        evidence_status="VERIFIED",
        counterfactual_carbon_stored_tco2e=Decimal("0.0"),
        assessment_status="COMPLIANT",
    )
    db_session.add(src)
    await db_session.flush()
    db_session.add_all([lot, decl, batch, cf])
    await db_session.flush()
    await db_session.commit()

    user = User(id=uuid.uuid4(), email=f"user2-{uuid.uuid4().hex[:6]}@test.org", role="SUPER_ADMIN", organization_id=org_id, full_name="Admin User")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/api/v1/biochar/puro/batches/{batch_id}/sourcing-compliance")
            assert res.status_code == 200
            data = res.json()
            assert data["batch_id"] == str(batch_id)
            assert data["is_compliant"] is True
            assert data["compliance_state"] == "COMPLIANT"
            assert data["counterfactual_assessment"]["counterfactual_path"] == "PATH_A_NEGLIGIBLE_STORAGE"
            assert float(data["deductible_counterfactual_tco2e"]) == 0.0
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
