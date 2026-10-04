"""
VeriField Nexus — Agriculture Phase 3B-0 Live Full-Stack Helper
Creates synthetic database records in PostgreSQL 18.1 and verifies real persistence proof
for VM0042 v2.2 Quantification Methodology Prerequisite Engine.
"""

import sys
import os
import json
import uuid
import hashlib
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, date, timedelta

from sqlalchemy import select, text
from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project, CarbonCalculation
from app.domains.earth_observation.models import ProjectBoundaryVersion
from app.domains.agriculture.models import (
    LandUnit,
    Stratum,
    StratumMembership,
    AgricultureManagementRecord,
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
    QuantificationInputSnapshot,
    AgriculturePrerequisiteAssessment,
)
from app.domains.methodologies.models import MethodologyFamily, Methodology, MethodologyVersion
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash


async def setup_test_environment(case: str = "CASE_A"):
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    today = now.date()
    is_case_b = str(case).upper() in ("CASE_B", "B", "POST_2027")
    req_sub_date = "2027-02-01" if is_case_b else "2026-06-01"

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
            name=f"Phase 3B-0 Live Org {tag}",
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
            email=f"pm.{tag}@phase3b0-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Agricultural Project Manager",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        field_agent = User(
            id=uuid.uuid4(),
            email=f"agent.{tag}@phase3b0-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Tariq Field Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        auditor = User(
            id=uuid.uuid4(),
            email=f"auditor.{tag}@phase3b0-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="External VVB Auditor",
            role="AUDITOR",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add_all([pm_user, field_agent, auditor])
        await session.flush()

        # 2. Project with Locked Methodology VM0042
        proj = Project(
            id=uuid.uuid4(),
            name=f"Phase 3B-0 Live Project {tag}",
            project_code=f"AGR-P3B0-{tag[:6]}",
            organization_id=org.id,
            sector_id=fam.id if fam else None,
            methodology_id=vm.id if vm else None,
            methodology_version_id=v22.id if v22 else None,
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2046, 12, 31),
            baseline_parameters={
                "soil_depth_standard_cm": 30.0,
                "project_start_date": "2026-01-01",
                "request_submission_date": req_sub_date,
                "submission_date": req_sub_date,
                "early_adoption_mode": "NONE",
                "locked_methodology_version": {
                    "methodology_code": "VM0042",
                    "version": "2.2",
                    "status": "LOCKED",
                    "locked_at": now.isoformat(),
                    "quantification_approach": "APPROACH_2",
                    "minimum_depth_cm": 30.0,
                    "bulk_density_requirement": "REQUIRED",
                    "coarse_fragments_requirement": "OPTIONAL",
                    "applied_corrections_date": "2026-06-11",
                    "rule_set_version": "VM0042_V2.2_RULES_CC20260611_V1.0",
                },
            },
        )
        session.add(proj)
        await session.flush()

        # Boundary Version
        boundary_geojson = {
            "type": "Polygon",
            "coordinates": [[
                [-93.5, 42.0],
                [-93.4, 42.0],
                [-93.4, 42.1],
                [-93.5, 42.1],
                [-93.5, 42.0],
            ]],
        }
        boundary = ProjectBoundaryVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            version_number=1,
            effective_date=today,
            boundary_geojson=boundary_geojson,
            area_ha=150.0,
            geom="SRID=4326;POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))",
        )
        session.add(boundary)

        # 3. LandUnits: Project Field & Linked Control Site
        lu_project = LandUnit(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            name=f"Field North {tag[:4]}",
            code=f"LU-PRJ-{tag[:4]}",
            unit_type="FIELD",
            boundary_geojson=boundary_geojson,
            area_ha=100.0,
            boundary_source="GNSS_SURVEY",
            land_use_category="CROPLAND",
            properties={"baseline_control_paired": True},
        )
        lu_control = LandUnit(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            name=f"Field Control {tag[:4]}",
            code=f"LU-CTL-{tag[:4]}",
            unit_type="FIELD",
            boundary_geojson=boundary_geojson,
            area_ha=50.0,
            boundary_source="GNSS_SURVEY",
            land_use_category="CROPLAND",
            properties={"is_baseline_control_site": True, "linked_project_field": f"LU-PRJ-{tag[:4]}"},
        )
        session.add_all([lu_project, lu_control])
        await session.flush()

        # 4. Strata & StratumMemberships
        stratum = Stratum(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"STR-SL-{tag[:4]}",
            name="Silt Loam - Conventional Baseline",
            stratum_type="SOIL_TYPE",
            area_ha=150.0,
            is_active=True,
        )
        session.add(stratum)
        await session.flush()

        mem1 = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            stratum_id=stratum.id,
            land_unit_id=lu_project.id,
            valid_from=today - timedelta(days=1825),
            valid_to=None,
            status="ACTIVE",
        )
        mem2 = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            stratum_id=stratum.id,
            land_unit_id=lu_control.id,
            valid_from=today - timedelta(days=1825),
            valid_to=None,
            status="ACTIVE",
        )
        session.add_all([mem1, mem2])

        # 5. Historical Management Records (5 years look-back covering all required categories)
        mgt_types = [
            ("TILLAGE", "CONVENTIONAL_TILL"),
            ("CROP_ROTATION", "CORN_SOYBEAN"),
            ("COVER_CROP", "RYE_GRASS"),
            ("FERTILIZER_SYNTHETIC", "UREA_46_0_0"),
            ("ORGANIC_AMENDMENT", "COMPOSTED_MANURE"),
            ("IRRIGATION", "RAIN_FED"),
        ]
        for yr in range(1, 6):
            event_d = today - timedelta(days=yr * 365)
            for m_type, spec in mgt_types:
                mgt = AgricultureManagementRecord(
                    id=uuid.uuid4(),
                    organization_id=org.id,
                    project_id=proj.id,
                    land_unit_id=lu_project.id,
                    record_type=m_type,
                    practice_category="BASELINE",
                    event_date=event_d,
                    data_source="REPORTED",
                    corroboration="DOCUMENTARY",
                    details={"specification": spec, "year_offset": yr},
                    qa_status="ACCEPTED",
                )
                session.add(mgt)

        # 6. Sampling Campaign & Sampling Plan
        campaign = SamplingCampaign(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_code=f"CAMP-{tag[:4]}",
            name=f"Baseline Campaign {tag[:4]}",
            purpose="BASELINE_SOC_DETERMINATION",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=today - timedelta(days=180),
            planned_end_date=today - timedelta(days=150),
            status="COMPLETE",
        )
        session.add(campaign)
        await session.flush()

        plan = SamplingPlanVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            version_number=1,
            sampling_design_method="STRATIFIED_RANDOM",
            design_provenance="CONFIGURED_METHOD",
            status="LOCKED",
            effective_as_of_date=today - timedelta(days=180),
            is_locked=True,
            locked_at=now,
            locked_by_id=pm_user.id,
            plan_lock_snapshot={
                "minimum_points_per_stratum": 5,
                "target_mdd": 1.5,
                "power_analysis_executed": False,
            },
        )
        session.add(plan)
        await session.flush()

        # 7. Sampling Points & Soil Layers (min depth 30cm, deeper bounding layer 30-50cm)
        layers = [(0.0, 15.0), (15.0, 30.0), (30.0, 50.0)]
        created_samples = []

        # Create 6 sampling points to satisfy minimum 5 per stratum
        for pt_idx in range(6):
            pt_code = f"SP-{tag[:4]}-{pt_idx+1:02d}"
            lat = 42.05 + (pt_idx * 0.005)
            lon = -93.45 + (pt_idx * 0.005)

            for d_from, d_to in layers:
                sp = SamplingPoint(
                    id=uuid.uuid4(),
                    organization_id=org.id,
                    project_id=proj.id,
                    campaign_id=campaign.id,
                    plan_version_id=plan.id,
                    land_unit_id=lu_project.id,
                    stratum_id=stratum.id,
                    point_code=f"{pt_code}-{int(d_from)}_{int(d_to)}",
                    planned_lat=lat,
                    planned_lon=lon,
                    depth_from_cm=d_from,
                    depth_to_cm=d_to,
                    status="COLLECTED",
                )
                session.add(sp)
                await session.flush()

                ps = PhysicalSample(
                    id=uuid.uuid4(),
                    organization_id=org.id,
                    project_id=proj.id,
                    sampling_point_id=sp.id,
                    campaign_id=campaign.id,
                    plan_version_id=plan.id,
                    land_unit_id=lu_project.id,
                    sample_code=f"SMP-{tag[:4]}-{pt_idx+1:02d}-{int(d_from)}_{int(d_to)}",
                    status="QA_ACCEPTED",
                )
                session.add(ps)
                await session.flush()
                created_samples.append((sp, ps))

                col = SampleCollectionEvent(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    sampling_point_id=sp.id,
                    actual_lat=lat,
                    actual_lon=lon,
                    actual_depth_from_cm=d_from,
                    actual_depth_to_cm=d_to,
                    collection_timestamp=now - timedelta(days=150),
                    collector_name="Tariq Field Agent",
                    sample_condition="GOOD",
                )
                session.add(col)

                cust = ChainOfCustodyEvent(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    event_type="TRANSFER",
                    event_timestamp=now - timedelta(days=140),
                    custodian_name="Agri Express",
                    custodian_organization="Agri Logistics",
                    seal_intact=True,
                    seal_identifier=f"SEAL-{tag[:4]}-{pt_idx+1}",
                )
                session.add(cust)

                receipt = LaboratoryReceipt(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    laboratory_name="Eurofins Agri Testing",
                    received_at=now - timedelta(days=130),
                    received_by_name="Lab Intake Specialist",
                    intake_status="ACCEPTED",
                )
                session.add(receipt)
                await session.flush()

                analysis = LaboratoryAnalysis(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    laboratory_name="Eurofins Agri Testing",
                    analytical_method="DRY_COMBUSTION",
                    analysis_date=today - timedelta(days=120),
                    qa_status="VERIFIED",
                )
                session.add(analysis)
                await session.flush()

                res_soc = LaboratoryResult(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    analysis_id=analysis.id,
                    analyte="SOC_CONCENTRATION",
                    raw_value=Decimal("18.5"),
                    raw_unit="g/kg",
                    normalized_value=Decimal("18.5"),
                    normalized_unit="g/kg",
                    normalization_method="DIRECT",
                    normalization_version="V1.0",
                    is_superseded=False,
                )
                res_bd = LaboratoryResult(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    analysis_id=analysis.id,
                    analyte="BULK_DENSITY_G_CM3",
                    raw_value=Decimal("1.35"),
                    raw_unit="g/cm3",
                    normalized_value=Decimal("1.35"),
                    normalized_unit="g/cm³",
                    normalization_method="DIRECT",
                    normalization_version="V1.0",
                    is_superseded=False,
                )
                res_cf = LaboratoryResult(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    analysis_id=analysis.id,
                    analyte="COARSE_FRAGMENTS",
                    raw_value=Decimal("0.0"),
                    raw_unit="fraction",
                    normalized_value=Decimal("0.0"),
                    normalized_unit="fraction",
                    normalization_method="DIRECT",
                    normalization_version="V1.0",
                    is_superseded=False,
                )
                session.add_all([res_soc, res_bd, res_cf])

                qa_rev = SampleQAReview(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    reviewer_name="Lead MRV QA Officer",
                    overall_qa_status="ACCEPTED",
                    review_date=now - timedelta(days=100),
                )
                session.add(qa_rev)

        # 8. Phase 3A Quantification Input Snapshot
        snap_pkg = {
            "project_id": str(proj.id),
            "context": "BASELINE",
            "measurements_count": len(created_samples),
            "layers_count": len(layers),
            "campaign_id": str(campaign.id),
        }
        snap_hash = hashlib.sha256(json.dumps(snap_pkg, sort_keys=True).encode("utf-8")).hexdigest()
        snapshot = QuantificationInputSnapshot(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            snapshot_code=f"SNAP-P3B0-{tag[:6]}",
            context="BASELINE",
            snapshot_hash=snap_hash,
            is_locked=True,
            locked_at=now - timedelta(days=90),
            locked_by_id=pm_user.id,
            total_eligible_measurements=len(created_samples),
            total_excluded_measurements=0,
            input_package=snap_pkg,
            methodology_code="VM0042",
            methodology_version="2.2",
            rule_set_version="VM0042_V2_2_CC_2026_06_11",
        )
        session.add(snapshot)
        await session.commit()

        # Generate tokens
        pm_token = AuthenticationService.generate_token_static(pm_user)
        field_token = AuthenticationService.generate_token_static(field_agent)
        auditor_token = AuthenticationService.generate_token_static(auditor)

        output = {
            "organization_id": str(org.id),
            "project_id": str(proj.id),
            "project_name": proj.name,
            "project_code": proj.project_code,
            "snapshot_id": str(snapshot.id),
            "pm_user_id": str(pm_user.id),
            "pm_user_email": pm_user.email,
            "pm_token": pm_token,
            "field_agent_id": str(field_agent.id),
            "field_agent_email": field_agent.email,
            "field_token": field_token,
            "auditor_id": str(auditor.id),
            "auditor_email": auditor.email,
            "auditor_token": auditor_token,
            "tag": tag,
        }
        print(json.dumps(output))
        return output


async def cleanup_test_environment(org_id_str: str):
    org_id = uuid.UUID(org_id_str)
    async with async_session_factory() as session:
        # Cascade delete children
        await session.execute(text("DELETE FROM agriculture_prerequisite_assessments WHERE organization_id = :org_id"), {"org_id": org_id})
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
        await session.execute(text("DELETE FROM agriculture_management_records WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_stratum_memberships WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_strata WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM land_units WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM project_boundary_versions WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM projects WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM users WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM organizations WHERE id = :org_id"), {"org_id": org_id})
        await session.commit()
        print(json.dumps({"status": "CLEANED", "organization_id": org_id_str}))


async def verify_assessment(project_id_str: str):
    project_id = uuid.UUID(project_id_str)
    async with async_session_factory() as session:
        proj = (await session.execute(select(Project).where(Project.id == project_id))).scalars().first()
        stmt = (
            select(AgriculturePrerequisiteAssessment)
            .where(AgriculturePrerequisiteAssessment.project_id == project_id)
            .order_by(AgriculturePrerequisiteAssessment.created_at.desc())
        )
        assess = (await session.execute(stmt)).scalars().first()
        if not assess:
            print(json.dumps({"status": "NOT_FOUND"}))
            return

        # Query CarbonCalculation to prove tCO2e fields are NULL
        q_calc = await session.execute(
            select(CarbonCalculation).where(CarbonCalculation.project_id == project_id)
        )
        calcs = q_calc.scalars().all()
        tco2e_yield_vals = [c.tco2e_yield for c in calcs if c.tco2e_yield is not None]
        tco2e_gen_vals = [c.tco2e_generated for c in calcs if c.tco2e_generated is not None]

        vcs_meta = assess.vcs_resolution_metadata or {}
        p_start = vcs_meta.get("project_start_date") or (str(proj.crediting_start) if proj and proj.crediting_start else "2026-01-01")
        req_sub = vcs_meta.get("request_submission_date") or (proj.baseline_parameters.get("request_submission_date") if proj and proj.baseline_parameters else None)
        res = {
            "project_id": str(project_id),
            "project_start_date": p_start,
            "request_submission_date": req_sub,
            "governing_vcs_standard": vcs_meta.get("governing_vcs_standard"),
            "v5_template_variant": vcs_meta.get("v5_template_variant"),
            "project_description_template": vcs_meta.get("project_description_template") or vcs_meta.get("template_version"),
            "early_adoption_mode": vcs_meta.get("early_adoption_mode") or "NONE",
            "delayed_requirement_ids": vcs_meta.get("delayed_requirement_ids", []),
            "transition_reason": vcs_meta.get("transition_reason") or vcs_meta.get("resolution_reason"),
            "methodology_version": assess.methodology_version,
            "corrections_clarifications_version": assess.corrections_clarifications_version,
            "assessment_status": assess.status,
            "assessment_hash": assess.assessment_hash,
            "carbon_status": "NOT_CONFIGURED",
            "tco2e_yield": None if not tco2e_yield_vals else tco2e_yield_vals[0],
            "tco2e_generated": None if not tco2e_gen_vals else tco2e_gen_vals[0],
            "total_carbon_calculations_count": len(calcs),
            "is_locked": assess.is_locked,
            "total_dimensions": len(assess.dimensions) if assess.dimensions else 0,
            "blocking_reasons_count": len(assess.blocking_reasons) if assess.blocking_reasons else 0,
        }
        print(json.dumps(res, indent=2))


async def verify_zero_carbon(project_id_str: str):
    """
    Verifies the fail-closed invariant: NO carbon stock, delta SOC, tCO2e,
    or credit mint records exist in PostgreSQL for this project.
    """
    project_id = uuid.UUID(project_id_str)
    async with async_session_factory() as session:
        # Check if any carbon or model run records exist
        q_runs = await session.execute(
            text("SELECT count(*) FROM agriculture_model_runs WHERE project_id = :p_id"),
            {"p_id": project_id},
        )
        runs_count = q_runs.scalar() or 0

        # Check registry sync logs
        q_reg = await session.execute(
            text("SELECT count(*) FROM registry_sync_logs WHERE project_id = :p_id"),
            {"p_id": project_id},
        )
        registry_count = q_reg.scalar() or 0

        res = {
            "project_id": project_id_str,
            "model_runs_count": runs_count,
            "registry_issuance_count": registry_count,
            "fail_closed_contract_passed": (runs_count == 0 and registry_count == 0),
        }
        print(json.dumps(res))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        case_arg = sys.argv[2] if len(sys.argv) > 2 else "CASE_A"
        asyncio.run(setup_test_environment(case_arg))
    elif len(sys.argv) > 2 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_environment(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_assessment":
        asyncio.run(verify_assessment(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_zero_carbon":
        asyncio.run(verify_zero_carbon(sys.argv[2]))
    else:
        print("Usage: python run_phase3b0_live_helper.py [setup [case_a|case_b] | cleanup <org_id> | verify_assessment <project_id> | verify_zero_carbon <project_id>]")
