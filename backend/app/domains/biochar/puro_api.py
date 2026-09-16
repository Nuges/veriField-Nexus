import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.abac import ABACEngine
from app.core.security import get_current_user
from app.db.session import get_db
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
    PuroAdditionalityAssessment,
    PuroAuditFinding,
    PuroAuditWorkflow,
    PuroBaselineAssessment,
    PuroCalculationExecution,
    PuroCharStreamRecord,
    PuroCoProductAllocation,
    PuroCreditingPeriod,
    PuroCutoffDecision,
    PuroEndUseCategory,
    PuroEndUseRecordLink,
    PuroFacilityProfile,
    PuroLCAModel,
    PuroLCIEntry,
    PuroMobileProductionSite,
    PuroMonitoringPlan,
    PuroNormativeDependency,
    PuroOutputReport,
    PuroRuleDefinition,
    PuroSupplierProfile,
)
from app.domains.biochar.puro_rules import (
    TABLE_3_2_CATEGORIES,
    NORMATIVE_DEPENDENCIES,
    METHODOLOGY_RULES_CATALOG,
    seed_puro_biochar_normative_metadata,
)
from app.domains.biochar.puro_schemas import (
    PuroAdditionalityAssessmentCreate,
    PuroAdditionalityAssessmentResponse,
    PuroAuditWorkflowCreate,
    PuroAuditWorkflowResponse,
    PuroAuthoritativeRequest,
    PuroBaselineAssessmentCreate,
    PuroBaselineAssessmentResponse,
    PuroCharStreamRecordCreate,
    PuroCharStreamRecordResponse,
    PuroCoProductAllocationCreate,
    PuroCoProductAllocationResponse,
    PuroCreditingPeriodCreate,
    PuroCreditingPeriodResponse,
    PuroCutoffDecisionCreate,
    PuroCutoffDecisionResponse,
    PuroEndUseCategoryResponse,
    PuroEndUseRecordLinkCreate,
    PuroEndUseRecordLinkResponse,
    PuroFacilityProfileCreate,
    PuroFacilityProfileResponse,
    PuroLCAModelCreate,
    PuroLCAModelResponse,
    PuroLCIEntryCreate,
    PuroLCIEntryResponse,
    PuroMobileSiteCreate,
    PuroMobileSiteResponse,
    PuroNormativeDependencySchema,
    PuroOutputReportResponse,
    PuroQuantificationBreakdown,
    PuroQuantificationRequest,
    PuroRegistryReadinessResponse,
    PuroRuleDefinitionSchema,
    PuroSimulationRequest,
    PuroSupplierProfileCreate,
    PuroSupplierProfileResponse,
)
from app.domains.biochar.services.puro_compliance import (
    PuroAuditManager,
    PuroComplianceEngine,
    PuroOutputReportBuilder,
)
from app.domains.biochar.services.puro_quantification import (
    PuroAuthoritativeQuantificationService,
    PuroCORCCalculator,
)
from app.domains.projects.models import Project

router = APIRouter(prefix="/puro", tags=["Biochar - Puro.earth Edition 2025 V2"])


def _check_org_access(current_user: User, target_org_id: UUID) -> None:
    if current_user.role != "SUPER_ADMIN" and current_user.organization_id != target_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Resource belongs to another organization.",
        )


# ---------------------------------------------------------------------------
# 1. Normative Rules, Dependencies & End-Use Categories
# ---------------------------------------------------------------------------

@router.get("/rules", response_model=List[PuroRuleDefinitionSchema])
async def list_puro_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists registered rule definitions for Puro.earth Biochar Edition 2025 V2 across all 11 chapters."""
    await seed_puro_biochar_normative_metadata(db)
    stmt = select(PuroRuleDefinition).order_by(PuroRuleDefinition.section_number, PuroRuleDefinition.rule_number)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/dependencies", response_model=List[PuroNormativeDependencySchema])
async def list_puro_dependencies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists versioned normative dependencies (General Rules, Biomass Sourcing Criteria, etc.)."""
    await seed_puro_biochar_normative_metadata(db)
    stmt = select(PuroNormativeDependency).order_by(PuroNormativeDependency.code)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/categories", response_model=List[PuroEndUseCategoryResponse])
async def list_puro_end_use_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists official Table 3.2 End-Use Categories (AF1, AF2, WM1, EM1, BE1, NE1, RC1)."""
    await seed_puro_biochar_normative_metadata(db)
    stmt = select(PuroEndUseCategory).order_by(PuroEndUseCategory.category_code)
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# 2. CO2 Removal Supplier Profile & Claim Rights
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/supplier", response_model=PuroSupplierProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier_profile(
    project_id: UUID,
    data: PuroSupplierProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers a CO2 Removal Supplier profile with legal claim rights and double-claim controls."""
    stmt_p = select(Project).where(Project.id == project_id)
    res_p = await db.execute(stmt_p)
    proj = res_p.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    _check_org_access(current_user, proj.organization_id)

    # Check facility
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == data.facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production facility not found.")
    _check_org_access(current_user, fac.organization_id)

    # Check existing supplier profile
    stmt_s = select(PuroSupplierProfile).where(PuroSupplierProfile.facility_id == data.facility_id)
    res_s = await db.execute(stmt_s)
    if res_s.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplier profile already registered for this facility. Update or supersede existing.",
        )

    profile = PuroSupplierProfile(
        organization_id=fac.organization_id,
        project_id=project_id,
        facility_id=data.facility_id,
        supplier_legal_name=data.supplier_legal_name,
        registration_number=data.registration_number,
        jurisdiction_country=data.jurisdiction_country,
        supplier_role=data.supplier_role,
        claim_rights_status=data.claim_rights_status,
        authorization_agreement_ref=data.authorization_agreement_ref,
        rights_declaration_doc_hash=data.rights_declaration_doc_hash,
        contract_effective_date=data.contract_effective_date,
        contract_expiry_date=data.contract_expiry_date,
        validation_state="VALIDATED" if data.claim_rights_status == "EXCLUSIVE_CLAIM_RIGHTS_ESTABLISHED" else "PENDING_AUDIT",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/projects/{project_id}/supplier", response_model=Optional[PuroSupplierProfileResponse])
async def get_supplier_profile(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_p = select(Project).where(Project.id == project_id)
    res_p = await db.execute(stmt_p)
    proj = res_p.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    _check_org_access(current_user, proj.organization_id)

    stmt_s = select(PuroSupplierProfile).where(PuroSupplierProfile.project_id == project_id)
    res_s = await db.execute(stmt_s)
    return res_s.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 3. Production Facility Classification (Stationary vs Mobile)
# ---------------------------------------------------------------------------

@router.post("/facilities/{facility_id}/profile", response_model=PuroFacilityProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_facility_profile(
    facility_id: UUID,
    data: PuroFacilityProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    # Check existing profile
    stmt_p = select(PuroFacilityProfile).where(PuroFacilityProfile.facility_id == facility_id)
    res_p = await db.execute(stmt_p)
    if res_p.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Facility profile already exists.")

    if data.facility_classification == "MOBILE" and not data.spatial_extent_geojson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile facility classification requires spatial_extent_geojson defining host country bounds.",
        )

    prof = PuroFacilityProfile(
        organization_id=fac.organization_id,
        facility_id=facility_id,
        facility_classification=data.facility_classification,
        host_country=data.host_country,
        reference_coordinates=data.reference_coordinates,
        spatial_extent_geojson=data.spatial_extent_geojson,
        receiving_location=data.receiving_location,
        pretreatment_location=data.pretreatment_location,
        conversion_location=data.conversion_location,
        packaging_location=data.packaging_location,
        technology_similarity_verified=data.technology_similarity_verified,
        commissioned_status=data.commissioned_status,
        operating_status=data.operating_status,
    )
    db.add(prof)
    await db.commit()
    await db.refresh(prof)
    return prof


@router.get("/facilities/{facility_id}/profile", response_model=Optional[PuroFacilityProfileResponse])
async def get_facility_profile(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    stmt_p = select(PuroFacilityProfile).where(PuroFacilityProfile.facility_id == facility_id)
    res_p = await db.execute(stmt_p)
    return res_p.scalar_one_or_none()


@router.post("/facilities/{facility_id}/mobile-sites", response_model=PuroMobileSiteResponse, status_code=status.HTTP_201_CREATED)
async def add_mobile_site(
    facility_id: UUID,
    data: PuroMobileSiteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_p = select(PuroFacilityProfile).where(PuroFacilityProfile.facility_id == facility_id)
    res_p = await db.execute(stmt_p)
    prof = res_p.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility profile not found.")

    _check_org_access(current_user, prof.organization_id)

    if prof.facility_classification != "MOBILE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile production sites can only be registered for MOBILE facility profiles.",
        )

    site = PuroMobileProductionSite(
        facility_profile_id=prof.id,
        site_code=data.site_code,
        site_name=data.site_name,
        coordinates=data.coordinates,
        owner_operator=data.owner_operator,
        date_range_start=data.date_range_start,
        date_range_end=data.date_range_end,
        regulatory_permit_ref=data.regulatory_permit_ref,
        stakeholder_evidence_ref=data.stakeholder_evidence_ref,
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


@router.get("/facilities/{facility_id}/mobile-sites", response_model=List[PuroMobileSiteResponse])
async def list_mobile_sites(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_p = select(PuroFacilityProfile).where(PuroFacilityProfile.facility_id == facility_id)
    res_p = await db.execute(stmt_p)
    prof = res_p.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility profile not found.")

    _check_org_access(current_user, prof.organization_id)

    stmt_s = select(PuroMobileProductionSite).where(PuroMobileProductionSite.facility_profile_id == prof.id)
    res_s = await db.execute(stmt_s)
    return res_s.scalars().all()


# ---------------------------------------------------------------------------
# 4. Crediting Period Engine
# ---------------------------------------------------------------------------

@router.post("/facilities/{facility_id}/crediting-periods", response_model=PuroCreditingPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_crediting_period(
    facility_id: UUID,
    data: PuroCreditingPeriodCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    # Check maximum renewals (max sequence_number = 3 -> initial + 2 renewals)
    if data.sequence_number > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Puro rules prohibit crediting period renewal more than twice (maximum 30 years total).",
        )

    # Check existing overlapping periods
    stmt_ex = select(PuroCreditingPeriod).where(PuroCreditingPeriod.facility_id == facility_id)
    res_ex = await db.execute(stmt_ex)
    existing_periods = res_ex.scalars().all()
    for ep in existing_periods:
        if not (data.end_date < ep.start_date or data.start_date > ep.end_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Crediting period overlaps with existing period {ep.sequence_number} ({ep.start_date} to {ep.end_date}).",
            )

    period = PuroCreditingPeriod(
        organization_id=fac.organization_id,
        facility_id=facility_id,
        sequence_number=data.sequence_number,
        start_date=data.start_date,
        end_date=data.end_date,
        crediting_duration_years=data.crediting_duration_years,
        status="ACTIVE",
        renewal_type=data.renewal_type,
        renewal_eligibility=True,
    )
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


@router.get("/facilities/{facility_id}/crediting-periods", response_model=List[PuroCreditingPeriodResponse])
async def list_crediting_periods(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    stmt_p = select(PuroCreditingPeriod).where(PuroCreditingPeriod.facility_id == facility_id).order_by(PuroCreditingPeriod.sequence_number)
    res_p = await db.execute(stmt_p)
    return res_p.scalars().all()


# ---------------------------------------------------------------------------
# 5. Baseline & Additionality Assessments
# ---------------------------------------------------------------------------

@router.post("/facilities/{facility_id}/baseline", response_model=PuroBaselineAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def record_baseline_assessment(
    facility_id: UUID,
    data: PuroBaselineAssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    # Check existing baseline
    stmt_b = select(PuroBaselineAssessment).where(PuroBaselineAssessment.facility_id == facility_id)
    res_b = await db.execute(stmt_b)
    existing_b = res_b.scalar_one_or_none()
    if existing_b and existing_b.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baseline assessment is locked for this facility across its crediting period.",
        )

    valid_scenarios = {"NEW_FACILITY", "RETROFIT_FACILITY", "CHARCOAL_REPURPOSE", "UNFORESEEN_CASE_REQUIRING_ISSUING_BODY_REVIEW"}
    if data.scenario not in valid_scenarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario. Must be one of {sorted(valid_scenarios)}.",
        )

    base = PuroBaselineAssessment(
        organization_id=fac.organization_id,
        project_id=fac.project_id or fac.organization_id,
        facility_id=facility_id,
        scenario=data.scenario,
        is_locked=True,
        historical_char_production_tpy=Decimal(str(data.historical_char_production_tpy)),
        baseline_removal_tco2e_per_year=Decimal(str(data.baseline_removal_tco2e_per_year)),
        historical_products_description=data.historical_products_description,
        prior_use_fate=data.prior_use_fate,
        baseline_land_use_evidence_type=data.baseline_land_use_evidence_type,
        land_use_evidence_ref=data.land_use_evidence_ref,
        assessment_status="LOCKED_VALIDATED",
        reviewed_by=current_user.email,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(base)
    await db.commit()
    await db.refresh(base)
    return base


@router.get("/facilities/{facility_id}/baseline", response_model=Optional[PuroBaselineAssessmentResponse])
async def get_baseline_assessment(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    stmt_b = select(PuroBaselineAssessment).where(PuroBaselineAssessment.facility_id == facility_id)
    res_b = await db.execute(stmt_b)
    return res_b.scalar_one_or_none()


@router.post("/facilities/{facility_id}/additionality", response_model=PuroAdditionalityAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def record_additionality_assessment(
    facility_id: UUID,
    data: PuroAdditionalityAssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    overall = "PASS" if (
        data.carbon_additionality_status == "PASS"
        and data.regulatory_additionality_status == "PASS"
        and data.financial_additionality_status == "PASS"
    ) else "DATA_REQUIRED"

    add = PuroAdditionalityAssessment(
        organization_id=fac.organization_id,
        project_id=fac.project_id or fac.organization_id,
        facility_id=facility_id,
        carbon_additionality_status=data.carbon_additionality_status,
        regulatory_additionality_status=data.regulatory_additionality_status,
        financial_additionality_status=data.financial_additionality_status,
        overall_status=overall,
        opex_per_tonne=Decimal(str(data.opex_per_tonne)) if data.opex_per_tonne is not None else None,
        capex_investment=Decimal(str(data.capex_investment)) if data.capex_investment is not None else None,
        biomass_cost_per_tonne=Decimal(str(data.biomass_cost_per_tonne)) if data.biomass_cost_per_tonne is not None else None,
        biochar_market_price_per_tonne=Decimal(str(data.biochar_market_price_per_tonne)) if data.biochar_market_price_per_tonne is not None else None,
        carbon_finance_dependency_pct=Decimal(str(data.carbon_finance_dependency_pct)) if data.carbon_finance_dependency_pct is not None else None,
        legal_mandate_evidence_ref=data.legal_mandate_evidence_ref,
        financial_model_evidence_hash=data.financial_model_evidence_hash,
    )
    db.add(add)
    await db.commit()
    await db.refresh(add)
    return add


@router.get("/facilities/{facility_id}/additionality", response_model=Optional[PuroAdditionalityAssessmentResponse])
async def get_additionality_assessment(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    stmt_a = select(PuroAdditionalityAssessment).where(PuroAdditionalityAssessment.facility_id == facility_id)
    res_a = await db.execute(stmt_a)
    return res_a.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 6. Table 3.2 End-Use Linking & Point of Creation
# ---------------------------------------------------------------------------

@router.post("/batches/{batch_id}/end-use", response_model=PuroEndUseRecordLinkResponse, status_code=status.HTTP_201_CREATED)
async def link_batch_to_puro_end_use(
    batch_id: UUID,
    data: PuroEndUseRecordLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_b = select(BiocharBatch).where(BiocharBatch.id == batch_id)
    res_b = await db.execute(stmt_b)
    batch = res_b.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")

    if batch.organization_id:
        _check_org_access(current_user, batch.organization_id)

    stmt_cat = select(PuroEndUseCategory).where(PuroEndUseCategory.id == data.category_id)
    res_cat = await db.execute(stmt_cat)
    cat = res_cat.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puro Table 3.2 category not found.")

    # Determine Point of Creation status
    if not cat.is_corc_eligible:
        corc_point = "CORC_POINT_INELIGIBLE"
    elif not data.final_durable_fate_verified:
        corc_point = "CORC_POINT_EVIDENCE_PENDING"
    elif not data.proof_of_delivery_ref or not data.application_attestation_ref:
        corc_point = "CORC_POINT_EVIDENCE_PENDING"
    elif not data.gps_verified or not data.geotagged_photos_verified:
        corc_point = "CORC_POINT_EVIDENCE_PENDING"
    else:
        corc_point = "CORC_POINT_ELIGIBLE"

    link = PuroEndUseRecordLink(
        organization_id=batch.organization_id or current_user.organization_id,
        batch_id=batch_id,
        end_use_record_id=data.end_use_record_id,
        category_id=data.category_id,
        is_pure_biochar=data.is_pure_biochar,
        formulation_biochar_pct=data.formulation_biochar_pct,
        manufacturer_name=data.manufacturer_name,
        intermediary_entity_name=data.intermediary_entity_name,
        intermediary_agreement_ref=data.intermediary_agreement_ref,
        cascade_stage=data.cascade_stage,
        final_durable_fate_verified=data.final_durable_fate_verified,
        proof_of_delivery_ref=data.proof_of_delivery_ref,
        application_attestation_ref=data.application_attestation_ref,
        gps_verified=data.gps_verified,
        geotagged_photos_verified=data.geotagged_photos_verified,
        corc_point_reached=corc_point,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.get("/batches/{batch_id}/end-use", response_model=List[PuroEndUseRecordLinkResponse])
async def list_batch_puro_end_uses(
    batch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_b = select(BiocharBatch).where(BiocharBatch.id == batch_id)
    res_b = await db.execute(stmt_b)
    batch = res_b.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")

    if batch.organization_id:
        _check_org_access(current_user, batch.organization_id)

    stmt_l = select(PuroEndUseRecordLink).where(PuroEndUseRecordLink.batch_id == batch_id)
    res_l = await db.execute(stmt_l)
    return res_l.scalars().all()


# ---------------------------------------------------------------------------
# 7. Deterministic CORC Quantification Execution
# ---------------------------------------------------------------------------

@router.post("/batches/{batch_id}/quantification", response_model=PuroQuantificationBreakdown)
async def execute_puro_quantification(
    batch_id: UUID,
    req: Optional[PuroQuantificationRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Authoritative CORC Quantification Execution (Edition 2025 V2, Engine 2.0.0).
    Derived strictly from verified server-side database records.
    Persists authoritative execution record and marks legacy v1.0.0 calculations as superseded.
    """
    stmt_b = select(BiocharBatch).where(BiocharBatch.id == batch_id)
    res_b = await db.execute(stmt_b)
    batch = res_b.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")

    if batch.organization_id:
        _check_org_access(current_user, batch.organization_id)

    org_id = batch.organization_id or current_user.organization_id
    result = await PuroAuthoritativeQuantificationService.resolve_and_execute(
        db=db,
        batch_id=batch_id,
        organization_id=org_id,
        mode="AUTHORITATIVE",
    )

    if result.get("calculation_status") == "SUCCESS":
        batch.net_co2e_removed_tonnes = result["final_corcs_issuable"]
        await db.commit()

    return PuroQuantificationBreakdown(
        eligible_dry_biochar_mass_tonnes=float(result.get("eligible_dry_biochar_mass_tonnes", Decimal("0.0"))),
        organic_carbon_pct=float(result.get("organic_carbon_pct", Decimal("0.0"))),
        molar_h_c=float(result.get("molar_h_c", 0.0)),
        soil_temperature_celsius=float(result.get("soil_temperature_celsius", 15.0)),
        persistence_fraction_pf=float(result.get("persistence_fraction_pf", 0.0)),
        regression_m=result.get("regression_m"),
        regression_a=result.get("regression_a"),
        durability_class=result.get("durability_class", "INELIGIBLE"),
        c_stored_tco2e=float(result.get("c_stored_tco2e", Decimal("0.0"))),
        c_baseline_tco2e=float(result.get("c_baseline_tco2e", Decimal("0.0"))),
        c_loss_tco2e=float(result.get("c_loss_tco2e", Decimal("0.0"))),
        e_project_tco2e=float(result.get("e_project_tco2e", Decimal("0.0"))),
        e_ops_biomass_tco2e=float(result.get("e_ops_biomass_tco2e", Decimal("0.0"))),
        e_ops_production_tco2e=float(result.get("e_ops_production_tco2e", Decimal("0.0"))),
        e_ops_use_tco2e=float(result.get("e_ops_use_tco2e", Decimal("0.0"))),
        e_ops_total_tco2e=float(result.get("e_ops_total_tco2e", Decimal("0.0"))),
        e_emb_infra_tco2e=float(result.get("e_emb_infra_tco2e", Decimal("0.0"))),
        e_emb_dluc_tco2e=float(result.get("e_emb_dluc_tco2e", Decimal("0.0"))),
        e_emb_annualized_tco2e=float(result.get("e_emb_annualized_tco2e", Decimal("0.0"))),
        leakage_eco_tco2e=float(result.get("leakage_eco_tco2e", Decimal("0.0"))),
        leakage_ma_tco2e=float(result.get("leakage_ma_tco2e", Decimal("0.0"))),
        leakage_iluc_tco2e=float(result.get("leakage_iluc_tco2e", Decimal("0.0"))),
        e_leakage_tco2e=float(result.get("e_leakage_tco2e", Decimal("0.0"))),
        net_corcs_calculated=float(result.get("net_corcs_calculated", Decimal("0.0"))),
        combined_uncertainty_pct=float(result.get("combined_uncertainty_pct", 0.0)),
        deductible_uncertainty_pct=0.0,
        final_corcs_issuable=float(result.get("final_corcs_issuable", Decimal("0.0"))),
        reported_uncertainty_text=result.get("reported_uncertainty_text"),
        calculation_mode=result.get("calculation_mode", "AUTHORITATIVE"),
        calculation_status=result.get("calculation_status", "FAIL_CLOSED"),
        corc_point_status=result.get("corc_point_status", "CORC_POINT_NOT_REACHED"),
        calculation_hash=result.get("calculation_hash", ""),
        methodology_version=result.get("methodology_version", "PURO_BIOCHAR_2025_V2"),
        coefficient_version=result.get("coefficient_version", "PURO_2025_V2_TABLE_6_1_INTEGER_LOOKUP"),
        engine_version=result.get("engine_version", "2.0.0"),
        timestamp=result.get("timestamp", datetime.now(timezone.utc)),
        execution_id=result.get("execution_id"),
        rule_references=result.get("rule_references", []),
        warnings=result.get("warnings", []),
        notes=result.get("notes"),
    )


@router.post("/batches/{batch_id}/simulate-quantification", response_model=PuroQuantificationBreakdown)
@router.post("/simulate-quantification", response_model=PuroQuantificationBreakdown)
async def simulate_puro_quantification(
    req: PuroSimulationRequest,
    batch_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Scenario Modeling & What-If Simulation Console (Edition 2025 V2, Engine 2.0.0).
    Runs calculations in SIMULATION mode without altering physical batch yield or creating sealed ledger entries.
    """
    b_id = batch_id or req.batch_id
    if b_id:
        stmt_b = select(BiocharBatch).where(BiocharBatch.id == b_id)
        res_b = await db.execute(stmt_b)
        batch = res_b.scalar_one_or_none()
        if batch and batch.organization_id:
            _check_org_access(current_user, batch.organization_id)

    result = PuroCORCCalculator.execute_quantification(
        eligible_dry_mass_tonnes=Decimal(str(req.dry_mass_tonnes)),
        c_org_pct=Decimal(str(req.c_org_pct)),
        molar_h_c=req.molar_h_c,
        soil_temperature_celsius=req.soil_temperature_celsius,
        baseline_scenario=req.baseline_scenario,
        historical_baseline_tco2e=Decimal(str(req.historical_baseline_tco2e)),
        end_use_category_code=req.end_use_category_code,
        reversal_discount_factor=Decimal(str(req.reversal_discount_factor)) if req.reversal_discount_factor else None,
        is_non_soil_durable=req.is_non_soil_durable,
        e_biomass=Decimal(str(req.e_biomass)),
        e_production=Decimal(str(req.e_production)),
        e_use=Decimal(str(req.e_use)),
        e_infra=Decimal(str(req.e_infra)),
        e_dluc=Decimal(str(req.e_dluc)),
        crediting_years=req.crediting_years,
        is_leakage_mitigated=req.is_leakage_mitigated,
        ecological_leakage_tco2e=Decimal(str(req.ecological_leakage_tco2e)),
        market_activity_shifting_tco2e=Decimal(str(req.market_activity_shifting_tco2e)),
        iluc_feedstock_category=req.iluc_feedstock_category,
        feedstock_quantity_dry_tonnes=Decimal(str(req.feedstock_quantity_dry_tonnes)),
        calculation_mode="SIMULATION",
        engine_version="2.0.0",
    )

    return PuroQuantificationBreakdown(
        eligible_dry_biochar_mass_tonnes=float(result.get("eligible_dry_biochar_mass_tonnes", Decimal("0.0"))),
        organic_carbon_pct=float(result.get("organic_carbon_pct", Decimal("0.0"))),
        molar_h_c=float(result.get("molar_h_c", 0.0)),
        soil_temperature_celsius=float(result.get("soil_temperature_celsius", 15.0)),
        persistence_fraction_pf=float(result.get("persistence_fraction_pf", 0.0)),
        regression_m=result.get("regression_m"),
        regression_a=result.get("regression_a"),
        durability_class=result.get("durability_class", "INELIGIBLE"),
        c_stored_tco2e=float(result.get("c_stored_tco2e", Decimal("0.0"))),
        c_baseline_tco2e=float(result.get("c_baseline_tco2e", Decimal("0.0"))),
        c_loss_tco2e=float(result.get("c_loss_tco2e", Decimal("0.0"))),
        e_project_tco2e=float(result.get("e_project_tco2e", Decimal("0.0"))),
        e_ops_biomass_tco2e=float(result.get("e_ops_biomass_tco2e", Decimal("0.0"))),
        e_ops_production_tco2e=float(result.get("e_ops_production_tco2e", Decimal("0.0"))),
        e_ops_use_tco2e=float(result.get("e_ops_use_tco2e", Decimal("0.0"))),
        e_ops_total_tco2e=float(result.get("e_ops_total_tco2e", Decimal("0.0"))),
        e_emb_infra_tco2e=float(result.get("e_emb_infra_tco2e", Decimal("0.0"))),
        e_emb_dluc_tco2e=float(result.get("e_emb_dluc_tco2e", Decimal("0.0"))),
        e_emb_annualized_tco2e=float(result.get("e_emb_annualized_tco2e", Decimal("0.0"))),
        leakage_eco_tco2e=float(result.get("leakage_eco_tco2e", Decimal("0.0"))),
        leakage_ma_tco2e=float(result.get("leakage_ma_tco2e", Decimal("0.0"))),
        leakage_iluc_tco2e=float(result.get("leakage_iluc_tco2e", Decimal("0.0"))),
        e_leakage_tco2e=float(result.get("e_leakage_tco2e", Decimal("0.0"))),
        net_corcs_calculated=float(result.get("net_corcs_calculated", Decimal("0.0"))),
        combined_uncertainty_pct=float(result.get("combined_uncertainty_pct", 0.0)),
        deductible_uncertainty_pct=0.0,
        final_corcs_issuable=float(result.get("final_corcs_issuable", Decimal("0.0"))),
        reported_uncertainty_text=result.get("reported_uncertainty_text"),
        calculation_mode="SIMULATION",
        calculation_status=result.get("calculation_status", "SUCCESS"),
        corc_point_status=result.get("corc_point_status", "CORC_POINT_ELIGIBLE"),
        calculation_hash=result.get("calculation_hash", ""),
        methodology_version="PURO_BIOCHAR_2025_V2",
        coefficient_version="PURO_2025_V2_TABLE_6_1_INTEGER_LOOKUP",
        engine_version="2.0.0",
        timestamp=result.get("timestamp", datetime.now(timezone.utc)),
        execution_id=None,
        rule_references=result.get("rule_references", []),
        warnings=result.get("warnings", []),
        notes="SIMULATION MODE: Scenario estimation completed. Not persisted to batch ledger.",
    )


# ---------------------------------------------------------------------------
# 7.1 Char Streams (Rule 3.5.2)
# ---------------------------------------------------------------------------

@router.post("/facilities/{facility_id}/char-streams", response_model=PuroCharStreamRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_char_stream(
    facility_id: UUID,
    data: PuroCharStreamRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    _check_org_access(current_user, fac.organization_id)

    stream = PuroCharStreamRecord(
        organization_id=fac.organization_id,
        facility_id=facility_id,
        stream_code=data.stream_code,
        stream_name=data.stream_name,
        feedstock_type=data.feedstock_type,
        pyrolyzer_unit=data.pyrolyzer_unit,
        operating_temperature_celsius=data.operating_temperature_celsius,
        residence_time_minutes=data.residence_time_minutes,
        is_active=data.is_active,
    )
    db.add(stream)
    await db.commit()
    await db.refresh(stream)
    return stream


@router.get("/facilities/{facility_id}/char-streams", response_model=List[PuroCharStreamRecordResponse])
async def list_char_streams(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PuroCharStreamRecord).where(PuroCharStreamRecord.facility_id == facility_id)
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# 7.2 LCA Models & Life Cycle Inventory (Chapter 7)
# ---------------------------------------------------------------------------

@router.post("/facilities/{facility_id}/lca-models", response_model=PuroLCAModelResponse, status_code=status.HTTP_201_CREATED)
async def create_lca_model(
    facility_id: UUID,
    data: PuroLCAModelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    _check_org_access(current_user, fac.organization_id)

    model = PuroLCAModel(
        organization_id=fac.organization_id,
        facility_id=facility_id,
        model_name=data.model_name,
        system_boundary=data.system_boundary,
        crediting_years=data.crediting_years,
        allocation_method=data.allocation_method,
        status="ACTIVE",
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.get("/facilities/{facility_id}/lca-models", response_model=List[PuroLCAModelResponse])
async def list_lca_models(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PuroLCAModel).where(PuroLCAModel.facility_id == facility_id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/lca-models/{lca_model_id}/entries", response_model=PuroLCIEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_lci_entry(
    lca_model_id: UUID,
    data: PuroLCIEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_m = select(PuroLCAModel).where(PuroLCAModel.id == lca_model_id)
    res_m = await db.execute(stmt_m)
    model = res_m.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LCA Model not found.")
    _check_org_access(current_user, model.organization_id)

    entry = PuroLCIEntry(
        organization_id=model.organization_id,
        lca_model_id=lca_model_id,
        category=data.category,
        item_name=data.item_name,
        quantity=Decimal(str(data.quantity)),
        unit=data.unit,
        emission_factor=Decimal(str(data.emission_factor)),
        ef_unit=data.ef_unit,
        ef_source=data.ef_source,
        ghg_emissions_tco2e=Decimal(str(data.ghg_emissions_tco2e)),
        notes=data.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/lca-models/{lca_model_id}/entries", response_model=List[PuroLCIEntryResponse])
async def list_lci_entries(
    lca_model_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PuroLCIEntry).where(PuroLCIEntry.lca_model_id == lca_model_id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/lca-models/{lca_model_id}/cutoff-decisions", response_model=PuroCutoffDecisionResponse, status_code=status.HTTP_201_CREATED)
async def create_cutoff_decision(
    lca_model_id: UUID,
    data: PuroCutoffDecisionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_m = select(PuroLCAModel).where(PuroLCAModel.id == lca_model_id)
    res_m = await db.execute(stmt_m)
    model = res_m.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LCA Model not found.")
    _check_org_access(current_user, model.organization_id)

    decision = PuroCutoffDecision(
        organization_id=model.organization_id,
        lca_model_id=lca_model_id,
        input_material_stream=data.input_material_stream,
        mass_energy_contribution_pct=data.mass_energy_contribution_pct,
        justified_reason=data.justified_reason,
        auditor_approved=data.auditor_approved,
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return decision


@router.get("/lca-models/{lca_model_id}/cutoff-decisions", response_model=List[PuroCutoffDecisionResponse])
async def list_cutoff_decisions(
    lca_model_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PuroCutoffDecision).where(PuroCutoffDecision.lca_model_id == lca_model_id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/production-runs/{production_run_id}/coproduct-allocations", response_model=PuroCoProductAllocationResponse, status_code=status.HTTP_201_CREATED)
async def create_coproduct_allocation(
    production_run_id: UUID,
    data: PuroCoProductAllocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_r = select(ProductionRun).where(ProductionRun.id == production_run_id)
    res_r = await db.execute(stmt_r)
    run = res_r.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production run not found.")
    _check_org_access(current_user, run.organization_id)

    alloc = PuroCoProductAllocation(
        organization_id=run.organization_id,
        production_run_id=production_run_id,
        co_product_record_id=data.co_product_record_id,
        allocation_basis="ENERGY_LHV",
        biochar_lhv_mj_kg=data.biochar_lhv_mj_kg,
        coproduct_lhv_mj_kg=data.coproduct_lhv_mj_kg,
        biochar_allocation_share_pct=data.biochar_allocation_share_pct,
        coproduct_allocation_share_pct=data.coproduct_allocation_share_pct,
        allocated_emissions_tco2e=Decimal(str(data.allocated_emissions_tco2e)),
        justification=data.justification,
    )
    db.add(alloc)
    await db.commit()
    await db.refresh(alloc)
    return alloc


# ---------------------------------------------------------------------------
# 8. Audits (Facility & Output)
# ---------------------------------------------------------------------------

@router.post("/facilities/{facility_id}/audits", response_model=PuroAuditWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    facility_id: UUID,
    data: PuroAuditWorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    audit = await PuroAuditManager.create_audit_workflow(
        db=db,
        organization_id=fac.organization_id,
        facility_id=facility_id,
        audit_type=data.audit_type,
        auditor_organization=data.auditor_organization,
        lead_auditor_name=data.lead_auditor_name,
        monitoring_period_id=data.monitoring_period_id,
        scheduled_date=data.scheduled_date,
    )
    return audit


@router.get("/facilities/{facility_id}/audits", response_model=List[PuroAuditWorkflowResponse])
async def list_audits(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    stmt_a = select(PuroAuditWorkflow).where(PuroAuditWorkflow.facility_id == facility_id).order_by(PuroAuditWorkflow.created_at.desc())
    res_a = await db.execute(stmt_a)
    return res_a.scalars().all()


# ---------------------------------------------------------------------------
# 9. Output Reports & Manifest Sealing
# ---------------------------------------------------------------------------

@router.post("/facilities/{facility_id}/output-reports", response_model=PuroOutputReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_output_report(
    facility_id: UUID,
    monitoring_period_id: str = Query(..., description="e.g. 2025-Q1"),
    crediting_period_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    report = await PuroOutputReportBuilder.build_and_seal_report(
        db=db,
        organization_id=fac.organization_id,
        facility_id=facility_id,
        monitoring_period_id=monitoring_period_id,
        crediting_period_id=crediting_period_id,
    )
    return report


@router.get("/facilities/{facility_id}/output-reports", response_model=List[PuroOutputReportResponse])
async def list_output_reports(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_f = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_f = await db.execute(stmt_f)
    fac = res_f.scalar_one_or_none()
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")

    _check_org_access(current_user, fac.organization_id)

    stmt_r = select(PuroOutputReport).where(PuroOutputReport.facility_id == facility_id).order_by(PuroOutputReport.created_at.desc())
    res_r = await db.execute(stmt_r)
    return res_r.scalars().all()


# ---------------------------------------------------------------------------
# 10. Registry Readiness
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/readiness", response_model=PuroRegistryReadinessResponse)
async def get_project_readiness(
    project_id: UUID,
    facility_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_p = select(Project).where(Project.id == project_id)
    res_p = await db.execute(stmt_p)
    proj = res_p.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    _check_org_access(current_user, proj.organization_id)

    return await PuroComplianceEngine.evaluate_registry_readiness(
        db=db,
        project_id=project_id,
        facility_id=facility_id,
    )
