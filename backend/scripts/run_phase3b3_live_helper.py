"""
VeriField Nexus — Agriculture Phase 3B-3 Live Full-Stack Helper
Seeds PostgreSQL test tenant with locked prerequisite assessment, baseline & monitoring
SOC stocks, and Phase 3B-2 SOC stock change result, enabling live Playwright E2E verification
of VM0042 v2.2 Net GHG Reductions & Removals (Eqs. 37-43) and Section 8.7 VCU Readiness.
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
from app.domains.projects.models import Project
from app.domains.earth_observation.models import ProjectBoundaryVersion
from app.domains.agriculture.models import (
    LandUnit,
    Stratum,
    StratumMembership,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    AgriculturePrerequisiteAssessment,
    AgricultureSOCStockResult,
    AgricultureSOCChangeResult,
    AgricultureNetGHGResult,
    AgricultureVintageGHGResult,
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
            name=f"Phase 3B-3 Live Org {tag}",
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
            email=f"pm.{tag}@phase3b3-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Agricultural Project Manager",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        field_agent = User(
            id=uuid.uuid4(),
            email=f"agent.{tag}@phase3b3-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Tariq Field Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        auditor = User(
            id=uuid.uuid4(),
            email=f"auditor.{tag}@phase3b3-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="External VVB Auditor",
            role="AUDITOR",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add_all([pm_user, field_agent, auditor])
        await session.flush()

        # JWT tokens
        pm_token = AuthenticationService.generate_token_static(pm_user)
        field_token = AuthenticationService.generate_token_static(field_agent)
        auditor_token = AuthenticationService.generate_token_static(auditor)

        # 2. Project
        proj = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=f"VM0042 Net GHG Live Pilot {tag}",
            project_code=f"PRJ-3B3-{tag.upper()}",
            sector_id=fam.id if fam else None,
            methodology_id=vm.id if vm else None,
            methodology_version_id=v22.id if v22 else None,
            country="USA",
        )
        session.add(proj)
        await session.flush()

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
                "minimum_points_per_stratum": 4,
                "target_mdd": 1.5,
                "power_analysis_executed": False,
            },
        )
        session.add(plan)
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
            vcs_standard_version="4.7",
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
        base_mean = Decimal("40.0000")
        mon_mean = Decimal("45.0000")

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
            soc_stock_t_c_per_ha=base_mean,
            unadjusted_stock_t_c_per_ha=base_mean,
            depth_sufficiency_status="SUFFICIENT",
            sample_count=4,
            area_ha=Decimal("100.00"),
            component_breakdown={"strata_results": []},
            calculation_hash=hashlib.sha256(f"base-{tag}".encode("utf-8")).hexdigest(),
            input_snapshot_hash=hashlib.sha256(b"base-snap").hexdigest(),
            result_status="FINALIZED",
            created_at=t_start,
        )
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
            soc_stock_t_c_per_ha=mon_mean,
            unadjusted_stock_t_c_per_ha=mon_mean,
            depth_sufficiency_status="SUFFICIENT",
            sample_count=4,
            area_ha=Decimal("100.00"),
            component_breakdown={"strata_results": []},
            calculation_hash=hashlib.sha256(f"mon-{tag}".encode("utf-8")).hexdigest(),
            input_snapshot_hash=hashlib.sha256(b"mon-snap").hexdigest(),
            result_status="FINALIZED",
            created_at=t_final,
        )
        session.add_all([baseline_stock, monitoring_stock])
        await session.flush()

        # 7. Phase 3B-2 SOC Stock Change Result
        if scenario == "eq37_branch_edge":
            delta_co2_bsl_yr = Decimal("-10.0000")
            delta_co2_wp_yr = Decimal("-5.0000")
            delta_net = Decimal("5.0000")
            delta_soc_prj_t_c = Decimal("-0.0136")
            delta_soc_bsl_t_c = Decimal("-0.0273")
            delta_soc_net_t_c = Decimal("0.0136")
        elif scenario == "eq37_adverse":
            delta_co2_bsl_yr = Decimal("-2.0000")
            delta_co2_wp_yr = Decimal("-10.0000")
            delta_net = Decimal("-8.0000")
            delta_soc_prj_t_c = Decimal("-0.0273")
            delta_soc_bsl_t_c = Decimal("-0.0055")
            delta_soc_net_t_c = Decimal("-0.0218")
        else:
            delta_co2_bsl_yr = Decimal("0.0000")
            delta_co2_wp_yr = Decimal("916.6700")
            delta_net = Decimal("916.6700")
            delta_soc_prj_t_c = Decimal("2.5000")
            delta_soc_bsl_t_c = Decimal("0.0000")
            delta_soc_net_t_c = Decimal("2.5000")

        soc_chg = AgricultureSOCChangeResult(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            baseline_stock_result_id=baseline_stock.id,
            monitoring_stock_result_id=monitoring_stock.id,
            prerequisite_assessment_id=prereq.id,
            result_code=f"SOC-CHG-{tag[:6].upper()}",
            methodology_version="2.2",
            corrections_clarifications_version="2026-06-11",
            calculation_engine_version="VM0042_V2_2_SOC_CHANGE_V1.0",
            quantification_approach="APPROACH_2",
            t_start=t_start,
            t_final=t_final,
            elapsed_years=Decimal("2.0000"),
            esm_algorithm="ELLERT_BETTANY_1995",
            reference_soil_mass_t_ha=Decimal("3900.00"),
            reference_depth_cm=Decimal("30.00"),
            total_project_area_ha=Decimal("100.00"),
            baseline_mean_soc_t_c_per_ha=base_mean,
            monitoring_mean_soc_t_c_per_ha=mon_mean,
            delta_soc_project_t_c_ha_yr=delta_soc_prj_t_c,
            delta_soc_baseline_t_c_ha_yr=delta_soc_bsl_t_c,
            delta_soc_net_t_c_ha_yr=delta_soc_net_t_c,
            delta_co2_project_tco2e_ha_yr=delta_co2_wp_yr / Decimal("100.00"),
            delta_co2_baseline_tco2e_ha_yr=delta_co2_bsl_yr / Decimal("100.00"),
            delta_co2_net_tco2e_ha_yr=delta_net / Decimal("100.00"),
            total_project_delta_co2_tco2e_yr=delta_co2_wp_yr,
            total_baseline_delta_co2_tco2e_yr=delta_co2_bsl_yr,
            total_net_delta_co2_tco2e_yr=delta_net,
            baseline_soc_change_tco2e_yr=delta_co2_bsl_yr,
            project_soc_change_tco2e_yr=delta_co2_wp_yr,
            qa2_net_soc_effect_tco2e_yr=delta_net,
            uncertainty_adjusted_soc_effect_tco2e_yr=delta_net,
            sign_indicator=1,
            eq44_eq45_status="COMPLETE",
            df_estimator="DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR",
            co2_to_c_ratio=Decimal("3.66666667"),
            variance_delta_soc_project=Decimal("0.00010000"),
            variance_delta_soc_baseline=Decimal("0.00000000"),
            total_variance_delta_soc=Decimal("0.00010000"),
            standard_error_delta_soc_t_c_ha_yr=Decimal("0.010000"),
            standard_error_tco2e_yr=Decimal("3.6667"),
            degrees_of_freedom=18,
            student_t_value_0667=Decimal("0.4385"),
            relative_uncertainty_pct=Decimal("0.4000"),
            allowable_uncertainty_pct=Decimal("0.0000"),
            uncertainty_deduction_pct=Decimal("0.0000"),
            uncertainty_deduction_fraction=Decimal("0.000000"),
            adjusted_net_delta_co2_tco2e_yr=delta_net,
            measurement_error_status="NEGLIGIBLE_PER_VM0042_CONDITIONS",
            measurement_error_router="CONVENTIONAL_DRY_COMBUSTION",
            strata_results=[],
            component_breakdown={},
            carbon_accounting_status="NOT_CONFIGURED",
            ledger_status="BLOCKED_FOR_AGRICULTURE",
            result_status="CALCULATED",
            calculation_hash=hashlib.sha256(f"soc-chg-{tag}".encode("utf-8")).hexdigest(),
            input_snapshot_hash=hashlib.sha256(b"soc-chg-snap").hexdigest(),
            created_at=now,
        )
        session.add(soc_chg)
        await session.commit()

        out = {
            "organization_id": str(org.id),
            "project_id": str(proj.id),
            "project_name": proj.name,
            "project_code": proj.project_code,
            "prerequisite_id": str(prereq.id),
            "prerequisite_code": prereq.assessment_code,
            "baseline_stock_id": str(baseline_stock.id),
            "monitoring_stock_id": str(monitoring_stock.id),
            "soc_change_id": str(soc_chg.id),
            "soc_change_code": soc_chg.result_code,
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


async def verify_net_ghg(project_id_str: str):
    async with async_session_factory() as session:
        proj_uuid = uuid.UUID(project_id_str)
        stmt = (
            select(AgricultureNetGHGResult)
            .where(AgricultureNetGHGResult.project_id == proj_uuid)
            .order_by(AgricultureNetGHGResult.created_at.desc())
        )
        res = (await session.execute(stmt)).scalars().first()
        if not res:
            out = {"found": False, "count": 0}
            print(json.dumps(out))
            return out

        # Fetch vintages
        vstmt = (
            select(AgricultureVintageGHGResult)
            .where(AgricultureVintageGHGResult.net_ghg_result_id == res.id)
            .order_by(AgricultureVintageGHGResult.vintage_year.asc())
        )
        vintages = (await session.execute(vstmt)).scalars().all()

        cb = res.component_breakdown or {}
        vmd0054_ver = cb.get("vmd0054_version", "VMD0054_1_1_CURRENT")
        vmd0054_eq = cb.get("vmd0054_source_equation", "VMD0054_V1.1_EQ13")
        vmd0054_basis = cb.get("vmd0054_transition_basis", "ACTIVE_STANDARD_V1_1")
        vmd0054_ruleset = cb.get("vmd0054_effective_ruleset", "VMD0054_V1.1_ACTIVE")

        v_list = []
        for v in vintages:
            vd = v.vintage_details or {}
            v_list.append({
                "vintage_year": v.vintage_year,
                "i_value": vd.get("i_delta_co2_wp"),
                "cumulative_project_stock_change": float(vd.get("cumulative_project_stock_change_tco2e", 0.0)),
                "current_year_delta_co2_wp": float(v.eq45_project_total_carbon_stock_change_tco2e),
                "current_year_delta_co2_bsl": float(v.eq44_baseline_total_carbon_stock_change_tco2e),
                "eq37_stock_component": float(vd.get("stock_reductions_term_tco2e", 0.0)),
                "er": float(v.gross_reductions_er_tco2e),
                "npr": float(res.npr_rating_pct) if res.npr_rating_pct is not None else None,
                "eq75_term": float(vd.get("stock_reductions_term_tco2e", 0.0)),
                "buer": float(v.buffer_deduction_reductions_tco2e) if v.buffer_deduction_reductions_tco2e is not None else None,
                "gross_reductions_er": float(v.gross_reductions_er_tco2e),
                "gross_removals_cr": float(v.gross_removals_cr_tco2e),
                "leakage": float(v.total_leakage_tco2e),
                "net_reductions_ernet": float(v.net_reductions_ernet_tco2e),
                "net_removals_crnet": float(v.net_removals_crnet_tco2e),
                "total_net_ghg_errnet": float(v.total_net_ghg_errnet_tco2e),
                "internal_vcu_eligible_total": float(v.internal_vcu_eligible_total_tco2e) if v.internal_vcu_eligible_total_tco2e is not None else None,
                "vmd0054_resolved_version": vd.get("vmd0054_version", vmd0054_ver),
                "vmd0054_source_equation": vd.get("vmd0054_source_equation", vmd0054_eq),
                "transition_basis": vd.get("vmd0054_transition_basis", vmd0054_basis),
            })

        first_vd = vintages[0].vintage_details if vintages else {}
        proof = {
            "i_value": first_vd.get("i_delta_co2_wp"),
            "cumulative_project_stock_change": float(first_vd.get("cumulative_project_stock_change_tco2e", 0.0)),
            "current_year_delta_co2_wp": float(vintages[0].eq45_project_total_carbon_stock_change_tco2e) if vintages else 0.0,
            "current_year_delta_co2_bsl": float(vintages[0].eq44_baseline_total_carbon_stock_change_tco2e) if vintages else 0.0,
            "eq37_stock_component": float(first_vd.get("stock_reductions_term_tco2e", 0.0)),
            "er": float(res.gross_reductions_er_tco2e),
            "npr": float(res.npr_rating_pct) if res.npr_rating_pct is not None else None,
            "eq75_term": float(first_vd.get("stock_reductions_term_tco2e", 0.0)),
            "buer": float(res.buffer_deduction_reductions_tco2e) if res.buffer_deduction_reductions_tco2e is not None else None,
            "vmd0054_resolved_version": vmd0054_ver,
            "vmd0054_source_equation": vmd0054_eq,
            "vmd0054_trace": cb.get("vmd0054_trace", {}),
            "transition_basis": vmd0054_basis,
            "effective_ruleset": vmd0054_ruleset,
            "calculation_hash": res.calculation_hash,
        }

        out = {
            "found": True,
            "id": str(res.id),
            "result_code": res.result_code,
            "result_status": res.result_status,
            "methodology_version": res.methodology_version,
            "ruleset_version": res.ruleset_version,
            "verification_period_start": res.verification_period_start.isoformat(),
            "verification_period_end": res.verification_period_end.isoformat(),
            "elapsed_years": float(res.elapsed_years),
            "total_baseline_emissions": float(res.total_baseline_emissions_tco2e),
            "total_project_emissions": float(res.total_project_emissions_tco2e),
            "gross_reductions_er": float(res.gross_reductions_er_tco2e),
            "gross_removals_cr": float(res.gross_removals_cr_tco2e),
            "total_leakage": float(res.total_leakage_tco2e),
            "leakage_er_lker": float(res.leakage_allocation_er_lker_tco2e),
            "leakage_cr_lkcr": float(res.leakage_allocation_cr_lkcr_tco2e),
            "net_reductions_ernet": float(res.net_reductions_ernet_tco2e),
            "net_removals_crnet": float(res.net_removals_crnet_tco2e),
            "total_net_ghg_errnet": float(res.total_net_ghg_errnet_tco2e),
            "vmd0054_resolved_version": vmd0054_ver,
            "vmd0054_source_equation": vmd0054_eq,
            "vmd0054_trace": cb.get("vmd0054_trace", {}),
            "npr_rating_pct": float(res.npr_rating_pct) if res.npr_rating_pct is not None else None,
            "total_buffer_deduction": float(res.total_buffer_deduction_tco2e) if res.total_buffer_deduction_tco2e is not None else None,
            "internal_vcu_eligible_total": float(res.internal_vcu_eligible_total_tco2e) if res.internal_vcu_eligible_total_tco2e is not None else None,
            "vcu_readiness_status": res.vcu_readiness_status,
            "internal_mrv_status": res.internal_mrv_status,
            "vvb_status": res.vvb_status,
            "registry_status": res.registry_status,
            "calculation_hash": res.calculation_hash,
            "input_snapshot_hash": res.input_snapshot_hash,
            "direct_postgresql_proof": proof,
            "vintages_count": len(v_list),
            "vintages": v_list,
            "fail_closed_contract_passed": (
                res.vvb_status in ("NOT_CONFIGURED", "NOT_CONFIGURED / EXTERNAL")
                and res.registry_status in ("NOT_CONFIGURED", "NOT_CONFIGURED / EXTERNAL")
                and res.internal_mrv_status == "CALCULATED"
            ),
        }
        print(json.dumps(out, indent=2))
        return out


async def cleanup_test_environment(org_id_str: str):
    async with async_session_factory() as session:
        org_id = uuid.UUID(org_id_str)
        # Delete test tenant cascade
        await session.execute(text("""
            DELETE FROM agriculture_vintage_ghg_results WHERE net_ghg_result_id IN (
                SELECT id FROM agriculture_net_ghg_results WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_net_ghg_results WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_soc_change_results WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_soc_layer_results WHERE stock_result_id IN (SELECT id FROM agriculture_soc_stock_results WHERE organization_id = :org_id)"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_soc_stock_results WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM agriculture_prerequisite_assessments WHERE organization_id = :org_id"), {"org_id": org_id})
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
        print(json.dumps({"status": "CLEANED", "org_id": org_id_str}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        scenario = sys.argv[2] if len(sys.argv) > 2 else "standard"
        asyncio.run(setup_test_environment(scenario))
    elif len(sys.argv) > 2 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_environment(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_net_ghg":
        asyncio.run(verify_net_ghg(sys.argv[2]))
    else:
        print("Usage: python run_phase3b3_live_helper.py [setup [standard|adverse] | cleanup <org_id> | verify_net_ghg <project_id>]")
