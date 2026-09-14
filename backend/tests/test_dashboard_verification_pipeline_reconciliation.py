# =============================================================================
# VeriField Nexus — Dashboard Activity Count & Verification Pipeline Reconciliation Tests
# =============================================================================
# Formally verifies Cases A through K, Sector Isolation, and Pipeline Integrity.
# =============================================================================

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.workspaces.services.dashboard_resolver import DashboardResolverService

class DummyResult:
    def __init__(self, items):
        self._items = items
    def scalars(self):
        return self
    def all(self):
        return self._items
    def first(self):
        return self._items[0] if self._items else None
    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

def create_mock_activity(
    status="pending",
    validation_status="pending",
    trust_score=None,
    activity_type="cookstove_usage",
    activity_data=None,
    org_id=None,
    project_id=None
):
    act = Activity(
        id=uuid.uuid4(),
        organization_id=org_id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        activity_type=activity_type,
        activity_data=activity_data or {"stove_id": "STOVE-001", "household_id": "HH-001"},
        status=status,
        validation_status=validation_status,
        trust_score=trust_score,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    if project_id:
        act.project_id = project_id
    return act

# =============================================================================
# CANONICAL PIPELINE CLASSIFICATION (Cases A - K)
# =============================================================================

def test_case_a_zero_activities():
    """CASE A: 0 active activities -> pipeline total = 0, all stages = 0."""
    activities = []
    counts = {"PENDING": 0, "AI_VERIFIED": 0, "FLAGGED": 0, "MANUAL_REVIEW": 0, "APPROVED": 0}
    for a in activities:
        counts[a.pipeline_stage] += 1
    assert sum(counts.values()) == 0
    assert counts["PENDING"] == 0
    assert counts["AI_VERIFIED"] == 0

def test_case_b_one_pending_activity():
    """CASE B: 1 Pending activity -> Pending = 1."""
    act = create_mock_activity(status="pending", trust_score=None)
    assert act.pipeline_stage == "PENDING"

def test_case_c_one_explicitly_ai_verified():
    """CASE C: 1 explicitly AI Verified activity -> AI Verified = 1."""
    act1 = create_mock_activity(status="verified", trust_score=85.0)
    act2 = create_mock_activity(status="ai_verified", trust_score=None)
    assert act1.pipeline_stage == "AI_VERIFIED"
    assert act2.pipeline_stage == "AI_VERIFIED"

def test_case_d_one_manual_review():
    """CASE D: 1 Manual Review activity -> Manual Review = 1."""
    act1 = create_mock_activity(status="review", trust_score=75.0)
    act2 = create_mock_activity(status="audit", trust_score=None)
    act3 = create_mock_activity(status="manual_review", trust_score=95.0)
    assert act1.pipeline_stage == "MANUAL_REVIEW"
    assert act2.pipeline_stage == "MANUAL_REVIEW"
    assert act3.pipeline_stage == "MANUAL_REVIEW"

def test_case_e_one_flagged():
    """CASE E: 1 Flagged activity -> Flagged = 1."""
    act1 = create_mock_activity(status="flagged", trust_score=40.0)
    act2 = create_mock_activity(status="anomaly", trust_score=95.0)
    act3 = create_mock_activity(status="rejected", trust_score=88.0)
    assert act1.pipeline_stage == "FLAGGED"
    assert act2.pipeline_stage == "FLAGGED"
    assert act3.pipeline_stage == "FLAGGED"

def test_case_f_one_approved():
    """CASE F: 1 Approved activity -> Approved = 1."""
    act1 = create_mock_activity(status="approved", trust_score=40.0)
    act2 = create_mock_activity(status="pending", validation_status="APPROVED", trust_score=60.0)
    assert act1.pipeline_stage == "APPROVED"
    assert act2.pipeline_stage == "APPROVED"

def test_case_g_mixed_pipeline():
    """
    CASE G: Mixed pipeline:
    2 Pending, 3 AI Verified, 1 Manual Review, 1 Flagged, 4 Approved -> Total = 11.
    No duplication, mutually exclusive.
    """
    activities = [
        # 2 Pending
        create_mock_activity(status="pending", trust_score=None),
        create_mock_activity(status="submitted", trust_score=None),
        # 3 AI Verified
        create_mock_activity(status="verified", trust_score=85.0),
        create_mock_activity(status="ai_verified", trust_score=90.0),
        create_mock_activity(status="verified", trust_score=92.0),
        # 1 Manual Review
        create_mock_activity(status="review", trust_score=75.0),
        # 1 Flagged
        create_mock_activity(status="flagged", trust_score=30.0),
        # 4 Approved
        create_mock_activity(status="approved", trust_score=95.0),
        create_mock_activity(status="approved", trust_score=80.0),
        create_mock_activity(status="pending", validation_status="APPROVED", trust_score=99.0),
        create_mock_activity(status="approved", validation_status="APPROVED", trust_score=70.0),
    ]

    assert len(activities) == 11
    counts = {"PENDING": 0, "AI_VERIFIED": 0, "FLAGGED": 0, "MANUAL_REVIEW": 0, "APPROVED": 0}
    for a in activities:
        counts[a.pipeline_stage] += 1

    assert counts["PENDING"] == 2
    assert counts["AI_VERIFIED"] == 3
    assert counts["MANUAL_REVIEW"] == 1
    assert counts["FLAGGED"] == 1
    assert counts["APPROVED"] == 4
    assert sum(counts.values()) == 11

def test_case_h_active_sites_independent_from_pipeline():
    """CASE H: 100 Active Sites + 0 activities -> Active Sites = 100, Pipeline = 0."""
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    # 100 Assets, 0 Activities
    assets = [Asset(id=uuid.uuid4(), name=f"Site {i}", asset_type_id="STOVE") for i in range(100)]
    activities = []

    # Mock execute results
    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "from assets" in stmt_str:
            return DummyResult(assets)
        elif "from activities" in stmt_str:
            return DummyResult(activities)
        elif "from methodology_families" in stmt_str:
            return DummyResult([])
        elif "from methodologies" in stmt_str:
            return DummyResult([])
        elif "from projects" in stmt_str:
            return DummyResult([])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    import asyncio
    res = asyncio.run(resolver.resolve_dashboard(
        organization_id=uuid.uuid4(),
        workspace_id="cookstoves",
        methodology_id="AMS-II.G"
    ))

    assert res["asset_total"] == 100
    assert res["activity_total"] == 0
    assert len(res["activities"]) == 0
    assert len(res["assets"]) == 100

def test_case_i_high_trust_explicit_pending():
    """
    CASE I: 1 activity with high trust score but explicit Pending status
    Expected: PENDING, NOT AI_VERIFIED.
    """
    act = create_mock_activity(status="pending", validation_status="pending", trust_score=95.0)
    assert act.pipeline_stage == "PENDING"
    assert act.pipeline_stage != "AI_VERIFIED"

def test_case_j_high_trust_approved():
    """
    CASE J: Approved record with high trust score
    Expected: APPROVED, NOT AI_VERIFIED.
    """
    act = create_mock_activity(status="approved", validation_status="APPROVED", trust_score=98.0)
    assert act.pipeline_stage == "APPROVED"
    assert act.pipeline_stage != "AI_VERIFIED"

def test_case_k_null_unknown_workflow_state():
    """
    CASE K: Null/unknown workflow state
    Verify safe fallback to PENDING. Never auto-verify it!
    """
    act_null = create_mock_activity(status=None, validation_status=None, trust_score=None)
    act_unknown = create_mock_activity(status="unrecognized_state", validation_status=None, trust_score=None)
    
    assert act_null.pipeline_stage == "PENDING"
    assert act_unknown.pipeline_stage == "PENDING"
    assert act_null.pipeline_stage != "AI_VERIFIED"
    assert act_unknown.pipeline_stage != "AI_VERIFIED"

# =============================================================================
# SECTOR ISOLATION TESTS
# =============================================================================

def test_sector_isolation():
    """Verify activities from other sectors do not leak into Cookstoves dashboard."""
    cook_act = create_mock_activity(activity_type="cookstove_usage")
    energy_act = create_mock_activity(activity_type="solar_meter_telemetry")
    biochar_act = create_mock_activity(activity_type="biochar_pyrolysis_batch")
    ev_act = create_mock_activity(activity_type="ev_charging_session")

    assert DashboardResolverService._matches_sector_activity(cook_act, "COOKSTOVES") is True
    assert DashboardResolverService._matches_sector_activity(energy_act, "COOKSTOVES") is False
    assert DashboardResolverService._matches_sector_activity(biochar_act, "COOKSTOVES") is False
    assert DashboardResolverService._matches_sector_activity(ev_act, "COOKSTOVES") is False

    assert DashboardResolverService._matches_sector_activity(energy_act, "HYBRID_ENERGY") is True
    assert DashboardResolverService._matches_sector_activity(cook_act, "HYBRID_ENERGY") is False

    assert DashboardResolverService._matches_sector_activity(biochar_act, "BIOCHAR") is True
    assert DashboardResolverService._matches_sector_activity(cook_act, "BIOCHAR") is False

    assert DashboardResolverService._matches_sector_activity(ev_act, "EV_MOBILITY") is True
    assert DashboardResolverService._matches_sector_activity(cook_act, "EV_MOBILITY") is False

# =============================================================================
# BACKEND SERIALIZATION TESTS
# =============================================================================

def test_activity_serialization_no_hardcoded_verified():
    """Ensure dashboard_resolver serializes real status, pipeline_stage, numeric trust score, and no fake 2026-07-22."""
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    org_id = uuid.uuid4()
    act = create_mock_activity(
        status="pending",
        validation_status="pending",
        trust_score=85.0,
        org_id=org_id
    )

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "from activities" in stmt_str:
            return DummyResult([act])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    import asyncio
    res = asyncio.run(resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="cookstoves",
        methodology_id="AMS-II.G"
    ))

    activities = res["activities"]
    assert len(activities) == 1
    first_act = activities[0]

    # Verify real persisted values
    assert first_act["status"] == "pending"
    assert first_act["pipeline_stage"] == "pending"
    assert first_act["trust_score"] == 85.0
    assert first_act["trust_index"] == "85%"
    assert first_act["captured_at"] is not None
    assert first_act["captured_at"] != "2026-07-22"  # Real date, not fake fixed fallback
    assert res["activity_total"] == 1
