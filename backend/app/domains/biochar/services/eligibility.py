import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.biochar.models import (
    BiocharBatch,
    BiocharLabAnalysis,
    FeedstockLot,
    FeedstockSource,
    ProductionFacility,
)
from app.domains.biochar.schemas import BiocharEligibilityResponse
from app.domains.projects.models import Project


class BiocharEligibilityEngine:
    """
    Standard-Specific Project and Batch Eligibility Engine.
    Implements factual rules for:
    - Verra VM0044 v1.2 (Active 27 June 2025; strict new facility rule; VCU)
    - Puro Standard Biochar Edition 2025 v2 (Active; existing & new facilities; CORC / CORC200+)
    - Gold Standard PARC (Under Development; Inactive)
    - India CCTS (No Active Methodology; Inactive)
    """

    @staticmethod
    async def evaluate_project_eligibility(
        db: AsyncSession,
        project_id: UUID,
        target_standard: str = "VERRA",
        target_methodology: str = "VM0044",
        methodology_version: str = "v1.2",
    ) -> BiocharEligibilityResponse:
        std = target_standard.upper()
        meth = target_methodology.upper()
        now = datetime.now(timezone.utc)

        # Handle Gold Standard PARC
        if "GOLD" in std or "PARC" in meth:
            return BiocharEligibilityResponse(
                project_id=project_id,
                target_standard="GOLD_STANDARD",
                target_methodology="GS_PARC",
                methodology_version="1.0_DRAFT",
                eligibility_status="NOT_SUPPORTED",
                facility_criteria_met=False,
                feedstock_criteria_met=False,
                additionality_status="METHODOLOGY_UNDER_DEVELOPMENT",
                requirements_complete=[],
                requirements_missing=["Methodology final approval by Gold Standard TAC"],
                blocking_findings=["Gold Standard PARC methodology is currently under development and not yet available for project crediting."],
                review_findings=[],
                source_references=["Gold Standard Methodology Pipeline (PARC / NMC 110)"],
                evaluated_at=now,
            )

        # Handle India CCTS
        if "INDIA" in std or "CCTS" in std or "CCTS" in meth:
            return BiocharEligibilityResponse(
                project_id=project_id,
                target_standard="INDIA_CCTS",
                target_methodology="NOT_SPECIFIED",
                methodology_version="N/A",
                eligibility_status="NOT_SUPPORTED",
                facility_criteria_met=False,
                feedstock_criteria_met=False,
                additionality_status="NO_ACTIVE_METHODOLOGY",
                requirements_complete=[],
                requirements_missing=["BEE Bureau of Energy Efficiency Biochar Sector Gazette Notification"],
                blocking_findings=["India Carbon Credit Trading Scheme (CCTS) has not published an approved methodology for biochar carbon removal."],
                review_findings=[],
                source_references=["Bureau of Energy Efficiency (BEE) CCTS Gazette Notifications"],
                evaluated_at=now,
            )

        # Handle VM0044 v2.0 Watchlist
        if "VM0044" in meth and ("v2" in methodology_version or "2.0" in methodology_version):
            return BiocharEligibilityResponse(
                project_id=project_id,
                target_standard="VERRA",
                target_methodology="VM0044",
                methodology_version="v2.0_WATCHLIST",
                eligibility_status="WATCHLIST",
                facility_criteria_met=False,
                feedstock_criteria_met=False,
                additionality_status="UNDER_REVIEW",
                requirements_complete=[],
                requirements_missing=["Verra public consultation conclusion and formal adoption"],
                blocking_findings=["VM0044 v2.0 is currently in public consultation / under review by Verra and cannot be selected for crediting."],
                review_findings=[],
                source_references=["Verra Methodology Development Pipeline: VM0044 v2.0"],
                evaluated_at=now,
            )

        # Query facilities linked to this project or org
        stmt_fac = select(ProductionFacility).where(ProductionFacility.project_id == project_id)
        res_fac = await db.execute(stmt_fac)
        facilities = res_fac.scalars().all()

        # Query feedstock sources
        stmt_src = select(FeedstockSource).where(FeedstockSource.project_id == project_id)
        res_src = await db.execute(stmt_src)
        sources = res_src.scalars().all()

        requirements_complete = []
        requirements_missing = []
        blocking_findings = []
        review_findings = []
        source_refs = []

        facility_met = True
        feedstock_met = True

        # Evaluate Verra VM0044 v1.2
        if "VERRA" in std or "VM0044" in meth:
            source_refs.append("Verra VM0044 Methodology for Biochar Utilization in Soil and Non-Soil Applications v1.2 (Active 27 June 2025)")
            
            # 1. Facility eligibility: VM0044 v1.2 strictly requires NEW facility
            if not facilities:
                facility_met = False
                requirements_missing.append("Production facility registration and commissioning evidence")
                blocking_findings.append("No registered production facility linked to this biochar project.")
            else:
                has_valid_new_facility = False
                for f in facilities:
                    if f.facility_status in ("NEW_OPERATIONAL", "PLANNED", "UNDER_CONSTRUCTION"):
                        has_valid_new_facility = True
                        requirements_complete.append(f"Facility '{f.facility_name}' complies with VM0044 new facility additionality criterion ({f.facility_status}).")
                    else:
                        blocking_findings.append(
                            f"Facility '{f.facility_name}' has status '{f.facility_status}'. "
                            "Verra VM0044 v1.2 Section 4 requires a new biochar production facility; existing facilities are ineligible without approved additionality proof."
                        )
                if not has_valid_new_facility:
                    facility_met = False

            # 2. Feedstock eligibility: Must be waste biomass or residues
            if not sources:
                feedstock_met = False
                requirements_missing.append("Feedstock source identification and baseline fate justification")
                blocking_findings.append("No feedstock sources registered for project.")
            else:
                for s in sources:
                    if s.waste_status == "CONFIRMED_WASTE_BIOMASS" or s.source_type in ("AGRICULTURAL_RESIDUE", "FORESTRY_RESIDUE", "MUNICIPAL_BIOMASS", "INDUSTRIAL_BIOGENIC"):
                        requirements_complete.append(f"Feedstock source '{s.source_name}' verified as biogenic residue ({s.source_type}, baseline fate: {s.baseline_fate}).")
                    else:
                        feedstock_met = False
                        blocking_findings.append(f"Feedstock source '{s.source_name}' has unverified waste status: '{s.waste_status}'. Purpose-grown biomass requires additionality demonstration.")

            # Determine overall status
            if blocking_findings:
                eligibility_status = "INELIGIBLE" if not facility_met else "REQUIRES_EVIDENCE"
            elif requirements_missing:
                eligibility_status = "REQUIRES_EVIDENCE"
            else:
                eligibility_status = "POTENTIALLY_ELIGIBLE"

            return BiocharEligibilityResponse(
                project_id=project_id,
                target_standard="VERRA",
                target_methodology="VM0044",
                methodology_version="v1.2",
                eligibility_status=eligibility_status,
                facility_criteria_met=facility_met,
                feedstock_criteria_met=feedstock_met,
                additionality_status="ACTIVITY_METHOD_ADDITIONALITY" if facility_met else "ADDITIONALITY_FAILED",
                requirements_complete=requirements_complete,
                requirements_missing=requirements_missing,
                blocking_findings=blocking_findings,
                review_findings=review_findings,
                source_references=source_refs,
                evaluated_at=now,
            )

        # Evaluate Puro Standard Biochar Edition 2025 v2
        if "PURO" in std or "PURO" in meth:
            source_refs.append("Puro Standard Biochar Methodology Edition 2025 Version 2 (CORC / CORC200+)")

            # 1. Facility eligibility: Puro accepts existing operational facilities
            if not facilities:
                facility_met = False
                requirements_missing.append("Production facility registration and audit documentation")
                blocking_findings.append("No production facility registered for project.")
            else:
                for f in facilities:
                    requirements_complete.append(f"Facility '{f.facility_name}' ({f.facility_status}) accepted under Puro Standard 2025 v2 operational criteria.")
                facility_met = True

            # 2. Feedstock eligibility
            if not sources:
                feedstock_met = False
                requirements_missing.append("Feedstock origin and sustainable sourcing documentation")
                blocking_findings.append("No feedstock sources registered.")
            else:
                for s in sources:
                    requirements_complete.append(f"Feedstock source '{s.source_name}' ({s.biomass_type}) documented with baseline fate {s.baseline_fate}.")

            status_str = "POTENTIALLY_ELIGIBLE" if (facility_met and feedstock_met and not requirements_missing) else "REQUIRES_EVIDENCE"

            return BiocharEligibilityResponse(
                project_id=project_id,
                target_standard="PURO_STANDARD",
                target_methodology="PURO_BIOCHAR_2025",
                methodology_version="Edition_2025_v2",
                eligibility_status=status_str,
                facility_criteria_met=facility_met,
                feedstock_criteria_met=feedstock_met,
                additionality_status="PURO_ADDITIONALITY_ACCEPTED",
                requirements_complete=requirements_complete,
                requirements_missing=requirements_missing,
                blocking_findings=blocking_findings,
                review_findings=review_findings,
                source_references=source_refs,
                evaluated_at=now,
            )

        # Generic / Unknown fallback
        return BiocharEligibilityResponse(
            project_id=project_id,
            target_standard=target_standard,
            target_methodology=target_methodology,
            methodology_version=methodology_version,
            eligibility_status="EXPERT_REVIEW_REQUIRED",
            facility_criteria_met=bool(facilities),
            feedstock_criteria_met=bool(sources),
            additionality_status="CUSTOM_REVIEW",
            requirements_complete=[],
            requirements_missing=["Standard methodology configuration"],
            blocking_findings=[],
            review_findings=["Unrecognized standard or methodology; requires manual registry alignment."],
            source_references=source_refs,
            evaluated_at=now,
        )
