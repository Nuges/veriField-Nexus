"""
=============================================================================
VeriField Nexus — Document Fraud & MRV Reconciliation Engine
=============================================================================
Reconciles extracted document facts against live database project state,
identifies discrepancies (methodology mismatch, sector mismatch, asset count delta,
duplicate files), and generates explainable Trust Scores.
=============================================================================
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.assets.models import Asset
from app.domains.documents.models import DocumentFraudFlag, ProjectDocument
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily
from app.domains.projects.models import Project

logger = logging.getLogger("verifield.documents.reconciliation")


class DocumentReconciliationEngine:
    """Performs rigorous discrepancy checks and calculates explainable Trust Scores."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconcile_document(
        self,
        document: ProjectDocument,
        extracted_facts: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes reconciliation rules against project and database state.
        Returns: {
            "trust_score": float,
            "trust_breakdown": dict,
            "fraud_flags": list of DocumentFraudFlag
        }
        """
        flags: List[DocumentFraudFlag] = []
        reasons: List[Dict[str, Any]] = []
        score = 100.0

        fields = extracted_facts.get("fields", {})

        # 1. Cryptographic Duplicate File Check
        dup_stmt = select(ProjectDocument).where(
            ProjectDocument.sha256 == document.sha256,
            ProjectDocument.id != document.id,
            ProjectDocument.organization_id == document.organization_id,
        )
        dup_res = await self.db.execute(dup_stmt)
        duplicates = dup_res.scalars().all()
        if duplicates:
            score -= 30.0
            flag = DocumentFraudFlag(
                document_id=document.id,
                organization_id=document.organization_id,
                flag_type="DUPLICATE_FILE",
                severity="HIGH",
                description=f"Identical SHA-256 hash matches existing document '{duplicates[0].title}' (v{duplicates[0].version}).",
                evidence_details={"matched_document_id": str(duplicates[0].id), "sha256": document.sha256},
            )
            flags.append(flag)
            reasons.append({
                "category": "Integrity",
                "label": "Duplicate File Detection",
                "status": "FLAG",
                "message": f"Exact SHA-256 duplicate found in organization repository.",
            })
        else:
            reasons.append({
                "category": "Integrity",
                "label": "Cryptographic Hash",
                "status": "PASS",
                "message": "SHA-256 integrity verified with zero collision.",
            })

        # If document is associated with a project, run project-level reconciliation
        if document.project_id:
            proj_stmt = (
                select(Project)
                .where(Project.id == document.project_id)
            )
            proj_res = await self.db.execute(proj_stmt)
            project = proj_res.scalar_one_or_none()

            if project:
                # 2. Methodology Invariant Check
                claimed_meth = fields.get("methodology_code", {}).get("value")
                if claimed_meth:
                    meth_stmt = select(Methodology).where(Methodology.id == project.methodology_id)
                    cur_meth_res = await self.db.execute(meth_stmt)
                    project_meth = cur_meth_res.scalar_one_or_none()

                    if project_meth:
                        # Compare normalized codes
                        claimed_clean = claimed_meth.upper().replace("-", "_").replace(".", "_")
                        proj_clean = project_meth.code.upper().replace("-", "_").replace(".", "_")

                        if claimed_clean != proj_clean:
                            score -= 25.0
                            flag = DocumentFraudFlag(
                                document_id=document.id,
                                organization_id=document.organization_id,
                                flag_type="METHODOLOGY_MISMATCH",
                                severity="HIGH",
                                description=f"Document claims methodology '{claimed_meth}' but project is configured for '{project_meth.code}'.",
                                evidence_details={"claimed": claimed_meth, "configured": project_meth.code},
                            )
                            flags.append(flag)
                            reasons.append({
                                "category": "Methodology",
                                "label": "Methodology Alignment",
                                "status": "FLAG",
                                "message": f"Mismatch: Claimed '{claimed_meth}' vs Project '{project_meth.code}'.",
                            })
                        else:
                            reasons.append({
                                "category": "Methodology",
                                "label": "Methodology Alignment",
                                "status": "PASS",
                                "message": f"Matches project methodology '{project_meth.code}'.",
                            })

                # 3. Sector Invariant Check
                claimed_sector = fields.get("sector_code", {}).get("value")
                if claimed_sector:
                    sec_stmt = select(MethodologyFamily).where(MethodologyFamily.id == project.sector_id)
                    cur_sec_res = await self.db.execute(sec_stmt)
                    project_sec = cur_sec_res.scalar_one_or_none()

                    if project_sec and claimed_sector.upper() != project_sec.code.upper():
                        score -= 35.0
                        flag = DocumentFraudFlag(
                            document_id=document.id,
                            organization_id=document.organization_id,
                            flag_type="METHODOLOGY_SECTOR_MISMATCH",
                            severity="CRITICAL",
                            description=f"Sector mismatch: Document belongs to sector '{claimed_sector}' but project sector is '{project_sec.name}'.",
                            evidence_details={"claimed_sector": claimed_sector, "project_sector": project_sec.code},
                        )
                        flags.append(flag)
                        reasons.append({
                            "category": "Sector",
                            "label": "Sector Invariant",
                            "status": "FLAG",
                            "message": f"Sector violation: Claimed '{claimed_sector}' does not match project sector '{project_sec.name}'.",
                        })
                    elif project_sec:
                        reasons.append({
                            "category": "Sector",
                            "label": "Sector Invariant",
                            "status": "PASS",
                            "message": f"Sector verified: '{project_sec.name}'.",
                        })

                # 4. MRV Declared Asset Count Reconciliation
                declared_count = fields.get("declared_asset_count", {}).get("value")
                if declared_count and isinstance(declared_count, (int, float)) and declared_count > 0:
                    asset_count_stmt = select(func.count(Asset.id)).where(Asset.project_id == project.id)
                    actual_count_res = await self.db.execute(asset_count_stmt)
                    actual_assets_count = actual_count_res.scalar_one() or 0

                    if actual_assets_count > 0:
                        delta = abs(declared_count - actual_assets_count)
                        pct_diff = (delta / actual_assets_count) * 100.0
                        if pct_diff > 20.0:
                            score -= 15.0
                            flag = DocumentFraudFlag(
                                document_id=document.id,
                                organization_id=document.organization_id,
                                flag_type="ASSET_COUNT_DISCREPANCY",
                                severity="MEDIUM",
                                description=f"Document declares {int(declared_count):,} assets, but live database contains {actual_assets_count:,} registered assets ({pct_diff:.1f}% variance).",
                                evidence_details={"declared_count": declared_count, "actual_count": actual_assets_count, "delta_pct": pct_diff},
                            )
                            flags.append(flag)
                            reasons.append({
                                "category": "MRV Reconciliation",
                                "label": "Asset Count Audit",
                                "status": "WARN",
                                "message": f"Variance detected: {int(declared_count):,} declared vs {actual_assets_count:,} registered in DB.",
                            })
                        else:
                            reasons.append({
                                "category": "MRV Reconciliation",
                                "label": "Asset Count Audit",
                                "status": "PASS",
                                "message": f"Asset counts aligned within tolerance ({actual_assets_count:,} active assets).",
                            })

        final_score = max(0.0, min(100.0, score))

        trust_breakdown = {
            "score": final_score,
            "flags_count": len(flags),
            "reasons": reasons,
            "status": "VERIFIED" if final_score >= 85 and not any(f.severity == "CRITICAL" for f in flags) else "REVIEW_REQUIRED",
        }

        return {
            "trust_score": final_score,
            "trust_breakdown": trust_breakdown,
            "fraud_flags": flags,
        }
