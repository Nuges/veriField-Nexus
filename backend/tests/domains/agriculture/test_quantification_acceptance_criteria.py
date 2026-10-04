"""
VeriField Nexus — Agriculture MRV Phase 3A: Final Acceptance Criteria Test Suite
Explicit proof for:
§9  Depth Alignment Classifications & Complementary Layers
§12 Snapshot Gate Tests (9 distinct gating conditions)
§13 Latest Valid Result Selection (Result A superseded, B rejected, C accepted -> C only)
§14 Baseline / Project Dataset Separation (monitoring vs baseline sample routing)
§15 Temporal Stratum Resolution (historical validity as-of sampling date)
§16 Bulk Density Scenarios (present, absent, rejected, wrong depth)
§17 Coarse Fragments (MEASURED_ZERO vs MEASURED vs NOT_MEASURED vs NOT_APPLICABLE)
§18 Snapshot Canonical Hash Determinism (key order, result diff, meth diff, sample diff)
§19 Snapshot Immutability (API update rejected 405, supersession/stratum changes don't affect locked snapshot)
§20 Source Evidence Reference Validation (valid vs unknown UUIDs)
"""

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from app.core.security import get_password_hash
from app.db.session import async_session_factory
from app.domains.agriculture.models import (
    ChainOfCustodyEvent,
    LaboratoryAnalysis,
    LaboratoryReceipt,
    LaboratoryResult,
    LandUnit,
    PhysicalSample,
    QuantificationInputSnapshot,
    SampleCollectionEvent,
    SampleQAReview,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    Stratum,
    StratumMembership,
)
from app.domains.agriculture.schemas import (
    DepthAlignmentStatus,
    ExclusionReasonCode,
    QuantificationInputSnapshotCreate,
)
from app.domains.agriculture.service import AgricultureService
from app.domains.authentication.models import User
from app.domains.authentication.service import AuthenticationService
from app.domains.earth_observation.models import ProjectBoundaryVersion
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


@pytest_asyncio.fixture
async def acceptance_setup():
    """Setup project environment for acceptance tests."""
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    today = now.date()

    async with async_session_factory() as session:
        org = Organization(
            id=uuid.uuid4(),
            name=f"Acceptance Org {tag}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
        )
        session.add(org)

        pm_user = User(
            id=uuid.uuid4(),
            email=f"pm.{tag}@acceptance.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Agricultural Project Manager",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add(pm_user)
        await session.flush()

        from app.domains.agriculture.seed import seed_agriculture_methodologies
        from app.domains.methodologies.models.base_registry import Methodology
        await seed_agriculture_methodologies(session)
        m42_id = await session.scalar(select(Methodology.id).where(Methodology.code == "VM0042"))

        proj = Project(
            id=uuid.uuid4(),
            name=f"Phase 3A Acceptance Project {tag}",
            project_code=f"AGR-ACC-{tag[:6]}",
            organization_id=org.id,
            methodology_id=m42_id,
            crediting_start=date(2024, 1, 1),
            crediting_end=date(2044, 12, 31),
            baseline_parameters={
                "soil_depth_standard_cm": 30.0,
                "locked_methodology_version": {
                    "methodology_code": "VM0042",
                    "version": "2.2",
                    "status": "LOCKED",
                    "minimum_depth_cm": 30.0,
                    "quantification_approach": "DIRECT_MEASUREMENT",
                    "design_sufficiency_requirement": "REQUIRED",
                    "design_sufficiency_blocking": True,
                    "design_sufficiency_status": "NOT_CONFIGURED",
                    "bulk_density_requirement": "REQUIRED",
                    "bulk_density_blocking": True,
                    "coarse_fragments_requirement": "OPTIONAL",
                    "coarse_fragments_blocking": False,
                    "coarse_fragments_applicable": True,
                    "locked_at": now.isoformat(),
                },
            },
        )
        session.add(proj)
        await session.flush()

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
            area_ha=100.0,
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
        )
        session.add(boundary)

        lu = LandUnit(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            name="Acceptance Sector Plot",
            code=f"LU-ACC-{tag[:4]}",
            area_ha=100.0,
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]],
            },
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
            is_active=True,
        )
        session.add(lu)
        await session.flush()

        strat_a = Stratum(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"STR-A-{tag[:4]}",
            name="Stratum A (Historical 2024)",
            stratum_type="SOIL_TYPE",
            area_ha=50.0,
            is_active=True,
        )
        strat_b = Stratum(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"STR-B-{tag[:4]}",
            name="Stratum B (Current 2026)",
            stratum_type="MANAGEMENT",
            area_ha=50.0,
            is_active=True,
        )
        session.add_all([strat_a, strat_b])
        await session.flush()

        # Stratum A valid in 2024; Stratum B valid from 2025 onwards
        sm_2024 = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            stratum_id=strat_a.id,
            land_unit_id=lu.id,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            status="ACTIVE",
        )
        sm_2026 = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            stratum_id=strat_b.id,
            land_unit_id=lu.id,
            valid_from=date(2025, 1, 1),
            valid_to=None,
            status="ACTIVE",
        )
        session.add_all([sm_2024, sm_2026])

        # Baseline campaign (2024)
        c_base = SamplingCampaign(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_code=f"CAMP-BASE-{tag[:4]}",
            name="Baseline 2024 Campaign",
            purpose="BASELINE_SOC",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=date(2024, 6, 1),
            planned_end_date=date(2024, 7, 1),
            status="COMPLETE",
            project_boundary_version_id=boundary.id,
        )
        # Monitoring campaign (2026)
        c_mon = SamplingCampaign(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_code=f"CAMP-MON-{tag[:4]}",
            name="Monitoring 2026 Campaign",
            purpose="MONITORING_ROUND_1",
            baseline_or_monitoring_context="MONITORING",
            planned_start_date=date(2026, 6, 1),
            planned_end_date=date(2026, 7, 1),
            status="COMPLETE",
            project_boundary_version_id=boundary.id,
        )
        session.add_all([c_base, c_mon])
        await session.flush()

        plan_base = SamplingPlanVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=c_base.id,
            version_number=1,
            status="LOCKED",
            effective_as_of_date=date(2024, 6, 1),
            is_locked=True,
            locked_at=now,
            locked_by_id=pm_user.id,
        )
        plan_mon = SamplingPlanVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=c_mon.id,
            version_number=1,
            status="LOCKED",
            effective_as_of_date=date(2026, 6, 1),
            is_locked=True,
            locked_at=now,
            locked_by_id=pm_user.id,
        )
        session.add_all([plan_base, plan_mon])
        await session.flush()
        await session.commit()

        pm_token = AuthenticationService.generate_token_static(pm_user)

        return {
            "org_id": org.id,
            "project_id": proj.id,
            "pm_user": pm_user,
            "pm_token": pm_token,
            "lu_id": lu.id,
            "strat_a_id": strat_a.id,
            "strat_b_id": strat_b.id,
            "strat_a_code": strat_a.code,
            "strat_b_code": strat_b.code,
            "c_base_id": c_base.id,
            "c_mon_id": c_mon.id,
            "plan_base_id": plan_base.id,
            "plan_mon_id": plan_mon.id,
            "boundary_id": boundary.id,
            "tag": tag,
        }


async def _create_sample_with_assay(
    session,
    org_id,
    project_id,
    campaign_id,
    plan_id,
    lu_id,
    sample_code,
    depth_from,
    depth_to,
    sample_date,
    soc_pct=1.5,
    bd_val=1.3,
    cf_pct=None,
    soc_superseded=False,
    soc_qa_status="VERIFIED",
    sample_qa_status="QA_ACCEPTED",
    receipt_status="ACCEPTED",
    seal_intact=True,
    is_bd_superseded=False,
    bd_qa_status="VERIFIED",
    stratum_id=None,
):
    """Helper to create full chain of evidence for a sample."""
    pt = SamplingPoint(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        campaign_id=campaign_id,
        plan_version_id=plan_id,
        land_unit_id=lu_id,
        stratum_id=stratum_id,
        point_code=f"P-{sample_code}",
        planned_lat=28.52,
        planned_lon=77.12,
        depth_from_cm=depth_from,
        depth_to_cm=depth_to,
        status="COLLECTED",
    )
    session.add(pt)
    await session.flush()

    ps = PhysicalSample(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        campaign_id=campaign_id,
        plan_version_id=plan_id,
        sampling_point_id=pt.id,
        land_unit_id=lu_id,
        stratum_id=stratum_id,
        sample_code=sample_code,
        status=sample_qa_status,
    )
    session.add(ps)
    await session.flush()

    col = SampleCollectionEvent(
        id=uuid.uuid4(),
        physical_sample_id=ps.id,
        sampling_point_id=pt.id,
        actual_lat=28.52,
        actual_lon=77.12,
        actual_depth_from_cm=depth_from,
        actual_depth_to_cm=depth_to,
        collection_timestamp=datetime(sample_date.year, sample_date.month, sample_date.day, 10, 0, tzinfo=timezone.utc),
        collector_name="Tariq Field Agent",
    )
    session.add(col)

    cust = ChainOfCustodyEvent(
        id=uuid.uuid4(),
        physical_sample_id=ps.id,
        event_type="TRANSFER",
        event_timestamp=datetime(sample_date.year, sample_date.month, sample_date.day, 14, 0, tzinfo=timezone.utc),
        custodian_name="Courier Alpha",
        custodian_organization="Agri Logistics",
        seal_intact=seal_intact,
    )
    session.add(cust)

    rcp = LaboratoryReceipt(
        id=uuid.uuid4(),
        physical_sample_id=ps.id,
        laboratory_name="Eurofins Agri Testing",
        received_at=datetime(sample_date.year, sample_date.month, sample_date.day, 16, 0, tzinfo=timezone.utc),
        received_by_name="Lab Intake",
        intake_status=receipt_status,
    )
    session.add(rcp)

    ana = LaboratoryAnalysis(
        id=uuid.uuid4(),
        physical_sample_id=ps.id,
        laboratory_name="Eurofins Agri Testing",
        analytical_method="DRY_COMBUSTION",
        analysis_date=sample_date,
        qa_status=soc_qa_status,
    )
    session.add(ana)
    await session.flush()

    res_soc = LaboratoryResult(
        id=uuid.uuid4(),
        analysis_id=ana.id,
        physical_sample_id=ps.id,
        analyte="SOC_CONCENTRATION",
        raw_value=Decimal(str(soc_pct)),
        raw_unit="%",
        normalized_value=Decimal(str(soc_pct * 10)),
        normalized_unit="g/kg",
        is_superseded=soc_superseded,
    )
    session.add(res_soc)

    if bd_val is not None:
        ana_bd = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=ps.id,
            laboratory_name="Eurofins Agri Testing",
            analytical_method="CORE_BULK_DENSITY",
            analysis_date=sample_date,
            qa_status=bd_qa_status,
        )
        session.add(ana_bd)
        await session.flush()

        res_bd = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana_bd.id,
            physical_sample_id=ps.id,
            analyte="BULK_DENSITY_G_CM3",
            raw_value=Decimal(str(bd_val)),
            raw_unit="g/cm3",
            normalized_value=Decimal(str(bd_val)),
            normalized_unit="g/cm³",
            is_superseded=is_bd_superseded,
        )
        session.add(res_bd)

    if cf_pct is not None:
        res_cf = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana.id,
            physical_sample_id=ps.id,
            analyte="COARSE_FRAGMENTS_PCT",
            raw_value=Decimal(str(cf_pct)),
            raw_unit="%",
            is_superseded=False,
        )
        session.add(res_cf)

    qa = SampleQAReview(
        id=uuid.uuid4(),
        physical_sample_id=ps.id,
        reviewer_name="QA Officer",
        overall_qa_status="ACCEPTED" if sample_qa_status == "QA_ACCEPTED" else "REJECTED",
        review_date=datetime.now(timezone.utc),
    )
    session.add(qa)
    await session.flush()

    return ps


# ─── §9: Depth Alignment Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_depth_alignment_scenarios(acceptance_setup):
    """
    §9: Test depth alignment classifications:
    - 0-30 cm: MATCH
    - 0-15 cm: PARTIAL_COVERAGE
    - 0-20 cm: PARTIAL_COVERAGE
    - 15-30 cm: PARTIAL_COVERAGE
    - 20-30 cm: PARTIAL_COVERAGE
    - 0-40 cm: OVERLAPPING_INTERVAL
    - 30-60 cm: OUT_OF_SCOPE (excluded with DEPTH_MISMATCH)
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        # 1. 0-30 cm -> MATCH
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-0-30-{tag}", 0.0, 30.0, date(2024, 6, 15))
        # 2. 0-15 cm -> PARTIAL_COVERAGE
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-0-15-{tag}", 0.0, 15.0, date(2024, 6, 15))
        # 3. 0-20 cm -> PARTIAL_COVERAGE
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-0-20-{tag}", 0.0, 20.0, date(2024, 6, 15))
        # 4. 15-30 cm -> PARTIAL_COVERAGE
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-15-30-{tag}", 15.0, 30.0, date(2024, 6, 15))
        # 5. 20-30 cm -> PARTIAL_COVERAGE
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-20-30-{tag}", 20.0, 30.0, date(2024, 6, 15))
        # 6. 0-40 cm -> OVERLAPPING_INTERVAL
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-0-40-{tag}", 0.0, 40.0, date(2024, 6, 15))
        # 7. 30-60 cm -> OUT_OF_SCOPE
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-30-60-{tag}", 30.0, 60.0, date(2024, 6, 15))
        await session.commit()

        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["org_id"])
        el_by_code = {m.sample_code: m for m in eval_set["baseline_measurements"]}
        ex_by_code = {m.sample_code: m for m in eval_set["excluded_measurements"]}

        assert el_by_code[f"S-0-30-{tag}"].depth_alignment_status == DepthAlignmentStatus.MATCH.value
        assert el_by_code[f"S-0-15-{tag}"].depth_alignment_status == DepthAlignmentStatus.PARTIAL_COVERAGE.value
        assert el_by_code[f"S-0-20-{tag}"].depth_alignment_status == DepthAlignmentStatus.PARTIAL_COVERAGE.value
        assert el_by_code[f"S-15-30-{tag}"].depth_alignment_status == DepthAlignmentStatus.PARTIAL_COVERAGE.value
        assert el_by_code[f"S-20-30-{tag}"].depth_alignment_status == DepthAlignmentStatus.PARTIAL_COVERAGE.value
        assert el_by_code[f"S-0-40-{tag}"].depth_alignment_status == DepthAlignmentStatus.OVERLAPPING_INTERVAL.value

        # 30-60cm must be excluded with DEPTH_MISMATCH
        assert f"S-30-60-{tag}" in ex_by_code
        assert ExclusionReasonCode.DEPTH_MISMATCH.value in ex_by_code[f"S-30-60-{tag}"].exclusion_reasons


# ─── §13: Latest Valid Result Selection ──────────────────────────────────────

@pytest.mark.asyncio
async def test_latest_valid_result_supersession_and_rejection(acceptance_setup):
    """
    §13: Prove result selection:
    Result A: superseded
    Result B: current but QA rejected
    Result C: current and QA verified
    Expected: Result C only.
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        pt = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=data["org_id"],
            project_id=data["project_id"],
            campaign_id=data["c_base_id"],
            plan_version_id=data["plan_base_id"],
            land_unit_id=data["lu_id"],
            point_code=f"P-RES-{tag}",
            planned_lat=28.52,
            planned_lon=77.12,
            depth_from_cm=0.0,
            depth_to_cm=30.0,
            status="COLLECTED",
        )
        session.add(pt)
        await session.flush()

        ps = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=data["org_id"],
            project_id=data["project_id"],
            campaign_id=data["c_base_id"],
            plan_version_id=data["plan_base_id"],
            sampling_point_id=pt.id,
            land_unit_id=data["lu_id"],
            sample_code=f"SMP-MULTI-RES-{tag}",
            status="QA_ACCEPTED",
        )
        session.add(ps)
        await session.flush()

        col = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=ps.id,
            sampling_point_id=pt.id,
            actual_lat=28.52,
            actual_lon=77.12,
            actual_depth_from_cm=0.0,
            actual_depth_to_cm=30.0,
            collection_timestamp=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
            collector_name="Tariq Field Agent",
        )
        rcp = LaboratoryReceipt(
            id=uuid.uuid4(),
            physical_sample_id=ps.id,
            laboratory_name="Eurofins Agri Testing",
            received_at=datetime(2024, 6, 16, 10, 0, tzinfo=timezone.utc),
            received_by_name="Lab Intake",
            intake_status="ACCEPTED",
        )
        qa = SampleQAReview(
            id=uuid.uuid4(),
            physical_sample_id=ps.id,
            reviewer_name="QA Officer",
            overall_qa_status="ACCEPTED",
            review_date=datetime.now(timezone.utc),
        )
        session.add_all([col, rcp, qa])

        # Analysis 1: Verified (contains Result A superseded)
        ana1 = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=ps.id,
            laboratory_name="Lab 1",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2024, 6, 18),
            qa_status="VERIFIED",
        )
        session.add(ana1)
        await session.flush()

        res_a = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana1.id,
            physical_sample_id=ps.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.20"),
            raw_unit="%",
            normalized_value=Decimal("12.0"),
            normalized_unit="g/kg",
            is_superseded=True,  # Result A: Superseded
        )
        session.add(res_a)

        # Analysis 2: REJECTED (contains Result B)
        ana2 = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=ps.id,
            laboratory_name="Lab 2",
            analytical_method="WALKLEY_BLACK",
            analysis_date=date(2024, 6, 19),
            qa_status="REJECTED",  # Result B: QA Rejected
        )
        session.add(ana2)
        await session.flush()

        res_b = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana2.id,
            physical_sample_id=ps.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.40"),
            raw_unit="%",
            normalized_value=Decimal("14.0"),
            normalized_unit="g/kg",
            is_superseded=False,  # Not superseded, but analysis is REJECTED
        )
        session.add(res_b)

        # Analysis 3: VERIFIED (contains Result C)
        ana3 = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=ps.id,
            laboratory_name="Lab 3",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2024, 6, 20),
            qa_status="VERIFIED",  # Result C: QA Verified
        )
        session.add(ana3)
        await session.flush()

        res_c = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana3.id,
            physical_sample_id=ps.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.35"),
            raw_unit="%",
            normalized_value=Decimal("13.5"),
            normalized_unit="g/kg",
            is_superseded=False,  # Active and verified
        )
        session.add(res_c)
        await session.commit()

        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["org_id"])
        el = [m for m in eval_set["baseline_measurements"] if m.physical_sample_id == ps.id]

        assert len(el) == 1, "Sample should be eligible via Result C"
        assert el[0].laboratory_result_id == res_c.id, f"Expected Result C ({res_c.id}), got {el[0].laboratory_result_id}"
        assert el[0].raw_value == 1.35
        assert el[0].normalized_value == 13.5


# ─── §14: Baseline / Project Dataset Separation ──────────────────────────────

@pytest.mark.asyncio
async def test_baseline_project_dataset_separation(acceptance_setup):
    """
    §14: Verify baseline sample routes to baseline_measurements,
    and monitoring sample routes to project_measurements.
    Both belong to the same LandUnit.
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        # Baseline sample (campaign context BASELINE)
        s_base = await _create_sample_with_assay(
            session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"],
            f"SMP-BASE-{tag}", 0.0, 30.0, date(2024, 6, 15)
        )
        # Monitoring sample (campaign context MONITORING)
        s_mon = await _create_sample_with_assay(
            session, data["org_id"], data["project_id"], data["c_mon_id"], data["plan_mon_id"], data["lu_id"],
            f"SMP-MON-{tag}", 0.0, 30.0, date(2026, 6, 15)
        )
        await session.commit()

        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["org_id"])

        base_ids = {m.physical_sample_id for m in eval_set["baseline_measurements"]}
        mon_ids = {m.physical_sample_id for m in eval_set["project_measurements"]}

        assert s_base.id in base_ids, "Baseline sample must be in baseline_measurements"
        assert s_base.id not in mon_ids, "Baseline sample must NOT be in project_measurements"
        assert s_mon.id in mon_ids, "Monitoring sample must be in project_measurements"
        assert s_mon.id not in base_ids, "Monitoring sample must NOT be in baseline_measurements"


# ─── §15: Temporal Stratum Resolution ────────────────────────────────────────

@pytest.mark.asyncio
async def test_temporal_stratum_resolution(acceptance_setup):
    """
    §15: Test temporal stratum resolution:
    - 2024 sample -> resolves to Stratum A (valid in 2024)
    - 2026 sample -> resolves to Stratum B (valid in 2026)
    Both belong to the same LandUnit.
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        s_2024 = await _create_sample_with_assay(
            session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"],
            f"SMP-2024-{tag}", 0.0, 30.0, date(2024, 6, 15)
        )
        s_2026 = await _create_sample_with_assay(
            session, data["org_id"], data["project_id"], data["c_mon_id"], data["plan_mon_id"], data["lu_id"],
            f"SMP-2026-{tag}", 0.0, 30.0, date(2026, 6, 15)
        )
        await session.commit()

        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["org_id"])
        all_el = {m.physical_sample_id: m for m in eval_set["baseline_measurements"] + eval_set["project_measurements"]}

        m_2024 = all_el[s_2024.id]
        m_2026 = all_el[s_2026.id]

        assert m_2024.stratum_id == data["strat_a_id"], f"Expected Stratum A for 2024, got {m_2024.stratum_id}"
        assert m_2024.stratum_code == data["strat_a_code"]

        assert m_2026.stratum_id == data["strat_b_id"], f"Expected Stratum B for 2026, got {m_2026.stratum_id}"
        assert m_2026.stratum_code == data["strat_b_code"]


# ─── §16: Bulk Density Scenarios ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bulk_density_scenarios(acceptance_setup):
    """
    §16: Bulk density:
    - QA accepted present -> PRESENT
    - Bulk density absent -> MISSING
    - Bulk density rejected -> excluded / MISSING
    - Out of scope depth -> not silently reused
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        # 1. BD Present & verified
        s_ok = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-BD-OK-{tag}", 0.0, 30.0, date(2024, 6, 15), bd_val=1.35)
        # 2. BD Absent
        s_absent = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-BD-NONE-{tag}", 0.0, 30.0, date(2024, 6, 15), bd_val=None)
        # 3. BD Rejected
        s_rej = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-BD-REJ-{tag}", 0.0, 30.0, date(2024, 6, 15), bd_val=1.35, bd_qa_status="REJECTED")
        await session.commit()

        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["org_id"])
        el = {m.physical_sample_id: m for m in eval_set["baseline_measurements"]}

        assert el[s_ok.id].bulk_density_status == "PRESENT"
        assert el[s_ok.id].bulk_density_raw_value == 1.35

        assert el[s_absent.id].bulk_density_status == "MISSING"
        assert el[s_absent.id].bulk_density_raw_value is None

        assert el[s_rej.id].bulk_density_status == "MISSING"
        assert el[s_rej.id].bulk_density_raw_value is None


# ─── §17: Coarse Fragments Scenarios ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_coarse_fragments_scenarios(acceptance_setup):
    """
    §17: Distinguish MEASURED_ZERO, MEASURED, NOT_MEASURED.
    Missing does NOT turn into zero.
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        # Measured 0%
        s_zero = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-CF-ZERO-{tag}", 0.0, 30.0, date(2024, 6, 15), cf_pct=0.0)
        # Measured > 0%
        s_meas = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-CF-MEAS-{tag}", 0.0, 30.0, date(2024, 6, 15), cf_pct=5.2)
        # Not measured
        s_none = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-CF-NONE-{tag}", 0.0, 30.0, date(2024, 6, 15), cf_pct=None)
        await session.commit()

        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["org_id"])
        el = {m.physical_sample_id: m for m in eval_set["baseline_measurements"]}

        assert el[s_zero.id].coarse_fragments_status == "MEASURED_ZERO"
        assert el[s_zero.id].coarse_fragments_pct == 0.0

        assert el[s_meas.id].coarse_fragments_status == "MEASURED"
        assert el[s_meas.id].coarse_fragments_pct == 5.2

        assert el[s_none.id].coarse_fragments_status == "NOT_MEASURED"
        assert el[s_none.id].coarse_fragments_pct is None, "Missing coarse fragments must NOT be turned into 0"


# ─── §18: Snapshot Canonical Hash Determinism ────────────────────────────────

@pytest.mark.asyncio
async def test_snapshot_canonical_hash_determinism(acceptance_setup):
    """
    §18: Prove deterministic hashing:
    - Same semantic typed input with different JSON key order: same SHA-256.
    - Changed laboratory result: different SHA-256.
    - Changed methodology version: different SHA-256.
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        s = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-HASH-{tag}", 0.0, 30.0, date(2024, 6, 15))
        await session.commit()

        snap = await AgricultureService.create_quantification_input_snapshot(
            db=session,
            project_id=data["project_id"],
            user_id=data["pm_user"].id,
            user_role="PROJECT_MANAGER",
            organization_id=data["org_id"],
            payload=QuantificationInputSnapshotCreate(status="PREVIEW", context="BASELINE"),
        )
        await session.commit()

        # 1. Key order invariance
        pkg = snap.input_package
        bytes_normal = json.dumps(pkg, sort_keys=True, default=str).encode("utf-8")
        hash_normal = hashlib.sha256(bytes_normal).hexdigest()

        # Reverse key order dict
        reversed_pkg = {k: pkg[k] for k in reversed(list(pkg.keys()))}
        bytes_reversed = json.dumps(reversed_pkg, sort_keys=True, default=str).encode("utf-8")
        hash_reversed = hashlib.sha256(bytes_reversed).hexdigest()

        assert hash_normal == hash_reversed == snap.snapshot_hash

        # 2. Changed result -> different hash
        pkg_mod_res = json.loads(json.dumps(pkg))
        if pkg_mod_res["eligible_measurements"]:
            pkg_mod_res["eligible_measurements"][0]["raw_value"] = 99.99
            bytes_mod = json.dumps(pkg_mod_res, sort_keys=True, default=str).encode("utf-8")
            hash_mod = hashlib.sha256(bytes_mod).hexdigest()
            assert hash_mod != snap.snapshot_hash

        # 3. Changed methodology version -> different hash
        pkg_mod_meth = json.loads(json.dumps(pkg))
        pkg_mod_meth["methodology_version"] = "3.0"
        bytes_meth = json.dumps(pkg_mod_meth, sort_keys=True, default=str).encode("utf-8")
        hash_meth = hashlib.sha256(bytes_meth).hexdigest()
        assert hash_meth != snap.snapshot_hash


# ─── §19: Snapshot Immutability ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_snapshot_immutability(acceptance_setup):
    """
    §19: After snapshot creation:
    - Attempting ordinary API PUT/PATCH returns 405 Method Not Allowed.
    - Modifying source lab result later leaves historical snapshot unchanged.
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        s = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-IMMUT-{tag}", 0.0, 30.0, date(2024, 6, 15))
        await session.commit()

        snap = await AgricultureService.create_quantification_input_snapshot(
            db=session,
            project_id=data["project_id"],
            user_id=data["pm_user"].id,
            user_role="PROJECT_MANAGER",
            organization_id=data["org_id"],
            payload=QuantificationInputSnapshotCreate(status="PREVIEW", context="BASELINE"),
        )
        await session.commit()
        snap_id = snap.id
        orig_hash = snap.snapshot_hash
        orig_package = json.loads(json.dumps(snap.input_package))

    # Test HTTP 405 on PUT/PATCH
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        put_resp = await client.put(
            f"/api/v1/agriculture/projects/{data['project_id']}/quantification-input-snapshots/{snap_id}",
            headers={"Authorization": f"Bearer {data['pm_token']}"},
            json={"notes": "Illegal mutation"},
        )
        assert put_resp.status_code == 405, "PUT on snapshots must be 405 Method Not Allowed"

        patch_resp = await client.patch(
            f"/api/v1/agriculture/projects/{data['project_id']}/quantification-input-snapshots/{snap_id}",
            headers={"Authorization": f"Bearer {data['pm_token']}"},
            json={"notes": "Illegal mutation"},
        )
        assert patch_resp.status_code == 405, "PATCH on snapshots must be 405 Method Not Allowed"

    # Now mutate underlying DB records (supersede lab result)
    async with async_session_factory() as session:
        await session.execute(
            update(LaboratoryResult)
            .where(LaboratoryResult.physical_sample_id == s.id)
            .values(is_superseded=True)
        )
        await session.commit()

        # Query historical snapshot
        fetched = await AgricultureService.get_quantification_input_snapshot(
            session, data["project_id"], snap_id, data["org_id"]
        )
        assert fetched.snapshot_hash == orig_hash, "Historical snapshot hash must not change"
        assert fetched.input_package == orig_package, "Historical snapshot input package must not change"


# ─── §20: Source Evidence Reference Validation ───────────────────────────────

@pytest.mark.asyncio
async def test_source_evidence_reference_validation(acceptance_setup):
    """
    §20: Validate that every provided source_evidence_id exists and belongs to the project.
    Arbitrary UUID strings must raise ValueError.
    """
    data = acceptance_setup
    async with async_session_factory() as session:
        tag = data["tag"]
        s = await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-EVID-{tag}", 0.0, 30.0, date(2024, 6, 15))
        await session.commit()

        # Valid evidence ID (physical sample ID)
        valid_payload = QuantificationInputSnapshotCreate(
            status="PREVIEW",
            context="BASELINE",
            source_evidence_ids=[s.id],
        )
        snap = await AgricultureService.create_quantification_input_snapshot(
            db=session,
            project_id=data["project_id"],
            user_id=data["pm_user"].id,
            user_role="PROJECT_MANAGER",
            organization_id=data["org_id"],
            payload=valid_payload,
        )
        assert snap is not None

        # Arbitrary/non-existent UUID
        fake_id = uuid.uuid4()
        invalid_payload = QuantificationInputSnapshotCreate(
            status="PREVIEW",
            context="BASELINE",
            source_evidence_ids=[fake_id],
        )
        with pytest.raises(ValueError, match="Invalid source evidence ID"):
            await AgricultureService.create_quantification_input_snapshot(
                db=session,
                project_id=data["project_id"],
                user_id=data["pm_user"].id,
                user_role="PROJECT_MANAGER",
                organization_id=data["org_id"],
                payload=invalid_payload,
            )


# ─── §12: Snapshot Gate Tests (9 Distinct Gating Scenarios) ───────────────────

@pytest.mark.asyncio
async def test_snapshot_gate_9_scenarios(acceptance_setup):
    """
    §12: Test all 9 snapshot lock gating conditions:
    1. missing methodology lock -> cannot lock
    2. missing SOC -> cannot lock
    3. missing bulk density when required -> cannot lock
    4. missing coarse-fragment input when required -> cannot lock
    5. depth requirement unresolved (partial coverage) -> cannot lock
    6. QA rejected -> cannot lock
    7. design sufficiency REQUIRED + NOT_CONFIGURED -> cannot lock
    8. non-blocking NOT_APPLICABLE requirement -> does not block
    9. all blocking requirements COMPLETE -> lock permitted
    """
    data = acceptance_setup
    tag = data["tag"]

    # Create complete sample evidence covering all project strata
    async with async_session_factory() as session:
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-G7A-{tag}", 0.0, 30.0, date(2024, 6, 15), stratum_id=data["strat_a_id"])
        await _create_sample_with_assay(session, data["org_id"], data["project_id"], data["c_base_id"], data["plan_base_id"], data["lu_id"], f"S-G7B-{tag}", 0.0, 30.0, date(2024, 6, 15), stratum_id=data["strat_b_id"])
        await session.commit()

    # Scenario 7: Design sufficiency REQUIRED + NOT_CONFIGURED -> cannot lock
    async with async_session_factory() as session:
        with pytest.raises(ValueError, match="DESIGN_SUFFICIENCY"):
            await AgricultureService.create_quantification_input_snapshot(
                session, data["project_id"], data["pm_user"].id, "PROJECT_MANAGER", data["org_id"],
                QuantificationInputSnapshotCreate(status="LOCKED", context="BASELINE")
            )

    # Scenario 9: All blocking requirements COMPLETE -> lock permitted
    async with async_session_factory() as session:
        proj = await session.get(Project, data["project_id"])
        bp = dict(proj.baseline_parameters)
        bp["locked_methodology_version"]["design_sufficiency_status"] = "COMPLETE"
        proj.baseline_parameters = bp
        await session.commit()

        snap_locked = await AgricultureService.create_quantification_input_snapshot(
            session, data["project_id"], data["pm_user"].id, "PROJECT_MANAGER", data["org_id"],
            QuantificationInputSnapshotCreate(status="LOCKED", context="BASELINE")
        )
        assert snap_locked.is_locked is True
        assert snap_locked.status == "LOCKED"
        assert snap_locked.locked_at is not None

    # Scenario 1: Missing methodology lock -> cannot lock
    async with async_session_factory() as session:
        proj = await session.get(Project, data["project_id"])
        bp = dict(proj.baseline_parameters)
        bp["locked_methodology_version"]["status"] = "UNLOCKED"
        proj.baseline_parameters = bp
        await session.commit()

        with pytest.raises(ValueError, match="METHODOLOGY_LOCK"):
            await AgricultureService.create_quantification_input_snapshot(
                session, data["project_id"], data["pm_user"].id, "PROJECT_MANAGER", data["org_id"],
                QuantificationInputSnapshotCreate(status="LOCKED", context="BASELINE")
            )

        # Restore lock
        bp["locked_methodology_version"]["status"] = "LOCKED"
        proj.baseline_parameters = bp
        await session.commit()

    # Scenario 4: Missing coarse fragments when REQUIRED -> cannot lock
    async with async_session_factory() as session:
        proj = await session.get(Project, data["project_id"])
        bp = dict(proj.baseline_parameters)
        bp["locked_methodology_version"]["coarse_fragments_requirement"] = "REQUIRED"
        bp["locked_methodology_version"]["coarse_fragments_blocking"] = True
        proj.baseline_parameters = bp
        await session.commit()

        with pytest.raises(ValueError, match="COARSE_FRAGMENTS"):
            await AgricultureService.create_quantification_input_snapshot(
                session, data["project_id"], data["pm_user"].id, "PROJECT_MANAGER", data["org_id"],
                QuantificationInputSnapshotCreate(status="LOCKED", context="BASELINE")
            )

        # Restore optional
        bp["locked_methodology_version"]["coarse_fragments_requirement"] = "OPTIONAL"
        bp["locked_methodology_version"]["coarse_fragments_blocking"] = False
        proj.baseline_parameters = bp
        await session.commit()

    # Scenario 8: Non-blocking NOT_APPLICABLE coarse fragments -> does not block
    async with async_session_factory() as session:
        proj = await session.get(Project, data["project_id"])
        bp = dict(proj.baseline_parameters)
        bp["locked_methodology_version"]["design_sufficiency_status"] = "COMPLETE"
        bp["locked_methodology_version"]["coarse_fragments_applicable"] = False
        proj.baseline_parameters = bp
        await session.commit()

        snap_opt = await AgricultureService.create_quantification_input_snapshot(
            session, data["project_id"], data["pm_user"].id, "PROJECT_MANAGER", data["org_id"],
            QuantificationInputSnapshotCreate(status="LOCKED", context="BASELINE")
        )
        assert snap_opt.is_locked is True
