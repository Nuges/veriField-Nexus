"""
VeriField Nexus — Laboratory Analysis State & Readiness Gating Deterministic Unit Tests
Verifies:
1. LaboratoryAnalysis creation defaults to qa_status = 'PENDING'.
2. Gating: When an analysis is 'PENDING', Ground Evidence Readiness qa_review is 'INCOMPLETE' and cannot be 'COMPLETE'.
3. QA review ACCEPTED propagates qa_status = 'VERIFIED' to associated LaboratoryAnalysis records.
4. When all analyses are 'VERIFIED' and sample QA review is 'ACCEPTED', readiness transitions to 'COMPLETE'.
5. QA review REJECTED propagates qa_status = 'REJECTED' to associated LaboratoryAnalysis records.
6. When an analysis or review is 'REJECTED', readiness transitions to 'NEEDS_REVIEW'.
"""

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.methodologies.models import MethodologyFamily, Methodology, MethodologyVersion
from app.domains.agriculture.models import (
    LandUnit,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    PhysicalSample,
    SampleCollectionEvent,
    ChainOfCustodyEvent,
    LaboratoryReceipt,
    LaboratoryAnalysis,
    LaboratoryResult,
    SampleQAReview,
    Stratum,
)
from app.domains.agriculture.schemas import (
    LabAnalysisCreate,
    LabResultCreate,
    SampleQAReviewCreate,
)
from app.domains.agriculture.service import AgricultureService


@pytest_asyncio.fixture
async def full_sample_fixture(db_session):
    """
    Sets up a fully configured physical sample up to laboratory receipt stage.
    """
    org = Organization(name=f"State Test Org {uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    fam_res = await db_session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE"))
    agri_family = fam_res.scalars().first()

    m42_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0042"))
    vm0042 = m42_res.scalars().first()

    v22 = None
    if vm0042:
        v22_res = await db_session.execute(
            select(MethodologyVersion).where(
                MethodologyVersion.methodology_id == vm0042.id,
            )
        )
        v22 = v22_res.scalars().first()

    proj = Project(
        name=f"State Test Project {uuid.uuid4().hex[:8]}",
        project_code=f"AGR-STAT-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        sector_id=agri_family.id if agri_family else None,
        methodology_id=vm0042.id if vm0042 else None,
        methodology_version_id=v22.id if v22 else None,
    )
    db_session.add(proj)
    await db_session.flush()

    lu = LandUnit(
        organization_id=org.id,
        project_id=proj.id,
        name="Field Parcel 1",
        code=f"FLD-{uuid.uuid4().hex[:4]}",
        area_ha=10.0,
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]],
        },
        geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
        is_active=True,
    )
    db_session.add(lu)
    await db_session.flush()

    stratum = Stratum(
        project_id=proj.id,
        organization_id=org.id,
        code="STRAT-01",
        name="Topsoil Stratum",
        stratum_type="SOIL_TYPE",
    )
    db_session.add(stratum)
    await db_session.flush()

    camp = SamplingCampaign(
        project_id=proj.id,
        organization_id=org.id,
        campaign_code=f"CAMP-{uuid.uuid4().hex[:6]}",
        name="Test Campaign",
        planned_start_date=date.today(),
        status="LAB_IN_PROGRESS",
    )
    db_session.add(camp)
    await db_session.flush()

    plan = SamplingPlanVersion(
        campaign_id=camp.id,
        project_id=proj.id,
        organization_id=org.id,
        version_number=1,
        effective_as_of_date=date.today(),
        is_locked=True,
        locked_at=datetime.now(timezone.utc),
    )
    db_session.add(plan)
    await db_session.flush()

    pt = SamplingPoint(
        campaign_id=camp.id,
        plan_version_id=plan.id,
        project_id=proj.id,
        organization_id=org.id,
        land_unit_id=lu.id,
        stratum_id=stratum.id,
        point_code="PT-01",
        planned_lat=28.5200,
        planned_lon=77.1200,
        geom="SRID=4326;POINT(77.1200 28.5200)",
    )
    db_session.add(pt)
    await db_session.flush()

    sample = PhysicalSample(
        sampling_point_id=pt.id,
        campaign_id=camp.id,
        project_id=proj.id,
        organization_id=org.id,
        land_unit_id=lu.id,
        stratum_id=stratum.id,
        sample_code=f"SMP-{uuid.uuid4().hex[:6]}",
        status="RECEIVED_BY_LAB",
    )
    db_session.add(sample)
    await db_session.flush()

    col = SampleCollectionEvent(
        physical_sample_id=sample.id,
        sampling_point_id=pt.id,
        collector_name="Field Tech Alpha",
        actual_lat=28.52001,
        actual_lon=77.12001,
        deviation_distance_m=1.2,
        collection_timestamp=datetime.now(timezone.utc),
    )
    db_session.add(col)

    coc = ChainOfCustodyEvent(
        physical_sample_id=sample.id,
        event_type="DISPATCH_TO_LAB",
        custodian_name="Courier Charlie",
        custodian_organization="FastFreight",
        event_timestamp=datetime.now(timezone.utc),
        seal_identifier="SEAL-001",
        seal_intact=True,
    )
    db_session.add(coc)

    receipt = LaboratoryReceipt(
        physical_sample_id=sample.id,
        laboratory_name="Certified AgroLab",
        received_by_name="Lab Tech Luna",
        received_at=datetime.now(timezone.utc),
        intake_status="ACCEPTED",
        condition_on_receipt="ACCEPTABLE",
        seal_status="SEALED_INTACT",
    )
    db_session.add(receipt)
    await db_session.commit()

    return {
        "org_id": org.id,
        "project_id": proj.id,
        "sample_id": sample.id,
    }


@pytest.mark.asyncio
async def test_lab_analysis_initial_pending_state_and_readiness_gating(db_session, full_sample_fixture):
    """
    Test that a newly recorded LaboratoryAnalysis defaults to 'PENDING',
    and Ground Evidence Readiness gates qa_review as 'INCOMPLETE'.
    """
    org_id = full_sample_fixture["org_id"]
    project_id = full_sample_fixture["project_id"]
    sample_id = full_sample_fixture["sample_id"]

    # Record laboratory analysis
    payload = LabAnalysisCreate(
        laboratory_name="Certified AgroLab",
        analysis_date=date.today(),
        analytical_method="DRY_COMBUSTION",
        results=[
            LabResultCreate(
                analyte="SOC_CONCENTRATION",
                raw_value=Decimal("1.85"),
                raw_unit="%",
            )
        ],
    )
    analysis = await AgricultureService.record_laboratory_analysis(
        db=db_session,
        sample_id=sample_id,
        organization_id=org_id,
        payload=payload,
    )
    await db_session.commit()

    # 1. Assert analysis qa_status defaults to PENDING
    assert analysis.qa_status == "PENDING"

    # 2. Evaluate readiness before QA review signoff
    readiness = await AgricultureService.evaluate_ground_evidence_readiness(
        db=db_session,
        project_id=project_id,
        organization_id=org_id,
    )

    # Required assays is complete (data recorded)
    assert readiness["components"]["required_assays"]["status"] == "COMPLETE"
    assert readiness["components"]["required_assays"]["details"]["pending_analyses"] == 1

    # But QA review is INCOMPLETE because analysis is still PENDING
    assert readiness["components"]["qa_review"]["status"] == "INCOMPLETE"
    assert "pending QA verification" in readiness["components"]["qa_review"]["message"]
    assert readiness["overall_status"] == "INCOMPLETE"


@pytest.mark.asyncio
async def test_qa_review_acceptance_synchronization_and_readiness_complete(db_session, full_sample_fixture):
    """
    Test that submitting an ACCEPTED QA review:
    1. Sets PhysicalSample.status = 'QA_ACCEPTED'
    2. Synchronizes LaboratoryAnalysis.qa_status = 'VERIFIED'
    3. Ground Evidence Readiness qa_review transitions to 'COMPLETE'
    4. Overall Ground Evidence Readiness transitions to 'COMPLETE'
    """
    org_id = full_sample_fixture["org_id"]
    project_id = full_sample_fixture["project_id"]
    sample_id = full_sample_fixture["sample_id"]

    # 1. Record laboratory analysis
    payload_analysis = LabAnalysisCreate(
        laboratory_name="Certified AgroLab",
        analysis_date=date.today(),
        analytical_method="DRY_COMBUSTION",
        results=[
            LabResultCreate(
                analyte="SOC_CONCENTRATION",
                raw_value=Decimal("1.85"),
                raw_unit="%",
            )
        ],
    )
    analysis = await AgricultureService.record_laboratory_analysis(
        db=db_session,
        sample_id=sample_id,
        organization_id=org_id,
        payload=payload_analysis,
    )
    await db_session.commit()
    assert analysis.qa_status == "PENDING"

    # 2. Record QA Review with ACCEPTED
    payload_qa = SampleQAReviewCreate(
        reviewer_name="Senior MRV Lead",
        overall_qa_status="ACCEPTED",
        location_verified=True,
        deviation_acceptable=True,
        depth_valid=True,
        custody_complete=True,
        lab_receipt_verified=True,
        required_assays_present=True,
        notes="All assays conform to VM0042 standards.",
    )
    qa_review = await AgricultureService.record_sample_qa_review(
        db=db_session,
        sample_id=sample_id,
        organization_id=org_id,
        payload=payload_qa,
    )
    await db_session.commit()

    # 3. Verify sample and analysis statuses in database
    sample = await AgricultureService.get_physical_sample_by_id(db_session, sample_id, org_id)
    assert sample.status == "QA_ACCEPTED"

    # Refresh analysis from database
    refreshed_analysis = await db_session.get(LaboratoryAnalysis, analysis.id)
    assert refreshed_analysis.qa_status == "VERIFIED"

    # 4. Verify Ground Evidence Readiness is now COMPLETE
    readiness = await AgricultureService.evaluate_ground_evidence_readiness(
        db=db_session,
        project_id=project_id,
        organization_id=org_id,
    )
    assert readiness["components"]["qa_review"]["status"] == "COMPLETE"
    assert readiness["components"]["qa_review"]["details"]["pending_analyses"] == 0
    assert readiness["components"]["qa_review"]["details"]["verified_analyses"] == 1
    assert readiness["overall_status"] == "COMPLETE"


@pytest.mark.asyncio
async def test_qa_review_rejection_synchronization_and_readiness_needs_review(db_session, full_sample_fixture):
    """
    Test that submitting a REJECTED QA review:
    1. Sets PhysicalSample.status = 'QA_REJECTED'
    2. Synchronizes LaboratoryAnalysis.qa_status = 'REJECTED'
    3. Ground Evidence Readiness qa_review transitions to 'NEEDS_REVIEW'
    4. Overall Ground Evidence Readiness transitions to 'NEEDS_REVIEW'
    """
    org_id = full_sample_fixture["org_id"]
    project_id = full_sample_fixture["project_id"]
    sample_id = full_sample_fixture["sample_id"]

    # 1. Record laboratory analysis
    payload_analysis = LabAnalysisCreate(
        laboratory_name="Certified AgroLab",
        analysis_date=date.today(),
        analytical_method="DRY_COMBUSTION",
        results=[
            LabResultCreate(
                analyte="SOC_CONCENTRATION",
                raw_value=Decimal("1.85"),
                raw_unit="%",
            )
        ],
    )
    analysis = await AgricultureService.record_laboratory_analysis(
        db=db_session,
        sample_id=sample_id,
        organization_id=org_id,
        payload=payload_analysis,
    )
    await db_session.commit()

    # 2. Record QA Review with REJECTED
    payload_qa = SampleQAReviewCreate(
        reviewer_name="Senior MRV Lead",
        overall_qa_status="REJECTED",
        location_verified=False,
        notes="Sample location exceeds spatial tolerance bounds.",
    )
    await AgricultureService.record_sample_qa_review(
        db=db_session,
        sample_id=sample_id,
        organization_id=org_id,
        payload=payload_qa,
    )
    await db_session.commit()

    # 3. Verify sample and analysis statuses in database
    sample = await AgricultureService.get_physical_sample_by_id(db_session, sample_id, org_id)
    assert sample.status == "QA_REJECTED"

    refreshed_analysis = await db_session.get(LaboratoryAnalysis, analysis.id)
    assert refreshed_analysis.qa_status == "REJECTED"

    # 4. Verify Ground Evidence Readiness transitions to NEEDS_REVIEW
    readiness = await AgricultureService.evaluate_ground_evidence_readiness(
        db=db_session,
        project_id=project_id,
        organization_id=org_id,
    )
    assert readiness["components"]["qa_review"]["status"] == "NEEDS_REVIEW"
    assert readiness["components"]["qa_review"]["details"]["rejected_analyses"] == 1
    assert readiness["overall_status"] == "NEEDS_REVIEW"
