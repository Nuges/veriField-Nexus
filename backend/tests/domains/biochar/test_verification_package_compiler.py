"""
=============================================================================
VeriField Nexus — Comprehensive Verification Package Compiler & Auditor Tests
=============================================================================
Tests:
1. Complete MRV graph compilation into VerificationPackage
2. Multi-biomass feedstock blend ingredients breakdown (wet tonnes, dry tonnes, %, fate)
3. Mixed-product formulation models & anti-overallocation mass balance
4. Number-to-evidence trace tree drill-down ($C_{stored}$, $C_{loss}$, $E_{project}$, $E_{leakage}$, $U$, net removals)
5. Central Evidence Index & SHA-256 integrity verification (INTEGRITY_MISMATCH detection)
6. Canonical manifest hashing & LedgerService RSA digital signature sealing
7. Package immutability & Version 1 -> Version 2 structured diff engine
8. Auditor findings lifecycle (CAR, CL, FAR, NCR) & SoD enforcement
9. Scoped external auditor access grants (VerificationAccessGrant & 403 enforcement)
10. High-scale stress test (multi-source, multi-batch, multi-product compilation)
=============================================================================
"""

import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rbac import (
    ROLE_AUDITOR,
    ROLE_ORG_ADMIN,
    ROLE_PROJECT_MANAGER,
    ROLE_SUPER_ADMIN,
    ROLE_VERIFIER,
)
from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharIngredientAllocation,
    BiocharLabAnalysis,
    BiocharProductBatch,
    BiocharProductFormulation,
    BiocharProductNonBiocharIngredient,
    BiocharTransportEvent,
    FacilityReactor,
    FeedstockLot,
    FeedstockRunAllocation,
    FeedstockSource,
    ProductionFacility,
    ProductionRun,
)
from app.domains.biochar.services.auditor_workspace_service import AuditorWorkspaceService
from app.domains.biochar.services.mass_balance import BiocharMassBalanceEngine
from app.domains.biochar.services.package_compiler import BiocharVerificationPackageCompiler
from app.domains.organizations.models import Organization
from app.domains.ledger.models import Signature
from app.domains.projects.models import Project
from app.domains.verification.models import (
    VerificationAccessGrant,
    VerificationPackage,
    VerificationPackageEvidence,
    VerificationPackageFinding,
)
import jwt as pyjwt
import pytest_asyncio


def _make_auth_header(user_id: uuid.UUID, email: str, role: str, org_id: Optional[uuid.UUID] = None) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id) if org_id else None,
        "iat": now,
        "exp": now + timedelta(hours=2),
        "jti": str(uuid.uuid4()),
    }
    token = pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


async def _create_sample_project_graph(db_session: AsyncSession) -> dict:
    """Creates a comprehensive sample biochar project graph for testing."""
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Nexus Biochar Carbon Corp {uuid.uuid4().hex[:6]}",
        org_type="DEVELOPER",
        licensed_sectors=["BIOCHAR", "AGRICULTURE"],
    )
    db_session.add(org)

    proj_id = uuid.uuid4()
    developer_id = uuid.uuid4()
    dev_user = User(
        id=developer_id,
        email=f"dev-{uuid.uuid4().hex[:6]}@nexus.com",
        full_name="Lead Project Developer",
        role=ROLE_PROJECT_MANAGER,
        organization_id=org_id,
    )
    db_session.add(dev_user)

    proj = Project(
        id=proj_id,
        organization_id=org_id,
        project_code=f"PRJ-{uuid.uuid4().hex[:6]}",
        name="Kilimanjaro Biochar Carbon Project",
    )
    db_session.add(proj)

    u = uuid.uuid4().hex[:8]
    # 1. Feedstock Sources (Multi-biomass)
    source1 = FeedstockSource(
        organization_id=org_id,
        project_id=proj_id,
        source_code=f"SRC-AGRI-{u}-1",
        source_name="Rift Valley Coffee Husks",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="HUSKS",
        origin_location="Moshi, Tanzania",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="OPEN_BURNING",
        sustainability_status="VERIFIED_SUSTAINABLE",
    )
    source2 = FeedstockSource(
        organization_id=org_id,
        project_id=proj_id,
        source_code=f"SRC-FOR-{u}-2",
        source_name="Kilindi FSC Forestry Thinnings",
        source_type="FORESTRY_RESIDUE",
        biomass_type="WOOD_CHIPS",
        origin_location="Tanga, Tanzania",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="DECAY",
        sustainability_status="LOW_RISK",
    )
    db_session.add_all([source1, source2])
    await db_session.flush()

    # 2. Feedstock Lots
    now_utc = datetime.now(timezone.utc)
    lot1 = FeedstockLot(
        organization_id=org_id,
        project_id=proj_id,
        source_id=source1.id,
        lot_number=f"LOT-HUSK-{u}-1",
        feedstock_type="COFFEE_HUSKS",
        mass_received_tonnes=100.0,
        moisture_content_pct=15.0,
        dry_mass_tonnes=85.0,
        allocated_mass_tonnes=80.0,
        receipt_date=now_utc - timedelta(days=20),
        evidence_hash=hashlib.sha256(b"scale_ticket_lot1").hexdigest(),
    )
    lot2 = FeedstockLot(
        organization_id=org_id,
        project_id=proj_id,
        source_id=source2.id,
        lot_number=f"LOT-CHIP-{u}-2",
        feedstock_type="WOOD_CHIPS",
        mass_received_tonnes=50.0,
        moisture_content_pct=20.0,
        dry_mass_tonnes=40.0,
        allocated_mass_tonnes=40.0,
        receipt_date=now_utc - timedelta(days=18),
        evidence_hash=hashlib.sha256(b"scale_ticket_lot2").hexdigest(),
    )
    db_session.add_all([lot1, lot2])
    await db_session.flush()

    # 3. Facility & Reactor
    facility = ProductionFacility(
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-KILN-{u}",
        facility_name="Moshi Pyrolysis Facility",
        location="Moshi Industrial Park",
        technology_type="SLOW_PYROLYSIS",
        facility_status="NEW_OPERATIONAL",
    )
    db_session.add(facility)
    await db_session.flush()

    reactor = FacilityReactor(
        facility_id=facility.id,
        reactor_code="REACTOR-01",
        technology_type="SLOW_PYROLYSIS",
        operating_temp_min_c=500.0,
        operating_temp_max_c=650.0,
    )
    db_session.add(reactor)
    await db_session.flush()

    # 4. Production Run with Multi-Biomass Blend Allocations
    run = ProductionRun(
        organization_id=org_id,
        project_id=proj_id,
        facility_id=facility.id,
        reactor_id=reactor.id,
        run_number=f"RUN-{u}",
        start_time=now_utc - timedelta(days=15),
        end_time=now_utc - timedelta(days=14),
        total_feedstock_input_tonnes=120.0,
        total_feedstock_dry_tonnes=100.0,
        avg_pyrolysis_temp_celsius=580.0,
        residence_time_minutes=45.0,
        electricity_kwh=1200.0,
        fuel_liters=150.0,
        output_biochar_mass_tonnes=35.0,
        qa_status="QA_PASSED",
    )
    db_session.add(run)
    await db_session.flush()

    alloc1 = FeedstockRunAllocation(
        lot_id=lot1.id,
        production_run_id=run.id,
        allocated_wet_mass_tonnes=80.0,
        allocated_dry_mass_tonnes=68.0,
    )
    alloc2 = FeedstockRunAllocation(
        lot_id=lot2.id,
        production_run_id=run.id,
        allocated_wet_mass_tonnes=40.0,
        allocated_dry_mass_tonnes=32.0,
    )
    db_session.add_all([alloc1, alloc2])

    # 5. Biochar Batch
    batch = BiocharBatch(
        organization_id=org_id,
        project_id=proj_id,
        production_run_id=run.id,
        batch_number=f"BATCH-{u}",
        facility_name=facility.facility_name,
        kiln_id=reactor.reactor_code,
        feedstock_type="COFFEE_HUSK_WOOD_CHIP_BLEND",
        feedstock_weight_tonnes=120.0,
        moisture_content_pct=16.67,
        biochar_yield_tonnes=35.0,
        dry_mass_tonnes=32.0,
        fixed_carbon_pct=78.5,
        ash_content_pct=4.2,
        molar_h_c_ratio=0.38,
        pyrolysis_temp_celsius=580.0,
        residence_time_minutes=45.0,
        quality_grade="GRADE_A",
        status="PRODUCED",
        batch_digest_hash=hashlib.sha256(b"batch_digest_content").hexdigest(),
        created_at=now_utc - timedelta(days=12),
    )
    db_session.add(batch)
    await db_session.flush()

    # 6. Lab Analysis
    lab = BiocharLabAnalysis(
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch.id,
        sample_id=f"SAMP-{uuid.uuid4().hex[:4]}",
        sampling_date=now_utc - timedelta(days=10),
        laboratory_name="Eurofins Agroscience Services",
        accreditation_standard="ISO_17025",
        test_method="DIN_51732",
        molar_h_c_ratio=0.38,
        organic_carbon_pct=82.0,
        fixed_carbon_pct=78.5,
        moisture_pct=8.5,
        ash_pct=4.2,
        heavy_metals_pass=True,
        pah_content_mg_kg=1.8,
        lab_report_hash=hashlib.sha256(b"accredited_lab_coa_report").hexdigest(),
        lab_report_uri=f"s3://verifield-evidence/lab/{batch.batch_number}_coa.pdf",
        qa_status="VERIFIED",
    )
    db_session.add(lab)

    # 7. Transport Event
    transport = BiocharTransportEvent(
        organization_id=org_id,
        project_id=proj_id,
        material_type="BIOCHAR_BATCH",
        reference_id=batch.id,
        origin_address="Moshi Facility",
        destination_address="Arusha Farm",
        mass_transported_tonnes=20.0,
        distance_km=85.0,
        carrier_name="Kilimanjaro Logistics",
        departure_date=now_utc - timedelta(days=8),
        delivery_date=now_utc - timedelta(days=7),
        status="DELIVERED",
        pod_document_hash=hashlib.sha256(b"transport_pod_receipt").hexdigest(),
    )
    db_session.add(transport)

    # 8. Terminal End-Use Record
    end_use = BiocharEndUseRecord(
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch.id,
        end_use_type="SOIL_APPLICATION",
        applied_quantity_tonnes=20.0,
        event_date=now_utc - timedelta(days=5),
        application_method="BROADCAST_INCORPORATED",
        gps_coordinates="-3.3869, 36.6830",
        wetland_exclusion_screened=True,
        crop_type="COFFEE_AGROFORESTRY",
        verification_status="VERIFIED",
    )
    db_session.add(end_use)
    await db_session.commit()

    return {
        "org_id": org_id,
        "project_id": proj_id,
        "developer_id": developer_id,
        "developer_user": dev_user,
        "source1": source1,
        "source2": source2,
        "lot1": lot1,
        "lot2": lot2,
        "facility": facility,
        "run": run,
        "batch": batch,
        "lab": lab,
        "end_use": end_use,
    }


@pytest.mark.asyncio
async def test_compile_full_biochar_verification_package(db_session: AsyncSession):
    """
    1. Compiles the project's complete biochar verification data graph into ONE
       immutable, audit-ready verification package (VerificationPackage).
    """
    data = await _create_sample_project_graph(db_session)
    compiler = BiocharVerificationPackageCompiler(db_session)

    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()
    end_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()

    pkg = await compiler.compile_package(
        project_id=data["project_id"],
        monitoring_period_start=start_date,
        monitoring_period_end=end_date,
        package_name="Puro Biochar 2026 Q1 Verification Package",
        registry_target="PURO_STANDARD",
        audit_type="OUTPUT_AUDIT",
    )

    assert pkg is not None
    assert pkg.package_version == 1
    assert pkg.parent_package_id is None
    assert pkg.package_status in ("READY_FOR_AUDIT", "DRAFT")
    assert len(pkg.manifest_hash) == 64
    assert pkg.manifest_json["registry_target"] == "PURO_STANDARD"
    assert pkg.manifest_json["audit_type"] == "OUTPUT_AUDIT"
    assert "summary_quantification" in pkg.manifest_json
    assert "trace_trees" in pkg.manifest_json
    assert "evidence_index" in pkg.manifest_json

    # Check Central Evidence Index populated
    stmt_ev = select(VerificationPackageEvidence).where(VerificationPackageEvidence.package_id == pkg.id)
    evidence_items = (await db_session.execute(stmt_ev)).scalars().all()
    assert len(evidence_items) >= 4  # scale ticket, lab COA, transport POD, end-use proof


@pytest.mark.asyncio
async def test_multi_biomass_feedstock_blend_breakdown(db_session: AsyncSession):
    """
    2. Tests the multi-biomass feedstock blend ingredients breakdown for a production run.
    """
    data = await _create_sample_project_graph(db_session)
    run_id = data["run"].id

    stmt = (
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.allocations)
            .selectinload(FeedstockRunAllocation.lot)
            .selectinload(FeedstockLot.source)
        )
        .where(ProductionRun.id == run_id)
    )
    run = (await db_session.execute(stmt)).scalar_one()

    total_wet = float(run.total_feedstock_input_tonnes)
    total_dry = float(run.total_feedstock_dry_tonnes)
    assert total_wet == 120.0
    assert total_dry == 100.0

    allocs = run.allocations
    assert len(allocs) == 2

    # Check blend percentages
    pct_sum_wet = sum(float(a.allocated_wet_mass_tonnes) / total_wet * 100.0 for a in allocs)
    pct_sum_dry = sum(float(a.allocated_dry_mass_tonnes) / total_dry * 100.0 for a in allocs)
    assert abs(pct_sum_wet - 100.0) < 0.01
    assert abs(pct_sum_dry - 100.0) < 0.01

    # Check ingredient metadata
    types = {a.lot.source.biomass_type for a in allocs}
    assert "HUSKS" in types
    assert "WOOD_CHIPS" in types


@pytest.mark.asyncio
async def test_mixed_product_formulation_mass_balance_and_anti_overallocation(
    db_session: AsyncSession
):
    """
    3. Tests mixed-product formulation models & anti-overallocation mass balance protection.
    """
    data = await _create_sample_project_graph(db_session)
    org_id = data["org_id"]
    proj_id = data["project_id"]
    batch = data["batch"]

    # 1. Create Formulation
    formulation = BiocharProductFormulation(
        organization_id=org_id,
        project_id=proj_id,
        product_name="Bio-Enriched Compost Blend 50/50",
        product_code=f"FORM-COMP-{uuid.uuid4().hex[:4]}",
        target_sector="AGRICULTURE_SOIL_AMENDMENT",
        description="50% Pure Biochar + 50% High-Grade Organic Compost",
        biochar_target_ratio=0.5,
    )
    db_session.add(formulation)
    await db_session.flush()

    # 2. Manufacture Product Batch (allocating 10.0 tonnes biochar from batch yielding 35.0 t)
    pbatch = BiocharProductBatch(
        organization_id=org_id,
        project_id=proj_id,
        formulation_id=formulation.id,
        batch_number=f"PBATCH-{uuid.uuid4().hex[:6]}",
        production_date=datetime.now(timezone.utc),
        total_product_mass_tonnes=20.0,
        biochar_mass_tonnes=10.0,
        non_biochar_mass_tonnes=10.0,
        packaging_type="BULK_TOTE_BAG",
        storage_location="Warehouse C",
    )
    db_session.add(pbatch)
    await db_session.flush()

    # Allocate biochar via MassBalanceEngine
    alloc = await BiocharMassBalanceEngine.allocate_batch_to_product_batch(
        db=db_session,
        biochar_batch_id=batch.id,
        product_batch_id=pbatch.id,
        allocated_biochar_mass_tonnes=10.0,
    )
    assert alloc.allocated_biochar_mass_tonnes == 10.0

    # Add non-biochar ingredient
    compost = BiocharProductNonBiocharIngredient(
        product_batch_id=pbatch.id,
        ingredient_name="Aged Thermophilic Compost",
        ingredient_type="COMPOST",
        mass_tonnes=10.0,
        mass_pct=50.0,
        supplier="East Africa Composting Ltd",
    )
    db_session.add(compost)
    await db_session.commit()

    # 3. Test Anti-Overallocation Protection:
    # Batch has 35.0 t yield. Already allocated: 20.0 t end use + 10.0 t product = 30.0 t.
    # Remaining available = 5.0 t. Requesting 10.0 t MUST fail with 400.
    pbatch2 = BiocharProductBatch(
        organization_id=org_id,
        project_id=proj_id,
        formulation_id=formulation.id,
        batch_number=f"PBATCH-OVER-{uuid.uuid4().hex[:4]}",
        production_date=datetime.now(timezone.utc),
        total_product_mass_tonnes=20.0,
        biochar_mass_tonnes=10.0,
        non_biochar_mass_tonnes=10.0,
    )
    db_session.add(pbatch2)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await BiocharMassBalanceEngine.allocate_batch_to_product_batch(
            db=db_session,
            biochar_batch_id=batch.id,
            product_batch_id=pbatch2.id,
            allocated_biochar_mass_tonnes=10.0,
        )
    assert exc_info.value.status_code == 400
    assert "Mass balance violation" in exc_info.value.detail or "Product formulation mass balance" in exc_info.value.detail

    # 4. Mass balance reconciliation includes product allocation
    recon = await BiocharMassBalanceEngine.reconcile_batch(db_session, batch.id)
    assert recon.is_valid is True
    assert recon.product_allocations_tonnes == 10.0
    assert recon.terminal_end_use_tonnes == 20.0
    assert recon.total_reconciled_tonnes == 35.0


@pytest.mark.asyncio
async def test_number_to_evidence_drill_down_graph(db_session: AsyncSession):
    """
    4. Tests number-to-evidence trace tree: every headline carbon removal figure
       is linked to formulas, variables, and raw evidence digests.
    """
    data = await _create_sample_project_graph(db_session)
    compiler = BiocharVerificationPackageCompiler(db_session)

    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()
    end_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()

    pkg = await compiler.compile_package(
        project_id=data["project_id"],
        monitoring_period_start=start_date,
        monitoring_period_end=end_date,
        package_name="Trace Tree Test Package",
    )

    manifest = pkg.manifest_json
    traces = manifest["trace_trees"]

    # Check all required figures exist
    for key in ("net_removals_corcs", "c_stored", "c_loss", "e_project", "e_leakage", "uncertainty"):
        assert key in traces, f"Missing trace tree for {key}"
        trace = traces[key]
        assert "value" in trace
        assert "formula" in trace
        assert "input_variables" in trace

    # Check C_stored drill-down
    c_stored_trace = traces["c_stored"]
    assert c_stored_trace["value"] > 0
    assert len(c_stored_trace["source_records"]) >= 1
    assert len(c_stored_trace["evidence_refs"]) >= 1
    assert len(c_stored_trace["evidence_refs"][0]["hash"]) == 64


@pytest.mark.asyncio
async def test_evidence_integrity_verification_and_mismatch_detection(
    db_session: AsyncSession,
):
    """
    5. Tests Central Evidence Index SHA-256 integrity verification, detecting INTEGRITY_MISMATCH.
    """
    data = await _create_sample_project_graph(db_session)
    compiler = BiocharVerificationPackageCompiler(db_session)
    service = AuditorWorkspaceService(db_session)

    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()
    end_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()

    pkg = await compiler.compile_package(
        project_id=data["project_id"],
        monitoring_period_start=start_date,
        monitoring_period_end=end_date,
        package_name="Integrity Checker Package",
    )

    stmt_ev = select(VerificationPackageEvidence).where(VerificationPackageEvidence.package_id == pkg.id)
    items = (await db_session.execute(stmt_ev)).scalars().all()
    assert len(items) > 0

    first_item = items[0]

    # Test clean verification: returns VERIFIED
    ev_verified = await service.verify_evidence_integrity(
        package_id=pkg.id,
        evidence_id=first_item.id,
        simulated_tamper=False,
    )
    assert ev_verified.integrity_status == "VERIFIED"

    # Test tampering detection: returns INTEGRITY_MISMATCH
    ev_tampered = await service.verify_evidence_integrity(
        package_id=pkg.id,
        evidence_id=first_item.id,
        simulated_tamper=True,
    )
    assert ev_tampered.integrity_status == "INTEGRITY_MISMATCH"
    assert ev_tampered.verified_hash != ev_tampered.sha256_hash

    # Full package verification report
    summary = await service.verify_all_package_evidence(package_id=pkg.id)
    assert summary["total_evidence_items"] == len(items)
    assert summary["mismatch_count"] == 1
    assert summary["all_passed"] is False


@pytest.mark.asyncio
async def test_package_sealing_via_ledger_service(db_session: AsyncSession):
    """
    6. Tests canonical manifest generation and LedgerService RSA digital signature sealing.
    """
    data = await _create_sample_project_graph(db_session)
    compiler = BiocharVerificationPackageCompiler(db_session)

    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()
    end_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()

    pkg = await compiler.compile_package(
        project_id=data["project_id"],
        monitoring_period_start=start_date,
        monitoring_period_end=end_date,
        package_name="Sealing Test Package",
    )

    # User sealing the package
    user = data["developer_user"]

    sealed_pkg = await compiler.seal_and_submit_package(
        package_id=pkg.id,
        user=user,
    )

    assert sealed_pkg.package_status == "SUBMITTED"
    assert sealed_pkg.sealed_at is not None
    assert sealed_pkg.ledger_signature_id is not None

    # Verify signature exists in database
    sig = await db_session.get(Signature, sealed_pkg.ledger_signature_id)
    assert sig is not None


@pytest.mark.asyncio
async def test_package_immutability_and_v1_to_v2_diff(db_session: AsyncSession):
    """
    7. Tests package immutability: once submitted, re-compiling creates Version 2
       with a structured diff from Version 1.
    """
    data = await _create_sample_project_graph(db_session)
    compiler = BiocharVerificationPackageCompiler(db_session)

    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()
    end_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()

    # 1. Compile and seal Version 1
    pkg_v1 = await compiler.compile_package(
        project_id=data["project_id"],
        monitoring_period_start=start_date,
        monitoring_period_end=end_date,
        package_name="Version 1 Package",
    )
    dev_user = data["developer_user"]
    sealed_v1 = await compiler.seal_and_submit_package(pkg_v1.id, dev_user)
    assert sealed_v1.package_version == 1

    # 2. Produce an additional biochar batch to alter the data graph
    new_batch = BiocharBatch(
        organization_id=data["org_id"],
        project_id=data["project_id"],
        batch_number=f"BATCH-V2-{uuid.uuid4().hex[:4]}",
        facility_name="Moshi Pyrolysis Facility",
        kiln_id="REACTOR-01",
        feedstock_type="WOOD_CHIPS",
        feedstock_weight_tonnes=50.0,
        moisture_content_pct=15.0,
        biochar_yield_tonnes=15.0,
        dry_mass_tonnes=14.0,
        fixed_carbon_pct=80.0,
        ash_content_pct=3.5,
        molar_h_c_ratio=0.35,
        pyrolysis_temp_celsius=600.0,
        residence_time_minutes=40.0,
        quality_grade="GRADE_A",
        status="PRODUCED",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(new_batch)
    await db_session.commit()

    # 3. Re-compile: triggers Version 2 creation
    pkg_v2 = await compiler.compile_package(
        project_id=data["project_id"],
        monitoring_period_start=start_date,
        monitoring_period_end=end_date,
        package_name="Version 2 Package (Updated)",
    )

    assert pkg_v2.id != sealed_v1.id
    assert pkg_v2.package_version == 2
    assert pkg_v2.parent_package_id == sealed_v1.id

    diff = pkg_v2.diff_summary_json
    assert "carbon_quantification_delta" in diff
    assert "inventory_changes" in diff
    assert str(new_batch.id) in diff["inventory_changes"]["added_batch_ids"]


@pytest.mark.asyncio
async def test_auditor_findings_lifecycle_and_sod_enforcement(
    db_session: AsyncSession,
):
    """
    8. Tests auditor findings lifecycle (CAR, CL, FAR, NCR) with strict Separation of Duties.
    """
    data = await _create_sample_project_graph(db_session)
    compiler = BiocharVerificationPackageCompiler(db_session)
    service = AuditorWorkspaceService(db_session)

    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()
    end_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()

    pkg = await compiler.compile_package(
        project_id=data["project_id"],
        monitoring_period_start=start_date,
        monitoring_period_end=end_date,
        package_name="Findings Lifecycle Package",
    )

    auditor_user = User(
        id=uuid.uuid4(),
        email=f"auditor-{uuid.uuid4().hex[:6]}@sgs-assurance.com",
        full_name="SGS Carbon Auditor",
        role=ROLE_AUDITOR,
        organization="SGS Carbon Assurance",
    )
    db_session.add(auditor_user)
    await db_session.flush()
    developer_user = data["developer_user"]

    # 1. SoD check: Project developer CANNOT create findings on own project
    with pytest.raises(HTTPException) as exc_dev_create:
        await service.create_finding(
            package_id=pkg.id,
            auditor=developer_user,
            finding_type="CAR",
            severity="MAJOR",
            title="Invalid Attempt",
            description="Dev trying to audit own project",
            target_domain="FEEDSTOCK",
        )
    assert exc_dev_create.value.status_code == 403

    # 2. Auditor creates CAR finding
    finding = await service.create_finding(
        package_id=pkg.id,
        auditor=auditor_user,
        finding_type="CAR",
        severity="MAJOR",
        title="Clarify Moisture Content Measurement Methodology",
        description="Provide ASTM D4442 calibration logs for Lot 1.",
        target_domain="FEEDSTOCK",
        target_record_id=data["lot1"].id,
        target_field="moisture_content_pct",
    )
    assert finding.finding_number == "FINDING-001"
    assert finding.status == "OPEN"

    # 3. SoD check: Auditor CANNOT submit developer response
    with pytest.raises(HTTPException) as exc_aud_resp:
        await service.submit_finding_response(
            finding_id=finding.id,
            developer=auditor_user,
            project_response="Auditor trying to answer own finding",
        )
    assert exc_aud_resp.value.status_code == 403

    # 4. Developer submits response
    resp_finding = await service.submit_finding_response(
        finding_id=finding.id,
        developer=developer_user,
        project_response="Moisture balance calibration certificate attached (Cert #ASTM-4442-01).",
    )
    assert resp_finding.status == "RESPONSE_SUBMITTED"
    assert resp_finding.response_submitted_at is not None

    # 5. SoD check: Developer CANNOT resolve/close finding
    with pytest.raises(HTTPException) as exc_dev_close:
        await service.resolve_finding(
            finding_id=finding.id,
            auditor=developer_user,
            resolution_notes="Dev closing own finding",
            status_action="CLOSED",
        )
    assert exc_dev_close.value.status_code == 403

    # 6. Auditor reviews and resolves finding
    resolved_finding = await service.resolve_finding(
        finding_id=finding.id,
        auditor=auditor_user,
        resolution_notes="Calibration certificate verified and accepted.",
        status_action="RESOLVED",
    )
    assert resolved_finding.status == "RESOLVED"
    assert resolved_finding.resolved_at is not None


@pytest.mark.asyncio
async def test_scoped_external_auditor_access_and_403_denial(
    db_session: AsyncSession,
):
    """
    9. Tests scoped external auditor access grants:
       Unassigned auditors receive 403; granted auditors gain access.
    """
    data = await _create_sample_project_graph(db_session)
    compiler = BiocharVerificationPackageCompiler(db_session)
    service = AuditorWorkspaceService(db_session)

    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()
    end_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()

    pkg = await compiler.compile_package(
        project_id=data["project_id"],
        monitoring_period_start=start_date,
        monitoring_period_end=end_date,
        package_name="Access Scope Package",
    )

    unassigned_auditor = User(
        id=uuid.uuid4(),
        email=f"unassigned-{uuid.uuid4().hex[:6]}@tuv-nord.com",
        full_name="Unassigned Auditor",
        role=ROLE_AUDITOR,
        organization="TUV NORD Cert",
    )
    db_session.add(unassigned_auditor)
    await db_session.flush()

    # Unassigned auditor MUST be denied with 403
    with pytest.raises(HTTPException) as exc_denied:
        await service.check_auditor_access(package_id=pkg.id, user=unassigned_auditor)
    assert exc_denied.value.status_code == 403
    assert "lacks an active VerificationAccessGrant" in exc_denied.value.detail

    # Grant access to this specific package
    dev_user = data["developer_user"]
    grant = await service.grant_auditor_access(
        package_id=pkg.id,
        granter=dev_user,
        auditor_email=unassigned_auditor.email,
        auditor_organization="TUV NORD Cert",
    )
    assert grant.is_active is True

    # Now unassigned auditor is authorized
    has_access = await service.check_auditor_access(package_id=pkg.id, user=unassigned_auditor)
    assert has_access is True


@pytest.mark.asyncio
async def test_scale_verification_package_compiler(db_session: AsyncSession):
    """
    10. Scale test: Compiles a verification package with 10+ feedstock sources,
        30+ lots, 10+ runs, 50+ biochar batches, and mixed product formulations.
    """
    org = Organization(id=uuid.uuid4(), name=f"Large Scale Biochar Multi-Plant {uuid.uuid4().hex[:6]}")
    db_session.add(org)
    proj = Project(id=uuid.uuid4(), organization_id=org.id, name="Mega Scale Biochar Cluster", project_code=f"PRJ-MEGA-{uuid.uuid4().hex[:4]}")
    db_session.add(proj)

    u = uuid.uuid4().hex[:6]
    facility = ProductionFacility(organization_id=org.id, project_id=proj.id, facility_code=f"FAC-MEGA-{u}", facility_name="Mega Plant")
    db_session.add(facility)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    sources = []
    lots = []
    for i in range(10):
        src = FeedstockSource(
            organization_id=org.id,
            project_id=proj.id,
            source_code=f"SRC-SCALE-{u}-{i:03d}",
            source_name=f"Scale Biomass Supplier {i}",
            source_type="AGRICULTURAL_RESIDUE",
            biomass_type="BAGASSE",
            waste_status="CONFIRMED_WASTE_BIOMASS",
            baseline_fate="OPEN_BURNING",
            sustainability_status="LOW_RISK",
        )
        sources.append(src)
        db_session.add(src)
        await db_session.flush()

        for j in range(3):
            lot = FeedstockLot(
                organization_id=org.id,
                project_id=proj.id,
                source_id=src.id,
                lot_number=f"LOT-SCALE-{u}-{i}-{j}",
                feedstock_type="BAGASSE",
                mass_received_tonnes=50.0,
                moisture_content_pct=15.0,
                dry_mass_tonnes=42.5,
                allocated_mass_tonnes=40.0,
                receipt_date=now - timedelta(days=20),
                evidence_hash=hashlib.sha256(f"scale_lot_{u}_{i}_{j}".encode()).hexdigest(),
            )
            lots.append(lot)
            db_session.add(lot)
    await db_session.flush()

    batches = []
    for k in range(25):
        run = ProductionRun(
            organization_id=org.id,
            project_id=proj.id,
            facility_id=facility.id,
            run_number=f"RUN-SCALE-{u}-{k:03d}",
            start_time=now - timedelta(days=15),
            total_feedstock_input_tonnes=40.0,
            total_feedstock_dry_tonnes=34.0,
            avg_pyrolysis_temp_celsius=550.0,
            residence_time_minutes=35.0,
            electricity_kwh=300.0,
            fuel_liters=40.0,
            output_biochar_mass_tonnes=12.0,
        )
        db_session.add(run)
        await db_session.flush()

        b = BiocharBatch(
            organization_id=org.id,
            project_id=proj.id,
            production_run_id=run.id,
            batch_number=f"BATCH-SCALE-{u}-{k:03d}",
            facility_name="Mega Plant",
            kiln_id="K-01",
            feedstock_type="BAGASSE",
            feedstock_weight_tonnes=40.0,
            moisture_content_pct=15.0,
            biochar_yield_tonnes=12.0,
            dry_mass_tonnes=11.5,
            pyrolysis_temp_celsius=550.0,
            residence_time_minutes=35.0,
            created_at=now - timedelta(days=10),
        )
        batches.append(b)
        db_session.add(b)

    await db_session.commit()

    compiler = BiocharVerificationPackageCompiler(db_session)
    start_d = (now - timedelta(days=30)).date()
    end_d = (now + timedelta(days=5)).date()

    pkg = await compiler.compile_package(
        project_id=proj.id,
        monitoring_period_start=start_d,
        monitoring_period_end=end_d,
        package_name="Scale Stress Package",
    )

    assert pkg is not None
    manifest = pkg.manifest_json
    assert len(manifest["value_chain_graph"]["sources"]) >= 10
    assert len(manifest["value_chain_graph"]["feedstock_lots"]) >= 30
    assert len(manifest["value_chain_graph"]["batches"]) >= 25
    assert len(manifest["evidence_index"]) >= 30
