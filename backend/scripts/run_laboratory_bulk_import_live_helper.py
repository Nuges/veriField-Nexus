"""
VeriField Nexus — Laboratory Bulk Data Import Live Full-Stack Helper
Creates synthetic database records and queries real PostgreSQL 18 for persistence proof.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import uuid
import hashlib
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, date

from sqlalchemy import select, text
from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.earth_observation.models import ProjectBoundaryVersion
from app.domains.agriculture.models import (
    LandUnit,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    SampleCollectionEvent,
    PhysicalSample,
    ChainOfCustodyEvent,
    LaboratoryReceipt,
    LaboratoryAnalysis,
    LaboratoryResult,
    SampleQAReview,
    Stratum,
    StratumMembership,
    LaboratoryImportBatch,
    LaboratoryImportRow,
)
from app.domains.methodologies.models import MethodologyFamily, Methodology, MethodologyVersion
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash


async def setup_test_environment():
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    today = now.date()

    async with async_session_factory() as session:
        # Fetch methodology and family
        fam = (await session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE"))).scalars().first()
        vm = (await session.execute(select(Methodology).where(Methodology.code == "VM0042"))).scalars().first()
        v22 = None
        if vm:
            v22 = (await session.execute(select(MethodologyVersion).where(MethodologyVersion.methodology_id == vm.id))).scalars().first()

        # 1. Organization & Users
        org = Organization(
            id=uuid.uuid4(),
            name=f"Lab Bulk Import Org {tag}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
            status="ACTIVE",
            max_installations=100,
            max_agents=5,
            api_calls_count=0,
            version=1,
            is_deleted=False,
        )
        session.add(org)
        await session.flush()

        pm_user = User(
            id=uuid.uuid4(),
            email=f"pm.{tag}@lab-import.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Agricultural Lab PM",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        field_agent = User(
            id=uuid.uuid4(),
            email=f"agent.{tag}@lab-import.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Field Sampler Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add_all([pm_user, field_agent])
        await session.flush()

        # 2. Project
        proj = Project(
            id=uuid.uuid4(),
            name=f"Lab Import Project {tag}",
            project_code=f"AGR-IMP-{tag[:6]}",
            organization_id=org.id,
            sector_id=fam.id if fam else None,
            methodology_id=vm.id if vm else None,
            methodology_version_id=v22.id if v22 else None,
            crediting_start=date(2025, 1, 1),
            crediting_end=date(2045, 12, 31),
            baseline_parameters={
                "soil_depth_standard_cm": 30.0,
                "locked_methodology_version": {
                    "methodology_code": "VM0042",
                    "version": "2.2",
                    "status": "LOCKED",
                    "locked_at": now.isoformat(),
                },
            },
        )
        session.add(proj)
        await session.flush()

        # 3. Project Boundary
        boundary = ProjectBoundaryVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            version_number=1,
            effective_date=today,
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]]
            },
            area_ha=60.0,
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
        )
        session.add(boundary)

        # 4. Land Unit & Stratum
        lu = LandUnit(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            name=f"Experimental Sector {tag}",
            code=f"LU-BLK-{tag[:4]}",
            area_ha=60.0,
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]]
            },
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
            is_active=True,
        )
        session.add(lu)
        await session.flush()

        stratum = Stratum(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"STR-SOIL-{tag[:4]}",
            name="Silty Clay Agricultural Loam",
            stratum_type="SOIL_TYPE",
            area_ha=60.0,
            is_active=True,
        )
        session.add(stratum)
        await session.flush()

        membership = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            land_unit_id=lu.id,
            stratum_id=stratum.id,
            valid_from=date(2025, 1, 1),
            status="ACTIVE",
        )
        session.add(membership)

        # 5. Campaign & Locked Plan Version
        campaign = SamplingCampaign(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_code=f"CAMP-BLK-{tag[:4]}",
            name="Bulk Import Baseline Campaign",
            purpose="BASELINE_SOC_DETERMINATION",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=date(2025, 2, 1),
            planned_end_date=date(2025, 3, 1),
            status="ACTIVE",
            project_boundary_version_id=boundary.id,
        )
        session.add(campaign)
        await session.flush()

        plan = SamplingPlanVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            version_number=1,
            status="LOCKED",
            effective_as_of_date=date(2025, 2, 1),
            is_locked=True,
            locked_at=now,
            locked_by_id=pm_user.id,
        )
        session.add(plan)
        await session.flush()

        # 6. Sampling Points & Physical Samples
        sample1_code = f"SMP-LIVE-01-{tag[:4]}"
        sample2_code = f"SMP-LIVE-02-{tag[:4]}"

        sp1 = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan.id,
            land_unit_id=lu.id,
            point_code=f"PT-1-{tag[:4]}",
            planned_lat=28.52,
            planned_lon=77.12,
            depth_from_cm=0.0,
            depth_to_cm=30.0,
            status="COLLECTED",
        )
        sp2 = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan.id,
            land_unit_id=lu.id,
            point_code=f"PT-2-{tag[:4]}",
            planned_lat=28.53,
            planned_lon=77.13,
            depth_from_cm=0.0,
            depth_to_cm=30.0,
            status="COLLECTED",
        )
        session.add_all([sp1, sp2])
        await session.flush()

        ps1 = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan.id,
            sampling_point_id=sp1.id,
            land_unit_id=lu.id,
            sample_code=sample1_code,
            status="IN_TRANSIT",
        )
        ps2 = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan.id,
            sampling_point_id=sp2.id,
            land_unit_id=lu.id,
            sample_code=sample2_code,
            status="IN_TRANSIT",
        )
        session.add_all([ps1, ps2])
        await session.commit()

        # Tokens
        pm_token = AuthenticationService.generate_token_static(pm_user)
        field_token = AuthenticationService.generate_token_static(field_agent)

        # Write sample test CSV
        csv_path = f"/tmp/sample_lab_import_{tag}.csv"
        csv_content = f"""sample_code,analyte,raw_value,raw_unit,depth_from_cm,depth_to_cm,analysis_date,method,lab_sample_id,notes
{sample1_code},SOC_CONCENTRATION,2.15,%,0,30,2026-09-20,DUMAS_COMBUSTION,LAB-001,Verified combustion assay
{sample2_code},BULK_DENSITY,1.32,g/cm3,0,30,2026-09-20,CORE_RING,LAB-002,Intact soil core assay
"""
        with open(csv_path, "w") as f:
            f.write(csv_content)

        # Write sample test XLSX
        import openpyxl
        xlsx_path = f"/tmp/sample_lab_import_{tag}.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Lab_Results"
        headers = ["sample_code", "analyte", "raw_value", "raw_unit", "depth_from_cm", "depth_to_cm", "analysis_date", "method", "lab_sample_id", "notes"]
        ws.append(headers)
        ws.append([sample1_code, "SOC_CONCENTRATION", 2.45, "%", 0, 30, "2026-09-20", "DUMAS_COMBUSTION", "LAB-XLSX-001", "Excel imported combustion assay"])
        ws.append([sample2_code, "BULK_DENSITY", 1.28, "g/cm3", 0, 30, "2026-09-20", "CORE_RING", "LAB-XLSX-002", "Excel imported core ring assay"])
        wb.save(xlsx_path)

        res_payload = {
            "organization_id": str(org.id),
            "project_id": str(proj.id),
            "project_name": proj.name,
            "project_code": proj.project_code,
            "campaign_id": str(campaign.id),
            "pm_user_id": str(pm_user.id),
            "pm_user_email": pm_user.email,
            "pm_token": pm_token,
            "field_agent_id": str(field_agent.id),
            "field_token": field_token,
            "sample1_code": sample1_code,
            "sample2_code": sample2_code,
            "csv_path": csv_path,
            "xlsx_path": xlsx_path,
            "tag": tag,
        }
        print(json.dumps(res_payload))


async def verify_committed(project_id_str: str):
    p_id = uuid.UUID(project_id_str)
    async with async_session_factory() as session:
        # Check batch
        batch = (await session.execute(
            select(LaboratoryImportBatch).where(LaboratoryImportBatch.project_id == p_id).order_by(LaboratoryImportBatch.created_at.desc())
        )).scalars().first()

        if not batch:
            print(json.dumps({"error": "No batch found"}))
            return

        # Check rows
        rows = (await session.execute(
            select(LaboratoryImportRow).where(LaboratoryImportRow.import_batch_id == batch.id)
        )).scalars().all()

        # Check results
        results = (await session.execute(
            select(LaboratoryResult)
            .join(PhysicalSample, LaboratoryResult.physical_sample_id == PhysicalSample.id)
            .where(PhysicalSample.project_id == p_id)
        )).scalars().all()

        analyses = (await session.execute(
            select(LaboratoryAnalysis)
            .join(PhysicalSample, LaboratoryAnalysis.physical_sample_id == PhysicalSample.id)
            .where(PhysicalSample.project_id == p_id)
        )).scalars().all()

        receipts = (await session.execute(
            select(LaboratoryReceipt)
            .join(PhysicalSample, LaboratoryReceipt.physical_sample_id == PhysicalSample.id)
            .where(PhysicalSample.project_id == p_id)
        )).scalars().all()

        soc_res = [r for r in results if r.analyte == "SOC_CONCENTRATION"]
        bd_res = [r for r in results if r.analyte == "BULK_DENSITY_G_CM3"]

        proof = {
            "batch_id": str(batch.id),
            "batch_status": batch.status,
            "total_rows": batch.total_rows,
            "valid_rows": batch.valid_rows,
            "imported_rows": batch.imported_rows,
            "file_sha256": batch.file_sha256,
            "evidence_id": str(batch.evidence_id) if batch.evidence_id else None,
            "row_statuses": [r.validation_status for r in rows],
            "receipts_count": len(receipts),
            "analyses_count": len(analyses),
            "analyses_qa_statuses": [a.qa_status for a in analyses],
            "results_count": len(results),
            "soc_normalized_value": float(soc_res[0].normalized_value) if soc_res else None,
            "soc_normalized_unit": soc_res[0].normalized_unit if soc_res else None,
            "bd_normalized_value": float(bd_res[0].normalized_value) if bd_res else None,
            "bd_normalized_unit": bd_res[0].normalized_unit if bd_res else None,
        }
        print(json.dumps(proof))


async def cleanup_environment(org_id_str: str):
    org_id = uuid.UUID(org_id_str)
    async with async_session_factory() as session:
        # Delete children in proper foreign-key order
        await session.execute(text("""
            DELETE FROM laboratory_import_rows WHERE import_batch_id IN (
                SELECT id FROM laboratory_import_batches WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        await session.execute(text("DELETE FROM laboratory_import_batches WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("""
            DELETE FROM laboratory_results WHERE physical_sample_id IN (
                SELECT id FROM physical_samples WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        await session.execute(text("""
            DELETE FROM laboratory_analyses WHERE physical_sample_id IN (
                SELECT id FROM physical_samples WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        await session.execute(text("""
            DELETE FROM laboratory_receipts WHERE physical_sample_id IN (
                SELECT id FROM physical_samples WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        await session.execute(text("""
            DELETE FROM chain_of_custody_events WHERE physical_sample_id IN (
                SELECT id FROM physical_samples WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        await session.execute(text("""
            DELETE FROM sample_collection_events WHERE physical_sample_id IN (
                SELECT id FROM physical_samples WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        await session.execute(text("DELETE FROM physical_samples WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM sampling_points WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM sampling_plan_versions WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM sampling_campaigns WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_stratum_memberships WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_strata WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM land_units WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM project_boundary_versions WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM projects WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM users WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM organizations WHERE id = :org_id"), {"org_id": org_id})
        await session.commit()
    print(json.dumps({"status": "cleaned"}))


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if action == "setup":
        asyncio.run(setup_test_environment())
    elif action == "verify_committed":
        asyncio.run(verify_committed(sys.argv[2]))
    elif action == "cleanup":
        asyncio.run(cleanup_environment(sys.argv[2]))
