"""
VeriField Nexus — Agriculture Phase 2 Live Full-Stack Helper
Creates synthetic database records and queries real PostgreSQL 18 for persistence proof.
"""

import sys
import os
import json
import uuid
import asyncio
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
)
from app.domains.methodologies.models import MethodologyFamily, Methodology, MethodologyVersion
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash


async def setup_test_environment():
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)

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
            name=f"Live Test Agriculture Org {tag}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
        )
        session.add(org)
        await session.flush()

        collector = User(
            id=uuid.uuid4(),
            email=f"collector.{tag}@synthetic-live.test",
            password_hash=get_password_hash("VeriField_Dev_2026!"),
            full_name="Tariq Field Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add(collector)

        qa_user = User(
            id=uuid.uuid4(),
            email=f"qa.lead.{tag}@synthetic-live.test",
            password_hash=get_password_hash("VeriField_Dev_2026!"),
            full_name="Lead MRV QA Officer",
            role="SUPER_ADMIN",  # Super Admin has all permissions including activity:verify
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add(qa_user)
        await session.flush()

        # 2. Project
        proj = Project(
            id=uuid.uuid4(),
            name=f"Synthetic Live Agriculture Project {tag}",
            project_code=f"AGR-LIVE-{tag[:6]}",
            organization_id=org.id,
            sector_id=fam.id if fam else None,
            methodology_id=vm.id if vm else None,
            methodology_version_id=v22.id if v22 else None,
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2046, 12, 31),
            baseline_parameters={"soil_depth_standard_cm": 30.0},
        )
        session.add(proj)
        await session.flush()

        # 3. Project Boundary
        boundary = ProjectBoundaryVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            version_number=1,
            effective_date=now.date(),
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]],
            },
            area_ha=25.0,
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
        )
        session.add(boundary)

        # 4. Land Unit
        lu = LandUnit(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            name=f"Live Field Sector {tag}",
            code=f"FIELD-{tag[:6]}",
            area_ha=25.0,
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]],
            },
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
            is_active=True,
        )
        session.add(lu)
        await session.flush()

        # 5. Stratum & Stratum Membership
        strat = Stratum(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"STRAT-{tag[:4]}",
            name=f"Baseline Loam Soil Stratum {tag}",
            stratum_type="SOIL_TYPE",
            area_ha=25.0,
            is_active=True,
        )
        session.add(strat)
        await session.flush()

        sm = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            stratum_id=strat.id,
            land_unit_id=lu.id,
            valid_from=date(2026, 1, 1),
            status="ACTIVE",
        )
        session.add(sm)
        await session.commit()

        collector_token = AuthenticationService.generate_token_static(collector)
        qa_token = AuthenticationService.generate_token_static(qa_user)

        data = {
            "organization_id": str(org.id),
            "project_id": str(proj.id),
            "project_name": proj.name,
            "project_code": proj.project_code,
            "land_unit_id": str(lu.id),
            "land_unit_name": lu.name,
            "stratum_id": str(strat.id),
            "stratum_name": strat.name,
            "collector_id": str(collector.id),
            "collector_email": collector.email,
            "collector_token": collector_token,
            "qa_user_id": str(qa_user.id),
            "qa_user_email": qa_user.email,
            "qa_user_token": qa_token,
            "tag": tag,
        }
        print(json.dumps(data))


async def verify_records(project_id: str):
    p_uuid = uuid.UUID(project_id)
    async with async_session_factory() as session:
        # 1. sampling_campaigns
        c_res = await session.execute(select(SamplingCampaign).where(SamplingCampaign.project_id == p_uuid))
        campaigns = c_res.scalars().all()

        # 2. sampling_plan_versions
        spv_res = await session.execute(select(SamplingPlanVersion).where(SamplingPlanVersion.project_id == p_uuid))
        plans = spv_res.scalars().all()

        # 3. sampling_points
        pts_res = await session.execute(select(SamplingPoint).where(SamplingPoint.project_id == p_uuid))
        points = pts_res.scalars().all()

        # 4. physical_samples
        smp_res = await session.execute(select(PhysicalSample).where(PhysicalSample.project_id == p_uuid))
        samples = smp_res.scalars().all()
        sample_ids = [s.id for s in samples]

        # 5. sample_collection_events
        col_res = await session.execute(select(SampleCollectionEvent).where(SampleCollectionEvent.physical_sample_id.in_(sample_ids))) if sample_ids else []
        collections = col_res.scalars().all() if sample_ids else []

        # 6. chain_of_custody_events
        coc_res = await session.execute(select(ChainOfCustodyEvent).where(ChainOfCustodyEvent.physical_sample_id.in_(sample_ids))) if sample_ids else []
        custody_events = coc_res.scalars().all() if sample_ids else []

        # 7. laboratory_receipts
        rcp_res = await session.execute(select(LaboratoryReceipt).where(LaboratoryReceipt.physical_sample_id.in_(sample_ids))) if sample_ids else []
        receipts = rcp_res.scalars().all() if sample_ids else []

        # 8. laboratory_analyses
        ana_res = await session.execute(select(LaboratoryAnalysis).where(LaboratoryAnalysis.physical_sample_id.in_(sample_ids))) if sample_ids else []
        analyses = ana_res.scalars().all() if sample_ids else []

        # 9. laboratory_results
        res_stmt = await session.execute(select(LaboratoryResult).where(LaboratoryResult.physical_sample_id.in_(sample_ids))) if sample_ids else []
        results = res_stmt.scalars().all() if sample_ids else []

        # 10. sample_qa_reviews
        qa_res = await session.execute(select(SampleQAReview).where(SampleQAReview.physical_sample_id.in_(sample_ids))) if sample_ids else []
        qa_reviews = qa_res.scalars().all() if sample_ids else []

        summary = {
            "sampling_campaigns": [{"id": str(c.id), "code": c.campaign_code, "status": c.status} for c in campaigns],
            "sampling_plan_versions": [{"id": str(p.id), "version": p.version_number, "is_locked": p.is_locked} for p in plans],
            "sampling_points": [{"id": str(pt.id), "code": pt.point_code, "lat": pt.planned_lat, "lon": pt.planned_lon} for pt in points],
            "sample_collection_events": [{"id": str(col.id), "collector_name": col.collector_name, "dev_m": col.deviation_distance_m} for col in collections],
            "physical_samples": [{"id": str(s.id), "code": s.sample_code, "status": s.status} for s in samples],
            "chain_of_custody_events": [{"id": str(c.id), "seal": c.seal_identifier, "intact": c.seal_intact} for c in custody_events],
            "laboratory_receipts": [{"id": str(r.id), "lab": r.laboratory_name, "status": r.intake_status} for r in receipts],
            "laboratory_analyses": [{"id": str(a.id), "method": a.analytical_method, "status": a.qa_status, "qa_status": a.qa_status} for a in analyses],
            "laboratory_results": [
                {
                    "id": str(res.id),
                    "analyte": res.analyte,
                    "raw_value": float(res.raw_value) if res.raw_value is not None else None,
                    "raw_unit": res.raw_unit,
                    "normalized_value": float(res.normalized_value) if res.normalized_value is not None else None,
                    "normalized_unit": res.normalized_unit,
                    "normalization_method": res.normalization_method,
                    "normalization_version": res.normalization_version,
                    "is_superseded": res.is_superseded,
                    "supersedes_id": str(res.supersedes_id) if res.supersedes_id else None,
                }
                for res in results
            ],
            "sample_qa_reviews": [{"id": str(q.id), "status": q.overall_qa_status, "reviewer": q.reviewer_name} for q in qa_reviews],
        }
        print(json.dumps(summary, indent=2))


async def cleanup_environment(org_id: str):
    o_uuid = uuid.UUID(org_id)
    async with async_session_factory() as session:
        # Fetch projects for this org
        p_res = await session.execute(select(Project.id).where(Project.organization_id == o_uuid))
        p_ids = p_res.scalars().all()
        for pid in p_ids:
            # Delete agriculture child tables
            smp_res = await session.execute(select(PhysicalSample.id).where(PhysicalSample.project_id == pid))
            s_ids = smp_res.scalars().all()
            if s_ids:
                await session.execute(text("DELETE FROM sample_qa_reviews WHERE physical_sample_id = ANY(:s_ids)"), {"s_ids": s_ids})
                await session.execute(text("DELETE FROM laboratory_results WHERE physical_sample_id = ANY(:s_ids)"), {"s_ids": s_ids})
                await session.execute(text("DELETE FROM laboratory_analyses WHERE physical_sample_id = ANY(:s_ids)"), {"s_ids": s_ids})
                await session.execute(text("DELETE FROM laboratory_receipts WHERE physical_sample_id = ANY(:s_ids)"), {"s_ids": s_ids})
                await session.execute(text("DELETE FROM chain_of_custody_events WHERE physical_sample_id = ANY(:s_ids)"), {"s_ids": s_ids})
                await session.execute(text("DELETE FROM sample_collection_events WHERE physical_sample_id = ANY(:s_ids)"), {"s_ids": s_ids})
                await session.execute(text("DELETE FROM physical_samples WHERE id = ANY(:s_ids)"), {"s_ids": s_ids})
            await session.execute(text("DELETE FROM sampling_points WHERE project_id = :pid"), {"pid": pid})
            await session.execute(text("DELETE FROM sampling_plan_versions WHERE project_id = :pid"), {"pid": pid})
            await session.execute(text("DELETE FROM sampling_campaigns WHERE project_id = :pid"), {"pid": pid})
            await session.execute(text("DELETE FROM agriculture_stratum_memberships WHERE land_unit_id IN (SELECT id FROM land_units WHERE project_id = :pid)"), {"pid": pid})
            await session.execute(text("DELETE FROM agriculture_strata WHERE project_id = :pid"), {"pid": pid})
            await session.execute(text("DELETE FROM land_units WHERE project_id = :pid"), {"pid": pid})
            await session.execute(text("DELETE FROM project_boundary_versions WHERE project_id = :pid"), {"pid": pid})
            await session.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": pid})

        await session.execute(text("DELETE FROM users WHERE organization_id = :org_id"), {"org_id": o_uuid})
        await session.execute(text("DELETE FROM organizations WHERE id = :org_id"), {"org_id": o_uuid})
        await session.commit()
        print(f"CLEANUP_SUCCESS: Organization {org_id} and all child records deleted cleanly.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_live_fullstack_helper.py [setup|verify <project_id>|cleanup <org_id>]")
        sys.exit(1)

    action = sys.argv[1]
    if action == "setup":
        asyncio.run(setup_test_environment())
    elif action == "verify" and len(sys.argv) >= 3:
        asyncio.run(verify_records(sys.argv[2]))
    elif action == "cleanup" and len(sys.argv) >= 3:
        asyncio.run(cleanup_environment(sys.argv[2]))
    else:
        print(f"Unknown action or missing args: {action}")
        sys.exit(1)
