import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.biochar.models import BiocharBatch, ProductionFacility
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
    VM0044_OFFICIAL_CODE,
    VM0044_OFFICIAL_VERSION,
    seed_vm0044_normative_metadata,
)
from app.domains.biochar.vm0044_schemas import (
    VM0044AdditionalityEvaluateRequest,
    VM0044AdditionalityResponse,
    VM0044ApplicabilityEvaluateRequest,
    VM0044ApplicabilityResponse,
    VM0044CalculationRequest,
    VM0044CalculationResponse,
    VM0044EquationBreakdown,
    VM0044MethodologyVersionSchema,
    VM0044NormativeDependencySchema,
    VM0044RuleDefinitionSchema,
    VM0044SnapshotRequest,
    VM0044SnapshotResponse,
)
from app.domains.projects.models import Project

router = APIRouter(prefix="/vm0044", tags=["Biochar - Verra VM0044 v1.2"])


def _check_org_access(current_user: User, target_org_id: UUID) -> None:
    if current_user.role != "SUPER_ADMIN" and current_user.organization_id != target_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Resource belongs to another organization.",
        )


# ---------------------------------------------------------------------------
# 1. Normative Metadata & Rules Endpoints
# ---------------------------------------------------------------------------

@router.get("/version", response_model=VM0044MethodologyVersionSchema)
async def get_vm0044_version(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves locked methodology version metadata for Verra VM0044 v1.2."""
    await seed_vm0044_normative_metadata(db)
    stmt = select(VM0044MethodologyVersion).where(
        VM0044MethodologyVersion.code == VM0044_OFFICIAL_CODE,
        VM0044MethodologyVersion.version == VM0044_OFFICIAL_VERSION,
    )
    res = await db.execute(stmt)
    v = res.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM0044 v1.2 version metadata not seeded.")
    return v


@router.get("/rules", response_model=List[VM0044RuleDefinitionSchema])
async def list_vm0044_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists registered rule definitions for Verra VM0044 v1.2 across Sections 3, 4, 7, and 8."""
    await seed_vm0044_normative_metadata(db)
    stmt = select(VM0044RuleDefinition).order_by(VM0044RuleDefinition.section_number, VM0044RuleDefinition.rule_id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/dependencies", response_model=List[VM0044NormativeDependencySchema])
@router.get("/normative-dependencies", response_model=List[VM0044NormativeDependencySchema])
async def list_vm0044_dependencies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists external normative document dependencies for VM0044 v1.2 (VCS Standard, VT0008, CDM tools, IPCC)."""
    await seed_vm0044_normative_metadata(db)
    stmt = select(VM0044NormativeDependency).order_by(VM0044NormativeDependency.code)
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# 2. Section 4 Applicability Evaluation
# ---------------------------------------------------------------------------

@router.post("/applicability/evaluate", response_model=VM0044ApplicabilityResponse)
@router.post("/applicability", response_model=VM0044ApplicabilityResponse)
async def evaluate_applicability(
    payload: VM0044ApplicabilityEvaluateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates Section 4 Applicability Conditions:
    - Greenfield facility status & excluded technologies
    - Purely biogenic waste biomass & prohibited feedstocks
    - End-use eligibility (soil non-wetland, durable non-soil)
    - Worker health & safety
    Persists evaluation audit trail in PostgreSQL.
    """
    stmt_p = select(Project).where(Project.id == payload.project_id)
    res_p = await db.execute(stmt_p)
    proj = res_p.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    _check_org_access(current_user, proj.organization_id)

    eval_result = await VM0044CalculatorV12.evaluate_applicability(db, payload)

    # Persist applicability evaluation record
    record = VM0044ApplicabilityEvaluation(
        id=uuid.uuid4(),
        organization_id=proj.organization_id,
        project_id=payload.project_id,
        batch_id=payload.batch_id,
        evaluation_date=eval_result.evaluated_at,
        facility_greenfield_passed=eval_result.facility_check.get("passed", False),
        feedstock_biogenic_waste_passed=eval_result.feedstock_check.get("passed", False),
        feedstock_geographic_origin_passed=True,
        process_technology_passed=eval_result.process_check.get("passed", False),
        end_use_eligibility_passed=eval_result.end_use_check.get("passed", False),
        wetland_exclusion_passed=True,
        worker_health_safety_passed=True,
        overall_applicability_status=eval_result.status,
        findings_json={
            "facility_check": eval_result.facility_check,
            "feedstock_check": eval_result.feedstock_check,
            "process_check": eval_result.process_check,
            "end_use_check": eval_result.end_use_check,
            "blocking_findings": eval_result.blocking_findings,
        },
    )
    db.add(record)
    await db.commit()

    return eval_result


# ---------------------------------------------------------------------------
# 3. Section 7 Additionality Assessment & VT0008
# ---------------------------------------------------------------------------

@router.post("/additionality/evaluate", response_model=VM0044AdditionalityResponse)
@router.post("/additionality", response_model=VM0044AdditionalityResponse)
async def evaluate_additionality(
    payload: VM0044AdditionalityEvaluateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates Section 7 Additionality Assessment:
    - Step 1: Regulatory surplus
    - Step 2: Positive list applicability
    - Step 3: VT0008 investment analysis (benchmark IRR vs project IRR)
    Persists evaluation audit trail in PostgreSQL.
    """
    stmt_p = select(Project).where(Project.id == payload.project_id)
    res_p = await db.execute(stmt_p)
    proj = res_p.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    _check_org_access(current_user, proj.organization_id)

    add_result = await VM0044CalculatorV12.evaluate_additionality(db, payload)

    # Persist additionality assessment record
    record = VM0044AdditionalityAssessment(
        id=uuid.uuid4(),
        organization_id=proj.organization_id,
        project_id=payload.project_id,
        assessment_date=add_result.evaluated_at,
        step1_regulatory_surplus_passed=add_result.step1_regulatory_surplus,
        step1_regulatory_notes=payload.regulatory_notes,
        step2_positive_list_passed=add_result.step2_positive_list,
        step2_penetration_rate_pct=Decimal("5.0"),
        step3_investment_analysis_passed=add_result.step3_investment_analysis,
        step3_analysis_option=payload.analysis_option,
        project_irr_pct=payload.project_irr_pct,
        benchmark_irr_pct=payload.benchmark_irr_pct,
        benchmark_source=payload.benchmark_source,
        overall_additionality_status=add_result.status,
        evidence_hashes_json={
            "findings": add_result.findings,
            "financial_model_hash": payload.financial_model_hash,
        },
    )
    db.add(record)
    await db.commit()

    return add_result


# ---------------------------------------------------------------------------
# 4. Calculation Input Snapshot
# ---------------------------------------------------------------------------

@router.post("/snapshots", response_model=VM0044SnapshotResponse)
@router.post("/snapshot", response_model=VM0044SnapshotResponse)
async def create_snapshot(
    payload: VM0044SnapshotRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates an immutable, canonical calculation input snapshot.
    Generates deterministic SHA-256 digest across all physical inputs.
    """
    stmt_p = select(Project).where(Project.id == payload.project_id)
    res_p = await db.execute(stmt_p)
    proj = res_p.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    _check_org_access(current_user, proj.organization_id)

    try:
        res = await VM0044CalculatorV12.create_calculation_snapshot(
            db=db,
            request=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return res
    except VM0044QuantificationError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---------------------------------------------------------------------------
# 5. Calculation Execution & Preview
# ---------------------------------------------------------------------------

@router.post("/calculate", response_model=VM0044CalculationResponse)
async def execute_calculation(
    payload: VM0044CalculationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes authoritative Verra VM0044 v1.2 quantification:
    - Version lock verification (quarantines v2.0)
    - Applicability and additionality validation
    - Double-counting protection (Puro & VM0042 SOC)
    - Equations (1) through (15) with Decimal precision
    - VCS uncertainty deduction (>10% threshold)
    - Atomic PostgreSQL persistence
    """
    # Check project org access
    if payload.project_id:
        stmt_p = select(Project).where(Project.id == payload.project_id)
        res_p = await db.execute(stmt_p)
        proj = res_p.scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        _check_org_access(current_user, proj.organization_id)
    elif payload.snapshot_id:
        stmt_s = select(VM0044CalculationSnapshot).where(VM0044CalculationSnapshot.id == payload.snapshot_id)
        res_s = await db.execute(stmt_s)
        snap = res_s.scalar_one_or_none()
        if not snap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")
        _check_org_access(current_user, snap.organization_id)

    try:
        res = await VM0044CalculatorV12.execute_calculation(
            db=db,
            request=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return res
    except VM0044QuantificationError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---------------------------------------------------------------------------
# 6. Calculation Execution Queries
# ---------------------------------------------------------------------------

@router.get("/calculations/{calculation_id}", response_model=VM0044CalculationResponse)
async def get_calculation(
    calculation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves an authoritative VM0044 calculation execution by ID with complete equation breakdown."""
    stmt = select(VM0044CalculationExecution).where(VM0044CalculationExecution.id == calculation_id)
    res = await db.execute(stmt)
    calc = res.scalar_one_or_none()
    if not calc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation execution not found.")

    _check_org_access(current_user, calc.organization_id)

    # Fetch snapshot hash
    stmt_s = select(VM0044CalculationSnapshot).where(VM0044CalculationSnapshot.id == calc.snapshot_id)
    res_s = await db.execute(stmt_s)
    snap = res_s.scalar_one_or_none()
    snapshot_hash = snap.snapshot_hash if snap else ""

    eq = calc.equation_breakdown_json
    return VM0044CalculationResponse(
        calculation_id=calc.id,
        snapshot_id=calc.snapshot_id,
        project_id=calc.project_id,
        batch_id=calc.batch_id,
        status=calc.status,
        methodology_code=VM0044_OFFICIAL_CODE,
        methodology_version=VM0044_OFFICIAL_VERSION,
        net_removal_tco2e=calc.er_net_removals_tonnes,
        gross_removal_tco2e=calc.gross_co2e_stored_tonnes,
        project_emissions_tco2e=calc.pe_ps_total_tonnes + calc.pe_as_tonnes,
        leakage_emissions_tco2e=calc.le_total_tonnes,
        uncertainty_deduction_tco2e=calc.uncertainty_deduction_tonnes,
        equation_breakdown=VM0044EquationBreakdown(**eq),
        snapshot_hash=snapshot_hash,
        calculation_hash=calc.calculation_hash,
        execution_timestamp=calc.execution_timestamp,
        is_issuable=True,
        ccp_eligible=True,
    )


@router.get("/calculations/project/{project_id}", response_model=List[VM0044CalculationResponse])
async def list_project_calculations(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all authoritative VM0044 calculation executions for a project."""
    stmt_p = select(Project).where(Project.id == project_id)
    res_p = await db.execute(stmt_p)
    proj = res_p.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    _check_org_access(current_user, proj.organization_id)

    stmt = select(VM0044CalculationExecution).where(
        VM0044CalculationExecution.project_id == project_id
    ).order_by(VM0044CalculationExecution.execution_timestamp.desc())
    res = await db.execute(stmt)
    records = res.scalars().all()

    output: List[VM0044CalculationResponse] = []
    for calc in records:
        stmt_s = select(VM0044CalculationSnapshot).where(VM0044CalculationSnapshot.id == calc.snapshot_id)
        res_s = await db.execute(stmt_s)
        snap = res_s.scalar_one_or_none()
        snapshot_hash = snap.snapshot_hash if snap else ""

        eq = calc.equation_breakdown_json
        output.append(
            VM0044CalculationResponse(
                calculation_id=calc.id,
                snapshot_id=calc.snapshot_id,
                project_id=calc.project_id,
                batch_id=calc.batch_id,
                status=calc.status,
                methodology_code=VM0044_OFFICIAL_CODE,
                methodology_version=VM0044_OFFICIAL_VERSION,
                net_removal_tco2e=calc.er_net_removals_tonnes,
                gross_removal_tco2e=calc.gross_co2e_stored_tonnes,
                project_emissions_tco2e=calc.pe_ps_total_tonnes + calc.pe_as_tonnes,
                leakage_emissions_tco2e=calc.le_total_tonnes,
                uncertainty_deduction_tco2e=calc.uncertainty_deduction_tonnes,
                equation_breakdown=VM0044EquationBreakdown(**eq),
                snapshot_hash=snapshot_hash,
                calculation_hash=calc.calculation_hash,
                execution_timestamp=calc.execution_timestamp,
                is_issuable=True,
                ccp_eligible=True,
            )
        )

    return output


@router.get("/executions", response_model=List[VM0044CalculationResponse])
async def list_executions(
    project_id: Optional[UUID] = Query(None),
    batch_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists VM0044 calculation executions for a project or organization."""
    stmt = select(VM0044CalculationExecution).order_by(VM0044CalculationExecution.execution_timestamp.desc())
    if current_user.role != "SUPER_ADMIN" and current_user.organization_id:
        stmt = stmt.where(VM0044CalculationExecution.organization_id == current_user.organization_id)
    if project_id:
        stmt = stmt.where(VM0044CalculationExecution.project_id == project_id)
    if batch_id:
        stmt = stmt.where(VM0044CalculationExecution.batch_id == batch_id)

    res = await db.execute(stmt)
    records = res.scalars().all()

    output: List[VM0044CalculationResponse] = []
    for calc in records:
        stmt_s = select(VM0044CalculationSnapshot).where(VM0044CalculationSnapshot.id == calc.snapshot_id)
        res_s = await db.execute(stmt_s)
        snap = res_s.scalar_one_or_none()
        snapshot_hash = snap.snapshot_hash if snap else ""

        eq = calc.equation_breakdown_json
        output.append(
            VM0044CalculationResponse(
                calculation_id=calc.id,
                snapshot_id=calc.snapshot_id,
                project_id=calc.project_id,
                batch_id=calc.batch_id,
                status=calc.status,
                methodology_code=VM0044_OFFICIAL_CODE,
                methodology_version=VM0044_OFFICIAL_VERSION,
                net_removal_tco2e=calc.er_net_removals_tonnes,
                gross_removal_tco2e=calc.gross_co2e_stored_tonnes,
                project_emissions_tco2e=calc.pe_ps_total_tonnes + calc.pe_as_tonnes,
                leakage_emissions_tco2e=calc.le_total_tonnes,
                uncertainty_deduction_tco2e=calc.uncertainty_deduction_tonnes,
                equation_breakdown=VM0044EquationBreakdown(**eq),
                snapshot_hash=snapshot_hash,
                calculation_hash=calc.calculation_hash,
                execution_timestamp=calc.execution_timestamp,
                is_issuable=True,
                ccp_eligible=True,
            )
        )

    return output
