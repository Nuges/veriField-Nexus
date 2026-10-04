"""
VeriField Nexus — Agriculture Phase 3B-1 Live Full-Stack Helper
Creates synthetic database records in PostgreSQL with sampling points, layers,
and locked prerequisite assessment, enabling live browser E2E verification of
VM0042 v2.2 SOC Stock & Equivalent Soil Mass Engine.
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
    AgricultureSOCStockSnapshot,
    AgricultureSOCStockResult,
    AgricultureSOCLayerResult,
)
from app.domains.methodologies.models import MethodologyFamily, Methodology, MethodologyVersion
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash


async def setup_test_environment(divergent_bd: bool = False):
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
            name=f"Phase 3B-1 Live Org {tag}",
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
            email=f"pm.{tag}@phase3b1-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Agricultural Project Manager",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        field_agent = User(
            id=uuid.uuid4(),
            email=f"agent.{tag}@phase3b1-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Tariq Field Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        auditor = User(
            id=uuid.uuid4(),
            email=f"auditor.{tag}@phase3b1-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="External VVB Auditor",
            role="AUDITOR",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add_all([pm_user, field_agent, auditor])
        await session.flush()

        # 2. Project
        proj = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=f"VM0042 SOC Stock Pilot {tag}",
            project_code=f"AGRI-3B1-{tag[:6].upper()}",
            sector_id=fam.id if fam else None,
            methodology_id=vm.id if vm else None,
            methodology_version_id=v22.id if v22 else None,
            country="Kenya",
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2036, 1, 1),
            baseline_parameters={
                "methodology_version": "2.2",
                "vcs_standard_version": "VCS_4_7",
                "project_start_date": "2026-01-01",
                "request_submission_date": "2026-06-01",
                "crediting_period_type": "RENEWABLE_10_YEAR",
                "early_adoption_requested": False,
            },
        )
        session.add(proj)
        await session.flush()

        # Boundary
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
            area_ha=100.0,
            geom="SRID=4326;POLYGON((-93.5 42.0, -93.4 42.0, -93.4 42.1, -93.5 42.1, -93.5 42.0))",
        )
        session.add(boundary)

        # 3. Land Unit & Stratum
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
        session.add(lu_project)
        await session.flush()

        stratum = Stratum(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"STR-SL-{tag[:4]}",
            name="Silt Loam - Baseline Stratum",
            stratum_type="SOIL_TYPE",
            area_ha=100.0,
            is_active=True,
        )
        session.add(stratum)
        await session.flush()

        mem = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            stratum_id=stratum.id,
            land_unit_id=lu_project.id,
            valid_from=today - timedelta(days=1825),
            valid_to=None,
            status="ACTIVE",
        )
        session.add(mem)

        # 4. Sampling Campaign & Plan
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

        # 5. Sampling Points & Soil Layers
        layers = [(0.0, 15.0), (15.0, 30.0)]
        created_samples = []

        bd1 = Decimal("1.42") if divergent_bd else Decimal("1.25")
        bd2 = Decimal("1.48") if divergent_bd else Decimal("1.35")

        for pt_idx in range(6):
            pt_code = f"SP-{tag[:4]}-{pt_idx+1:02d}"
            lat = 42.05 + (pt_idx * 0.005)
            lon = -93.45 + (pt_idx * 0.005)

            for d_idx, (d_from, d_to) in enumerate(layers):
                prof_code = f"PROF-{tag[:4]}-{pt_idx+1:02d}"
                sp = SamplingPoint(
                    id=uuid.uuid4(),
                    organization_id=org.id,
                    project_id=proj.id,
                    campaign_id=campaign.id,
                    plan_version_id=plan.id,
                    land_unit_id=lu_project.id,
                    stratum_id=stratum.id,
                    point_code=f"{pt_code}-{int(d_from)}_{int(d_to)}",
                    soil_profile_id=prof_code,
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
                    soil_profile_id=prof_code,
                    core_count=1,
                    core_diameter_mm=Decimal("50.00"),
                    status="COLLECTED",
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

                layer_bd = bd1 if d_idx == 0 else bd2
                layer_soc = Decimal("21.5") if d_idx == 0 else Decimal("12.0")

                res_soc = LaboratoryResult(
                    id=uuid.uuid4(),
                    physical_sample_id=ps.id,
                    analysis_id=analysis.id,
                    analyte="SOC_CONCENTRATION",
                    raw_value=layer_soc,
                    raw_unit="g/kg",
                    normalized_value=layer_soc,
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
                    raw_value=layer_bd,
                    raw_unit="g/cm3",
                    normalized_value=layer_bd,
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
                    raw_value=Decimal("0.02"),
                    raw_unit="fraction",
                    normalized_value=Decimal("0.02"),
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

        # 6. Phase 3A Quantification Input Snapshot
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
            snapshot_code=f"SNAP-P3B1-{tag[:6]}",
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
        await session.flush()

        # 7. Phase 3B-0 Prerequisite Assessment
        assess_hash = hashlib.sha256(f"prereq-{tag}".encode()).hexdigest()
        assessment = AgriculturePrerequisiteAssessment(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            snapshot_id=snapshot.id,
            assessment_code=f"PREREQ-P3B1-{tag[:6]}",
            version=1,
            status="LOCKED",
            overall_readiness="READY",
            methodology_code="VM0042",
            methodology_version="2.2",
            corrections_clarifications_version="2026-06-11",
            rule_set_version="VM0042_V2_2_CC_2026_06_11",
            vcs_standard_version="VCS_4_7",
            vcs_resolution_metadata={
                "governing_vcs_standard": "VCS_4_7",
                "v5_template_variant": "NONE",
                "project_description_template": "VCS_PROJECT_DESCRIPTION_V4.4",
                "early_adoption_mode": "NONE",
                "resolution_reason": "VCS 4.7 Standard baseline",
            },
            assessment_hash=assess_hash,
            is_locked=True,
            locked_at=now - timedelta(days=30),
            locked_by_id=pm_user.id,
            created_by_id=pm_user.id,
            dimensions={
                "METHODOLOGY_RULESET": {"status": "READY", "finding_type": "BLOCKING", "blocking": False},
                "VCS_PROGRAM_RULESET": {"status": "READY", "finding_type": "BLOCKING", "blocking": False},
                "QUANTIFICATION_UNIT": {"status": "READY", "finding_type": "BLOCKING", "blocking": False},
                "DEPTH": {"status": "READY", "finding_type": "BLOCKING", "blocking": False},
                "ESM_INPUTS": {"status": "READY", "finding_type": "BLOCKING", "blocking": False},
                "LABORATORY_QA": {"status": "READY", "finding_type": "BLOCKING", "blocking": False},
            },
            quantification_route_map={
                "selected_route": "ESM_DIRECT_MEASUREMENT",
                "status": "READY",
            },
            notes="Authoritative locked prerequisite dossier for Phase 3B-1 testing.",
        )
        session.add(assessment)
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
            "prerequisite_id": str(assessment.id),
            "prerequisite_code": assessment.assessment_code,
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
        await session.execute(text("DELETE FROM agriculture_soc_layer_results WHERE stock_result_id IN (SELECT id FROM agriculture_soc_stock_results WHERE organization_id = :org_id)"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_soc_stock_results WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_soc_stock_snapshots WHERE organization_id = :org_id"), {"org_id": org_id})
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
        await session.execute(text("DELETE FROM agriculture_stratum_memberships WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_strata WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM land_units WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM project_boundary_versions WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM projects WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM users WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM organizations WHERE id = :org_id"), {"org_id": org_id})
        await session.commit()
    print(json.dumps({"status": "CLEANED", "organization_id": org_id_str}))


async def verify_soc_stock(project_id_str: str):
    project_id = uuid.UUID(project_id_str)
    async with async_session_factory() as session:
        stmt = (
            select(AgricultureSOCStockResult)
            .where(AgricultureSOCStockResult.project_id == project_id)
            .order_by(AgricultureSOCStockResult.created_at.desc())
        )
        stocks = (await session.execute(stmt)).scalars().all()
        if not stocks:
            print(json.dumps({"status": "NOT_FOUND", "stocks_count": 0}))
            return

        latest_stock = stocks[0]
        q_lyr = (
            select(AgricultureSOCLayerResult)
            .where(AgricultureSOCLayerResult.stock_result_id == latest_stock.id)
            .order_by(AgricultureSOCLayerResult.layer_index)
        )
        layers = (await session.execute(q_lyr)).scalars().all()

        q_calc = await session.execute(
            select(CarbonCalculation).where(CarbonCalculation.project_id == project_id)
        )
        calcs = q_calc.scalars().all()
        tco2e_yield_vals = [c.tco2e_yield for c in calcs if c.tco2e_yield is not None]

        q_mint = await session.execute(
            text("SELECT count(*) FROM registry_sync_logs WHERE project_id = :p_id"),
            {"p_id": project_id},
        )
        mint_count = q_mint.scalar() or 0

        resolved_eq_depth = latest_stock.equivalent_depth_cm
        if resolved_eq_depth is None:
            pt_stock = next((s for s in stocks if s.aggregation_level == "SAMPLE_POINT" and s.equivalent_depth_cm is not None), None)
            if pt_stock:
                resolved_eq_depth = pt_stock.equivalent_depth_cm

        res = {
            "project_id": str(project_id),
            "result_code": latest_stock.result_code,
            "measurement_period_type": latest_stock.measurement_period_type,
            "aggregation_level": latest_stock.aggregation_level,
            "soc_stock_t_c_per_ha": float(latest_stock.soc_stock_t_c_per_ha) if latest_stock.soc_stock_t_c_per_ha else None,
            "reference_soil_mass_t_ha": float(latest_stock.reference_soil_mass_t_ha) if latest_stock.reference_soil_mass_t_ha else None,
            "reference_depth_cm": float(latest_stock.reference_depth_cm) if latest_stock.reference_depth_cm else None,
            "equivalent_depth_cm": float(resolved_eq_depth) if resolved_eq_depth else None,
            "esm_algorithm": latest_stock.esm_algorithm,
            "depth_sufficiency_status": latest_stock.depth_sufficiency_status,
            "calculation_hash": latest_stock.calculation_hash,
            "input_snapshot_hash": latest_stock.input_snapshot_hash,
            "layers_count": len(layers),
            "sample_count": latest_stock.sample_count,
            "tco2e_yield": None if not tco2e_yield_vals else tco2e_yield_vals[0],
            "carbon_status": "NOT_CONFIGURED",
            "ledger_mint_count": mint_count,
            "fail_closed_contract_passed": (len(tco2e_yield_vals) == 0 and mint_count == 0),
        }
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        is_divergent = len(sys.argv) > 2 and sys.argv[2] == "--divergent-bd"
        asyncio.run(setup_test_environment(is_divergent))
    elif len(sys.argv) > 2 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_environment(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_soc_stock":
        asyncio.run(verify_soc_stock(sys.argv[2]))
    else:
        print("Usage: python run_phase3b1_live_helper.py [setup [--divergent-bd] | cleanup <org_id> | verify_soc_stock <project_id>]")
