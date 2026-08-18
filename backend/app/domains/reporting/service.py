"""
=============================================================================
VeriField Nexus — Reporting Service with Real PDF Generation
=============================================================================
Replaces simulated sleep() with genuine ReportLab PDF synthesis grounded in
live database state (projects, organizations, methodologies, verified carbon metrics).
=============================================================================
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select

from app.domains.assets.models import Asset
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.reporting.models import Report
from app.domains.reporting.repository import ReportRepository
from app.domains.reporting.schemas import ReportCreate
from app.domains.reporting.services.generator import RealDocumentGeneratorService

logger = logging.getLogger("verifield.reporting.service")
REPORTS_STORAGE_DIR = os.path.join("static", "reports")


class ReportingService:
    def __init__(self, repository: ReportRepository):
        self.repository = repository

    async def get_report(self, report_id: UUID) -> Optional[Report]:
        return await self.repository.get_by_id(report_id)

    async def list_reports(
        self, org_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Report]:
        return await self.repository.list_for_org(org_id, skip=skip, limit=limit)

    async def generate_report(
        self, payload: ReportCreate, creator_id: Optional[UUID] = None
    ) -> Report:
        report = Report(
            org_id=payload.org_id,
            title=payload.title,
            report_type=payload.report_type,
            parameters=payload.parameters or {},
            created_by=creator_id,
            status="GENERATING",
        )
        created = await self.repository.create(report)

        # Dispatch real PDF generation in background
        asyncio.create_task(self._generate_real_pdf(created.id, payload))

        return created

    async def _generate_real_pdf(self, report_id: UUID, payload: ReportCreate):
        from app.db.session import async_session_factory
        try:
            async with async_session_factory() as db:
                from app.domains.reporting.repository import ReportRepository
                rep_repo = ReportRepository(db)


            # Fetch organization name
            org_stmt = select(Organization).where(Organization.id == payload.org_id)
            org_res = await db.execute(org_stmt)
            org = org_res.scalar_one_or_none()
            org_name = org.name if org else "VeriField Partner"

            # Fetch project details if supplied
            project_id = payload.parameters.get("project_id")
            project_name = "Portfolio Aggregated Scope"
            sector_name = "Multi-Sector Climate Portfolio"
            methodology_name = "Registry Standard MRV"
            methodology_code = "VERIFIELD_MRV_V1"

            assets_sample: List[Dict[str, Any]] = []
            total_reductions = 0.0
            total_assets = 0

            if project_id:
                try:
                    p_uuid = UUID(str(project_id))
                    # Enforce tenant isolation on project lookup
                    p_stmt = select(Project).where(Project.id == p_uuid, Project.organization_id == payload.org_id)
                    p_res = await db.execute(p_stmt)
                    project = p_res.scalar_one_or_none()
                    if project:
                        project_name = project.name

                        if project.sector_id:
                            sec_stmt = select(MethodologyFamily).where(MethodologyFamily.id == project.sector_id)
                            sec_res = await db.execute(sec_stmt)
                            sec = sec_res.scalar_one_or_none()
                            if sec:
                                sector_name = sec.name

                        if project.methodology_id:
                            m_stmt = select(Methodology).where(Methodology.id == project.methodology_id)
                            m_res = await db.execute(m_stmt)
                            meth = m_res.scalar_one_or_none()
                            if meth:
                                methodology_name = meth.name
                                methodology_code = meth.code

                        # Query real assets belonging to this tenant's project
                        asset_stmt = select(Asset).where(Asset.project_id == p_uuid).limit(15)
                        a_res = await db.execute(asset_stmt)
                        db_assets = a_res.scalars().all()
                        total_assets = len(db_assets)
                        for a in db_assets:
                            attrs = a.attributes or {}
                            co2_offset = float(attrs.get("carbon_offset_kg", 0)) / 1000.0
                            total_reductions += co2_offset
                            assets_sample.append({
                                "id": str(a.id),
                                "property_type": a.asset_type or "Asset",
                                "baseline_fuel": float(attrs.get("baseline_fuel_consumption", 0.0)),
                                "reductions_tco2e": co2_offset,
                                "trust_score": float(attrs.get("trust_score", 0.0)),
                            })
                except Exception as ex:
                    logger.warning(f"Could not load project context for report {report_id}: {ex}")

            avg_trust = (sum(a["trust_score"] for a in assets_sample) / len(assets_sample)) if assets_sample else 0.0
            metrics = {
                "total_reductions_tco2e": round(total_reductions, 2),
                "total_assets": total_assets,
                "avg_trust_score": round(avg_trust, 1) if avg_trust > 0 else 0.0,
                "portfolio_value_usd": round(total_reductions * 15.0, 2),
            }


            output_dir = os.path.join(REPORTS_STORAGE_DIR, str(payload.org_id))
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{report_id}.pdf")

            RealDocumentGeneratorService.generate_mrv_report_pdf(
                report_id=report_id,
                title=payload.title,
                org_name=org_name,
                project_name=project_name,
                sector_name=sector_name,
                methodology_name=methodology_name,
                methodology_code=methodology_code,
                metrics=metrics,
                assets_sample=assets_sample,
                output_path=output_file,
            )

            await rep_repo.update_status(
                report_id,
                status="COMPLETED",
                file_uri=output_file,
            )
            logger.info(f"Generated physical PDF report {report_id} at {output_file}")


        except Exception as e:
            logger.error(f"Real PDF report generation failed for {report_id}: {e}", exc_info=True)
            async with async_session_factory() as fail_db:
                fail_repo = ReportRepository(fail_db)
                await fail_repo.update_status(report_id, status="FAILED", file_uri=None)


    async def get_report_file_for_download(
        self, report_id: UUID, current_user: Any
    ) -> Tuple[str, str, str]:
        """Validates tenant authorization and returns (filepath, filename, mime_type)."""
        report = await self.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if current_user.role != "SUPER_ADMIN":
            if report.org_id != current_user.organization_id:
                raise HTTPException(status_code=403, detail="Forbidden: Cannot access another organization's report.")

        if not report.file_uri or not os.path.exists(report.file_uri):
            raise HTTPException(status_code=404, detail="Physical PDF report file not found on disk.")

        clean_filename = f"{report.title.lower().replace(' ', '_')}_{str(report.id)[:8]}.pdf"
        return report.file_uri, clean_filename, "application/pdf"
