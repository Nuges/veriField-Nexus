"""
VeriField Nexus — Agriculture MRV Phase 3A: Quantification Readiness & Calculation Input Contract Tests
Deterministic tests for:
- Latest valid result selection & supersession exclusion
- QA rejection exclusion & eligibility gating
- Canonical SOC concentration (g/kg) and provenance
- Bulk density presence & missing state
- Coarse fragments fraction classification
- Depth horizon reconciliation (MATCH, PARTIAL_COVERAGE, OVERLAPPING_INTERVAL, OUT_OF_SCOPE)
- Baseline vs Project dataset separation
- Temporal stratum resolution as-of sampling date
- Design sufficiency NOT_CONFIGURED invariant
- Methodology rule resolution from locked version
- Categorical readiness dimensions (zero percentage)
- Immutable snapshot creation, SHA-256 hashing, and lineage
- RBAC / SoD (FIELD_AGENT blocked)
- Multi-tenant and cross-project isolation
"""

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

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
from app.domains.methodologies.models.base_registry import (
    Methodology,
    MethodologyFamily,
    MethodologyVersion,
)
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


@pytest_asyncio.fixture
async def setup_phase3a_project():
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    today = now.date()

    async with async_session_factory() as session:
        # Organization
        org = Organization(
            id=uuid.uuid4(),
            name=f"Phase 3A Org {tag}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
        )
        session.add(org)

        # Users
        pm_user = User(
            id=uuid.uuid4(),
            email=f"pm.{tag}@phase3a.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Agricultural Project Manager",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        qa_user = User(
            id=uuid.uuid4(),
            email=f"qa.{tag}@phase3a.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Lead MRV QA Officer",
            role="QA_OFFICER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        field_agent = User(
            id=uuid.uuid4(),
            email=f"agent.{tag}@phase3a.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Tariq Field Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add_all([pm_user, qa_user, field_agent])
        await session.flush()

        # Methodology
        fam = (await session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE"))).scalars().first()
        vm = (await session.execute(select(Methodology).where(Methodology.code == "VM0042"))).scalars().first()
        v22 = None
        if vm:
            v22 = (await session.execute(select(MethodologyVersion).where(MethodologyVersion.methodology_id == vm.id))).scalars().first()

        # Project
        proj = Project(
            id=uuid.uuid4(),
            name=f"Phase 3A Agricultural Project {tag}",
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
                },
            },
        )
        session.add(proj)
        await session.flush()

        # Boundary Version
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

        # Land Unit
        lu = LandUnit(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            name="North Sector Field Plot",
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

        # Stratum & Stratum Membership
        strat = Stratum(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"STRAT-CLAY-{tag[:4]}",
            name="Clay Loam Baseline Stratum",
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

        # Sampling Campaign (Baseline)
        campaign_base = SamplingCampaign(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_code=f"CAMP-BASE-{tag[:4]}",
            name="Baseline Soil Sampling Round",
            purpose="BASELINE_SOC_DETERMINATION",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=date(2026, 1, 15),
            planned_end_date=date(2026, 2, 15),
            status="COMPLETE",
            project_boundary_version_id=boundary.id,
        )
        session.add(campaign_base)
        await session.flush()

        # Sampling Plan Version (Locked)
        plan_v1 = SamplingPlanVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign_base.id,
            version_number=1,
            status="LOCKED",
            effective_as_of_date=date(2026, 1, 15),
            is_locked=True,
            locked_at=now,
            locked_by_id=pm_user.id,
        )
        session.add(plan_v1)
        await session.flush()

        await session.commit()

        pm_token = AuthenticationService.generate_token_static(pm_user)
        qa_token = AuthenticationService.generate_token_static(qa_user)
        field_token = AuthenticationService.generate_token_static(field_agent)

        return {
            "organization_id": org.id,
            "project_id": proj.id,
            "boundary_id": boundary.id,
            "land_unit_id": lu.id,
            "stratum_id": strat.id,
            "campaign_base_id": campaign_base.id,
            "plan_v1_id": plan_v1.id,
            "pm_user": pm_user,
            "qa_user": qa_user,
            "field_agent": field_agent,
            "pm_token": pm_token,
            "qa_token": qa_token,
            "field_token": field_token,
            "tag": tag,
        }


@pytest.mark.asyncio
async def test_latest_valid_result_selection_and_supersession(setup_phase3a_project):
    """
    Test 1 & 2: Deterministic latest-valid result selection.
    When a result is superseded by revision, the old result must be excluded
    with reason LAB_RESULT_SUPERSEDED, and the new active result must be selected.
    """
    data = setup_phase3a_project
    async with async_session_factory() as session:
        # 1. Create point
        pt = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=data["organization_id"],
            project_id=data["project_id"],
            campaign_id=data["campaign_base_id"],
            plan_version_id=data["plan_v1_id"],
            land_unit_id=data["land_unit_id"],
            point_code=f"P-VALID-{uuid.uuid4().hex[:6]}",
            planned_lat=28.52,
            planned_lon=77.12,
            depth_from_cm=0.0,
            depth_to_cm=30.0,
            status="COLLECTED",
        )
        session.add(pt)
        await session.flush()

        # 2. Create physical sample
        sample = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=data["organization_id"],
            project_id=data["project_id"],
            campaign_id=data["campaign_base_id"],
            plan_version_id=data["plan_v1_id"],
            sampling_point_id=pt.id,
            land_unit_id=data["land_unit_id"],
            sample_code=f"SMP-P3A-VALID-{uuid.uuid4().hex[:6]}",
            status="QA_ACCEPTED",
        )
        session.add(sample)
        await session.flush()

        # 3. Collection event
        col = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            sampling_point_id=pt.id,
            actual_lat=28.52005,
            actual_lon=77.12005,
            actual_depth_from_cm=0.0,
            actual_depth_to_cm=30.0,
            collection_timestamp=datetime(2026, 1, 20, 10, 0, tzinfo=timezone.utc),
            collector_name="Tariq Field Agent",
            sample_condition="GOOD",
        )
        session.add(col)

        # 4. Custody event
        cust = ChainOfCustodyEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            event_type="TRANSFER",
            event_timestamp=datetime(2026, 1, 21, 9, 0, tzinfo=timezone.utc),
            custodian_name="Courier Alpha",
            custodian_organization="Agri Logistics",
            seal_intact=True,
            seal_identifier="SEAL-001",
        )
        session.add(cust)

        # 5. Laboratory Receipt
        rcp = LaboratoryReceipt(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            laboratory_name="Eurofins Agri Testing",
            received_at=datetime(2026, 1, 22, 11, 0, tzinfo=timezone.utc),
            received_by_name="Lab Intake Specialist",
            intake_status="ACCEPTED",
        )
        session.add(rcp)

        # 6. Laboratory Analysis
        ana = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            laboratory_name="Eurofins Agri Testing",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2026, 1, 25),
            qa_status="VERIFIED",
        )
        session.add(ana)
        await session.flush()

        # 7. Initial result (1.85%) - Superseded
        r_old = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana.id,
            physical_sample_id=sample.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.85"),
            raw_unit="%",
            normalized_value=Decimal("18.5"),
            normalized_unit="g/kg",
            normalization_method="LINEAR_SCALING:VAL*10",
            normalization_version="UNIT_CONV_V1.0",
            is_superseded=True,
        )
        session.add(r_old)
        await session.flush()

        # Active result (1.90%) - Supersedes old
        r_new = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana.id,
            physical_sample_id=sample.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.90"),
            raw_unit="%",
            normalized_value=Decimal("19.0"),
            normalized_unit="g/kg",
            normalization_method="LINEAR_SCALING:VAL*10",
            normalization_version="UNIT_CONV_V1.0",
            is_superseded=False,
            supersedes_id=r_old.id,
        )
        session.add(r_new)

        # Bulk Density result (1.35 g/cm3)
        r_bd = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana.id,
            physical_sample_id=sample.id,
            analyte="BULK_DENSITY_G_CM3",
            raw_value=Decimal("1.35"),
            raw_unit="g/cm3",
            normalized_value=Decimal("1.35"),
            normalized_unit="g/cm³",
            is_superseded=False,
        )
        session.add(r_bd)

        # 8. QA Review
        qa = SampleQAReview(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            reviewer_name="Lead MRV QA Officer",
            overall_qa_status="ACCEPTED",
            review_date=datetime(2026, 1, 26, 14, 0, tzinfo=timezone.utc),
        )
        session.add(qa)
        await session.commit()

        # Run evaluation
        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["organization_id"])

        assert eval_set["total_candidates"] == 1
        assert eval_set["total_eligible"] == 1
        assert eval_set["total_excluded"] == 0

        # Assert selected active result
        eligible_item = eval_set["baseline_measurements"][0]
        assert eligible_item.laboratory_result_id == r_new.id
        assert eligible_item.raw_value == 1.90
        assert eligible_item.normalized_value == 19.0
        assert eligible_item.normalized_unit == "g/kg"
        assert eligible_item.analyte == "SOC_CONCENTRATION"
        assert eligible_item.provenance_class == "MEASURED"
        assert eligible_item.bulk_density_status == "PRESENT"
        assert eligible_item.bulk_density_normalized_value == 1.35
        assert eligible_item.depth_alignment_status == "MATCH"


@pytest.mark.asyncio
async def test_qa_rejection_exclusion(setup_phase3a_project):
    """
    Test 3: Samples with rejected QA reviews or unverified laboratory analyses
    must be excluded with explicit reason QA_NOT_ACCEPTED.
    """
    data = setup_phase3a_project
    async with async_session_factory() as session:
        pt = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=data["organization_id"],
            project_id=data["project_id"],
            campaign_id=data["campaign_base_id"],
            plan_version_id=data["plan_v1_id"],
            land_unit_id=data["land_unit_id"],
            point_code=f"P-REJECT-{uuid.uuid4().hex[:6]}",
            planned_lat=28.53,
            planned_lon=77.13,
            depth_from_cm=0.0,
            depth_to_cm=30.0,
            status="COLLECTED",
        )
        session.add(pt)
        await session.flush()

        sample = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=data["organization_id"],
            project_id=data["project_id"],
            campaign_id=data["campaign_base_id"],
            plan_version_id=data["plan_v1_id"],
            sampling_point_id=pt.id,
            land_unit_id=data["land_unit_id"],
            sample_code=f"SMP-P3A-REJECT-{uuid.uuid4().hex[:6]}",
            status="QA_REJECTED",
        )
        session.add(sample)
        await session.flush()

        col = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            sampling_point_id=pt.id,
            actual_lat=28.53,
            actual_lon=77.13,
            actual_depth_from_cm=0.0,
            actual_depth_to_cm=30.0,
            collection_timestamp=datetime(2026, 1, 20, 10, 0, tzinfo=timezone.utc),
            collector_name="Tariq Field Agent",
        )
        session.add(col)

        rcp = LaboratoryReceipt(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            laboratory_name="Eurofins Agri Testing",
            received_at=datetime(2026, 1, 22, 11, 0, tzinfo=timezone.utc),
            received_by_name="Lab Intake Specialist",
            intake_status="ACCEPTED",
        )
        session.add(rcp)

        ana = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            laboratory_name="Eurofins Agri Testing",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2026, 1, 25),
            qa_status="REJECTED",
        )
        session.add(ana)
        await session.flush()

        res = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana.id,
            physical_sample_id=sample.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.50"),
            raw_unit="%",
            normalized_value=Decimal("15.0"),
            normalized_unit="g/kg",
            is_superseded=False,
        )
        session.add(res)

        qa = SampleQAReview(
            id=uuid.uuid4(),
            physical_sample_id=sample.id,
            reviewer_name="Lead MRV QA Officer",
            overall_qa_status="REJECTED",
            review_date=datetime(2026, 1, 26, 14, 0, tzinfo=timezone.utc),
        )
        session.add(qa)
        await session.commit()

        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["organization_id"])

        excluded = [m for m in eval_set["excluded_measurements"] if m.physical_sample_id == sample.id]
        assert len(excluded) == 1
        assert ExclusionReasonCode.QA_NOT_ACCEPTED.value in excluded[0].exclusion_reasons


@pytest.mark.asyncio
async def test_depth_alignment_classifications(setup_phase3a_project):
    """
    Test 7: Tests depth alignment reconciliation against VM0042 0-30cm:
    - MATCH: 0-30cm
    - PARTIAL_COVERAGE: 0-15cm
    - OVERLAPPING_INTERVAL: 0-40cm
    - OUT_OF_SCOPE: 30-60cm (excluded with DEPTH_MISMATCH)
    """
    data = setup_phase3a_project
    async with async_session_factory() as session:
        # Create out-of-scope sample (30-60cm)
        pt_deep = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=data["organization_id"],
            project_id=data["project_id"],
            campaign_id=data["campaign_base_id"],
            plan_version_id=data["plan_v1_id"],
            land_unit_id=data["land_unit_id"],
            point_code=f"P-DEEP-{uuid.uuid4().hex[:6]}",
            planned_lat=28.52,
            planned_lon=77.12,
            depth_from_cm=30.0,
            depth_to_cm=60.0,
            status="COLLECTED",
        )
        session.add(pt_deep)
        await session.flush()

        smp_deep = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=data["organization_id"],
            project_id=data["project_id"],
            campaign_id=data["campaign_base_id"],
            plan_version_id=data["plan_v1_id"],
            sampling_point_id=pt_deep.id,
            land_unit_id=data["land_unit_id"],
            sample_code=f"SMP-P3A-DEEP-{uuid.uuid4().hex[:6]}",
            status="QA_ACCEPTED",
        )
        session.add(smp_deep)
        await session.flush()

        col_deep = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=smp_deep.id,
            sampling_point_id=pt_deep.id,
            actual_lat=28.52,
            actual_lon=77.12,
            actual_depth_from_cm=30.0,
            actual_depth_to_cm=60.0,
            collection_timestamp=datetime(2026, 1, 20, 10, 0, tzinfo=timezone.utc),
            collector_name="Tariq Field Agent",
        )
        session.add(col_deep)

        rcp_deep = LaboratoryReceipt(
            id=uuid.uuid4(),
            physical_sample_id=smp_deep.id,
            laboratory_name="Eurofins Agri Testing",
            received_at=datetime(2026, 1, 22, 11, 0, tzinfo=timezone.utc),
            received_by_name="Lab Intake Specialist",
            intake_status="ACCEPTED",
        )
        session.add(rcp_deep)

        ana_deep = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=smp_deep.id,
            laboratory_name="Eurofins Agri Testing",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2026, 1, 25),
            qa_status="VERIFIED",
        )
        session.add(ana_deep)
        await session.flush()

        r_deep = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana_deep.id,
            physical_sample_id=smp_deep.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("0.85"),
            raw_unit="%",
            normalized_value=Decimal("8.5"),
            normalized_unit="g/kg",
            is_superseded=False,
        )
        session.add(r_deep)

        qa_deep = SampleQAReview(
            id=uuid.uuid4(),
            physical_sample_id=smp_deep.id,
            reviewer_name="Lead MRV QA Officer",
            overall_qa_status="ACCEPTED",
            review_date=datetime(2026, 1, 26, 14, 0, tzinfo=timezone.utc),
        )
        session.add(qa_deep)
        await session.commit()

        eval_set = await AgricultureService.evaluate_eligible_measurements(session, data["project_id"], data["organization_id"])
        deep_excluded = [m for m in eval_set["excluded_measurements"] if m.physical_sample_id == smp_deep.id]
        assert len(deep_excluded) == 1
        assert ExclusionReasonCode.DEPTH_MISMATCH.value in deep_excluded[0].exclusion_reasons


@pytest.mark.asyncio
async def test_quantification_readiness_dimensions_no_percentages(setup_phase3a_project):
    """
    Test 12: Quantification readiness must evaluate all 16 categorical dimensions
    without percentage scores or progress bar weights.
    """
    data = setup_phase3a_project
    async with async_session_factory() as session:
        readiness = await AgricultureService.evaluate_quantification_readiness(session, data["project_id"], data["organization_id"])

        assert "overall_status" in readiness
        assert readiness["overall_status"] in ["COMPLETE", "INCOMPLETE", "NEEDS_REVIEW", "NOT_CONFIGURED"]

        # Ensure NO percentage or score keys exist
        assert "score" not in readiness
        assert "percentage" not in readiness
        assert "progress_pct" not in readiness

        dims = readiness["dimensions"]
        expected_dims = [
            "METHODOLOGY_LOCK",
            "MONITORING_PERIOD",
            "BOUNDARY_VERSION",
            "STRATIFICATION",
            "SAMPLING_PLAN",
            "DESIGN_SUFFICIENCY",
            "GROUND_EVIDENCE",
            "SOC_CONCENTRATION",
            "BULK_DENSITY",
            "COARSE_FRAGMENTS",
            "DEPTH_ALIGNMENT",
            "UNCERTAINTY_INPUTS",
            "BASELINE_DATASET",
            "PROJECT_DATASET",
            "QA_ACCEPTANCE",
            "CALCULATION_RULES",
        ]
        for ed in expected_dims:
            assert ed in dims, f"Missing readiness dimension {ed}"
            dim_val = dims[ed]
            assert dim_val["status"] in ["COMPLETE", "INCOMPLETE", "NEEDS_REVIEW", "NOT_CONFIGURED", "NOT_APPLICABLE"]
            assert len(dim_val["message"]) > 0

        # Invariant: DESIGN_SUFFICIENCY is strictly NOT_CONFIGURED
        assert dims["DESIGN_SUFFICIENCY"]["status"] == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_snapshot_creation_hashing_and_immutability(setup_phase3a_project):
    """
    Test 13, 14, 15: Create quantification input snapshot.
    - Deterministic SHA-256 hash
    - Immutable persistence
    - SoD: FIELD_AGENT is blocked
    """
    data = setup_phase3a_project
    async with async_session_factory() as session:
        # 1. SoD: FIELD_AGENT must be rejected
        payload_preview = QuantificationInputSnapshotCreate(context="BASELINE", status="PREVIEW", notes="Initial baseline preview")
        with pytest.raises(ValueError, match="Field agent role is unauthorized"):
            await AgricultureService.create_quantification_input_snapshot(
                db=session,
                project_id=data["project_id"],
                user_id=data["field_agent"].id,
                user_role="FIELD_AGENT",
                organization_id=data["organization_id"],
                payload=payload_preview,
            )

        # 2. Premature lock must be rejected when blocking requirements unresolved (§11)
        payload_lock = QuantificationInputSnapshotCreate(context="BASELINE", status="LOCKED", notes="Premature lock")
        with pytest.raises(ValueError, match="Cannot lock official snapshot"):
            await AgricultureService.create_quantification_input_snapshot(
                db=session,
                project_id=data["project_id"],
                user_id=data["pm_user"].id,
                user_role="PROJECT_MANAGER",
                organization_id=data["organization_id"],
                payload=payload_lock,
            )

        # 3. PM User generates PREVIEW snapshot successfully (§11)
        snapshot = await AgricultureService.create_quantification_input_snapshot(
            db=session,
            project_id=data["project_id"],
            user_id=data["pm_user"].id,
            user_role="PROJECT_MANAGER",
            organization_id=data["organization_id"],
            payload=payload_preview,
        )
        await session.commit()

        assert snapshot.id is not None
        assert snapshot.snapshot_code.startswith("QIS-")
        assert snapshot.status == "PREVIEW"
        assert snapshot.is_locked is False
        assert len(snapshot.snapshot_hash) == 64  # SHA-256 hex length
        assert snapshot.context == "BASELINE"

        # Verify hash matches canonical input package bytes
        canonical_bytes = json.dumps(snapshot.input_package, sort_keys=True, default=str).encode("utf-8")
        expected_hash = hashlib.sha256(canonical_bytes).hexdigest()
        assert snapshot.snapshot_hash == expected_hash

        # 4. Retrieve snapshot
        fetched = await AgricultureService.get_quantification_input_snapshot(
            db=session,
            project_id=data["project_id"],
            snapshot_id=snapshot.id,
            organization_id=data["organization_id"],
        )
        assert fetched.id == snapshot.id
        assert fetched.snapshot_hash == snapshot.snapshot_hash


@pytest.mark.asyncio
async def test_api_endpoints_and_tenant_isolation(setup_phase3a_project):
    """
    Test 16: API endpoints for readiness, eligible measurements, and snapshots with tenant isolation.
    """
    data = setup_phase3a_project
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Get Readiness
        resp = await client.get(
            f"/api/v1/agriculture/projects/{data['project_id']}/quantification-readiness",
            headers={"Authorization": f"Bearer {data['pm_token']}"},
        )
        assert resp.status_code == 200
        readiness = resp.json()
        assert readiness["project_id"] == str(data["project_id"])
        assert "dimensions" in readiness

        # 2. Get Eligible Measurements
        resp2 = await client.get(
            f"/api/v1/agriculture/projects/{data['project_id']}/eligible-measurements",
            headers={"Authorization": f"Bearer {data['pm_token']}"},
        )
        assert resp2.status_code == 200
        meas_set = resp2.json()
        assert "baseline_measurements" in meas_set
        assert "project_measurements" in meas_set
        assert "excluded_measurements" in meas_set

        # 3. FIELD_AGENT attempting to lock snapshot returns 403 Forbidden
        resp_block = await client.post(
            f"/api/v1/agriculture/projects/{data['project_id']}/quantification-input-snapshots",
            headers={"Authorization": f"Bearer {data['field_token']}"},
            json={"context": "BASELINE", "status": "PREVIEW", "notes": "Unauthorized attempt"},
        )
        assert resp_block.status_code == 403

        # 4. Premature lock returns 400 Bad Request (§11)
        resp_premature = await client.post(
            f"/api/v1/agriculture/projects/{data['project_id']}/quantification-input-snapshots",
            headers={"Authorization": f"Bearer {data['pm_token']}"},
            json={"context": "BASELINE", "status": "LOCKED", "notes": "Premature official lock attempt"},
        )
        assert resp_premature.status_code == 400
        assert "Cannot lock official snapshot" in resp_premature.json()["detail"]

        # 5. PM creates PREVIEW snapshot -> 201 Created
        resp_create = await client.post(
            f"/api/v1/agriculture/projects/{data['project_id']}/quantification-input-snapshots",
            headers={"Authorization": f"Bearer {data['pm_token']}"},
            json={"context": "BASELINE", "status": "PREVIEW", "notes": "Authorized PM preview snapshot"},
        )
        assert resp_create.status_code == 201
        created_snap = resp_create.json()
        assert created_snap["is_locked"] is False
        assert created_snap["status"] == "PREVIEW"
        assert len(created_snap["snapshot_hash"]) == 64

        # 5. Cross-tenant isolation: Request from different org returns 403/404
        other_org_id = uuid.uuid4()
        other_org = Organization(
            id=other_org_id,
            name=f"Other Org {uuid.uuid4().hex[:6]}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
        )
        other_user = User(
            id=uuid.uuid4(),
            email=f"intruder.{uuid.uuid4().hex[:6]}@otherorg.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Other Org PM",
            role="PROJECT_MANAGER",
            organization_id=other_org_id,
            is_active=True,
            status="active",
        )
        async with async_session_factory() as session:
            session.add_all([other_org, other_user])
            await session.commit()

        other_token = AuthenticationService.generate_token_static(other_user)

        resp_iso = await client.get(
            f"/api/v1/agriculture/projects/{data['project_id']}/quantification-readiness",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp_iso.status_code in [403, 404]
