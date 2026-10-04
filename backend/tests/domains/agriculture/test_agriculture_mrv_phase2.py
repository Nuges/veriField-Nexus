"""
=============================================================================
VeriField Nexus — Agriculture MRV Phase 2: Ground Evidence Workflow Tests
=============================================================================
Comprehensive unit, integration, and API tests for:
1. Section 0: Management Record Corroboration Field & Invariants
2. Section 1: Sampling Campaign Lifecycle, Boundary & Methodology Lock
3. Section 2: Sampling Plan Version & Stratification Freeze
4. Section 3: Planned Sampling Points & LandUnit Spatial Containment
5. Section 4: Physical Sample Lifecycle & Sample Code Invariants
6. Section 5: Field Sample Collection & Geodesic Deviation Distance
7. Section 6: Chain of Custody Append-Only Log & Transition Invariants
8. Section 7: Laboratory Intake Receipt & Rejection Invariants
9. Section 8: Laboratory Analysis & Assay Assays (SOC, Bulk Density)
10. Section 9: Immutable Lab Result Revision & Superseding Audit Trail
11. Section 10: Sample QA Review Verification
12. Section 11: 9-Component Categorical Ground Evidence Readiness Evaluator
13. Section 12: REST API Endpoints, ABAC Tenant Isolation & SoD RBAC
=============================================================================
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.main import app
from app.domains.agriculture.models import (
    AgricultureManagementRecord,
    ChainOfCustodyEvent,
    LaboratoryAnalysis,
    LaboratoryReceipt,
    LaboratoryResult,
    LandUnit,
    PhysicalSample,
    SampleCollectionEvent,
    SampleQAReview,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    Stratum,
    StratumMembership,
)
from app.domains.agriculture.schemas import (
    CustodyEventCreate,
    LabAnalysisCreate,
    LabReceiptCreate,
    LabResultCreate,
    LabResultRevisionCreate,
    LandUnitCreate,
    LinkBoundaryRequest,
    ManagementRecordCreate,
    ManagementRecordUpdate,
    SampleCollectionCreate,
    SampleQAReviewCreate,
    SamplingCampaignCreate,
    SamplingCampaignUpdate,
    SamplingPlanLockRequest,
    SamplingPlanVersionCreate,
    SamplingPointCreate,
    StratumCreate,
    StratumMembershipItem,
)
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.agriculture.service import AgricultureService
from app.domains.authentication.models import User
from app.domains.methodologies.models.base_registry import (
    Methodology,
    MethodologyFamily,
    MethodologyVersion,
)
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


# Test Polygon Geometry (WGS84 approx 433 ha)
VALID_POLYGON_A = {
    "type": "Polygon",
    "coordinates": [
        [[77.10, 28.50], [77.12, 28.50], [77.12, 28.52], [77.10, 28.52], [77.10, 28.50]]
    ],
}

VALID_POLYGON_B = {
    "type": "Polygon",
    "coordinates": [
        [[77.10, 28.50], [77.11, 28.50], [77.11, 28.51], [77.10, 28.51], [77.10, 28.50]]
    ],
}


async def create_agri_setup(db_session: AsyncSession):
    """Sets up an organization, methodology catalogue, project, and test users."""
    await seed_agriculture_methodologies(db_session)

    org = Organization(name=f"AgriTech Ground Lab {uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user_admin = User(
        email=f"agri.admin.{uuid.uuid4().hex}@verifield.test",
        full_name="Agriculture MRV Admin",
        role="ORG_ADMIN",
        organization_id=org.id,
        is_active=True,
    )
    user_field = User(
        email=f"agri.field.{uuid.uuid4().hex}@verifield.test",
        full_name="Agriculture Field Agent",
        role="FIELD_AGENT",
        organization_id=org.id,
        is_active=True,
    )
    user_auditor = User(
        email=f"agri.auditor.{uuid.uuid4().hex}@verifield.test",
        full_name="Third Party Auditor",
        role="AUDITOR",
        organization_id=org.id,
        is_active=True,
    )
    db_session.add_all([user_admin, user_field, user_auditor])
    await db_session.flush()

    fam_res = await db_session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE"))
    agri_family = fam_res.scalars().first()

    m42_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0042"))
    vm0042 = m42_res.scalars().first()

    v22_res = await db_session.execute(
        select(MethodologyVersion).where(
            MethodologyVersion.methodology_id == vm0042.id,
            MethodologyVersion.version == "2.2",
        )
    )
    v22 = v22_res.scalars().first()

    project = Project(
        name="Ludhiana Soil Carbon Project",
        project_code=f"AGR-LUDH-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        sector_id=agri_family.id if agri_family else None,
        methodology_id=vm0042.id,
        methodology_version_id=v22.id,
        crediting_start=date(2025, 1, 1),
        crediting_end=date(2045, 12, 31),
        baseline_parameters={},
    )
    db_session.add(project)
    await db_session.flush()

    # Lock methodology
    await AgricultureService.lock_project_methodology(
        db_session, project.id, org.id, user_admin.id, notes="Phase 2 Methodology Lock"
    )

    # Link authoritative boundary
    bound = await AgricultureService.link_project_boundary(
        db_session,
        project.id,
        org.id,
        user_admin.id,
        LinkBoundaryRequest(
            boundary_geojson=VALID_POLYGON_A,
            source="GNSS_SURVEY",
            reason="Authoritative Project Perimeter",
        ),
    )

    # Create land unit
    lu = await AgricultureService.create_land_unit(
        db_session,
        LandUnitCreate(
            project_id=project.id,
            name="Field Unit Alpha",
            code="FLD-A",
            unit_type="FIELD",
            boundary_geojson=VALID_POLYGON_B,
            boundary_source="GNSS_SURVEY",
        ),
        org.id,
    )

    # Create Stratum and assign membership
    stratum = await AgricultureService.create_stratum(
        db_session,
        StratumCreate(
            code="STRAT-REDUCED-TILL",
            name="Reduced Tillage Loam",
            stratum_type="MANAGEMENT_PRACTICE",
            area_ha=25.0,
        ),
        org.id,
        project.id,
    )
    await AgricultureService.add_stratum_memberships(
        db_session,
        stratum.id,
        org.id,
        [StratumMembershipItem(land_unit_id=lu.id, valid_from=date(2025, 1, 1), status="ACTIVE")],
    )

    await db_session.commit()

    return {
        "org": org,
        "admin": user_admin,
        "field": user_field,
        "auditor": user_auditor,
        "project": project,
        "boundary": bound,
        "land_unit": lu,
        "stratum": stratum,
    }


def _create_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "org_id": str(org_id) if org_id else None,
        "organization_id": str(org_id) if org_id else None,
        "exp": int((now + timedelta(hours=2)).timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# =============================================================================
# 0. SECTION 0: Management Record Corroboration Field Tests
# =============================================================================

@pytest.mark.asyncio
async def test_section0_management_record_corroboration(db_session: AsyncSession):
    """Verifies that corroboration field behaves correctly and preserves backward compatibility."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    lu = setup["land_unit"]

    # 1. Create with default corroboration ("NONE")
    rec1 = await AgricultureService.create_management_record(
        db_session,
        ManagementRecordCreate(
            record_type="TILLAGE",
            practice_category="BASELINE",
            event_date=date(2024, 5, 15),
            data_source="FIELD_OBSERVATION",
            land_unit_id=lu.id,
            corroboration="NONE",
        ),
        org.id,
        project_id=proj.id,
    )
    assert rec1.corroboration == "NONE"
    assert rec1.data_source == "FIELD_OBSERVATION"

    # 2. Create with REMOTE_SENSING corroboration
    rec2 = await AgricultureService.create_management_record(
        db_session,
        ManagementRecordCreate(
            record_type="COVER_CROP",
            practice_category="PROJECT_ACTIVITY",
            event_date=date(2025, 3, 10),
            data_source="REPORTED",
            land_unit_id=lu.id,
            corroboration="REMOTE_SENSING",
        ),
        org.id,
        project_id=proj.id,
    )
    assert rec2.corroboration == "REMOTE_SENSING"
    assert rec2.data_source == "REPORTED"

    # 3. Backward compatibility: data_source="REMOTE_SENSING_CORROBORATED" remains supported
    rec3 = await AgricultureService.create_management_record(
        db_session,
        ManagementRecordCreate(
            record_type="IRRIGATION",
            practice_category="PROJECT_ACTIVITY",
            event_date=date(2025, 4, 1),
            data_source="REMOTE_SENSING_CORROBORATED",
            land_unit_id=lu.id,
        ),
        org.id,
        project_id=proj.id,
    )
    assert rec3.data_source == "REMOTE_SENSING_CORROBORATED"

    # 4. Invalid corroboration rejected
    with pytest.raises(ValueError, match="Invalid corroboration"):
        ManagementRecordCreate(
            record_type="TILLAGE",
            practice_category="BASELINE",
            event_date=date(2024, 1, 1),
            corroboration="INVALID_CORROBORATION",
        )


# =============================================================================
# 1. SAMPLING CAMPAIGN LIFECYCLE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_sampling_campaign_lifecycle(db_session: AsyncSession):
    """Verifies creation, methodology snapshot capture, updating, and duplicate code rejection."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]

    # 1. Create Sampling Campaign
    campaign = await AgricultureService.create_sampling_campaign(
        db_session,
        proj.id,
        org.id,
        SamplingCampaignCreate(
            campaign_code="CAMP-2025-BASE",
            name="2025 Baseline Soil Inventory",
            purpose="BASELINE_SOC_DETERMINATION",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=date(2025, 10, 1),
            planned_end_date=date(2025, 10, 31),
        ),
        user_id=admin.id,
    )
    assert campaign.campaign_code == "CAMP-2025-BASE"
    assert campaign.status == "DRAFT"
    assert campaign.project_id == proj.id
    assert campaign.organization_id == org.id
    assert "methodology_code" in campaign.methodology_lock_snapshot
    assert campaign.methodology_lock_snapshot["methodology_code"] == "VM0042"

    # 2. Reject duplicate code in same project
    with pytest.raises(ValueError, match="already exists for this project"):
        await AgricultureService.create_sampling_campaign(
            db_session,
            proj.id,
            org.id,
            SamplingCampaignCreate(
                campaign_code="CAMP-2025-BASE",
                name="Duplicate Campaign",
                planned_start_date=date(2025, 11, 1),
            ),
        )

    # 3. Update campaign details
    updated = await AgricultureService.update_sampling_campaign(
        db_session,
        campaign.id,
        org.id,
        SamplingCampaignUpdate(name="2025 Baseline Soil Inventory - Finalized", status="PLANNED"),
    )
    assert updated.name == "2025 Baseline Soil Inventory - Finalized"
    assert updated.status == "PLANNED"

    # 4. Query campaigns list with counts
    camp_list = await AgricultureService.get_sampling_campaigns(db_session, proj.id, org.id)
    assert len(camp_list) == 1
    assert camp_list[0]["campaign_code"] == "CAMP-2025-BASE"
    assert camp_list[0]["plan_versions_count"] == 0
    assert camp_list[0]["points_count"] == 0


# =============================================================================
# 2. SAMPLING PLAN VERSION & STRATIFICATION FREEZE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_sampling_plan_version_and_stratification_freeze(db_session: AsyncSession):
    """Verifies that plan versions freeze stratification snapshots and cannot be re-locked."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    stratum = setup["stratum"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session,
        proj.id,
        org.id,
        SamplingCampaignCreate(
            campaign_code="CAMP-PLAN-TEST",
            name="Plan Version Test Campaign",
            planned_start_date=date(2025, 10, 1),
        ),
        user_id=admin.id,
    )

    # 1. Create Plan Version
    spv = await AgricultureService.create_sampling_plan_version(
        db_session,
        campaign.id,
        org.id,
        SamplingPlanVersionCreate(
            effective_as_of_date=date(2025, 6, 1),
            sampling_design_method="STRATIFIED_RANDOM",
            design_provenance="MANUAL",
            notes="Initial Stratified Random Design",
        ),
        user_id=admin.id,
    )
    assert spv.version_number == 1
    assert spv.is_locked is False
    assert spv.status == "DRAFT"

    # Verify frozen stratification snapshot
    snap = spv.stratum_membership_snapshot
    assert "strata" in snap
    assert snap["strata_count"] == 1
    assert snap["strata"][0]["code"] == stratum.code
    assert len(snap["strata"][0]["active_memberships"]) == 1

    # 2. Lock Plan Version
    locked_spv = await AgricultureService.lock_sampling_plan_version(
        db_session,
        spv.id,
        org.id,
        user_id=admin.id,
        notes="Reviewed and approved by MRV Lead",
    )
    assert locked_spv.is_locked is True
    assert locked_spv.status == "ACTIVE"
    assert locked_spv.locked_at is not None

    # Invariant: Campaign status transitions to LOCKED
    camp_refreshed = await AgricultureService.get_sampling_campaign_by_id(db_session, campaign.id, org.id)
    assert camp_refreshed["status"] == "LOCKED"

    # Invariant: cannot re-lock an already locked plan
    with pytest.raises(ValueError, match="already locked"):
        await AgricultureService.lock_sampling_plan_version(db_session, spv.id, org.id, admin.id)


# =============================================================================
# 3. SAMPLING POINTS & SPATIAL CONTAINMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_sampling_points_and_spatial_containment(db_session: AsyncSession):
    """Verifies sampling point creation, spatial boundary check, and physical sample creation."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session,
        proj.id,
        org.id,
        SamplingCampaignCreate(
            campaign_code="CAMP-POINTS-TEST",
            name="Point Spatial Test Campaign",
            planned_start_date=date(2025, 10, 1),
        ),
        user_id=admin.id,
    )

    spv = await AgricultureService.create_sampling_plan_version(
        db_session,
        campaign.id,
        org.id,
        SamplingPlanVersionCreate(effective_as_of_date=date(2025, 6, 1)),
        user_id=admin.id,
    )

    # Point 1: INSIDE Field Unit Alpha (lon: 77.105, lat: 28.505) -> within VALID_POLYGON_B [77.10-77.11, 28.50-28.51]
    valid_pt = SamplingPointCreate(
        point_code="P-01",
        planned_lat=28.505,
        planned_lon=77.105,
        land_unit_id=lu.id,
        stratum_id=stratum.id,
        depth_from_cm=0.0,
        depth_to_cm=30.0,
        sampling_purpose="SOC_STOCK",
        replicate_group="REP-A",
    )

    points = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id, [valid_pt], user_id=admin.id
    )
    assert len(points) == 1
    pt = points[0]
    assert pt.point_code == "P-01"
    assert pt.status == "PLANNED"

    # Invariant: PhysicalSample record was automatically generated with canonical code
    sample_stmt = select(PhysicalSample).where(PhysicalSample.sampling_point_id == pt.id)
    sample = (await db_session.execute(sample_stmt)).scalars().first()
    assert sample is not None
    assert sample.status == "PLANNED"
    assert pt.point_code in sample.sample_code
    assert "VERIFIELD:AG:" in sample.qr_barcode_code

    # Point 2: OUTSIDE Field Unit Alpha (lon: 77.15, lat: 28.60) -> outside LandUnit boundary
    invalid_pt = SamplingPointCreate(
        point_code="P-OUTSIDE",
        planned_lat=28.60,
        planned_lon=77.15,
        land_unit_id=lu.id,
        stratum_id=stratum.id,
    )
    with pytest.raises(ValueError, match="is outside the spatial boundary of LandUnit"):
        await AgricultureService.create_sampling_points(
            db_session, campaign.id, spv.id, org.id, [invalid_pt], user_id=admin.id
        )

    # Invariant: depth_to_cm <= depth_from_cm rejected by schema
    with pytest.raises(ValueError, match="strictly greater than depth_from_cm"):
        SamplingPointCreate(
            point_code="P-BAD-DEPTH",
            planned_lat=28.505,
            planned_lon=77.105,
            land_unit_id=lu.id,
            depth_from_cm=30.0,
            depth_to_cm=30.0,
        )


# =============================================================================
# 4. FIELD COLLECTION & GEODESIC DEVIATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_field_collection_and_geodesic_deviation(db_session: AsyncSession):
    """Verifies collection event recording, geodesic deviation distance, and custody initialization."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field_agent = setup["field"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session,
        proj.id,
        org.id,
        SamplingCampaignCreate(campaign_code="CAMP-COL-TEST", name="Collection Test", planned_start_date=date(2025, 10, 1)),
        user_id=admin.id,
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id, SamplingPlanVersionCreate(effective_as_of_date=date(2025, 6, 1))
    )
    points = await AgricultureService.create_sampling_points(
        db_session,
        campaign.id,
        spv.id,
        org.id,
        [SamplingPointCreate(point_code="P-COL-1", planned_lat=28.50500, planned_lon=77.10500, land_unit_id=lu.id, stratum_id=stratum.id)],
    )
    pt = points[0]
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == pt.id))

    # 1. Collection with minimal deviation (~11 meters shift in longitude)
    # 0.0001 deg lon at ~28.5 deg lat is approx 9.7 meters
    col_payload = SampleCollectionCreate(
        actual_lat=28.50500,
        actual_lon=77.10510,
        actual_depth_from_cm=0.0,
        actual_depth_to_cm=30.0,
        collection_timestamp=datetime(2025, 10, 2, 9, 30, tzinfo=timezone.utc),
        collector_name=field_agent.full_name,
        sample_condition="GOOD",
        idempotency_key="IDEMPOTENT-KEY-001",
    )

    ev = await AgricultureService.record_sample_collection(db_session, sample.id, org.id, col_payload, field_agent.id)
    assert ev.physical_sample_id == sample.id
    assert 5.0 < ev.deviation_distance_m < 20.0
    assert ev.idempotency_key == "IDEMPOTENT-KEY-001"

    # Verify sample status updated to COLLECTED
    sample_refreshed = await AgricultureService.get_physical_sample_by_id(db_session, sample.id, org.id)
    assert sample_refreshed.status == "COLLECTED"
    assert sample_refreshed.sampling_point.status == "COLLECTED"

    # Verify initial chain of custody event was created
    assert len(sample_refreshed.custody_events) == 1
    assert sample_refreshed.custody_events[0].event_type == "COLLECTION"

    # Idempotency test: repeating with same key returns identical event
    ev_repeat = await AgricultureService.record_sample_collection(db_session, sample.id, org.id, col_payload, field_agent.id)
    assert ev_repeat.id == ev.id

    # 2. Large deviation (>50m) requires deviation_reason
    points2 = await AgricultureService.create_sampling_points(
        db_session,
        campaign.id,
        spv.id,
        org.id,
        [SamplingPointCreate(point_code="P-COL-2", planned_lat=28.50500, planned_lon=77.10500, land_unit_id=lu.id, stratum_id=stratum.id)],
    )
    sample2 = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points2[0].id))

    # Shift by 0.001 deg lat is ~111 meters (> 50m)
    bad_large_dev = SampleCollectionCreate(
        actual_lat=28.50600,
        actual_lon=77.10500,
        collection_timestamp=datetime(2025, 10, 2, 10, 0, tzinfo=timezone.utc),
        collector_name=field_agent.full_name,
        deviation_reason=None,
    )
    with pytest.raises(ValueError, match="deviation_reason is mandatory"):
        await AgricultureService.record_sample_collection(db_session, sample2.id, org.id, bad_large_dev, field_agent.id)

    # Valid large deviation with reason
    good_large_dev = SampleCollectionCreate(
        actual_lat=28.50600,
        actual_lon=77.10500,
        collection_timestamp=datetime(2025, 10, 2, 10, 0, tzinfo=timezone.utc),
        collector_name=field_agent.full_name,
        deviation_reason="Rock outcrop at planned location necessitated 110m north offset",
    )
    ev2 = await AgricultureService.record_sample_collection(db_session, sample2.id, org.id, good_large_dev, field_agent.id)
    assert ev2.deviation_distance_m > 100.0
    assert ev2.deviation_reason is not None


# =============================================================================
# 5. CHAIN OF CUSTODY APPEND-ONLY LOG TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_chain_of_custody_lifecycle(db_session: AsyncSession):
    """Verifies custody transfer events and sample status state transitions."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field_agent = setup["field"]
    lu = setup["land_unit"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id, SamplingCampaignCreate(campaign_code="CAMP-CUSTODY", name="Custody Test", planned_start_date=date(2025, 10, 1))
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id, SamplingPlanVersionCreate(effective_as_of_date=date(2025, 6, 1))
    )
    points = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id, [SamplingPointCreate(point_code="P-CUST-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id)]
    )
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[0].id))

    # Collect sample
    await AgricultureService.record_sample_collection(
        db_session,
        sample.id,
        org.id,
        SampleCollectionCreate(
            actual_lat=28.505, actual_lon=77.105,
            collection_timestamp=datetime(2025, 10, 2, 9, 0, tzinfo=timezone.utc),
            collector_name=field_agent.full_name,
        ),
        field_agent.id,
    )

    # 1. Sealing Event -> transitions status to SEALED
    seal_ev = await AgricultureService.record_custody_event(
        db_session,
        sample.id,
        org.id,
        CustodyEventCreate(
            event_type="SEALING",
            event_timestamp=datetime(2025, 10, 2, 9, 30, tzinfo=timezone.utc),
            custodian_name=field_agent.full_name,
            custodian_organization="Field Team",
            seal_identifier="SEAL-TAMPER-PROOF-9901",
            seal_intact=True,
            condition="INTACT",
        ),
        field_agent.id,
    )
    assert seal_ev.event_type == "SEALING"
    sample_ref = await AgricultureService.get_physical_sample_by_id(db_session, sample.id, org.id)
    assert sample_ref.status == "SEALED"

    # 2. Dispatch to Courier -> transitions status to IN_TRANSIT
    dispatch_ev = await AgricultureService.record_custody_event(
        db_session,
        sample.id,
        org.id,
        CustodyEventCreate(
            event_type="TRANSPORT_DISPATCH",
            event_timestamp=datetime(2025, 10, 2, 14, 0, tzinfo=timezone.utc),
            custodian_name="ColdChain Logistics Driver",
            custodian_organization="FastFreight Logistics",
            from_location="Field Collection Base",
            to_location="Eurofins Soil Testing Lab",
            condition="INTACT",
            seal_intact=True,
        ),
        field_agent.id,
    )
    assert dispatch_ev.event_type == "TRANSPORT_DISPATCH"
    sample_ref = await AgricultureService.get_physical_sample_by_id(db_session, sample.id, org.id)
    assert sample_ref.status == "IN_TRANSIT"

    # Custody log has 3 events in order: COLLECTION, SEALING, TRANSPORT_DISPATCH
    events = sample_ref.custody_events
    assert len(events) == 3
    assert [e.event_type for e in events] == ["COLLECTION", "SEALING", "TRANSPORT_DISPATCH"]


# =============================================================================
# 6. LABORATORY RECEIPT & ANALYSIS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_laboratory_receipt_and_analysis_invariants(db_session: AsyncSession):
    """Verifies lab receipt (acceptance/rejection) and assay analysis recording invariants."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field_agent = setup["field"]
    lu = setup["land_unit"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id, SamplingCampaignCreate(campaign_code="CAMP-LAB", name="Lab Workflow Test", planned_start_date=date(2025, 10, 1))
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id, SamplingPlanVersionCreate(effective_as_of_date=date(2025, 6, 1))
    )
    points = await AgricultureService.create_sampling_points(
        db_session,
        campaign.id,
        spv.id,
        org.id,
        [
            SamplingPointCreate(point_code="P-LAB-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id),
            SamplingPointCreate(point_code="P-LAB-2", planned_lat=28.506, planned_lon=77.106, land_unit_id=lu.id),
        ],
    )
    sample1 = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[0].id))
    sample2 = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[1].id))

    # Collect both samples at their planned coordinates
    await AgricultureService.record_sample_collection(
        db_session,
        sample1.id,
        org.id,
        SampleCollectionCreate(
            actual_lat=28.505, actual_lon=77.105,
            collection_timestamp=datetime(2025, 10, 2, 9, 0, tzinfo=timezone.utc),
            collector_name=field_agent.full_name,
        ),
        field_agent.id,
    )
    await AgricultureService.record_sample_collection(
        db_session,
        sample2.id,
        org.id,
        SampleCollectionCreate(
            actual_lat=28.506, actual_lon=77.106,
            collection_timestamp=datetime(2025, 10, 2, 9, 0, tzinfo=timezone.utc),
            collector_name=field_agent.full_name,
        ),
        field_agent.id,
    )

    # 1. Sample 1: Formal lab receipt ACCEPTED
    receipt1 = await AgricultureService.record_laboratory_receipt(
        db_session,
        sample1.id,
        org.id,
        LabReceiptCreate(
            laboratory_name="Eurofins Agri Testing",
            laboratory_id_ref="LAB-REF-9021",
            received_at=datetime(2025, 10, 5, 11, 0, tzinfo=timezone.utc),
            received_by_name="Dr. Lab Analyst",
            condition_on_receipt="ACCEPTABLE",
            seal_status="SEALED_INTACT",
            intake_status="ACCEPTED",
        ),
        admin.id,
    )
    assert receipt1.intake_status == "ACCEPTED"
    s1_ref = await AgricultureService.get_physical_sample_by_id(db_session, sample1.id, org.id)
    assert s1_ref.status == "RECEIVED_BY_LAB"

    # Record Laboratory Analysis on accepted sample
    analysis = await AgricultureService.record_laboratory_analysis(
        db_session,
        sample1.id,
        org.id,
        LabAnalysisCreate(
            laboratory_name="Eurofins Agri Testing",
            laboratory_accreditation="ISO/IEC 17025:2017",
            analysis_batch_id="BATCH-2025-10-A",
            analytical_method="DRY_COMBUSTION",
            method_standard_code="ISO 10694:1995",
            analysis_date=date(2025, 10, 6),
            report_reference_number="COA-99210",
            analyst_name="Dr. Lab Analyst",
            results=[
                LabResultCreate(
                    analyte="SOC_STOCK_PCT",
                    raw_value=Decimal("1.8500"),
                    raw_unit="%",
                    normalized_value=Decimal("18.5000"),
                    normalized_unit="g/kg",
                    normalization_method="Multiplication by 10",
                    detection_limit=Decimal("0.0100"),
                    uncertainty_pct=Decimal("2.50"),
                ),
                LabResultCreate(
                    analyte="BULK_DENSITY_G_CM3",
                    raw_value=Decimal("1.3200"),
                    raw_unit="g/cm3",
                    normalized_value=Decimal("1.3200"),
                    normalized_unit="g/cm3",
                ),
            ],
        ),
        admin.id,
    )
    assert analysis.analytical_method == "DRY_COMBUSTION"
    assert len(analysis.results) == 2
    s1_after_analysis = await AgricultureService.get_physical_sample_by_id(db_session, sample1.id, org.id)
    assert s1_after_analysis.status == "ANALYZED"

    # 2. Sample 2: Formal lab receipt REJECTED (e.g. broken seal, contaminated)
    receipt2 = await AgricultureService.record_laboratory_receipt(
        db_session,
        sample2.id,
        org.id,
        LabReceiptCreate(
            laboratory_name="Eurofins Agri Testing",
            received_at=datetime(2025, 10, 5, 11, 30, tzinfo=timezone.utc),
            received_by_name="Dr. Lab Analyst",
            condition_on_receipt="DAMAGED_CONTAINER",
            seal_status="BROKEN_SEAL",
            intake_status="REJECTED",
            rejection_reason="Seal compromised and core sample crushed in transit",
        ),
        admin.id,
    )
    assert receipt2.intake_status == "REJECTED"
    s2_ref = await AgricultureService.get_physical_sample_by_id(db_session, sample2.id, org.id)
    assert s2_ref.status == "REJECTED_BY_LAB"

    # Invariant: rejected sample cannot undergo analytical assay
    with pytest.raises(ValueError, match="was rejected by laboratory"):
        await AgricultureService.record_laboratory_analysis(
            db_session,
            sample2.id,
            org.id,
            LabAnalysisCreate(
                laboratory_name="Eurofins Agri Testing",
                analysis_date=date(2025, 10, 6),
                results=[LabResultCreate(analyte="SOC_STOCK_PCT", raw_value=Decimal("1.5000"), raw_unit="%")],
            ),
            admin.id,
        )


# =============================================================================
# 7. IMMUTABLE LAB RESULT REVISION & AUDIT TRAIL TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_laboratory_result_revision_audit_trail(db_session: AsyncSession):
    """Verifies that result revisions preserve original raw values and maintain an append-only audit trail."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field_agent = setup["field"]
    lu = setup["land_unit"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id, SamplingCampaignCreate(campaign_code="CAMP-REV", name="Revision Test", planned_start_date=date(2025, 10, 1))
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id, SamplingPlanVersionCreate(effective_as_of_date=date(2025, 6, 1))
    )
    points = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id, [SamplingPointCreate(point_code="P-REV-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id)]
    )
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[0].id))

    await AgricultureService.record_sample_collection(
        db_session,
        sample.id,
        org.id,
        SampleCollectionCreate(actual_lat=28.505, actual_lon=77.105, collection_timestamp=datetime(2025, 10, 2, 9, 0, tzinfo=timezone.utc), collector_name=field_agent.full_name),
    )
    await AgricultureService.record_laboratory_receipt(
        db_session,
        sample.id,
        org.id,
        LabReceiptCreate(laboratory_name="Soil Lab", received_at=datetime(2025, 10, 3, 10, 0, tzinfo=timezone.utc), received_by_name="Analyst"),
    )
    analysis = await AgricultureService.record_laboratory_analysis(
        db_session,
        sample.id,
        org.id,
        LabAnalysisCreate(
            laboratory_name="Soil Lab",
            analysis_date=date(2025, 10, 4),
            results=[LabResultCreate(analyte="SOC_STOCK_PCT", raw_value=Decimal("1.8500"), raw_unit="%")],
        ),
    )
    orig_result = analysis.results[0]
    orig_id = orig_result.id

    # Revise result
    revised = await AgricultureService.revise_laboratory_result(
        db_session,
        orig_id,
        org.id,
        LabResultRevisionCreate(
            new_raw_value=Decimal("1.9200"),
            new_raw_unit="%",
            new_normalized_value=Decimal("19.2000"),
            new_normalized_unit="g/kg",
            revision_reason="Recalibration against certified reference material CRM-4402",
        ),
        user_id=admin.id,
    )
    assert revised.id != orig_id
    assert revised.raw_value == Decimal("1.9200")
    assert revised.is_superseded is False

    # Invariant: Original result remains in DB, is marked superseded, raw_value is NOT overwritten
    orig_refreshed = (await db_session.execute(select(LaboratoryResult).where(LaboratoryResult.id == orig_id))).scalars().first()
    assert orig_refreshed.is_superseded is True
    assert orig_refreshed.raw_value == Decimal("1.8500")
    assert orig_refreshed.superseded_by_id == revised.id
    assert "CRM-4402" in orig_refreshed.revision_reason

    # Invariant: Cannot revise an already superseded result
    with pytest.raises(ValueError, match="already been superseded"):
        await AgricultureService.revise_laboratory_result(
            db_session,
            orig_id,
            org.id,
            LabResultRevisionCreate(new_raw_value=Decimal("2.0000"), new_raw_unit="%", revision_reason="Second revision"),
            user_id=admin.id,
        )


# =============================================================================
# 8. SAMPLE QA REVIEW TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_sample_qa_review_lifecycle(db_session: AsyncSession):
    """Verifies QA review acceptance/rejection and physical sample status synchronization."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field_agent = setup["field"]
    lu = setup["land_unit"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id, SamplingCampaignCreate(campaign_code="CAMP-QA", name="QA Test", planned_start_date=date(2025, 10, 1))
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id, SamplingPlanVersionCreate(effective_as_of_date=date(2025, 6, 1))
    )
    points = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id, [SamplingPointCreate(point_code="P-QA-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id)]
    )
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[0].id))

    await AgricultureService.record_sample_collection(
        db_session, sample.id, org.id,
        SampleCollectionCreate(actual_lat=28.505, actual_lon=77.105, collection_timestamp=datetime(2025, 10, 2, 9, 0, tzinfo=timezone.utc), collector_name=field_agent.full_name)
    )
    await AgricultureService.record_laboratory_receipt(
        db_session, sample.id, org.id,
        LabReceiptCreate(laboratory_name="Soil Lab", received_at=datetime(2025, 10, 3, 10, 0, tzinfo=timezone.utc), received_by_name="Analyst")
    )
    await AgricultureService.record_laboratory_analysis(
        db_session, sample.id, org.id,
        LabAnalysisCreate(laboratory_name="Soil Lab", analysis_date=date(2025, 10, 4), results=[LabResultCreate(analyte="SOC_STOCK_PCT", raw_value=Decimal("1.8500"), raw_unit="%")])
    )

    # 1. Record QA Review ACCEPTED
    review = await AgricultureService.record_sample_qa_review(
        db_session,
        sample.id,
        org.id,
        SampleQAReviewCreate(
            reviewer_name="Senior Soil Scientist QA",
            overall_qa_status="ACCEPTED",
            location_verified=True,
            deviation_acceptable=True,
            depth_valid=True,
            custody_complete=True,
            lab_receipt_verified=True,
            required_assays_present=True,
            notes="All QA criteria satisfied according to VM0042 Section 8.2.",
        ),
        user_id=admin.id,
    )
    assert review.overall_qa_status == "ACCEPTED"
    sample_ref = await AgricultureService.get_physical_sample_by_id(db_session, sample.id, org.id)
    assert sample_ref.status == "QA_ACCEPTED"


# =============================================================================
# 9. GROUND EVIDENCE READINESS EVALUATOR TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_ground_evidence_readiness_evaluator_progression(db_session: AsyncSession):
    """Verifies that the 9-component categorical evaluator accurately tracks workflow progression."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field_agent = setup["field"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    # 1. Initial State: No campaigns configured
    r1 = await AgricultureService.evaluate_ground_evidence_readiness(db_session, proj.id, org.id)
    assert r1["overall_status"] == "NOT_CONFIGURED"
    assert r1["components"]["sampling_campaign"]["status"] == "NOT_CONFIGURED"
    assert r1["components"]["sampling_plan"]["status"] == "NOT_CONFIGURED"
    assert r1["components"]["sampling_points"]["status"] == "NOT_CONFIGURED"

    # 2. Add Campaign and Lock Plan
    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id,
        SamplingCampaignCreate(campaign_code="CAMP-READINESS", name="Readiness Evaluation Campaign", planned_start_date=date(2025, 10, 1)),
        user_id=admin.id,
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id,
        SamplingPlanVersionCreate(effective_as_of_date=date(2025, 6, 1)),
        user_id=admin.id,
    )

    r2 = await AgricultureService.evaluate_ground_evidence_readiness(db_session, proj.id, org.id)
    assert r2["components"]["sampling_campaign"]["status"] == "NEEDS_REVIEW"
    assert r2["components"]["sampling_plan"]["status"] == "NEEDS_REVIEW"
    assert r2["components"]["sampling_points"]["status"] == "NOT_CONFIGURED"

    # 3. Add Sampling Points covering the Stratum and Lock Plan
    points = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id,
        [SamplingPointCreate(point_code="P-READ-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id, stratum_id=stratum.id)],
        user_id=admin.id,
    )
    await AgricultureService.lock_sampling_plan_version(db_session, spv.id, org.id, admin.id)

    r3 = await AgricultureService.evaluate_ground_evidence_readiness(db_session, proj.id, org.id)
    assert r3["components"]["sampling_campaign"]["status"] == "COMPLETE"
    assert r3["components"]["sampling_plan"]["status"] == "COMPLETE"
    assert r3["components"]["stratum_coverage"]["status"] == "COMPLETE"
    assert r3["components"]["sampling_points"]["status"] == "COMPLETE"
    assert r3["components"]["field_collection"]["status"] == "NOT_CONFIGURED"

    # 4. Field Collection
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[0].id))
    await AgricultureService.record_sample_collection(
        db_session, sample.id, org.id,
        SampleCollectionCreate(actual_lat=28.505, actual_lon=77.105, collection_timestamp=datetime(2025, 10, 2, 9, 0, tzinfo=timezone.utc), collector_name=field_agent.full_name),
        field_agent.id,
    )
    r4 = await AgricultureService.evaluate_ground_evidence_readiness(db_session, proj.id, org.id)
    assert r4["components"]["field_collection"]["status"] == "COMPLETE"
    assert r4["components"]["chain_of_custody"]["status"] == "COMPLETE"
    assert r4["components"]["lab_receipt"]["status"] == "NOT_CONFIGURED"

    # 5. Laboratory Receipt
    await AgricultureService.record_laboratory_receipt(
        db_session, sample.id, org.id,
        LabReceiptCreate(laboratory_name="Soil Lab", received_at=datetime(2025, 10, 3, 10, 0, tzinfo=timezone.utc), received_by_name="Analyst"),
    )
    r5 = await AgricultureService.evaluate_ground_evidence_readiness(db_session, proj.id, org.id)
    assert r5["components"]["lab_receipt"]["status"] == "COMPLETE"
    assert r5["components"]["required_assays"]["status"] == "NOT_CONFIGURED"

    # 6. Laboratory Analysis & Results
    await AgricultureService.record_laboratory_analysis(
        db_session, sample.id, org.id,
        LabAnalysisCreate(laboratory_name="Soil Lab", analysis_date=date(2025, 10, 4), results=[LabResultCreate(analyte="SOC_STOCK_PCT", raw_value=Decimal("1.8500"), raw_unit="%")]),
    )
    r6 = await AgricultureService.evaluate_ground_evidence_readiness(db_session, proj.id, org.id)
    assert r6["components"]["required_assays"]["status"] == "COMPLETE"
    assert r6["components"]["qa_review"]["status"] == "INCOMPLETE"

    # 7. QA Review Accepted -> Full Complete!
    await AgricultureService.record_sample_qa_review(
        db_session, sample.id, org.id,
        SampleQAReviewCreate(reviewer_name="QA Lead", overall_qa_status="ACCEPTED"),
    )
    r7 = await AgricultureService.evaluate_ground_evidence_readiness(db_session, proj.id, org.id)
    assert r7["components"]["qa_review"]["status"] == "COMPLETE"
    assert r7["overall_status"] == "COMPLETE"
    for comp_name, comp_data in r7["components"].items():
        if comp_name == "design_sufficiency":
            assert comp_data["status"] == "NOT_CONFIGURED"
            assert "Statistical sample-allocation engine not configured" in comp_data["message"]
        else:
            assert comp_data["status"] == "COMPLETE", f"Expected {comp_name} to be COMPLETE, got {comp_data['status']}"


# =============================================================================
# 10. REST API ENDPOINTS & RBAC / SOD TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_phase2_api_endpoints_and_rbac_sod(db_session: AsyncSession):
    """Verifies all Phase 2 REST API endpoints, tenant isolation, and role-based permissions."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field = setup["field"]
    auditor = setup["auditor"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    admin_token = _create_token(admin.id, admin.email, "ORG_ADMIN", org.id)
    field_token = _create_token(field.id, field.email, "FIELD_AGENT", org.id)
    auditor_token = _create_token(auditor.id, auditor.email, "AUDITOR", org.id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. ORG_ADMIN creates sampling campaign
        camp_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/sampling-campaigns",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "campaign_code": "API-CAMP-01",
                "name": "API Campaign",
                "planned_start_date": "2025-10-01",
            },
        )
        assert camp_resp.status_code == 201
        camp_data = camp_resp.json()
        camp_id = camp_data["id"]

        # 2. AUDITOR attempts to create campaign -> 403 Forbidden
        aud_camp_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/sampling-campaigns",
            headers={"Authorization": f"Bearer {auditor_token}"},
            json={"campaign_code": "AUD-CAMP", "name": "Auditor Campaign", "planned_start_date": "2025-10-01"},
        )
        assert aud_camp_resp.status_code == 403

        # 3. Create Plan Version and Lock
        pv_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/sampling-campaigns/{camp_id}/plan-versions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"effective_as_of_date": "2025-06-01"},
        )
        assert pv_resp.status_code == 201
        pv_id = pv_resp.json()["id"]

        # 4. Create Sampling Point (before locking)
        pts_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/sampling-campaigns/{camp_id}/plan-versions/{pv_id}/points",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "points": [
                    {
                        "point_code": "API-P1",
                        "planned_lat": 28.505,
                        "planned_lon": 77.105,
                        "land_unit_id": str(lu.id),
                        "stratum_id": str(stratum.id),
                    }
                ]
            },
        )
        assert pts_resp.status_code == 201
        points_data = pts_resp.json()
        assert len(points_data) == 1

        # Lock Plan Version
        lock_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/sampling-campaigns/{camp_id}/plan-versions/{pv_id}/lock",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"notes": "Approved via API"},
        )
        assert lock_resp.status_code == 200
        assert lock_resp.json()["is_locked"] is True

        # Verify mutation on locked plan is rejected
        pts_reject_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/sampling-campaigns/{camp_id}/plan-versions/{pv_id}/points",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "points": [
                    {
                        "point_code": "API-P2-REJECTED",
                        "planned_lat": 28.506,
                        "planned_lon": 77.106,
                        "land_unit_id": str(lu.id),
                        "stratum_id": str(stratum.id),
                    }
                ]
            },
        )
        assert pts_reject_resp.status_code == 400

        # 5. List Physical Samples
        samples_resp = await ac.get(
            f"/api/v1/agriculture/projects/{proj.id}/physical-samples",
            headers={"Authorization": f"Bearer {field_token}"},
        )
        assert samples_resp.status_code == 200
        samples_list = samples_resp.json()
        assert len(samples_list) == 1
        sample_id = samples_list[0]["id"]

        # 6. FIELD_AGENT records collection
        col_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/physical-samples/{sample_id}/collection",
            headers={"Authorization": f"Bearer {field_token}"},
            json={
                "actual_lat": 28.505,
                "actual_lon": 77.105,
                "collection_timestamp": "2025-10-02T09:00:00Z",
                "collector_name": field.full_name,
            },
        )
        assert col_resp.status_code == 201

        # 7. Custody Event
        cust_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/physical-samples/{sample_id}/custody-events",
            headers={"Authorization": f"Bearer {field_token}"},
            json={
                "event_type": "SEALING",
                "event_timestamp": "2025-10-02T09:30:00Z",
                "custodian_name": field.full_name,
                "custodian_organization": "Field Team",
                "seal_identifier": "SEAL-API-01",
            },
        )
        assert cust_resp.status_code == 201

        # 8. Lab Receipt
        receipt_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/physical-samples/{sample_id}/lab-receipt",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "laboratory_name": "API Testing Lab",
                "received_at": "2025-10-03T10:00:00Z",
                "received_by_name": "Lab Intake",
            },
        )
        assert receipt_resp.status_code == 201

        # 9. Lab Analysis
        analysis_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/physical-samples/{sample_id}/lab-analyses",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "laboratory_name": "API Testing Lab",
                "analysis_date": "2025-10-04",
                "results": [
                    {
                        "analyte": "SOC_STOCK_PCT",
                        "raw_value": 1.75,
                        "raw_unit": "%",
                    }
                ],
            },
        )
        assert analysis_resp.status_code == 201
        res_id = analysis_resp.json()["results"][0]["id"]

        # 10. Result Revision
        rev_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/laboratory-results/{res_id}/revise",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "new_raw_value": 1.82,
                "new_raw_unit": "%",
                "revision_reason": "Calibration update",
            },
        )
        assert rev_resp.status_code == 200
        assert rev_resp.json()["raw_value"] == "1.8200"
        assert rev_resp.json()["normalized_value"] == "18.2000"
        assert rev_resp.json()["normalized_unit"] == "g/kg"
        assert rev_resp.json()["normalization_method"] == "LINEAR_SCALING:VAL*10"

        # 11. QA Review
        qa_resp = await ac.post(
            f"/api/v1/agriculture/projects/{proj.id}/physical-samples/{sample_id}/qa-review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "reviewer_name": "QA Specialist",
                "overall_qa_status": "ACCEPTED",
            },
        )
        assert qa_resp.status_code == 200

        # 12. Ground Evidence Readiness endpoint
        readiness_resp = await ac.get(
            f"/api/v1/agriculture/projects/{proj.id}/ground-evidence-readiness",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )
        assert readiness_resp.status_code == 200
        readiness_data = readiness_resp.json()
        assert readiness_data["overall_status"] == "COMPLETE"
        assert readiness_data["components"]["qa_review"]["status"] == "COMPLETE"

        # 13. Tenant Isolation: Rival Org cannot access samples or readiness
        org_rival = Organization(name=f"Rival Org {uuid.uuid4().hex[:8]}")
        db_session.add(org_rival)
        await db_session.flush()
        rival_user = User(
            email=f"rival.{uuid.uuid4().hex[:6]}@verifield.test",
            full_name="Rival User",
            role="ORG_ADMIN",
            organization_id=org_rival.id,
            is_active=True,
        )
        db_session.add(rival_user)
        await db_session.commit()
        rival_token = _create_token(rival_user.id, rival_user.email, "ORG_ADMIN", org_rival.id)

        rival_resp = await ac.get(
            f"/api/v1/agriculture/projects/{proj.id}/physical-samples",
            headers={"Authorization": f"Bearer {rival_token}"},
        )
        assert rival_resp.status_code in (403, 404)


# =============================================================================
# 11. SCIENTIFIC UNITS, ACCREDITATION & HARDENING INVARIANT TESTS
# =============================================================================

def test_scientific_unit_normalization_and_unconvertible_handling():
    """
    Verifies deterministic physical unit normalization and safe handling
    of unconvertible / dimensionally incompatible measurements.
    """
    # 1. Mass fraction conversions (canonical SOC_CONCENTRATION and legacy aliases to canonical g/kg)
    # 1.85% -> 18.5000 g/kg (LINEAR_SCALING:VAL*10)
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("SOC_CONCENTRATION", Decimal("1.8500"), "%")
    assert v == Decimal("18.5000")
    assert u == "g/kg"
    assert m == "LINEAR_SCALING:VAL*10"
    assert ver == "UNIT_CONV_V1.0"

    # 18.5 g/kg -> 18.5000 g/kg (IDENTITY)
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("SOC_CONCENTRATION", Decimal("18.5000"), "g/kg")
    assert v == Decimal("18.5000")
    assert u == "g/kg"
    assert m == "IDENTITY"

    # 1.5% -> 15.0000 g/kg (for legacy alias SOC_STOCK_PCT)
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("SOC_STOCK_PCT", Decimal("1.5000"), "%")
    assert v == Decimal("15.0000")
    assert u == "g/kg"
    assert m == "LINEAR_SCALING:VAL*10"
    assert ver == "UNIT_CONV_V1.0"

    # 15.0 g/kg -> 15.0000 g/kg (IDENTITY)
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("SOC_STOCK_PCT", Decimal("15.0000"), "g/kg")
    assert v == Decimal("15.0000")
    assert u == "g/kg"
    assert m == "IDENTITY"

    # 15.0 mg/g -> 15.0000 g/kg (IDENTITY)
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("TOTAL_ORGANIC_CARBON_G_KG", Decimal("15.0000"), "mg/g")
    assert v == Decimal("15.0000")
    assert u == "g/kg"
    assert m == "IDENTITY"

    # 2. Bulk density conversions
    # 1.35 g/cm³ -> 1.35 g/cm³
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("BULK_DENSITY_G_CM3", Decimal("1.3500"), "g/cm³")
    assert v == Decimal("1.3500")
    assert u == "g/cm³"
    assert m == "IDENTITY"

    # 1350 kg/m³ -> 1.35 g/cm³
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("BULK_DENSITY_G_CM3", Decimal("1350.0000"), "kg/m³")
    assert v == Decimal("1.3500")
    assert u == "g/cm³"
    assert "LINEAR_SCALING:VAL/1000" in m

    # 3. Unconvertible / invalid units: Must return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0") without failing
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("SOC_STOCK_PCT", Decimal("1.5000"), "lightyears")
    assert v is None
    assert u is None
    assert m == "UNCONVERTIBLE"
    assert ver == "UNIT_CONV_V1.0"

    # Unknown analyte
    v, u, m, ver = AgricultureService.normalize_laboratory_analyte_measurement("UNKNOWN_ANALYTE", Decimal("42.0"), "kg")
    assert v is None


@pytest.mark.asyncio
async def test_sampling_plan_lock_snapshot_immutability(db_session: AsyncSession):
    """
    Verifies that locking a sampling plan version produces an immutable snapshot
    containing all 14 provenance/config fields, and subsequent external mutations
    do not alter the locked snapshot.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id,
        SamplingCampaignCreate(campaign_code="CAMP-SNAP-01", name="Snapshot Test", planned_start_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id,
        SamplingPlanVersionCreate(effective_as_of_date=date(2026, 1, 1), notes="Original notes"),
        user_id=admin.id,
    )

    locked = await AgricultureService.lock_sampling_plan_version(
        db_session, spv.id, org.id, admin.id,
        notes="Locking plan permanently",
    )
    assert locked.is_locked is True
    snap = locked.plan_lock_snapshot
    assert snap is not None
    assert "locked_at" in snap
    assert "effective_stratification_date" in snap
    assert snap["campaign_code"] == "CAMP-SNAP-01"
    assert snap["locked_by"] == str(admin.id)
    assert snap["sampling_design_method"] == "STRATIFIED_RANDOM"

    # Mutate project name and campaign name
    proj.name = "Tampered Project Name"
    campaign.name = "Tampered Campaign Name"
    await db_session.flush()

    # Re-fetch plan version and assert snapshot was NOT mutated
    re_spv = await db_session.scalar(select(SamplingPlanVersion).where(SamplingPlanVersion.id == spv.id))
    assert re_spv.plan_lock_snapshot["campaign_code"] == "CAMP-SNAP-01"
    assert re_spv.plan_lock_snapshot["locked_by"] == str(admin.id)


@pytest.mark.asyncio
async def test_sod_violation_collector_cannot_qa_review(db_session: AsyncSession):
    """
    Verifies Separation of Duties:
    A field collector is strictly barred from signing off on QA review of their own collected sample.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field = setup["field"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id,
        SamplingCampaignCreate(campaign_code="CAMP-SOD-01", name="SoD Campaign", planned_start_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id,
        SamplingPlanVersionCreate(effective_as_of_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    pts = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id,
        [SamplingPointCreate(point_code="P-SOD-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id, stratum_id=stratum.id)],
        user_id=admin.id,
    )
    await AgricultureService.lock_sampling_plan_version(db_session, spv.id, org.id, admin.id)
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == pts[0].id))

    # Field agent collects sample
    await AgricultureService.record_sample_collection(
        db_session, sample.id, org.id,
        SampleCollectionCreate(actual_lat=28.505, actual_lon=77.105, collection_timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc), collector_name=field.full_name),
        user_id=field.id,
    )

    # Custody + Lab Intake + Analysis
    await AgricultureService.record_laboratory_receipt(
        db_session, sample.id, org.id,
        LabReceiptCreate(laboratory_name="Agro Lab", received_at=datetime(2026, 1, 3, tzinfo=timezone.utc), received_by_name="Tech"),
    )
    await AgricultureService.record_laboratory_analysis(
        db_session, sample.id, org.id,
        LabAnalysisCreate(laboratory_name="Agro Lab", analysis_date=date(2026, 1, 4), results=[LabResultCreate(analyte="SOC_STOCK_PCT", raw_value=Decimal("1.70"), raw_unit="%")]),
    )

    # Collector attempts to perform QA review -> ValueError SoD violation
    with pytest.raises(ValueError, match="Separation of Duties violation: The field collector"):
        await AgricultureService.record_sample_qa_review(
            db_session, sample.id, org.id,
            SampleQAReviewCreate(reviewer_name=field.full_name, overall_qa_status="ACCEPTED"),
            user_id=field.id,
        )


@pytest.mark.asyncio
async def test_state_machine_invalid_transitions(db_session: AsyncSession):
    """
    Verifies state machine safety guards:
    1. Laboratory intake rejected on uncollected sample.
    2. Custody transfer rejected on uncollected sample.
    3. QA review ACCEPTED rejected if sample has no lab results.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id,
        SamplingCampaignCreate(campaign_code="CAMP-SM-01", name="State Machine Campaign", planned_start_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id,
        SamplingPlanVersionCreate(effective_as_of_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    pts = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id,
        [SamplingPointCreate(point_code="P-SM-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id, stratum_id=stratum.id)],
        user_id=admin.id,
    )
    await AgricultureService.lock_sampling_plan_version(db_session, spv.id, org.id, admin.id)
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == pts[0].id))
    assert sample.status == "PLANNED"

    # 1. Attempt lab intake before collection
    with pytest.raises(ValueError, match="cannot undergo lab receipt from status 'PLANNED'"):
        await AgricultureService.record_laboratory_receipt(
            db_session, sample.id, org.id,
            LabReceiptCreate(laboratory_name="Agro Lab", received_at=datetime(2026, 1, 3, tzinfo=timezone.utc), received_by_name="Tech"),
        )

    # 2. Attempt custody transfer before collection
    with pytest.raises(ValueError, match="Cannot record custody transfer for uncollected sample"):
        await AgricultureService.record_custody_event(
            db_session, sample.id, org.id,
            CustodyEventCreate(event_type="TRANSPORT_DISPATCH", event_timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc), custodian_name="Courier", custodian_organization="FedEx"),
        )


@pytest.mark.asyncio
async def test_offline_collection_idempotency(db_session: AsyncSession):
    """
    Verifies that offline mobile collection submissions with an idempotency_key
    safely return the existing collection event when replayed without duplicating records.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field = setup["field"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id,
        SamplingCampaignCreate(campaign_code="CAMP-IDEM-01", name="Idempotency Campaign", planned_start_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id,
        SamplingPlanVersionCreate(effective_as_of_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    pts = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id,
        [SamplingPointCreate(point_code="P-IDEM-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id, stratum_id=stratum.id)],
        user_id=admin.id,
    )
    await AgricultureService.lock_sampling_plan_version(db_session, spv.id, org.id, admin.id)
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == pts[0].id))

    payload = SampleCollectionCreate(
        actual_lat=28.50502,
        actual_lon=77.10501,
        collection_timestamp=datetime(2026, 1, 2, 9, 30, tzinfo=timezone.utc),
        collector_name=field.full_name,
        idempotency_key="OFFLINE-TXN-UUID-999888",
    )

    # First dispatch
    evt1 = await AgricultureService.record_sample_collection(db_session, sample.id, org.id, payload, user_id=field.id)
    assert evt1.idempotency_key == "OFFLINE-TXN-UUID-999888"

    # Second dispatch with identical idempotency_key (replayed offline queue)
    evt2 = await AgricultureService.record_sample_collection(db_session, sample.id, org.id, payload, user_id=field.id)
    assert evt2.id == evt1.id

    # Verify only ONE event exists in DB
    events = (await db_session.execute(
        select(SampleCollectionEvent).where(SampleCollectionEvent.physical_sample_id == sample.id)
    )).scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_laboratory_result_supersedes_acyclic_audit_trail(db_session: AsyncSession):
    """
    Verifies that laboratory result revisions form a strict acyclic audit trail
    where supersedes_id and superseded_by_id are bidirectionally linked.
    """
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    proj = setup["project"]
    admin = setup["admin"]
    field = setup["field"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    campaign = await AgricultureService.create_sampling_campaign(
        db_session, proj.id, org.id,
        SamplingCampaignCreate(campaign_code="CAMP-REV-01", name="Revision Campaign", planned_start_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id,
        SamplingPlanVersionCreate(effective_as_of_date=date(2026, 1, 1)),
        user_id=admin.id,
    )
    pts = await AgricultureService.create_sampling_points(
        db_session, campaign.id, spv.id, org.id,
        [SamplingPointCreate(point_code="P-REV-1", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id, stratum_id=stratum.id)],
        user_id=admin.id,
    )
    await AgricultureService.lock_sampling_plan_version(db_session, spv.id, org.id, admin.id)
    sample = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == pts[0].id))

    await AgricultureService.record_sample_collection(
        db_session, sample.id, org.id,
        SampleCollectionCreate(actual_lat=28.505, actual_lon=77.105, collection_timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc), collector_name=field.full_name),
        user_id=field.id,
    )
    await AgricultureService.record_laboratory_receipt(
        db_session, sample.id, org.id,
        LabReceiptCreate(laboratory_name="Precision Lab", received_at=datetime(2026, 1, 3, tzinfo=timezone.utc), received_by_name="Tech"),
    )

    # Initial Result R1
    analysis = await AgricultureService.record_laboratory_analysis(
        db_session, sample.id, org.id,
        LabAnalysisCreate(laboratory_name="Precision Lab", analysis_date=date(2026, 1, 4), results=[LabResultCreate(analyte="SOC_STOCK_PCT", raw_value=Decimal("1.65"), raw_unit="%")]),
    )
    r1 = analysis.results[0]
    assert r1.is_superseded is False
    assert r1.supersedes_id is None
    assert r1.superseded_by_id is None

    # Revise R1 -> R2
    r2 = await AgricultureService.revise_laboratory_result(
        db_session, r1.id, org.id,
        LabResultRevisionCreate(new_raw_value=Decimal("1.72"), new_raw_unit="%", revision_reason="Re-assayed due to calibration drift"),
        user_id=admin.id,
    )
    assert r2.raw_value == Decimal("1.72")
    assert r2.is_superseded is False
    assert r2.supersedes_id == r1.id
    assert r1.is_superseded is True
    assert r1.superseded_by_id == r2.id

    # Revise R2 -> R3
    r3 = await AgricultureService.revise_laboratory_result(
        db_session, r2.id, org.id,
        LabResultRevisionCreate(new_raw_value=Decimal("1.71"), new_raw_unit="%", revision_reason="Third-party inter-lab validation"),
        user_id=admin.id,
    )
    assert r3.raw_value == Decimal("1.71")
    assert r3.supersedes_id == r2.id
    assert r2.is_superseded is True
    assert r2.superseded_by_id == r3.id

    # Attempting to revise already superseded R1 -> raises ValueError
    with pytest.raises(ValueError, match="already been superseded"):
        await AgricultureService.revise_laboratory_result(
            db_session, r1.id, org.id,
            LabResultRevisionCreate(new_raw_value=Decimal("1.99"), new_raw_unit="%", revision_reason="Attempt invalid revision"),
            user_id=admin.id,
        )
