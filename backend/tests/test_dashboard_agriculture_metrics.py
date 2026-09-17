# =============================================================================
# VeriField Nexus — Agriculture & Land Use Dashboard Metric Resolution Tests
# =============================================================================
# Verifies:
# 1. Root Bug: AGRICULTURE_LAND_USE does not receive EV metrics (co2_displaced, charging_sessions, etc.)
# 2. Unknown Sector: SYNTHETIC_UNKNOWN resolves to generic neutral KPIs, never EV or Cookstoves
# 3. Agriculture KPI Data: Real calculation of monitored area, land units, field activities, QA findings
# 4. Nested Area Double-Counting Protection: Only top-level units (parent_id=None) contribute to area
# 5. Empty State: 0 land units, 0 activities resolves to "—" area, "0" units, "0" activities, "—" QA findings
# 6. Sector Regression: Cookstoves, Hybrid Energy, Biochar, EV Mobility preserve legitimate KPIs
# =============================================================================

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.agriculture.models import LandUnit
from app.domains.workspaces.services.dashboard_resolver import DashboardResolverService, canonical_sector_code


class DummyResult:
    def __init__(self, items):
        self._items = items if isinstance(items, list) else [items] if items is not None else []

    def scalars(self):
        return self

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


def create_land_unit(
    unit_type="PARCEL",
    name="Parcel Alpha",
    area_ha=100.0,
    parent_id=None,
    org_id=None,
    project_id=None,
    is_active=True
):
    lu_id = uuid.uuid4()
    return LandUnit(
        id=lu_id,
        organization_id=org_id or uuid.uuid4(),
        project_id=project_id or uuid.uuid4(),
        parent_id=parent_id,
        unit_type=unit_type,
        name=name,
        code=f"LU-{unit_type[:3]}-{str(lu_id)[:4].upper()}",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[77.1, 28.6], [77.2, 28.6], [77.2, 28.7], [77.1, 28.7], [77.1, 28.6]]]
        },
        boundary_source="DECLARED",
        boundary_crs="EPSG:4326",
        area_ha=area_ha,
        centroid_lat=28.65,
        centroid_lon=77.15,
        is_active=is_active,
        properties={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def create_activity(
    activity_type="soil_sample_collection",
    status="verified",
    validation_status="VERIFIED",
    trust_score=90.0,
    org_id=None,
    project_id=None,
    activity_data=None
):
    act = Activity(
        id=uuid.uuid4(),
        organization_id=org_id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        activity_type=activity_type,
        activity_data=activity_data or {"sample_id": "SMP-001", "depth": "0-30cm"},
        status=status,
        validation_status=validation_status,
        trust_score=trust_score,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        property_id=project_id,
    )
    if project_id:
        act.project_id = project_id
    return act


@pytest.mark.asyncio
async def test_root_bug_agriculture_does_not_receive_ev_metrics():
    """
    Test 1: Root Bug Regression
    Ensures AGRICULTURE_LAND_USE resolves to Agriculture KPIs, NEVER EV Mobility KPIs
    (CO₂ DISPLACED, CHARGING SESSIONS, ELECTRICITY DELIVERED, FLEET UTILISATION).
    """
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    org_id = uuid.uuid4()
    p_id = uuid.uuid4()
    land_unit = create_land_unit(name="Wheat Field", area_ha=50.0, org_id=org_id, project_id=p_id)
    agri_act = create_activity(activity_type="field_boundary_survey", org_id=org_id, project_id=p_id)

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "from land_units" in stmt_str:
            return DummyResult([land_unit])
        elif "from activities" in stmt_str:
            return DummyResult([agri_act])
        elif "from assets" in stmt_str:
            return DummyResult([])
        elif "from methodology_families" in stmt_str:
            return DummyResult([])
        elif "from methodologies" in stmt_str:
            return DummyResult([])
        elif "from projects" in stmt_str:
            return DummyResult([])
        elif "from verification_tasks" in stmt_str:
            return DummyResult([])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    res = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="AGRICULTURE_LAND_USE",
        methodology_id="VM0042",
        project_id=str(p_id)
    )

    kpi_labels = [k["label"] for k in res["kpis"]]
    kpi_codes = [k["code"] for k in res["kpis"]]

    # Assert NO EV metrics
    assert "CHARGING SESSIONS" not in kpi_labels
    assert "ELECTRICITY DELIVERED" not in kpi_labels
    assert "FLEET UTILISATION" not in kpi_labels
    assert "charging_sessions" not in kpi_codes
    assert "kwh_delivered" not in kpi_codes
    assert "fleet_util" not in kpi_codes

    # Assert Agriculture KPIs are present
    assert "MONITORED AREA" in kpi_labels
    assert "LAND UNITS" in kpi_labels
    assert "FIELD ACTIVITIES" in kpi_labels
    assert "OPEN QA FINDINGS" in kpi_labels

    assert "monitored_area" in kpi_codes
    assert "land_units" in kpi_codes
    assert "field_activities" in kpi_codes
    assert "qa_findings" in kpi_codes


@pytest.mark.asyncio
async def test_unknown_sector_resolves_to_generic_neutral_kpis():
    """
    Test 2: Unknown Sector Fallback
    Ensures an unrecognized sector code resolves to neutral generic KPIs,
    NEVER EV Mobility and NEVER Cookstoves.
    """
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    org_id = uuid.uuid4()

    async def mock_execute(stmt):
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    res = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="SYNTHETIC_UNKNOWN_SECTOR",
        methodology_id="UNKNOWN_METH"
    )

    kpi_labels = [k["label"] for k in res["kpis"]]
    kpi_codes = [k["code"] for k in res["kpis"]]

    # Assert NO EV metrics
    assert "CHARGING SESSIONS" not in kpi_labels
    assert "ELECTRICITY DELIVERED" not in kpi_labels
    assert "FLEET UTILISATION" not in kpi_labels

    # Assert NO Cookstove metrics
    assert "HOUSEHOLDS REACHED" not in kpi_labels
    assert "STOVE USAGE RATE" not in kpi_labels

    # Assert Generic Neutral KPIs
    assert "MONITORED ASSETS" in kpi_labels
    assert "ACTIVITIES" in kpi_labels
    assert "OPEN FINDINGS" in kpi_labels
    assert "MONITORING STATUS" in kpi_labels

    assert "monitored_assets" in kpi_codes
    assert "field_activities" in kpi_codes
    assert "open_findings" in kpi_codes
    assert "monitoring_status" in kpi_codes


@pytest.mark.asyncio
async def test_agriculture_kpi_data_calculation():
    """
    Test 3: Agriculture KPI Data Aggregation
    With 2 valid top-level land units (100 ha + 50 ha), 3 field activities,
    and 1 open QA finding (flagged activity).
    Asserts:
    - monitored_area == "150 ha"
    - land_units == "2"
    - field_activities == "3"
    - qa_findings == "1"
    """
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    org_id = uuid.uuid4()
    p_id = uuid.uuid4()

    unit1 = create_land_unit(name="North Farm", area_ha=100.0, parent_id=None, org_id=org_id, project_id=p_id)
    unit2 = create_land_unit(name="South Farm", area_ha=50.0, parent_id=None, org_id=org_id, project_id=p_id)

    act1 = create_activity(activity_type="cover_crop_planting", status="verified", validation_status="VERIFIED", org_id=org_id, project_id=p_id)
    act2 = create_activity(activity_type="tillage_reduction", status="verified", validation_status="VERIFIED", org_id=org_id, project_id=p_id)
    act3_flagged = create_activity(activity_type="fertilizer_application", status="flagged", validation_status="FLAGGED", org_id=org_id, project_id=p_id)

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "from land_units" in stmt_str:
            return DummyResult([unit1, unit2])
        elif "from activities" in stmt_str:
            return DummyResult([act1, act2, act3_flagged])
        elif "from assets" in stmt_str:
            return DummyResult([])
        elif "from methodology_families" in stmt_str:
            return DummyResult([])
        elif "from methodologies" in stmt_str:
            return DummyResult([])
        elif "from projects" in stmt_str:
            return DummyResult([])
        elif "from verification_tasks" in stmt_str:
            return DummyResult([])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    res = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="agriculture",
        methodology_id="VM0042",
        project_id=str(p_id)
    )

    kpis = {k["code"]: k for k in res["kpis"]}

    assert kpis["monitored_area"]["value"] == "150 ha"
    assert kpis["monitored_area"]["numeric_value"] == 150.0
    assert kpis["monitored_area"]["state"] == "AVAILABLE"

    assert kpis["land_units"]["value"] == "2"
    assert kpis["land_units"]["numeric_value"] == 2

    assert kpis["field_activities"]["value"] == "3"
    assert kpis["field_activities"]["numeric_value"] == 3

    assert kpis["qa_findings"]["value"] == "1"
    assert kpis["qa_findings"]["numeric_value"] == 1
    assert kpis["qa_findings"]["state"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_nested_area_double_counting_protection():
    """
    Test 4: Nested Area Double-Counting Protection
    Hierarchy:
    - 1 Parent Parcel (100 ha, parent_id=None)
    - 2 Child Strata (60 ha and 40 ha, parent_id=Parcel.id)
    Asserts:
    - monitored_area == "100 ha" (NOT 200 ha!)
    - total land_units count == "3"
    """
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    org_id = uuid.uuid4()
    p_id = uuid.uuid4()

    parent_parcel = create_land_unit(
        unit_type="PARCEL",
        name="Main Estate Parcel",
        area_ha=100.0,
        parent_id=None,
        org_id=org_id,
        project_id=p_id
    )
    stratum_a = create_land_unit(
        unit_type="STRATUM",
        name="Stratum A (Loam)",
        area_ha=60.0,
        parent_id=parent_parcel.id,
        org_id=org_id,
        project_id=p_id
    )
    stratum_b = create_land_unit(
        unit_type="STRATUM",
        name="Stratum B (Clay)",
        area_ha=40.0,
        parent_id=parent_parcel.id,
        org_id=org_id,
        project_id=p_id
    )

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "from land_units" in stmt_str:
            return DummyResult([parent_parcel, stratum_a, stratum_b])
        elif "from activities" in stmt_str:
            return DummyResult([])
        elif "from assets" in stmt_str:
            return DummyResult([])
        elif "from methodology_families" in stmt_str:
            return DummyResult([])
        elif "from methodologies" in stmt_str:
            return DummyResult([])
        elif "from projects" in stmt_str:
            return DummyResult([])
        elif "from verification_tasks" in stmt_str:
            return DummyResult([])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    res = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="agriculture_land_use",
        methodology_id="VM0042",
        project_id=str(p_id)
    )

    kpis = {k["code"]: k for k in res["kpis"]}

    # Area MUST be only the 100 ha top-level parcel, NOT 100 + 60 + 40 = 200 ha
    assert kpis["monitored_area"]["value"] == "100 ha"
    assert kpis["monitored_area"]["numeric_value"] == 100.0
    assert "1 top-level parcel" in kpis["monitored_area"]["subtext"]

    # Total units count encompasses all 3 registered units (1 parcel + 2 strata)
    assert kpis["land_units"]["value"] == "3"
    assert kpis["land_units"]["numeric_value"] == 3
    assert "1 top-level parcels, 2 sub-units" in kpis["land_units"]["subtext"]


@pytest.mark.asyncio
async def test_empty_agriculture_project():
    """
    Test 5: Empty Agriculture Project
    With 0 land units and 0 activities:
    - monitored_area == "—" (numeric_value is None, state is "NO_DATA")
    - land_units == "0"
    - field_activities == "0"
    - qa_findings == "—" (numeric_value is None, state is "NO_DATA")
    """
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    org_id = uuid.uuid4()
    p_id = uuid.uuid4()

    async def mock_execute(stmt):
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    res = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="agriculture",
        methodology_id="VM0042",
        project_id=str(p_id)
    )

    kpis = {k["code"]: k for k in res["kpis"]}

    assert kpis["monitored_area"]["value"] == "—"
    assert kpis["monitored_area"]["numeric_value"] is None
    assert kpis["monitored_area"]["state"] == "NO_DATA"

    assert kpis["land_units"]["value"] == "0"
    assert kpis["land_units"]["numeric_value"] == 0

    assert kpis["field_activities"]["value"] == "0"
    assert kpis["field_activities"]["numeric_value"] == 0

    assert kpis["qa_findings"]["value"] == "—"
    assert kpis["qa_findings"]["numeric_value"] is None
    assert kpis["qa_findings"]["state"] == "NO_DATA"


@pytest.mark.asyncio
async def test_sector_regression_existing_sectors_preserved():
    """
    Test 6: Existing Sector Regression Protection
    Ensures Cookstoves, Hybrid Energy, Biochar, and EV Mobility each maintain
    their own legitimate KPIs and canonical sector resolution.
    """
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    org_id = uuid.uuid4()

    async def mock_execute(stmt):
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    # 1. Cookstoves
    cs_res = await resolver.resolve_dashboard(organization_id=org_id, workspace_id="cookstoves", methodology_id="AMS-II.G")
    cs_codes = [k["code"] for k in cs_res["kpis"]]
    assert cs_codes == ["co2_reduced", "households", "usage_rate", "credit_value"]

    # 2. Hybrid Energy
    he_res = await resolver.resolve_dashboard(organization_id=org_id, workspace_id="hybrid_energy", methodology_id="AMS-I.D")
    he_codes = [k["code"] for k in he_res["kpis"]]
    assert he_codes == ["co2_displaced", "energy_gen", "diesel_avoided", "active_sites"]

    # 3. Biochar
    bc_res = await resolver.resolve_dashboard(organization_id=org_id, workspace_id="biochar", methodology_id="VM0044")
    bc_codes = [k["code"] for k in bc_res["kpis"]]
    assert bc_codes == ["biochar_produced", "active_batches", "feedstock_processed", "open_qa_findings"]

    # 4. EV Mobility
    ev_res = await resolver.resolve_dashboard(organization_id=org_id, workspace_id="ev_mobility", methodology_id="AMS-III.C")
    ev_codes = [k["code"] for k in ev_res["kpis"]]
    assert ev_codes == ["co2_displaced", "charging_sessions", "kwh_delivered", "fleet_util"]


@pytest.mark.asyncio
async def test_qa_findings_deduplication_linked_verification_task():
    """
    Test 7: QA Findings Deduplication
    1 flagged activity + 1 verification task created to investigate that flagged activity
    must equal 1 finding, NOT 2 (1 issue = 1 finding).
    """
    from app.domains.verification.models import VerificationTask

    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)

    org_id = uuid.uuid4()
    p_id = uuid.uuid4()

    flagged_act = create_activity(
        activity_type="tree_observation",
        status="flagged",
        validation_status="FLAGGED",
        org_id=org_id,
        project_id=p_id
    )

    # Task linked to the flagged activity via findings
    linked_task = VerificationTask(
        id=uuid.uuid4(),
        project_id=p_id,
        status="ASSIGNED",
        findings={"activity_id": str(flagged_act.id), "reason": "Anomaly in DBH measurement"}
    )

    # An independent task not linked to any flagged activity
    independent_task = VerificationTask(
        id=uuid.uuid4(),
        project_id=p_id,
        status="IN_PROGRESS",
        findings={"reason": "Independent boundary audit finding"}
    )

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "from activities" in stmt_str:
            return DummyResult([flagged_act])
        elif "from verification_tasks" in stmt_str:
            return DummyResult([linked_task, independent_task])
        elif "from land_units" in stmt_str:
            return DummyResult([])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    res = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="AGRICULTURE_LAND_USE",
        methodology_id="VM0042",
        project_id=str(p_id)
    )

    kpis = {k["code"]: k for k in res["kpis"]}
    # 1 flagged activity + 1 independent task = 2 findings (the linked task is deduplicated!)
    assert kpis["qa_findings"]["numeric_value"] == 2
    assert kpis["qa_findings"]["value"] == "2"


@pytest.mark.asyncio
async def test_qa_empty_state_unevaluated_vs_evaluated():
    """
    Test 8: QA Empty State Semantics
    - Unevaluated activity: status='pending', validation_status=None, trust_score=None
      -> Must render '—' (NO_DATA)
    - Evaluated activity: validation_status='VALID', trust_score=95, status='verified'
      -> Must render '0' (AVAILABLE, 'All checks clear')
    """
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)
    org_id = uuid.uuid4()
    p_id = uuid.uuid4()

    # Case A: Unevaluated activity
    unevaluated_act = Activity(
        id=uuid.uuid4(),
        organization_id=org_id,
        user_id=uuid.uuid4(),
        activity_type="soil_sample_collection",
        activity_data={},
        status="pending",
        validation_status=None,
        trust_score=None,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        property_id=p_id,
    )

    async def mock_execute_unevaluated(stmt):
        stmt_str = str(stmt).lower()
        if "from activities" in stmt_str:
            return DummyResult([unevaluated_act])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute_unevaluated)

    res_unevaluated = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="AGRICULTURE_LAND_USE",
        methodology_id="VM0042",
        project_id=str(p_id)
    )
    qa_kpi_a = next(k for k in res_unevaluated["kpis"] if k["code"] == "qa_findings")
    assert qa_kpi_a["value"] == "—"
    assert qa_kpi_a["state"] == "NO_DATA"
    assert qa_kpi_a["subtext"] == "No QA aggregate available"

    # Case B: Evaluated activity with 0 flags
    evaluated_act = create_activity(
        activity_type="soil_sample_collection",
        status="verified",
        validation_status="VALID",
        trust_score=95.0,
        org_id=org_id,
        project_id=p_id
    )

    async def mock_execute_evaluated(stmt):
        stmt_str = str(stmt).lower()
        if "from activities" in stmt_str:
            return DummyResult([evaluated_act])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute_evaluated)

    res_evaluated = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="AGRICULTURE_LAND_USE",
        methodology_id="VM0042",
        project_id=str(p_id)
    )
    qa_kpi_b = next(k for k in res_evaluated["kpis"] if k["code"] == "qa_findings")
    assert qa_kpi_b["value"] == "0"
    assert qa_kpi_b["state"] == "AVAILABLE"
    assert qa_kpi_b["subtext"] == "All checks clear"


@pytest.mark.asyncio
async def test_authoritative_monitored_area_excludes_plots_and_child_fields():
    """
    Test 9: Authoritative Monitored Area
    - 1 Top-level Parcel (120 ha, parent_id=None, unit_type='PARCEL')
    - 2 Child Fields (60 ha + 60 ha, parent_id=parcel.id, unit_type='FIELD')
    - 1 Standalone Monitoring Plot (0.04 ha, parent_id=None, unit_type='MONITORING_PLOT')
    - 1 Child Monitoring Plot (0.04 ha, parent_id=child_field.id, unit_type='MONITORING_PLOT')
    Area must be exactly 120.0 ha.
    Total units must be 5.
    """
    mock_db = AsyncMock()
    resolver = DashboardResolverService(mock_db)
    org_id = uuid.uuid4()
    p_id = uuid.uuid4()

    parcel = create_land_unit(unit_type="PARCEL", name="Main Parcel", area_ha=120.0, parent_id=None, org_id=org_id, project_id=p_id)
    field_a = create_land_unit(unit_type="FIELD", name="Field A", area_ha=60.0, parent_id=parcel.id, org_id=org_id, project_id=p_id)
    field_b = create_land_unit(unit_type="FIELD", name="Field B", area_ha=60.0, parent_id=parcel.id, org_id=org_id, project_id=p_id)
    plot_orphan = create_land_unit(unit_type="MONITORING_PLOT", name="Plot 1 (Orphan)", area_ha=0.04, parent_id=None, org_id=org_id, project_id=p_id)
    plot_child = create_land_unit(unit_type="MONITORING_PLOT", name="Plot 2 (Child)", area_ha=0.04, parent_id=field_a.id, org_id=org_id, project_id=p_id)

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "from land_units" in stmt_str:
            return DummyResult([parcel, field_a, field_b, plot_orphan, plot_child])
        return DummyResult([])

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    res = await resolver.resolve_dashboard(
        organization_id=org_id,
        workspace_id="AGRICULTURE_LAND_USE",
        methodology_id="VM0042",
        project_id=str(p_id)
    )

    kpis = {k["code"]: k for k in res["kpis"]}
    # Only the 120 ha parcel counts towards monitored area
    assert kpis["monitored_area"]["value"] == "120 ha"
    assert kpis["monitored_area"]["numeric_value"] == 120.0

    # Total management units counts all 5
    assert kpis["land_units"]["value"] == "5"
    assert kpis["land_units"]["numeric_value"] == 5
    assert "1 top-level parcels, 4 sub-units" in kpis["land_units"]["subtext"]


def test_canonical_sector_code_comprehensive_aliases():
    """Test 10: Canonical Sector Code Alias Truth."""
    agri_aliases = [
        "AGRICULTURE_LAND_USE",
        "agriculture_land_use",
        "AGRICULTURE",
        "agriculture",
        "AFOLU",
        "afolu",
        "land_use",
        "agri",
        "farm",
        "farming",
        "soil",
        "rice",
        "vm0042",
        "vm0047",
        "vt0014",
        "vmd0053",
        "vm0051",
    ]
    for alias in agri_aliases:
        assert canonical_sector_code(alias) == "AGRICULTURE_LAND_USE", f"Failed for {alias}"

    # Verify unknown sectors do not collapse to EV or any known sector
    assert canonical_sector_code("WASTE_MANAGEMENT") == "WASTE_MANAGEMENT"
    assert canonical_sector_code("forestry_reforestation") == "FORESTRY_REFORESTATION"
    assert canonical_sector_code("unknown_sector") == "UNKNOWN_SECTOR"
