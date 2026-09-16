import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharLabAnalysis,
    FeedstockLot,
    FeedstockSource,
    ProductionFacility,
)
from app.domains.biochar.puro_models import (
    PuroAdditionalityAssessment,
    PuroAuditFinding,
    PuroAuditWorkflow,
    PuroBaselineAssessment,
    PuroBiomassSourceDeclaration,
    PuroCalculationExecution,
    PuroComplianceEvaluation,
    PuroCreditingPeriod,
    PuroEndUseCategory,
    PuroEndUseRecordLink,
    PuroFacilityProfile,
    PuroMethodologyVersion,
    PuroMonitoringPlan,
    PuroNormativeDependency,
    PuroOutputReport,
    PuroQualityControlPlan,
    PuroRuleDefinition,
    PuroSamplingPlan,
    PuroSupplierProfile,
)
from app.domains.biochar.puro_schemas import PuroRegistryReadinessResponse
from app.domains.ledger.service import HashGenerator, _get_platform_keypair
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


class PuroComplianceEngine:
    """
    Puro.earth Biochar Edition 2025 V2 Methodology Compliance & Registry Readiness Engine.
    Evaluates rule-level requirements and identifies authoritative blockers.
    """

    @staticmethod
    async def evaluate_registry_readiness(
        db: AsyncSession,
        project_id: UUID,
        facility_id: Optional[UUID] = None,
    ) -> PuroRegistryReadinessResponse:
        now = datetime.now(timezone.utc)
        blockers: List[str] = []
        unresolved_deps: List[str] = []

        # 1. Check Normative Dependencies
        stmt_deps = select(PuroNormativeDependency).where(
            PuroNormativeDependency.implementation_state == "DEPENDENCY_REQUIRED"
        )
        res_deps = await db.execute(stmt_deps)
        unverified_deps = res_deps.scalars().all()
        for dep in unverified_deps:
            unresolved_deps.append(f"{dep.code}: {dep.title} (Verification Required)")
            blockers.append(f"NORMATIVE_DEPENDENCY_UNVERIFIED:{dep.code}")

        # 2. Check Facility Existence & Classification
        stmt_fac = select(ProductionFacility).where(ProductionFacility.project_id == project_id)
        if facility_id:
            stmt_fac = stmt_fac.where(ProductionFacility.id == facility_id)
        res_fac = await db.execute(stmt_fac)
        facility = res_fac.scalars().first()

        if not facility:
            blockers.append("FACILITY_REGISTRATION_MISSING")
            return PuroRegistryReadinessResponse(
                project_id=project_id,
                facility_id=facility_id,
                methodology_code="PURO_BIOCHAR_2025_V2",
                readiness_state="BLOCKED",
                overall_capability_status="BLOCKED",
                active_blockers=blockers,
                unresolved_dependencies=unresolved_deps,
                audit_readiness_status="NOT_READY",
                quantification_status="NOT_CONFIGURED",
                issuance_status="NOT_ISSUED",
                corc_point_verified_batches_count=0,
                total_eligible_batches_count=0,
                evaluated_at=now,
            )

        # 3. Check Puro Facility Profile (Stationary vs Mobile)
        stmt_prof = select(PuroFacilityProfile).where(PuroFacilityProfile.facility_id == facility.id)
        res_prof = await db.execute(stmt_prof)
        facility_profile = res_prof.scalar_one_or_none()
        if not facility_profile:
            blockers.append("FACILITY_CLASSIFICATION_INCOMPLETE")

        # 4. Check Supplier Profile & Exclusive Rights (Double Claim Protection)
        stmt_supp = select(PuroSupplierProfile).where(PuroSupplierProfile.facility_id == facility.id)
        res_supp = await db.execute(stmt_supp)
        supplier_profile = res_supp.scalar_one_or_none()
        if not supplier_profile or supplier_profile.claim_rights_status != "EXCLUSIVE_CLAIM_RIGHTS_ESTABLISHED":
            blockers.append("SUPPLIER_RIGHTS_INCOMPLETE")

        # 5. Check Baseline Scenario Assessment
        stmt_base = select(PuroBaselineAssessment).where(PuroBaselineAssessment.facility_id == facility.id)
        res_base = await db.execute(stmt_base)
        baseline = res_base.scalar_one_or_none()
        if not baseline or not baseline.is_locked:
            blockers.append("BASELINE_INCOMPLETE")

        # 6. Check Three-Pillar Additionality Assessment
        stmt_add = select(PuroAdditionalityAssessment).where(PuroAdditionalityAssessment.facility_id == facility.id)
        res_add = await db.execute(stmt_add)
        additionality = res_add.scalar_one_or_none()
        if not additionality or additionality.overall_status != "PASS":
            blockers.append("ADDITIONALITY_INCOMPLETE")

        # 7. Check Monitoring Plan Validation
        stmt_mp = select(PuroMonitoringPlan).where(
            PuroMonitoringPlan.facility_id == facility.id,
            PuroMonitoringPlan.status == "VALIDATED",
        )
        res_mp = await db.execute(stmt_mp)
        monitoring_plan = res_mp.scalar_one_or_none()
        if not monitoring_plan:
            blockers.append("MONITORING_PLAN_NOT_VALIDATED")

        # 8. Check Batches, Lab Analyses, and End-Use Records
        stmt_batches = select(BiocharBatch).where(BiocharBatch.project_id == project_id)
        res_batches = await db.execute(stmt_batches)
        batches = res_batches.scalars().all()

        total_batches = len(batches)
        eligible_batches_count = 0
        corc_point_verified_count = 0

        for b in batches:
            # Check lab analysis
            stmt_lab = select(BiocharLabAnalysis).where(BiocharLabAnalysis.batch_id == b.id)
            res_lab = await db.execute(stmt_lab)
            labs = res_lab.scalars().all()
            if not labs or any(l.molar_h_c_ratio > 0.70 for l in labs):
                blockers.append(f"LAB_DATA_INCOMPLETE_OR_INELIGIBLE:Batch-{b.batch_number}")
                continue

            # Check Table 3.2 End Use link
            stmt_link = select(PuroEndUseRecordLink).where(
                PuroEndUseRecordLink.batch_id == b.id,
                PuroEndUseRecordLink.corc_point_reached == "CORC_POINT_ELIGIBLE",
            )
            res_link = await db.execute(stmt_link)
            links = res_link.scalars().all()
            if not links:
                blockers.append(f"END_USE_UNPROVEN:Batch-{b.batch_number}")
                continue

            eligible_batches_count += 1
            corc_point_verified_count += 1

        # 9. Check Facility Audit Workflow Status
        stmt_fa = select(PuroAuditWorkflow).where(
            PuroAuditWorkflow.facility_id == facility.id,
            PuroAuditWorkflow.audit_type == "PRODUCTION_FACILITY_AUDIT",
            PuroAuditWorkflow.audit_status == "PASSED",
        )
        res_fa = await db.execute(stmt_fa)
        passed_fa = res_fa.scalar_one_or_none()
        if not passed_fa:
            blockers.append("FACILITY_AUDIT_REQUIRED")

        # 10. Check Open Audit Non-Conformities
        stmt_find = select(PuroAuditFinding).join(PuroAuditWorkflow).where(
            PuroAuditWorkflow.facility_id == facility.id,
            PuroAuditFinding.status == "OPEN",
        )
        res_find = await db.execute(stmt_find)
        open_findings = res_find.scalars().all()
        if open_findings:
            blockers.append(f"OPEN_NONCONFORMITY_COUNT:{len(open_findings)}")

        # Determine Readiness State
        if not blockers and not unresolved_deps:
            readiness_state = "READY_FOR_REGISTRY_SUBMISSION"
            capability_status = "PRODUCTION_READY"
            audit_status = "AUDIT_COMPLETE"
            quant_status = "CONFIGURED_AND_VERIFIED"
        elif "FACILITY_AUDIT_REQUIRED" in blockers or any("NORMATIVE_DEPENDENCY" in b for b in blockers):
            readiness_state = "IN_PROGRESS"
            capability_status = "PRODUCTION_READY_WITH_LIMITATION"
            audit_status = "READY_FOR_AUDIT" if "FACILITY_AUDIT_REQUIRED" in blockers else "IN_PROGRESS"
            quant_status = "CALCULATOR_AVAILABLE"
        else:
            readiness_state = "BLOCKED"
            capability_status = "PRODUCTION_READY_WITH_LIMITATION"
            audit_status = "BLOCKED"
            quant_status = "DATA_REQUIRED"

        return PuroRegistryReadinessResponse(
            project_id=project_id,
            facility_id=facility.id,
            methodology_code="PURO_BIOCHAR_2025_V2",
            readiness_state=readiness_state,
            overall_capability_status=capability_status,
            active_blockers=list(set(blockers)),
            unresolved_dependencies=unresolved_deps,
            audit_readiness_status=audit_status,
            quantification_status=quant_status,
            issuance_status="NOT_ISSUED",
            corc_point_verified_batches_count=corc_point_verified_count,
            total_eligible_batches_count=eligible_batches_count,
            evaluated_at=now,
        )


class PuroAuditManager:
    """
    Manages Puro Production Facility Audit and Output Audit workflows.
    """

    @staticmethod
    async def create_audit_workflow(
        db: AsyncSession,
        organization_id: UUID,
        facility_id: UUID,
        audit_type: str,
        auditor_organization: str,
        lead_auditor_name: Optional[str] = None,
        monitoring_period_id: Optional[str] = None,
        scheduled_date: Optional[date] = None,
    ) -> PuroAuditWorkflow:
        workflow = PuroAuditWorkflow(
            organization_id=organization_id,
            facility_id=facility_id,
            audit_type=audit_type,
            auditor_organization=auditor_organization,
            lead_auditor_name=lead_auditor_name,
            monitoring_period_id=monitoring_period_id,
            audit_status="AUDIT_SCHEDULED" if scheduled_date else "READY_FOR_AUDIT",
            scheduled_date=scheduled_date,
        )
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)
        return workflow

    @staticmethod
    async def log_audit_finding(
        db: AsyncSession,
        audit_id: UUID,
        rule_ref: str,
        finding_type: str,
        description: str,
        evidence_ref: Optional[str] = None,
        response_due_date: Optional[date] = None,
    ) -> PuroAuditFinding:
        finding = PuroAuditFinding(
            audit_id=audit_id,
            rule_ref=rule_ref,
            finding_type=finding_type,
            description=description,
            evidence_ref=evidence_ref,
            status="OPEN",
            response_due_date=response_due_date,
        )
        db.add(finding)
        await db.commit()
        await db.refresh(finding)
        return finding

    @staticmethod
    async def resolve_audit_finding(
        db: AsyncSession,
        finding_id: UUID,
        evidence_of_closure_ref: str,
    ) -> PuroAuditFinding:
        stmt = select(PuroAuditFinding).where(PuroAuditFinding.id == finding_id)
        res = await db.execute(stmt)
        finding = res.scalar_one_or_none()
        if not finding:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

        finding.status = "CLOSED"
        finding.closed_at = datetime.now(timezone.utc)
        finding.evidence_ref = evidence_of_closure_ref
        await db.commit()
        await db.refresh(finding)
        return finding


class PuroOutputReportBuilder:
    """
    Builds and cryptographically seals Puro Output Reports & CORC packages.
    """

    @staticmethod
    async def build_and_seal_report(
        db: AsyncSession,
        organization_id: UUID,
        facility_id: UUID,
        monitoring_period_id: str,
        crediting_period_id: Optional[UUID] = None,
    ) -> PuroOutputReport:
        # Fetch facility
        stmt_fac = select(ProductionFacility).where(ProductionFacility.id == facility_id)
        res_fac = await db.execute(stmt_fac)
        fac = res_fac.scalar_one_or_none()
        if not fac:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")

        # Fetch calculation executions for this facility and period (strictly authoritative and active)
        stmt_calcs = select(PuroCalculationExecution).where(
            PuroCalculationExecution.facility_id == facility_id,
            PuroCalculationExecution.calculation_status == "SUCCESS",
            PuroCalculationExecution.calculation_mode == "AUTHORITATIVE",
            PuroCalculationExecution.superseded_at.is_(None),
        )
        res_calcs = await db.execute(stmt_calcs)
        calcs = res_calcs.scalars().all()

        total_mass = sum(Decimal(str(c.eligible_dry_biochar_mass_tonnes)) for c in calcs)
        total_corcs = sum(Decimal(str(c.final_corcs_issuable)) for c in calcs)

        report_num = f"PUR-REP-{fac.facility_code}-{monitoring_period_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

        manifest = {
            "report_number": report_num,
            "facility_id": str(fac.id),
            "facility_name": fac.facility_name,
            "monitoring_period_id": monitoring_period_id,
            "crediting_period_id": str(crediting_period_id) if crediting_period_id else None,
            "methodology": "PURO_BIOCHAR_2025_V2",
            "total_eligible_biochar_mass_tonnes": f"{total_mass:.6f}",
            "total_net_corcs": f"{total_corcs:.6f}",
            "calculation_count": len(calcs),
            "calculations": [
                {
                    "batch_id": str(c.batch_id),
                    "c_stored": f"{Decimal(str(c.c_stored_tco2e)):.6f}",
                    "c_loss": f"{Decimal(str(c.c_loss_tco2e)):.6f}",
                    "e_project": f"{Decimal(str(c.e_project_tco2e)):.6f}",
                    "final_corcs": f"{Decimal(str(c.final_corcs_issuable)):.6f}",
                    "calc_hash": c.calculation_hash,
                }
                for c in calcs
            ],
            "sealed_at": datetime.now(timezone.utc).isoformat(),
        }

        manifest_hash = HashGenerator.generate_canonical_hash(manifest)

        report = PuroOutputReport(
            organization_id=organization_id,
            facility_id=facility_id,
            crediting_period_id=crediting_period_id,
            monitoring_period_id=monitoring_period_id,
            report_number=report_num,
            report_version=1,
            report_status="AUDITED_SEALED",
            total_eligible_biochar_mass_tonnes=total_mass,
            total_net_corcs=total_corcs,
            manifest_json=manifest,
            manifest_hash=manifest_hash,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report
