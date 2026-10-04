"""
VeriField Nexus — Agriculture Phase 3A Live Full-Stack Helper
Creates synthetic database records and queries real PostgreSQL 18 for persistence proof.
"""

import sys
import os
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
    QuantificationInputSnapshot,
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
            name=f"Phase 3A Live Org {tag}",
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
            email=f"pm.{tag}@phase3a-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Agricultural Project Manager",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        field_agent = User(
            id=uuid.uuid4(),
            email=f"agent.{tag}@phase3a-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Tariq Field Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add_all([pm_user, field_agent])
        await session.flush()

        # 2. Project with Locked Methodology
        proj = Project(
            id=uuid.uuid4(),
            name=f"Phase 3A Live Project {tag}",
            project_code=f"AGR-P3A-{tag[:6]}",
            organization_id=org.id,
            sector_id=fam.id if fam else None,
            methodology_id=vm.id if vm else None,
            methodology_version_id=v22.id if v22 else None,
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2046, 12, 31),
            baseline_parameters={
                "soil_depth_standard_cm": 30.0,
                "locked_methodology_version": {
                    "methodology_code": "VM0042",
                    "version": "2.2",
                    "status": "LOCKED",
                    "locked_at": now.isoformat(),
                    "quantification_approach": "DIRECT_MEASUREMENT",
                    "minimum_depth_cm": 30.0,
                    "design_sufficiency_status": "NOT_APPLICABLE",
                    "design_sufficiency_requirement": "NOT_APPLICABLE",
                    "design_sufficiency_blocking": False,
                    "bulk_density_requirement": "REQUIRED",
                    "coarse_fragments_requirement": "OPTIONAL",
                },
            },
        )
        session.add(proj)
        await session.flush()

        # 3. Boundary Version
        boundary = ProjectBoundaryVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            version_number=1,
            effective_date=today,
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]],
            },
            area_ha=50.0,
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
        )
        session.add(boundary)

        # 4. Land Unit
        lu = LandUnit(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            name=f"Plot Alpha {tag[:4]}",
            code=f"LU-{tag[:4]}",
            area_ha=50.0,
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
            name=f"Clay Loam {tag[:4]}",
            stratum_type="SOIL_TYPE",
            area_ha=50.0,
            is_active=True,
        )
        session.add(strat)
        await session.flush()

        sm = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            stratum_id=strat.id,
            land_unit_id=lu.id,
            valid_from=date(2025, 1, 1),
            valid_to=None,
            status="ACTIVE",
        )
        session.add(sm)

        # 6. Sampling Campaign & Plan Version (Locked)
        campaign = SamplingCampaign(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_code=f"CAMP-{tag[:4]}",
            name=f"Baseline Campaign {tag[:4]}",
            purpose="BASELINE_SOC_DETERMINATION",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=date(2026, 1, 10),
            planned_end_date=date(2026, 2, 10),
            status="COMPLETE",
            project_boundary_version_id=boundary.id,
        )
        session.add(campaign)
        await session.flush()

        plan_version = SamplingPlanVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            version_number=1,
            status="LOCKED",
            effective_as_of_date=date(2026, 1, 10),
            is_locked=True,
            locked_at=now,
            locked_by_id=pm_user.id,
        )
        session.add(plan_version)
        await session.flush()

        # 7. Eligible Sample (0-30cm standard match)
        pt1 = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan_version.id,
            land_unit_id=lu.id,
            stratum_id=strat.id,
            point_code=f"P1-{tag[:4]}",
            planned_lat=28.52,
            planned_lon=77.12,
            depth_from_cm=0.0,
            depth_to_cm=30.0,
            status="COLLECTED",
        )
        session.add(pt1)
        await session.flush()

        sample1 = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan_version.id,
            sampling_point_id=pt1.id,
            land_unit_id=lu.id,
            sample_code=f"SMP1-{tag[:4]}",
            status="QA_ACCEPTED",
        )
        session.add(sample1)
        await session.flush()

        col1 = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            sampling_point_id=pt1.id,
            actual_lat=28.52002,
            actual_lon=77.12002,
            actual_depth_from_cm=0.0,
            actual_depth_to_cm=30.0,
            collection_timestamp=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            collector_name="Tariq Field Agent",
            sample_condition="GOOD",
        )
        session.add(col1)

        cust1 = ChainOfCustodyEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            event_type="TRANSFER",
            event_timestamp=datetime(2026, 1, 16, 10, 0, tzinfo=timezone.utc),
            custodian_name="Agri Express",
            custodian_organization="Agri Logistics",
            seal_intact=True,
            seal_identifier=f"SEAL-{tag[:4]}",
        )
        session.add(cust1)

        rcp1 = LaboratoryReceipt(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            laboratory_name="Eurofins Agri Testing",
            received_at=datetime(2026, 1, 17, 9, 0, tzinfo=timezone.utc),
            received_by_name="Lab Intake Specialist",
            intake_status="ACCEPTED",
        )
        session.add(rcp1)

        ana1 = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            laboratory_name="Eurofins Agri Testing",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2026, 1, 20),
            qa_status="VERIFIED",
        )
        session.add(ana1)
        await session.flush()

        res_soc = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana1.id,
            physical_sample_id=sample1.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.85"),
            raw_unit="%",
            normalized_value=Decimal("18.5"),
            normalized_unit="g/kg",
            normalization_method="LINEAR_SCALING:VAL*10",
            normalization_version="UNIT_CONV_V1.0",
            is_superseded=False,
        )
        session.add(res_soc)

        res_bd = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana1.id,
            physical_sample_id=sample1.id,
            analyte="BULK_DENSITY_G_CM3",
            raw_value=Decimal("1.35"),
            raw_unit="g/cm3",
            normalized_value=Decimal("1.35"),
            normalized_unit="g/cm³",
            is_superseded=False,
        )
        session.add(res_bd)

        qa1 = SampleQAReview(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            reviewer_name="Lead MRV QA Officer",
            overall_qa_status="ACCEPTED",
            review_date=datetime(2026, 1, 22, 14, 0, tzinfo=timezone.utc),
        )
        session.add(qa1)

        # 8. Excluded Sample (Depth Mismatch: 30-60cm)
        pt2 = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan_version.id,
            land_unit_id=lu.id,
            stratum_id=strat.id,
            point_code=f"P2-DEEP-{tag[:4]}",
            planned_lat=28.53,
            planned_lon=77.13,
            depth_from_cm=30.0,
            depth_to_cm=60.0,
            status="COLLECTED",
        )
        session.add(pt2)
        await session.flush()

        sample2 = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan_version.id,
            sampling_point_id=pt2.id,
            land_unit_id=lu.id,
            sample_code=f"SMP2-DEEP-{tag[:4]}",
            status="QA_ACCEPTED",
        )
        session.add(sample2)
        await session.flush()

        col2 = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            sampling_point_id=pt2.id,
            actual_lat=28.53,
            actual_lon=77.13,
            actual_depth_from_cm=30.0,
            actual_depth_to_cm=60.0,
            collection_timestamp=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
            collector_name="Tariq Field Agent",
        )
        session.add(col2)

        cust2 = ChainOfCustodyEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            event_type="TRANSFER",
            event_timestamp=datetime(2026, 1, 16, 11, 0, tzinfo=timezone.utc),
            custodian_name="Agri Express",
            custodian_organization="Agri Logistics",
            seal_intact=True,
            seal_identifier=f"SEAL-DEEP-{tag[:4]}",
        )
        session.add(cust2)

        rcp2 = LaboratoryReceipt(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            laboratory_name="Eurofins Agri Testing",
            received_at=datetime(2026, 1, 17, 9, 0, tzinfo=timezone.utc),
            received_by_name="Lab Intake Specialist",
            intake_status="ACCEPTED",
        )
        session.add(rcp2)

        ana2 = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            laboratory_name="Eurofins Agri Testing",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2026, 1, 20),
            qa_status="VERIFIED",
        )
        session.add(ana2)
        await session.flush()

        res_deep = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana2.id,
            physical_sample_id=sample2.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("0.85"),
            raw_unit="%",
            normalized_value=Decimal("8.5"),
            normalized_unit="g/kg",
            is_superseded=False,
        )
        session.add(res_deep)

        qa2 = SampleQAReview(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            reviewer_name="Lead MRV QA Officer",
            overall_qa_status="ACCEPTED",
            review_date=datetime(2026, 1, 22, 14, 0, tzinfo=timezone.utc),
        )
        session.add(qa2)

        await session.commit()

        pm_token = AuthenticationService.generate_token_static(pm_user)
        field_token = AuthenticationService.generate_token_static(field_agent)

        output = {
            "organization_id": str(org.id),
            "project_id": str(proj.id),
            "project_name": proj.name,
            "project_code": proj.project_code,
            "pm_user_id": str(pm_user.id),
            "pm_user_email": pm_user.email,
            "pm_token": pm_token,
            "field_agent_id": str(field_agent.id),
            "field_agent_email": field_agent.email,
            "field_token": field_token,
            "sample1_code": sample1.sample_code,
            "sample2_code": sample2.sample_code,
            "tag": tag,
        }
        print(json.dumps(output))


async def cleanup_test_environment(org_id_str: str):
    org_id = uuid.UUID(org_id_str)
    async with async_session_factory() as session:
        # Delete children in proper foreign-key order
        await session.execute(text("DELETE FROM quantification_input_snapshots WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("""
            DELETE FROM sample_qa_reviews WHERE physical_sample_id IN (
                SELECT id FROM physical_samples WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
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
        print(json.dumps({"status": "CLEANED", "organization_id": org_id_str}))


async def verify_snapshot(project_id_str: str):
    project_id = uuid.UUID(project_id_str)
    async with async_session_factory() as session:
        stmt = (
            select(QuantificationInputSnapshot)
            .where(QuantificationInputSnapshot.project_id == project_id)
            .order_by(QuantificationInputSnapshot.created_at.desc())
        )
        snap = (await session.execute(stmt)).scalars().first()
        if not snap:
            print(json.dumps({"status": "NOT_FOUND"}))
            return

        canonical_bytes = json.dumps(snap.input_package, sort_keys=True, default=str).encode("utf-8")
        expected_hash = hashlib.sha256(canonical_bytes).hexdigest()
        is_hash_valid = snap.snapshot_hash == expected_hash

        res = {
            "snapshot_id": str(snap.id),
            "snapshot_code": snap.snapshot_code,
            "snapshot_hash": snap.snapshot_hash,
            "expected_hash": expected_hash,
            "is_hash_valid": is_hash_valid,
            "is_locked": snap.is_locked,
            "total_eligible_measurements": snap.total_eligible_measurements,
            "total_excluded_measurements": snap.total_excluded_measurements,
            "context": snap.context,
            "methodology_code": snap.methodology_code,
            "methodology_version": snap.methodology_version,
            "rule_set_version": snap.rule_set_version,
        }
        print(json.dumps(res))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        asyncio.run(setup_test_environment())
    elif len(sys.argv) > 2 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_environment(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_snapshot":
        asyncio.run(verify_snapshot(sys.argv[2]))
    else:
        print("Usage: python run_phase3a_live_helper.py [setup | cleanup <org_id> | verify_snapshot <project_id>]")
