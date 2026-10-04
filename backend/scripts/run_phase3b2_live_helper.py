"""
VeriField Nexus — Agriculture Phase 3B-2 Live Full-Stack Helper
Creates synthetic database records in PostgreSQL with locked prerequisite assessment,
baseline SOC stock result, and monitoring SOC stock result, enabling live browser E2E
verification of VM0042 v2.2 SOC Stock Change & Uncertainty Engine.
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
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    PhysicalSample,
    SampleCollectionEvent,
    LaboratoryReceipt,
    LaboratoryAnalysis,
    LaboratoryResult,
    SampleQAReview,
    QuantificationInputSnapshot,
    AgriculturePrerequisiteAssessment,
    AgricultureSOCStockResult,
    AgricultureSOCLayerResult,
    AgricultureSOCChangeResult,
)
from app.domains.methodologies.models import MethodologyFamily, Methodology, MethodologyVersion
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash


async def setup_test_environment(scenario: str = "standard"):
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
            name=f"Phase 3B-2 Live Org {tag}",
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
            email=f"pm.{tag}@phase3b2-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Agricultural Project Manager",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        field_agent = User(
            id=uuid.uuid4(),
            email=f"agent.{tag}@phase3b2-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Tariq Field Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        auditor = User(
            id=uuid.uuid4(),
            email=f"auditor.{tag}@phase3b2-live.test",
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
            name=f"VM0042 SOC Change Pilot {tag}",
            project_code=f"AGRI-3B2-{tag[:6].upper()}",
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
            name=f"Field Central {tag}",
            code=f"LU-PRJ-{tag}",
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
            code=f"STR-SL-{tag}",
            name="Silt Loam - QA2 Project Stratum",
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
            campaign_code=f"CAMP-{tag}",
            name=f"Multi-Period Campaign {tag}",
            purpose="MEASURE_AND_REMEASURE",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=today - timedelta(days=730),
            planned_end_date=today,
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
            effective_as_of_date=today - timedelta(days=730),
            is_locked=True,
            locked_at=now,
            locked_by_id=pm_user.id,
            plan_lock_snapshot={
                "minimum_points_per_stratum": 6,
                "target_mdd": 1.5,
                "power_analysis_executed": False,
            },
        )
        session.add(plan)
        await session.flush()

        # Create 6 real SamplingPoint records
        sampling_points = []
        for pt_idx in range(6):
            pt_code = f"SP-{tag}-{pt_idx+1:02d}"
            lat = 42.05 + (pt_idx * 0.005)
            lon = -93.45 + (pt_idx * 0.005)
            sp = SamplingPoint(
                id=uuid.uuid4(),
                organization_id=org.id,
                project_id=proj.id,
                campaign_id=campaign.id,
                plan_version_id=plan.id,
                land_unit_id=lu_project.id,
                stratum_id=stratum.id,
                point_code=pt_code,
                soil_profile_id=f"PROF-{tag}-{pt_idx+1:02d}",
                planned_lat=lat,
                planned_lon=lon,
                depth_from_cm=0.0,
                depth_to_cm=30.0,
                status="COLLECTED",
            )
            session.add(sp)
            sampling_points.append(sp)
        await session.flush()

        # 5. Locked Prerequisite Assessment
        prereq = AgriculturePrerequisiteAssessment(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            assessment_code=f"PRA-{tag[:6].upper()}-001",
            version=1,
            status="LOCKED",
            is_locked=True,
            locked_at=now - timedelta(days=30),
            locked_by_id=pm_user.id,
            overall_readiness="READY",
            methodology_code="VM0042",
            methodology_version="2.2",
            rule_set_version="VM0042_V2_2_CC_2026_06_11",
            corrections_clarifications_version="2026-06-11",
            assessment_hash=hashlib.sha256(f"prereq-{tag}".encode("utf-8")).hexdigest(),
            dimensions={
                "VCS_PROGRAM_RULESET": {"status": "READY", "details": {"governing_vcs_standard": "VCS_4_7"}},
                "METHODOLOGY_VERSION_LOCK": {"status": "READY"},
                "SOIL_DEPTH_HORIZONS": {"status": "READY"},
                "SAMPLING_DESIGN_SUFFICIENCY": {"status": "READY"},
            },
        )
        session.add(prereq)
        await session.flush()

        # 6. Baseline & Monitoring SOC Stock Results
        t_start = now - timedelta(days=730)
        t_final = now - timedelta(days=1)
        base_hash = hashlib.sha256(f"base-{tag}".encode("utf-8")).hexdigest()

        if scenario == "unfavorable":
            base_mean_val = Decimal("48.7800")
            mon_mean_val = Decimal("43.1200")
            base_delta_step = Decimal("0.35")
            mon_delta_step = Decimal("0.40")
        else:
            base_mean_val = Decimal("45.1200")
            mon_mean_val = Decimal("48.7800")
            base_delta_step = Decimal("0.40")
            mon_delta_step = Decimal("0.35")

        base_strata = [{
            "stratum_id": str(stratum.id),
            "stratum_code": stratum.code,
            "stratum_area_ha": "100.00",
            "area_weight": "1.0000",
            "stratum_mean_soc_t_c_per_ha": str(base_mean_val),
            "sample_count": 6,
        }]
        mon_strata = [{
            "stratum_id": str(stratum.id),
            "stratum_code": stratum.code,
            "stratum_area_ha": "100.00",
            "area_weight": "1.0000",
            "stratum_mean_soc_t_c_per_ha": str(mon_mean_val),
            "sample_count": 6,
        }]

        baseline_stock = AgricultureSOCStockResult(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            prerequisite_assessment_id=prereq.id,
            result_code=f"SOC-BASE-{tag[:6].upper()}",
            measurement_period_type="BASELINE",
            aggregation_level="PROJECT",
            stratum_id=stratum.id,
            esm_algorithm="ELLERT_BETTANY_1995",
            reference_depth_cm=Decimal("30.00"),
            reference_soil_mass_t_ha=Decimal("3900.00"),
            soc_stock_t_c_per_ha=base_mean_val,
            unadjusted_stock_t_c_per_ha=base_mean_val - Decimal("0.27"),
            depth_sufficiency_status="SUFFICIENT",
            sample_count=6,
            area_ha=Decimal("100.00"),
            component_breakdown={"strata_results": base_strata},
            calculation_hash=base_hash,
            input_snapshot_hash=hashlib.sha256(b"base-snap").hexdigest(),
            result_status="FINALIZED",
            created_at=t_start,
        )
        session.add(baseline_stock)
        await session.flush()

        # Add 6 Baseline Sample Point Stock Results
        base_pt_stocks = []
        for i in range(6):
            pt_val = base_mean_val + Decimal(str((i - 2.5))) * base_delta_step
            sp_id = sampling_points[i].id
            pt_stock = AgricultureSOCStockResult(
                id=uuid.uuid4(),
                organization_id=org.id,
                project_id=proj.id,
                prerequisite_assessment_id=prereq.id,
                result_code=f"SOC-PT-BASE-{tag}-{i+1:02d}",
                measurement_period_type="BASELINE",
                aggregation_level="SAMPLE_POINT",
                sampling_point_id=sp_id,
                stratum_id=stratum.id,
                esm_algorithm="ELLERT_BETTANY_1995",
                reference_depth_cm=Decimal("30.00"),
                reference_soil_mass_t_ha=Decimal("3900.00"),
                soc_stock_t_c_per_ha=pt_val,
                unadjusted_stock_t_c_per_ha=pt_val - Decimal("0.2"),
                depth_sufficiency_status="SUFFICIENT",
                sample_count=1,
                calculation_hash=hashlib.sha256(f"pt-base-{tag}-{i}".encode("utf-8")).hexdigest(),
                input_snapshot_hash=hashlib.sha256(b"pt-base-snap").hexdigest(),
                result_status="FINALIZED",
                created_at=t_start,
            )
            base_pt_stocks.append(pt_stock)
        session.add_all(base_pt_stocks)

        # 7. Monitoring SOC Stock Result (T1, current)
        mon_hash = hashlib.sha256(f"mon-{tag}".encode("utf-8")).hexdigest()
        monitoring_stock = AgricultureSOCStockResult(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            prerequisite_assessment_id=prereq.id,
            result_code=f"SOC-MON-{tag[:6].upper()}",
            measurement_period_type="MONITORING",
            aggregation_level="PROJECT",
            stratum_id=stratum.id,
            esm_algorithm="ELLERT_BETTANY_1995",
            reference_depth_cm=Decimal("30.00"),
            reference_soil_mass_t_ha=Decimal("3900.00"),
            soc_stock_t_c_per_ha=mon_mean_val,
            unadjusted_stock_t_c_per_ha=mon_mean_val - Decimal("0.28"),
            depth_sufficiency_status="SUFFICIENT",
            sample_count=6,
            area_ha=Decimal("100.00"),
            component_breakdown={"strata_results": mon_strata},
            calculation_hash=mon_hash,
            input_snapshot_hash=hashlib.sha256(b"mon-snap").hexdigest(),
            result_status="FINALIZED",
            created_at=t_final,
        )
        session.add(monitoring_stock)
        await session.flush()

        # Add 6 Monitoring Sample Point Stock Results (paired to baseline points)
        mon_pt_stocks = []
        for i in range(6):
            pt_val = mon_mean_val + Decimal(str((i - 2.5))) * mon_delta_step
            pt_stock = AgricultureSOCStockResult(
                id=uuid.uuid4(),
                organization_id=org.id,
                project_id=proj.id,
                prerequisite_assessment_id=prereq.id,
                result_code=f"SOC-PT-MON-{tag}-{i+1:02d}",
                measurement_period_type="MONITORING",
                aggregation_level="SAMPLE_POINT",
                sampling_point_id=base_pt_stocks[i].sampling_point_id,
                stratum_id=stratum.id,
                esm_algorithm="ELLERT_BETTANY_1995",
                reference_depth_cm=Decimal("30.00"),
                reference_soil_mass_t_ha=Decimal("3900.00"),
                soc_stock_t_c_per_ha=pt_val,
                unadjusted_stock_t_c_per_ha=pt_val - Decimal("0.2"),
                depth_sufficiency_status="SUFFICIENT",
                sample_count=1,
                calculation_hash=hashlib.sha256(f"pt-mon-{tag}-{i}".encode("utf-8")).hexdigest(),
                input_snapshot_hash=hashlib.sha256(b"pt-mon-snap").hexdigest(),
                result_status="FINALIZED",
                created_at=t_final,
            )
            mon_pt_stocks.append(pt_stock)
        session.add_all(mon_pt_stocks)
        await session.commit()

        # Generate JWT tokens
        pm_token = AuthenticationService.generate_token_static(pm_user)
        field_token = AuthenticationService.generate_token_static(field_agent)
        auditor_token = AuthenticationService.generate_token_static(auditor)

        out = {
            "organization_id": str(org.id),
            "project_id": str(proj.id),
            "project_name": proj.name,
            "project_code": proj.project_code,
            "prerequisite_id": str(prereq.id),
            "prerequisite_code": prereq.assessment_code,
            "baseline_stock_id": str(baseline_stock.id),
            "baseline_stock_code": baseline_stock.result_code,
            "monitoring_stock_id": str(monitoring_stock.id),
            "monitoring_stock_code": monitoring_stock.result_code,
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
        print(json.dumps(out))
        return out


async def cleanup_test_environment(org_id_str: str):
    org_id = uuid.UUID(org_id_str)
    async with async_session_factory() as session:
        # Cascade clean all Phase 3B-2, 3B-1, 3B-0, 3A, Phase 2, Phase 1 records
        await session.execute(text("DELETE FROM agriculture_soc_change_results WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("""
            DELETE FROM agriculture_soc_layer_results WHERE stock_result_id IN (
                SELECT id FROM agriculture_soc_stock_results WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_soc_stock_snapshots WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_soc_stock_results WHERE organization_id = :org_id"), {"org_id": org_id})
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


async def verify_soc_change(project_id_str: str):
    project_id = uuid.UUID(project_id_str)
    async with async_session_factory() as session:
        stmt = (
            select(AgricultureSOCChangeResult)
            .where(AgricultureSOCChangeResult.project_id == project_id)
            .order_by(AgricultureSOCChangeResult.created_at.desc())
        )
        changes = (await session.execute(stmt)).scalars().all()
        if not changes:
            print(json.dumps({"status": "NOT_FOUND", "changes_count": 0}))
            return

        latest_change = changes[0]

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

        res = {
            "project_id": str(project_id),
            "result_id": str(latest_change.id),
            "result_code": latest_change.result_code,
            "quantification_approach": latest_change.quantification_approach,
            "t_start": latest_change.t_start.isoformat(),
            "t_final": latest_change.t_final.isoformat(),
            "elapsed_years": float(latest_change.elapsed_years),
            "total_project_area_ha": float(latest_change.total_project_area_ha),
            "baseline_mean_soc_t_c_per_ha": float(latest_change.baseline_mean_soc_t_c_per_ha),
            "monitoring_mean_soc_t_c_per_ha": float(latest_change.monitoring_mean_soc_t_c_per_ha),
            "delta_soc_project_t_c_ha_yr": float(latest_change.delta_soc_project_t_c_ha_yr),
            "delta_soc_baseline_t_c_ha_yr": float(latest_change.delta_soc_baseline_t_c_ha_yr),
            "delta_soc_net_t_c_ha_yr": float(latest_change.delta_soc_net_t_c_ha_yr),
            "delta_co2_net_tco2e_ha_yr": float(latest_change.delta_co2_net_tco2e_ha_yr),
            "total_net_delta_co2_tco2e_yr": float(latest_change.total_net_delta_co2_tco2e_yr),
            "baseline_soc_change_tco2e_yr": float(latest_change.baseline_soc_change_tco2e_yr) if latest_change.baseline_soc_change_tco2e_yr is not None else None,
            "project_soc_change_tco2e_yr": float(latest_change.project_soc_change_tco2e_yr) if latest_change.project_soc_change_tco2e_yr is not None else None,
            "qa2_net_soc_effect_tco2e_yr": float(latest_change.qa2_net_soc_effect_tco2e_yr) if latest_change.qa2_net_soc_effect_tco2e_yr is not None else None,
            "uncertainty_adjusted_soc_effect_tco2e_yr": float(latest_change.uncertainty_adjusted_soc_effect_tco2e_yr) if latest_change.uncertainty_adjusted_soc_effect_tco2e_yr is not None else None,
            "sign_indicator": latest_change.sign_indicator,
            "eq44_eq45_status": latest_change.eq44_eq45_status,
            "df_estimator": latest_change.df_estimator,
            "co2_to_c_ratio": float(latest_change.co2_to_c_ratio),
            "variance_delta_soc_project": float(latest_change.variance_delta_soc_project),
            "variance_delta_soc_baseline": float(latest_change.variance_delta_soc_baseline),
            "total_variance_delta_soc": float(latest_change.total_variance_delta_soc),
            "degrees_of_freedom": latest_change.degrees_of_freedom,
            "student_t_value_0667": float(latest_change.student_t_value_0667),
            "relative_uncertainty_pct": float(latest_change.relative_uncertainty_pct),
            "uncertainty_deduction_pct": float(latest_change.uncertainty_deduction_pct),
            "adjusted_net_delta_co2_tco2e_yr": float(latest_change.adjusted_net_delta_co2_tco2e_yr),
            "measurement_error_status": latest_change.measurement_error_status,
            "measurement_error_router": latest_change.measurement_error_router,
            "carbon_accounting_status": latest_change.carbon_accounting_status,
            "ledger_status": latest_change.ledger_status,
            "result_status": latest_change.result_status,
            "calculation_hash": latest_change.calculation_hash,
            "input_snapshot_hash": latest_change.input_snapshot_hash,
            "tco2e_yield": None if not tco2e_yield_vals else tco2e_yield_vals[0],
            "ledger_mint_count": mint_count,
            "fail_closed_contract_passed": (
                len(tco2e_yield_vals) == 0
                and mint_count == 0
                and latest_change.carbon_accounting_status == "NOT_CONFIGURED"
                and latest_change.ledger_status in ("BLOCKED_FOR_AGRICULTURE", "REJECTED_CARBON_MINTING_NOT_SUPPORTED_FOR_SOC_CHANGE")
            ),
        }
        print(json.dumps(res, indent=2))
        return res


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        scenario = sys.argv[2] if len(sys.argv) > 2 else "standard"
        asyncio.run(setup_test_environment(scenario))
    elif len(sys.argv) > 2 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_environment(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_soc_change":
        asyncio.run(verify_soc_change(sys.argv[2]))
    else:
        print("Usage: python run_phase3b2_live_helper.py [setup [standard|unfavorable] | cleanup <org_id> | verify_soc_change <project_id>]")
