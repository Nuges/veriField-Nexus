import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    FeedstockLot,
    FeedstockRunAllocation,
    FeedstockSource,
    ProductionFacility,
    ProductionRun,
)
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.workspaces.services.dashboard_resolver import DashboardResolverService


@pytest.mark.asyncio
async def test_biochar_dashboard_kpi_semantics(db_session: AsyncSession):
    """
    Mandatory Tests for Sections 44, 45, 46, 47:
    - Section 44: Active Batches Filter (2 active, 1 closed, 1 rejected -> exactly 2)
    - Section 45: Dry Feedstock Processed Basis (derived from allocations)
    - Section 46: Production Source (no double counting of runs and batches)
    - Section 47: Open QA Findings deduplication (1 issue per batch, not multiple)
    """
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Dashboard Biochar Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"dash_user_{uuid.uuid4().hex[:6]}@synthetic-nexus.org",
        full_name="Dashboard User",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name="Dashboard KPI Biochar Project",
        project_code=f"DASH-BIO-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        country="Kenya",
    )
    db_session.add(project)

    facility = ProductionFacility(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        facility_code=f"FAC-DASH-{uuid.uuid4().hex[:6].upper()}",
        facility_name="Dash Pyrolysis Plant",
        location="Nairobi",
        facility_status="OPERATIONAL",
        technology_type="CONTINUOUS_RETORT",
    )
    db_session.add(facility)

    source = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        source_code=f"SRC-DASH-{uuid.uuid4().hex[:6].upper()}",
        source_name="Dash Forestry Residue",
        source_type="FORESTRY_RESIDUE",
        biomass_type="WOOD_CHIPS",
    )
    db_session.add(source)

    # 1. Section 45: Feedstock Lot & Allocation
    # Lot: 10 t wet, 20% moisture -> 8 t dry
    # Allocation: only 6 t dry allocated/processed
    lot = FeedstockLot(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        source_id=source.id,
        lot_number=f"LOT-DASH-{uuid.uuid4().hex[:6].upper()}",
        feedstock_type="WOOD_CHIPS",
        mass_received_tonnes=10.0,
        moisture_content_pct=20.0,
        dry_mass_tonnes=8.0,
        allocated_mass_tonnes=7.5,
    )
    db_session.add(lot)

    # Section 46: Production Run outputs 2.0 t biochar
    run = ProductionRun(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        facility_id=facility.id,
        run_number=f"RUN-DASH-{uuid.uuid4().hex[:6].upper()}",
        start_time=datetime.now(timezone.utc),
        avg_pyrolysis_temp_celsius=600.0,
        residence_time_minutes=30.0,
        output_biochar_mass_tonnes=2.0,
        total_feedstock_input_tonnes=7.5,
        total_feedstock_dry_tonnes=6.0,
    )
    db_session.add(run)

    alloc = FeedstockRunAllocation(
        id=uuid.uuid4(),
        lot_id=lot.id,
        production_run_id=run.id,
        allocated_wet_mass_tonnes=7.5,
        allocated_dry_mass_tonnes=6.0,
    )
    db_session.add(alloc)

    # 2. Section 44: Batches Lifecycle
    # Batch 1: Active (PRODUCED) - 2.0 t yield (canonical batch from Run)
    b1_active = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        production_run_id=run.id,
        batch_number=f"BATCH-ACT1-{uuid.uuid4().hex[:6].upper()}",
        facility_name="Dash Pyrolysis Plant",
        kiln_id="K1",
        feedstock_type="WOOD_CHIPS",
        feedstock_weight_tonnes=3.75,
        moisture_content_pct=20.0,
        pyrolysis_temp_celsius=600.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=2.0,
        fixed_carbon_pct=80.0,
        ash_content_pct=4.0,
        molar_h_c_ratio=0.35,
        status="PRODUCED",
        has_anomaly=False,
    )
    db_session.add(b1_active)

    # Batch 2: Active (IN_STORAGE) - 1.0 t yield
    b2_active = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        batch_number=f"BATCH-ACT2-{uuid.uuid4().hex[:6].upper()}",
        facility_name="Dash Pyrolysis Plant",
        kiln_id="K1",
        feedstock_type="WOOD_CHIPS",
        feedstock_weight_tonnes=2.0,
        moisture_content_pct=20.0,
        pyrolysis_temp_celsius=600.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=1.0,
        fixed_carbon_pct=80.0,
        ash_content_pct=4.0,
        molar_h_c_ratio=0.35,
        status="IN_STORAGE",
        has_anomaly=False,
    )
    db_session.add(b2_active)

    # Batch 3: Closed (CLOSED) - 1.5 t yield -> Must NOT be counted in ACTIVE BATCHES
    b3_closed = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        batch_number=f"BATCH-CLS3-{uuid.uuid4().hex[:6].upper()}",
        facility_name="Dash Pyrolysis Plant",
        kiln_id="K1",
        feedstock_type="WOOD_CHIPS",
        feedstock_weight_tonnes=3.0,
        moisture_content_pct=20.0,
        pyrolysis_temp_celsius=600.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=1.5,
        fixed_carbon_pct=80.0,
        ash_content_pct=4.0,
        molar_h_c_ratio=0.35,
        status="CLOSED",
        has_anomaly=False,
    )
    db_session.add(b3_closed)

    # Batch 4: Rejected (REJECTED) - 0.5 t yield -> Must NOT be counted in ACTIVE BATCHES,
    # and has anomaly + rejected grade: Section 47 requires deduplication (counts as 1 open issue, not 2)
    b4_rejected = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        batch_number=f"BATCH-REJ4-{uuid.uuid4().hex[:6].upper()}",
        facility_name="Dash Pyrolysis Plant",
        kiln_id="K1",
        feedstock_type="WOOD_CHIPS",
        feedstock_weight_tonnes=1.0,
        moisture_content_pct=20.0,
        pyrolysis_temp_celsius=600.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=0.5,
        fixed_carbon_pct=50.0,
        ash_content_pct=20.0,
        molar_h_c_ratio=0.85,
        status="REJECTED",
        quality_grade="REJECTED",
        has_anomaly=True,
        anomaly_reason="Molar H/C ratio exceeds threshold (0.85 > 0.70)",
    )
    db_session.add(b4_rejected)

    await db_session.commit()

    resolver = DashboardResolverService(db_session)
    dashboard_data = await resolver.resolve_dashboard(
        organization_id=str(org_id),
        workspace_id="BIOCHAR",
        methodology_id="VM0044",
        project_id=str(project_id),
    )

    kpis = {k["code"]: k for k in dashboard_data["kpis"]}

    # Section 44 Verification: Exactly 2 active batches (excluding CLOSED and REJECTED)
    assert kpis["active_batches"]["value"] == "2", f"Expected '2' active batches, got {kpis['active_batches']['value']}"

    # Section 45 Verification: 6 t dry feedstock processed (derived from FeedstockRunAllocation)
    assert "6" in kpis["feedstock_processed"]["value"], f"Expected '6' t dry feedstock, got {kpis['feedstock_processed']['value']}"
    assert "Dry biomass feedstock" in kpis["feedstock_processed"]["unit"]

    # Section 46 Verification: Canonical biochar produced excludes rejected batch: 2.0 + 1.0 + 1.5 = 4.5 t (no double counting of runs + batches)
    assert "4.5" in kpis["biochar_produced"]["value"]

    # Section 47 Verification: Deduplicated QA findings (batch 4 has anomaly AND is rejected -> counts as 1 open issue, not 2)
    assert kpis["open_qa_findings"]["value"] == "1", f"Expected 1 open QA finding, got {kpis['open_qa_findings']['value']}"
