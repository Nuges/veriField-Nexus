import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.biochar.models import (
    BiocharBatch,
    FeedstockLot,
    FeedstockRunAllocation,
    FeedstockSource,
    ProductionFacility,
    ProductionRun,
)
from app.domains.biochar.puro_models import (
    PuroBiomassSourceDeclaration,
    PuroCounterfactualStorageAssessment,
    PuroCreditingPeriod,
)
from app.domains.biochar.puro_rules import (
    OFFICIAL_PURO_BIOMASS_SOURCING_V1_3,
    PURO_MATERIAL_STORAGE_FATES,
    PURO_NEGLIGIBLE_STORAGE_FATES,
    PURO_PERMITTED_FEEDSTOCK_CATEGORIES,
    PURO_PROHIBITED_FEEDSTOCK_CATEGORIES,
    evaluate_biomass_sourcing_applicability,
    resolve_puro_standard_configuration,
)


class PuroBiomassSourcingEngine:
    """
    Puro Biomass Sourcing Criteria Engine (v1.3 & Transitional).
    Evaluates feedstock classification, legality, chain of custody, contamination exclusion,
    and cross-tenant/cross-facility isolation.
    """

    @staticmethod
    def evaluate_feedstock_source(
        source: FeedstockSource,
        declaration: Optional[PuroBiomassSourceDeclaration],
        criteria_version: str = "1.3",
        reference_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        blockers: List[str] = []
        now = datetime.now(timezone.utc)
        ref_d = reference_date or now.date()

        # 1. Prohibited Categories Check
        source_type = (source.source_type or "").upper().strip()
        biomass_type = (source.biomass_type or "").upper().strip()

        if source_type in PURO_PROHIBITED_FEEDSTOCK_CATEGORIES or biomass_type in PURO_PROHIBITED_FEEDSTOCK_CATEGORIES:
            return {
                "status": "NON_COMPLIANT",
                "is_eligible": False,
                "reason_code": "PROHIBITED_FEEDSTOCK_CATEGORY",
                "category": source_type,
                "criteria_version": criteria_version,
                "blockers": [f"Feedstock category '{source_type}' is strictly prohibited under Puro Biomass Sourcing Criteria."],
                "notes": "Prohibited feedstock identified; fails closed.",
                "evaluated_at": now,
            }

        # 2. Permitted Categories Check
        if source_type not in PURO_PERMITTED_FEEDSTOCK_CATEGORIES:
            blockers.append(f"Feedstock category '{source_type}' is not recognized under permitted categories.")

        # 3. Declaration Existence and Validity
        if not declaration:
            return {
                "status": "DATA_REQUIRED",
                "is_eligible": False,
                "reason_code": "SOURCING_DECLARATION_MISSING",
                "category": source_type,
                "criteria_version": criteria_version,
                "blockers": [f"Source {source.source_code} has no registered PuroBiomassSourceDeclaration."],
                "notes": "Biomass source declaration is required before authoritative crediting.",
                "evaluated_at": now,
            }

        if not declaration.is_active:
            blockers.append(f"Source declaration {declaration.source_declaration_code} is marked inactive.")

        if declaration.declared_validity_start and ref_d < declaration.declared_validity_start:
            blockers.append(f"Declaration not yet valid (start: {declaration.declared_validity_start}, ref: {ref_d}).")

        if declaration.declared_validity_end and ref_d > declaration.declared_validity_end:
            blockers.append(f"Declaration expired on {declaration.declared_validity_end} (ref: {ref_d}).")

        # 4. Chain of Custody & Origin
        if not source.origin_location and not source.metadata_json.get("origin_coordinates"):
            blockers.append("Feedstock origin location is unspecified.")

        # 5. Result Synthesis
        is_eligible = len(blockers) == 0
        status_code = "COMPLIANT" if is_eligible else "NON_COMPLIANT"
        reason_code = "SOURCING_CRITERIA_SATISFIED" if is_eligible else "SOURCING_CRITERIA_FAILED"

        return {
            "status": status_code,
            "is_eligible": is_eligible,
            "reason_code": reason_code,
            "category": declaration.puro_category_ref or source_type,
            "criteria_version": criteria_version,
            "source_code": source.source_code,
            "declaration_code": declaration.source_declaration_code,
            "sustainability_scheme": declaration.sustainability_certification_scheme,
            "risk_classification": declaration.risk_classification,
            "blockers": blockers,
            "notes": "Biomass source verified against Puro Sourcing Criteria." if is_eligible else f"Blockers: {'; '.join(blockers)}",
            "evaluated_at": now,
        }

    @classmethod
    async def evaluate_batch_sourcing_compliance(
        cls,
        db: AsyncSession,
        batch: BiocharBatch,
        organization_id: UUID,
        reference_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Traces batch -> production run -> feedstock run allocations -> feedstock lots -> feedstock sources -> declarations.
        Enforces tenant isolation and criteria compliance.
        """
        now = datetime.now(timezone.utc)
        blockers: List[str] = []
        sources_found: List[Dict[str, Any]] = []

        # Enforce organization ownership
        if batch.organization_id and batch.organization_id != organization_id:
            return {
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "is_compliant": False,
                "compliance_state": "FAILED",
                "criteria_version": OFFICIAL_PURO_BIOMASS_SOURCING_V1_3,
                "reason_code": "TENANT_MISMATCH",
                "blockers": ["Cross-tenant batch access prohibited."],
                "feedstock_sources": [],
                "sourcing_evaluation": {},
                "evaluated_at": now,
            }

        ref_d = reference_date or (batch.created_at.date() if batch.created_at else now.date())

        # Collect lots used in batch
        lots: List[FeedstockLot] = []

        if batch.production_run_id:
            stmt_alloc = (
                select(FeedstockLot)
                .join(FeedstockRunAllocation, FeedstockRunAllocation.lot_id == FeedstockLot.id)
                .where(FeedstockRunAllocation.production_run_id == batch.production_run_id)
            )
            res_alloc = await db.execute(stmt_alloc)
            lots.extend(res_alloc.scalars().all())

        # Also check direct lot association if present in metadata
        direct_lot_id = batch.metadata_json.get("feedstock_lot_id")
        if direct_lot_id:
            if isinstance(direct_lot_id, str):
                try:
                    direct_lot_id = UUID(direct_lot_id)
                except Exception:
                    pass
            stmt_direct = select(FeedstockLot).where(FeedstockLot.id == direct_lot_id)
            res_direct = await db.execute(stmt_direct)
            direct_lot = res_direct.scalar_one_or_none()
            if direct_lot and direct_lot not in lots:
                lots.append(direct_lot)

        if not lots:
            # Fallback: check if source is declared directly in batch metadata
            direct_source_id = batch.metadata_json.get("feedstock_source_id")
            if direct_source_id:
                if isinstance(direct_source_id, str):
                    try:
                        direct_source_id = UUID(direct_source_id)
                    except Exception:
                        pass
                stmt_s = select(FeedstockSource).where(
                    FeedstockSource.id == direct_source_id,
                    FeedstockSource.organization_id == organization_id,
                )
                res_s = await db.execute(stmt_s)
                direct_src = res_s.scalar_one_or_none()
                if direct_src:
                    # Evaluate declaration
                    stmt_decl = select(PuroBiomassSourceDeclaration).where(
                        PuroBiomassSourceDeclaration.feedstock_source_id == direct_src.id,
                        PuroBiomassSourceDeclaration.organization_id == organization_id,
                    )
                    res_decl = await db.execute(stmt_decl)
                    decl = res_decl.scalars().first()
                    eval_res = cls.evaluate_feedstock_source(direct_src, decl, reference_date=ref_d)
                    sources_found.append(eval_res)
                    if not eval_res["is_eligible"]:
                        blockers.extend(eval_res["blockers"])
            else:
                blockers.append("No traceable feedstock lot or source allocation mapped to this batch.")
        else:
            for lot in lots:
                # Enforce tenant isolation on lot
                if lot.organization_id != organization_id:
                    blockers.append(f"Feedstock lot {lot.lot_number} belongs to another tenant.")
                    continue

                stmt_src = select(FeedstockSource).where(
                    FeedstockSource.id == lot.source_id,
                    FeedstockSource.organization_id == organization_id,
                )
                res_src = await db.execute(stmt_src)
                src = res_src.scalar_one_or_none()
                if not src:
                    blockers.append(f"Feedstock lot {lot.lot_number} has no valid feedstock source in tenant.")
                    continue

                stmt_decl = select(PuroBiomassSourceDeclaration).where(
                    PuroBiomassSourceDeclaration.feedstock_source_id == src.id,
                    PuroBiomassSourceDeclaration.organization_id == organization_id,
                )
                res_decl = await db.execute(stmt_decl)
                decl = res_decl.scalars().first()

                eval_res = cls.evaluate_feedstock_source(src, decl, reference_date=ref_d)
                sources_found.append({
                    "lot_number": lot.lot_number,
                    "dry_mass_tonnes": float(lot.dry_mass_tonnes or 0.0),
                    **eval_res,
                })
                if not eval_res["is_eligible"]:
                    blockers.extend(eval_res["blockers"])

        is_compliant = len(blockers) == 0 and len(sources_found) > 0
        state = "COMPLIANT" if is_compliant else ("INCOMPLETE" if not sources_found else "FAILED")

        return {
            "batch_id": batch.id,
            "batch_number": batch.batch_number,
            "is_compliant": is_compliant,
            "compliance_state": state,
            "criteria_version": OFFICIAL_PURO_BIOMASS_SOURCING_V1_3,
            "feedstock_sources": sources_found,
            "blockers": blockers,
            "sourcing_evaluation": {
                "total_sources_evaluated": len(sources_found),
                "compliant_sources": sum(1 for s in sources_found if s.get("is_eligible")),
            },
            "evaluated_at": now,
        }


class PuroCounterfactualService:
    """
    Biomass Counterfactual Storage Service (Puro Biomass Sourcing Criteria v1.3 Section 3).
    Evaluates:
    - Path A: Negligible storage (requires verified evidence). Deduction = 0.
    - Path B: Material storage (requires quantified storage). Deduction = C_counterfactual.
    """

    @staticmethod
    def evaluate_counterfactual(
        assessment: Optional[PuroCounterfactualStorageAssessment],
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)

        if not assessment:
            return {
                "status": "DATA_REQUIRED",
                "is_compliant": False,
                "counterfactual_path": None,
                "baseline_fate": None,
                "deductible_counterfactual_tco2e": Decimal("0.0"),
                "reason_code": "PURO_COUNTERFACTUAL_ASSESSMENT_REQUIRED",
                "notes": "No counterfactual storage assessment registered. Fails closed.",
                "evaluated_at": now,
            }

        path = (assessment.counterfactual_path or "").upper().strip()
        fate = (assessment.baseline_fate or "").upper().strip()
        ev_status = (assessment.evidence_status or "").upper().strip()

        if path == "PATH_A_NEGLIGIBLE_STORAGE":
            # Must be an authorized negligible-storage fate
            if fate not in PURO_NEGLIGIBLE_STORAGE_FATES:
                return {
                    "status": "NON_COMPLIANT",
                    "is_compliant": False,
                    "counterfactual_path": path,
                    "baseline_fate": fate,
                    "deductible_counterfactual_tco2e": Decimal("0.0"),
                    "reason_code": "PURO_INVALID_NEGLIGIBLE_FATE",
                    "notes": f"Baseline fate '{fate}' is not eligible for Path A negligible storage.",
                    "evaluated_at": now,
                }

            # Must have verified evidence
            if ev_status != "VERIFIED":
                return {
                    "status": "EVIDENCE_REQUIRED",
                    "is_compliant": False,
                    "counterfactual_path": path,
                    "baseline_fate": fate,
                    "deductible_counterfactual_tco2e": Decimal("0.0"),
                    "reason_code": "PURO_COUNTERFACTUAL_EVIDENCE_REQUIRED",
                    "notes": f"Path A negligible storage requires VERIFIED evidence. Current status: '{ev_status}'.",
                    "evaluated_at": now,
                }

            return {
                "status": "COMPLIANT",
                "is_compliant": True,
                "counterfactual_path": path,
                "baseline_fate": fate,
                "deductible_counterfactual_tco2e": Decimal("0.0"),
                "reason_code": "PURO_COUNTERFACTUAL_NEGLIGIBLE_VERIFIED",
                "notes": "Negligible counterfactual storage demonstrated with verified evidence.",
                "evaluated_at": now,
            }

        elif path == "PATH_B_MATERIAL_STORAGE":
            # Must have quantified non-zero deduction
            deduction = Decimal(str(assessment.counterfactual_carbon_stored_tco2e or 0.0))
            if deduction <= Decimal("0.0"):
                return {
                    "status": "DEDUCTION_REQUIRED",
                    "is_compliant": False,
                    "counterfactual_path": path,
                    "baseline_fate": fate,
                    "deductible_counterfactual_tco2e": Decimal("0.0"),
                    "reason_code": "PURO_COUNTERFACTUAL_DEDUCTION_REQUIRED",
                    "notes": "Path B material storage requires quantified strictly positive counterfactual storage deduction.",
                    "evaluated_at": now,
                }

            if ev_status != "VERIFIED":
                return {
                    "status": "EVIDENCE_REQUIRED",
                    "is_compliant": False,
                    "counterfactual_path": path,
                    "baseline_fate": fate,
                    "deductible_counterfactual_tco2e": deduction,
                    "reason_code": "PURO_COUNTERFACTUAL_EVIDENCE_REQUIRED",
                    "notes": f"Path B material storage deduction requires VERIFIED quantification evidence. Current status: '{ev_status}'.",
                    "evaluated_at": now,
                }

            return {
                "status": "COMPLIANT",
                "is_compliant": True,
                "counterfactual_path": path,
                "baseline_fate": fate,
                "deductible_counterfactual_tco2e": deduction,
                "reason_code": "PURO_COUNTERFACTUAL_MATERIAL_QUANTIFIED",
                "notes": f"Material counterfactual storage quantified: deduction of {deduction} tCO2e.",
                "evaluated_at": now,
            }

        else:
            return {
                "status": "NON_COMPLIANT",
                "is_compliant": False,
                "counterfactual_path": path,
                "baseline_fate": fate,
                "deductible_counterfactual_tco2e": Decimal("0.0"),
                "reason_code": "PURO_UNKNOWN_COUNTERFACTUAL_PATH",
                "notes": f"Unknown counterfactual path: '{path}'. Supported: PATH_A_NEGLIGIBLE_STORAGE, PATH_B_MATERIAL_STORAGE.",
                "evaluated_at": now,
            }

    @classmethod
    async def get_assessment_for_batch(
        cls,
        db: AsyncSession,
        batch_id: UUID,
        organization_id: UUID,
    ) -> Optional[PuroCounterfactualStorageAssessment]:
        stmt = (
            select(PuroCounterfactualStorageAssessment)
            .where(
                PuroCounterfactualStorageAssessment.batch_id == batch_id,
                PuroCounterfactualStorageAssessment.organization_id == organization_id,
            )
            .order_by(PuroCounterfactualStorageAssessment.created_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()
