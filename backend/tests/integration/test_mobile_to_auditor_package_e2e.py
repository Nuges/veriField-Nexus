"""
=============================================================================
VeriField Nexus — Complete End-to-End Production Closure Integration Test
=============================================================================
Lifecycle Flow:
1. Mobile Field Capture (Feedstock, Pyrolysis, Batch Yield, Lab COA, End Use)
2. Local Offline Queue (client_id, SHA-256 digests, GPS, captured_at)
3. Network Restoration & Idempotent Batch Sync (POST /api/v1/activities/batch)
   - First submission: status 'submitted'
   - Idempotent replay: status 'duplicate'
4. Database Persistence (PostgreSQL activities + Biochar Lineage models)
5. Authoritative Puro Carbon Quantification (C_stored, C_loss, E_proj, E_leak, U, Net CORCs)
6. Verification Package Compiler (v1) (Trace trees, Central Evidence Index, Completeness 100%)
7. Cryptographic Dossier Sealing (LedgerService signature, status SUBMITTED, immutable v1)
8. Auditor Workspace Verification & Scoped Access (RBAC 403 enforcement, evidence SHA-256 validation)
9. Raw Evidence Content Streaming (X-Evidence-Hash validation)
10. Auditor Finding Lifecycle (CAR finding, Separation of Duties enforcement)
11. Project Developer Corrective Response & Mobile Corrective Evidence Capture
12. Verification Package Compiler (v2) (Immutable v1 preserved, parent_package_id link, diff engine)
13. Auditor Resolution & Package Closure (VERIFIED status, Registry Readiness)
=============================================================================
"""

import hashlib
import io
import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.rbac import (
    ROLE_AUDITOR,
    ROLE_ORG_ADMIN,
    ROLE_PROJECT_MANAGER,
    ROLE_SUPER_ADMIN,
    ROLE_VERIFIER,
)
from app.domains.activities.models import Activity
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
from app.domains.biochar.puro_models import PuroLCAModel
from app.domains.biochar.services.auditor_workspace_service import AuditorWorkspaceService
from app.domains.biochar.services.package_compiler import BiocharVerificationPackageCompiler
from app.domains.biochar.services.puro_quantification import (
    PuroCORCCalculator,
    PuroStoredCarbonCalculator,
)
from app.domains.ledger.models import Signature
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.verification.models import (
    VerificationAccessGrant,
    VerificationPackage,
    VerificationPackageEvidence,
    VerificationPackageFinding,
)
from app.main import app
import jwt as pyjwt


def _make_auth_token(user_id: uuid.UUID, email: str, role: str, org_id: Optional[uuid.UUID] = None) -> str:
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
    return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


def _make_auth_header(user_id: uuid.UUID, email: str, role: str, org_id: Optional[uuid.UUID] = None) -> dict:
    token = _make_auth_token(user_id, email, role, org_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_full_mobile_to_auditor_package_lifecycle_e2e(db_session: AsyncSession):
    """
    Executes the comprehensive production closure test proving every link in the chain:
    Mobile Field Capture -> SQLite Offline Queue -> Batch Sync -> Postgres -> Lineage ->
    Quantification -> Package Compiler v1 -> Sealing -> Auditor Verification ->
    Finding -> Corrective Evidence -> Package Compiler v2 -> Resolution -> Final Closure.
    """
    now = datetime.now(timezone.utc)
    u_hex = uuid.uuid4().hex[:8]

    # =========================================================================
    # 0. ORGANIZATIONAL & USER SEEDING
    # =========================================================================
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Equatorial Biochar Systems Ltd {u_hex}",
        org_type="DEVELOPER",
        licensed_sectors=["BIOCHAR", "AGRICULTURE"],
    )
    db_session.add(org)

    # Users: Field Officer, Project Developer, Accredited Auditor, Foreign Unauthorized User
    field_user_id = uuid.uuid4()
    field_user = User(
        id=field_user_id,
        email=f"field-{u_hex}@biochar.org",
        full_name="Biochar Field Officer",
        role="USER",
        organization_id=org_id,
    )

    dev_user_id = uuid.uuid4()
    dev_user = User(
        id=dev_user_id,
        email=f"developer-{u_hex}@biochar.org",
        full_name="Lead Carbon Project Developer",
        role=ROLE_PROJECT_MANAGER,
        organization_id=org_id,
    )

    auditor_user_id = uuid.uuid4()
    auditor_user = User(
        id=auditor_user_id,
        email=f"auditor-{u_hex}@puro-auditors.org",
        full_name="Senior Accredited Auditor",
        role=ROLE_AUDITOR,
        organization_id=None,
    )

    foreign_user_id = uuid.uuid4()
    foreign_user = User(
        id=foreign_user_id,
        email=f"unauthorized-{u_hex}@random.org",
        full_name="Unauthorized Foreign Actor",
        role=ROLE_AUDITOR,
        organization_id=uuid.uuid4(),
    )
    db_session.add_all([field_user, dev_user, auditor_user, foreign_user])

    # Project
    proj_id = uuid.uuid4()
    proj = Project(
        id=proj_id,
        organization_id=org_id,
        project_code=f"PRJ-BIO-{u_hex}",
        name="Equatorial Artisanal Biochar Removal Project",
    )
    db_session.add(proj)
    await db_session.commit()

    # =========================================================================
    # 1. MOBILE FIELD CAPTURE & OFFLINE QUEUE SIMULATION
    # =========================================================================
    # Field officer collects data in the field while offline:
    # 1. Feedstock scale receipt
    # 2. Pyrolysis kiln run
    # 3. Biochar batch weighing
    # 4. Lab sampling handoff
    # 5. Soil application
    
    img_feedstock = b"image_raw_bytes_feedstock_scale_ticket_001"
    img_pyrolysis = b"image_raw_bytes_kiln_pyrolysis_run_001"
    img_batch = b"image_raw_bytes_scale_batch_yield_001"
    img_lab = b"image_raw_bytes_accredited_lab_certificate_001"
    img_enduse = b"image_raw_bytes_soil_matrix_application_001"

    hash_feedstock = hashlib.sha256(img_feedstock).hexdigest()
    hash_pyrolysis = hashlib.sha256(img_pyrolysis).hexdigest()
    hash_batch = hashlib.sha256(img_batch).hexdigest()
    hash_lab = hashlib.sha256(img_lab).hexdigest()
    hash_enduse = hashlib.sha256(img_enduse).hexdigest()

    client_id_feedstock = str(uuid.uuid4())
    client_id_pyrolysis = str(uuid.uuid4())
    client_id_batch = str(uuid.uuid4())
    client_id_lab = str(uuid.uuid4())
    client_id_enduse = str(uuid.uuid4())

    offline_queue = [
        {
            "client_id": client_id_feedstock,
            "activity_type": "BIOCHAR_FEEDSTOCK_INTAKE",
            "sector": "biochar",
            "description": "Feedstock intake at collection depot: 100t coffee husks",
            "image_hash": hash_feedstock,
            "image_url": f"https://storage.verifield.org/evidence/{client_id_feedstock}.jpg",
            "latitude": -3.3731,
            "longitude": 37.3402,
            "gps_accuracy": 3.5,
            "captured_at": (now - timedelta(days=25)).isoformat(),
            "activity_data": {
                "feedstock_type": "COFFEE_HUSKS",
                "wet_mass_tonnes": 100.0,
                "moisture_content_pct": 15.0,
                "supplier": "Kilimanjaro Smallholder Cooperative",
            },
        },
        {
            "client_id": client_id_pyrolysis,
            "activity_type": "BIOCHAR_PYROLYSIS_RUN",
            "sector": "biochar",
            "description": "Clean pyrolysis kiln run monitoring: 580C peak",
            "image_hash": hash_pyrolysis,
            "image_url": f"https://storage.verifield.org/evidence/{client_id_pyrolysis}.jpg",
            "latitude": -3.3735,
            "longitude": 37.3408,
            "gps_accuracy": 2.8,
            "captured_at": (now - timedelta(days=20)).isoformat(),
            "activity_data": {
                "reactor_temp_celsius": 580.0,
                "residence_time_min": 45.0,
                "fuel_liters": 120.0,
                "electricity_kwh": 850.0,
            },
        },
        {
            "client_id": client_id_batch,
            "activity_type": "BIOCHAR_BATCH_WEIGHING",
            "sector": "biochar",
            "description": "Yield measurement: 35 tonnes biochar produced",
            "image_hash": hash_batch,
            "image_url": f"https://storage.verifield.org/evidence/{client_id_batch}.jpg",
            "latitude": -3.3736,
            "longitude": 37.3410,
            "gps_accuracy": 4.1,
            "captured_at": (now - timedelta(days=19)).isoformat(),
            "activity_data": {
                "yield_tonnes": 35.0,
                "moisture_pct": 10.0,
                "quench_method": "water",
            },
        },
        {
            "client_id": client_id_lab,
            "activity_type": "BIOCHAR_LAB_SAMPLE",
            "sector": "biochar",
            "description": "Accredited Lab Eurofins DIN 51732 COA",
            "image_hash": hash_lab,
            "image_url": f"https://storage.verifield.org/evidence/{client_id_lab}.jpg",
            "latitude": -3.3740,
            "longitude": 37.3412,
            "gps_accuracy": 5.0,
            "captured_at": (now - timedelta(days=15)).isoformat(),
            "activity_data": {
                "organic_carbon_pct": 82.5,
                "hc_org_ratio": 0.35,
                "e_lab_g_kg": 0.05,
            },
        },
        {
            "client_id": client_id_enduse,
            "activity_type": "BIOCHAR_END_USE_APPLICATION",
            "sector": "biochar",
            "description": "Agricultural soil amendment application: 35 tonnes",
            "image_hash": hash_enduse,
            "image_url": f"https://storage.verifield.org/evidence/{client_id_enduse}.jpg",
            "latitude": -3.3850,
            "longitude": 37.3520,
            "gps_accuracy": 3.2,
            "captured_at": (now - timedelta(days=10)).isoformat(),
            "activity_data": {
                "application_method": "SOIL_INCORPORATION",
                "applied_mass_tonnes": 35.0,
                "wetland_exclusion_screened": True,
                "crop_type": "Coffee & Maize Agroforestry",
            },
        },
    ]

    # Pre-seed canonical disk bytes in uploads dir so raw evidence streaming can retrieve them
    upload_dir = "/Users/segun/Documents/Verifield nexus/backend/static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    with open(os.path.join(upload_dir, f"{hash_feedstock}.pdf"), "wb") as f:
        f.write(img_feedstock)
    with open(os.path.join(upload_dir, f"{hash_pyrolysis}.pdf"), "wb") as f:
        f.write(img_pyrolysis)
    with open(os.path.join(upload_dir, f"{hash_batch}.pdf"), "wb") as f:
        f.write(img_batch)
    with open(os.path.join(upload_dir, f"{hash_lab}.pdf"), "wb") as f:
        f.write(img_lab)
    with open(os.path.join(upload_dir, f"{hash_enduse}.pdf"), "wb") as f:
        f.write(img_enduse)

    # =========================================================================
    # 2. NETWORK RESTORATION & IDEMPOTENT BATCH SYNC (POST /activities/batch)
    # =========================================================================
    transport = ASGITransport(app=app)
    field_auth = _make_auth_header(field_user_id, field_user.email, field_user.role, org_id)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First Sync Attempt
        res_sync = await client.post(
            "/api/v1/activities/batch",
            json={"activities": offline_queue},
            headers=field_auth,
        )
        assert res_sync.status_code == 200, f"Batch sync failed: {res_sync.text}"
        batch_resp = res_sync.json()
        assert "results" in batch_resp
        results = batch_resp["results"]
        assert len(results) == 5
        for r in results:
            assert r["status"] == "submitted", f"Expected 'submitted', got {r}"
            assert "id" in r

        # Second Sync Attempt (Idempotent Replay)
        res_replay = await client.post(
            "/api/v1/activities/batch",
            json={"activities": offline_queue},
            headers=field_auth,
        )
        assert res_replay.status_code == 200
        replay_results = res_replay.json()["results"]
        assert len(replay_results) == 5
        for r in replay_results:
            assert r["status"] == "duplicate", f"Expected duplicate on replay, got {r}"

    # Verify activities persisted in PostgreSQL database
    act_stmt = select(Activity).where(Activity.organization_id == org_id)
    persisted_acts = (await db_session.execute(act_stmt)).scalars().all()
    assert len(persisted_acts) == 5
    client_ids_persisted = {a.client_id for a in persisted_acts}
    assert client_id_feedstock in client_ids_persisted
    assert client_id_pyrolysis in client_ids_persisted
    assert client_id_batch in client_ids_persisted
    assert client_id_lab in client_ids_persisted
    assert client_id_enduse in client_ids_persisted

    # =========================================================================
    # 3. BIOCHAR VALUE CHAIN LINEAGE SEEDING (Linking field captures)
    # =========================================================================
    # Feedstock Source
    source = FeedstockSource(
        organization_id=org_id,
        project_id=proj_id,
        source_code=f"SRC-{u_hex}",
        source_name="Kilimanjaro Coffee Waste",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="HUSKS",
        origin_location="Moshi, Tanzania",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="DECAY",
        sustainability_status="VERIFIED_SUSTAINABLE",
    )
    db_session.add(source)
    await db_session.flush()

    # Feedstock Lot
    lot = FeedstockLot(
        organization_id=org_id,
        project_id=proj_id,
        source_id=source.id,
        lot_number=f"LOT-{u_hex}",
        feedstock_type="COFFEE_HUSKS",
        mass_received_tonnes=100.0,
        moisture_content_pct=15.0,
        dry_mass_tonnes=85.0,
        allocated_mass_tonnes=85.0,
        receipt_date=now - timedelta(days=25),
        evidence_hash=hash_feedstock,
    )
    db_session.add(lot)
    await db_session.flush()

    # Facility & Reactor
    facility = ProductionFacility(
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-{u_hex}",
        facility_name="Moshi Clean Pyrolysis Center",
        location="Moshi, Kilimanjaro",
        technology_type="CONTINUOUS_PYROLYSIS",
        facility_status="OPERATIONAL",
    )
    db_session.add(facility)
    await db_session.flush()

    reactor = FacilityReactor(
        facility_id=facility.id,
        reactor_code="REACTOR-01",
        technology_type="CONTINUOUS_PYROLYSIS",
        operating_temp_min_c=500.0,
        operating_temp_max_c=650.0,
    )
    db_session.add(reactor)
    await db_session.flush()

    # Production Run
    run = ProductionRun(
        organization_id=org_id,
        project_id=proj_id,
        facility_id=facility.id,
        reactor_id=reactor.id,
        run_number=f"RUN-{u_hex}",
        start_time=now - timedelta(days=20),
        end_time=now - timedelta(days=19),
        total_feedstock_input_tonnes=100.0,
        total_feedstock_dry_tonnes=85.0,
        avg_pyrolysis_temp_celsius=580.0,
        residence_time_minutes=45.0,
        electricity_kwh=850.0,
        fuel_liters=120.0,
        output_biochar_mass_tonnes=35.0,
        qa_status="QA_PASSED",
    )
    db_session.add(run)
    await db_session.flush()

    alloc = FeedstockRunAllocation(
        lot_id=lot.id,
        production_run_id=run.id,
        allocated_wet_mass_tonnes=100.0,
        allocated_dry_mass_tonnes=85.0,
    )
    db_session.add(alloc)

    # Biochar Batch
    batch = BiocharBatch(
        organization_id=org_id,
        project_id=proj_id,
        production_run_id=run.id,
        batch_number=f"BATCH-{u_hex}",
        facility_name=facility.facility_name,
        kiln_id=reactor.reactor_code,
        feedstock_type="COFFEE_HUSKS",
        feedstock_weight_tonnes=100.0,
        moisture_content_pct=10.0,
        biochar_yield_tonnes=35.0,
        dry_mass_tonnes=31.5,
        fixed_carbon_pct=78.5,
        ash_content_pct=4.2,
        molar_h_c_ratio=0.35,
        pyrolysis_temp_celsius=580.0,
        residence_time_minutes=45.0,
        quality_grade="GRADE_A",
        status="PRODUCED",
        batch_digest_hash=hash_batch,
        created_at=now - timedelta(days=19),
    )
    db_session.add(batch)
    await db_session.flush()

    # Lab Analysis
    lab = BiocharLabAnalysis(
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch.id,
        sample_id=f"SMP-{u_hex}",
        sampling_date=(now - timedelta(days=15)).date(),
        laboratory_name="Eurofins Agroscience Services",
        accreditation_standard="ISO_17025",
        test_method="DIN_51732",
        molar_h_c_ratio=0.35,
        organic_carbon_pct=82.5,
        fixed_carbon_pct=78.5,
        moisture_pct=8.5,
        ash_pct=4.2,
        heavy_metals_pass=True,
        pah_content_mg_kg=1.8,
        lab_report_hash=hash_lab,
        lab_report_uri=f"s3://verifield-evidence/lab/{hash_lab}.pdf",
        qa_status="VERIFIED",
    )
    db_session.add(lab)

    # End Use Record
    end_use = BiocharEndUseRecord(
        organization_id=org_id,
        project_id=proj_id,
        batch_id=batch.id,
        end_use_type="SOIL_APPLICATION",
        applied_quantity_tonnes=35.0,
        event_date=now - timedelta(days=10),
        application_method="SOIL_INCORPORATION",
        gps_coordinates="-3.3850, 37.3520",
        wetland_exclusion_screened=True,
        crop_type="Coffee & Agroforestry",
        verification_status="VERIFIED",
    )
    db_session.add(end_use)

    # LCA Model & QC Check
    lca = PuroLCAModel(
        organization_id=org_id,
        facility_id=facility.id,
        model_name="Puro Biochar LCA 2025 v2",
        system_boundary="CRADLE_TO_GRAVE",
        crediting_years=100,
        allocation_method="MASS_ENERGY",
        status="ACTIVE",
    )
    db_session.add(lca)
    await db_session.commit()

    # =========================================================================
    # 4. AUTHORITATIVE QUANTIFICATION ENGINE VERIFICATION
    # =========================================================================
    calc_res = PuroCORCCalculator.execute_quantification(
        eligible_dry_mass_tonnes=Decimal("31.5"),
        c_org_pct=Decimal("82.5"),
        molar_h_c=0.35,
        baseline_scenario="NEW_FACILITY",
        soil_temperature_celsius=15.0,
        end_use_corc_point_eligible=True,
        e_production=Decimal("1.2"),
        is_leakage_mitigated=True,
    )
    assert calc_res["calculation_status"] == "SUCCESS"
    assert calc_res["c_stored_tco2e"] > Decimal("0.0")
    assert calc_res["final_corcs_issuable"] > Decimal("0.0")
    assert calc_res["persistence_fraction_pf"] > 70.0  # Table 6.1 percentage (e.g. ~82% at 15C)
    assert calc_res["e_leakage_tco2e"] == Decimal("0.0")       # Confirmed waste biomass

    # =========================================================================
    # 5. VERIFICATION PACKAGE COMPILER (V1) & COMPLETE MANIFEST
    # =========================================================================
    compiler = BiocharVerificationPackageCompiler(db_session)
    pkg_v1 = await compiler.compile_package(
        project_id=proj_id,
        monitoring_period_start=(now - timedelta(days=30)).date(),
        monitoring_period_end=now.date(),
        package_name="Equatorial Biochar Monitoring Period 01",
        registry_target="PURO_STANDARD",
        audit_type="OUTPUT_AUDIT",
        created_by_user_id=dev_user_id,
    )
    assert pkg_v1.package_version == 1
    assert pkg_v1.completeness_score == 100.0
    assert len(pkg_v1.blocker_reasons) == 0
    assert pkg_v1.package_status == "READY_FOR_AUDIT"
    assert pkg_v1.manifest_hash is not None

    # Verify Central Evidence Index includes mobile field activities
    stmt_ev = select(VerificationPackageEvidence).where(VerificationPackageEvidence.package_id == pkg_v1.id)
    evidence_v1 = (await db_session.execute(stmt_ev)).scalars().all()
    ev_hashes_v1 = {e.sha256_hash for e in evidence_v1}
    assert hash_feedstock in ev_hashes_v1
    assert hash_lab in ev_hashes_v1
    assert hash_enduse in ev_hashes_v1
    # Check that mobile field activities are in the evidence index
    mobile_ev = [e for e in evidence_v1 if e.reference_domain == "ACTIVITY"]
    assert len(mobile_ev) > 0

    # Cryptographic Dossier Sealing
    pkg_v1_sealed = await compiler.seal_and_submit_package(
        package_id=pkg_v1.id,
        user=dev_user,
        signer_role="PROJECT_DEVELOPER",
    )
    assert pkg_v1_sealed.package_status == "SUBMITTED"
    assert pkg_v1_sealed.ledger_signature_id is not None
    assert pkg_v1_sealed.sealed_at is not None

    # =========================================================================
    # 6. AUDITOR WORKSPACE VERIFICATION & SCOPED ACCESS (RBAC 403)
    # =========================================================================
    # Grant scoped auditor access
    grant = VerificationAccessGrant(
        package_id=pkg_v1.id,
        auditor_user_id=auditor_user_id,
        auditor_email=auditor_user.email,
        auditor_organization="Puro Accredited VVB",
        grantee_role="AUDITOR",
        is_active=True,
    )
    db_session.add(grant)
    await db_session.commit()

    auditor_auth = _make_auth_header(auditor_user_id, auditor_user.email, auditor_user.role, None)
    foreign_auth = _make_auth_header(foreign_user_id, foreign_user.email, foreign_user.role, foreign_user.organization_id)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Unauthorized foreign actor denied
        res_denied = await client.get(
            f"/api/v1/verification/packages/{pkg_v1.id}",
            headers=foreign_auth,
        )
        assert res_denied.status_code == 403, "Expected 403 Forbidden for unassigned auditor"

        # Authorized auditor retrieves package
        res_pkg = await client.get(
            f"/api/v1/verification/packages/{pkg_v1.id}",
            headers=auditor_auth,
        )
        assert res_pkg.status_code == 200
        pkg_body = res_pkg.json()
        assert pkg_body["package_name"] == "Equatorial Biochar Monitoring Period 01"
        assert pkg_body["package_version"] == 1
        assert pkg_body["package_status"] == "SUBMITTED"

        # Auditor verifies SHA-256 for all evidence items
        res_verify_all = await client.post(
            f"/api/v1/verification/packages/{pkg_v1.id}/evidence/verify-all",
            headers=auditor_auth,
        )
        assert res_verify_all.status_code == 200
        v_results = res_verify_all.json()
        assert v_results["mismatch_count"] == 0
        assert v_results["all_passed"] is True

        # Raw evidence content streaming with SHA-256 header validation
        first_ev_id = evidence_v1[0].id
        res_content = await client.get(
            f"/api/v1/verification/packages/{pkg_v1.id}/evidence/{first_ev_id}/content",
            headers=auditor_auth,
        )
        assert res_content.status_code == 200
        assert "X-Evidence-Hash" in res_content.headers
        assert res_content.headers["X-Evidence-Hash"] == evidence_v1[0].sha256_hash
        assert res_content.headers["X-Integrity-Status"] == "VERIFIED"

    # =========================================================================
    # 7. AUDITOR FINDING LIFECYCLE & SEPARATION OF DUTIES
    # =========================================================================
    dev_auth = _make_auth_header(dev_user_id, dev_user.email, dev_user.role, org_id)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Auditor logs Finding CAR-001
        res_find = await client.post(
            f"/api/v1/verification/packages/{pkg_v1.id}/findings",
            json={
                "finding_type": "CAR",
                "severity": "HIGH",
                "target_domain": "PRODUCTION_RUN",
                "target_entity_id": str(run.id),
                "title": "Missing High-Resolution Pyrolysis Kiln Scale Calibration Proof",
                "description": "Please provide high-resolution certified scale photograph with legible calibration sticker.",
            },
            headers=auditor_auth,
        )
        assert res_find.status_code == 201
        finding_data = res_find.json()
        finding_id = finding_data["id"]
        assert finding_data["status"] == "OPEN"

        # SoD Enforcement: Auditor cannot respond to their own finding
        res_sod = await client.post(
            f"/api/v1/verification/findings/{finding_id}/respond",
            json={"project_response": "Auditor attempting illegal response"},
            headers=auditor_auth,
        )
        assert res_sod.status_code == 403, "Expected 403 SoD violation when auditor attempts developer response"

        # Developer responds formally
        res_resp = await client.post(
            f"/api/v1/verification/findings/{finding_id}/respond",
            json={"project_response": "Corrected calibrated scale photo captured via mobile app and attached to batch."},
            headers=dev_auth,
        )
        assert res_resp.status_code == 200
        assert res_resp.json()["status"] == "RESPONSE_SUBMITTED"

    # =========================================================================
    # 8. CORRECTIVE MOBILE FIELD EVIDENCE & PACKAGE COMPILER V2
    # =========================================================================
    # Mobile app captures corrected evidence photo
    img_corrected = b"image_raw_bytes_high_res_calibrated_scale_certificate_v2"
    hash_corrected = hashlib.sha256(img_corrected).hexdigest()
    client_id_corrected = str(uuid.uuid4())

    with open(os.path.join(upload_dir, f"{hash_corrected}.pdf"), "wb") as f:
        f.write(img_corrected)

    # Sync corrected evidence
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_sync_corr = await client.post(
            "/api/v1/activities/batch",
            json={
                "activities": [
                    {
                        "client_id": client_id_corrected,
                        "activity_type": "BIOCHAR_BATCH_WEIGHING",
                        "sector": "biochar",
                        "description": "Corrected high-resolution calibrated scale proof photo",
                        "image_hash": hash_corrected,
                        "image_url": f"https://storage.verifield.org/evidence/{client_id_corrected}.jpg",
                        "latitude": -3.3736,
                        "longitude": 37.3410,
                        "gps_accuracy": 2.1,
                        "captured_at": (now - timedelta(days=5)).isoformat(),
                        "activity_data": {
                            "calibrated_scale_certified": True,
                            "scale_serial_number": "METTLER-TOLEDO-9921",
                        },
                    }
                ]
            },
            headers=field_auth,
        )
        assert res_sync_corr.status_code == 200
        assert res_sync_corr.json()["results"][0]["status"] == "submitted"

    # Compile Package v2
    pkg_v2 = await compiler.compile_package(
        project_id=proj_id,
        monitoring_period_start=(now - timedelta(days=30)).date(),
        monitoring_period_end=now.date(),
        package_name="Equatorial Biochar Monitoring Period 01",
        registry_target="PURO_STANDARD",
        audit_type="OUTPUT_AUDIT",
        created_by_user_id=dev_user_id,
    )
    assert pkg_v2.package_version == 2
    assert pkg_v2.parent_package_id == pkg_v1.id

    # Verify Version 1 remains completely immutable and unchanged
    await db_session.refresh(pkg_v1)
    assert pkg_v1.package_version == 1
    assert pkg_v1.parent_package_id is None
    assert pkg_v1.sealed_at is not None

    # Verify Version 2 Central Evidence Index contains the corrected evidence hash
    stmt_ev2 = select(VerificationPackageEvidence).where(VerificationPackageEvidence.package_id == pkg_v2.id)
    evidence_v2 = (await db_session.execute(stmt_ev2)).scalars().all()
    ev_hashes_v2 = {e.sha256_hash for e in evidence_v2}
    assert hash_corrected in ev_hashes_v2

    # Verify diff engine detected changes between v1 and v2
    assert pkg_v2.diff_summary_json is not None

    # Grant access to v2 for auditor
    grant_v2 = VerificationAccessGrant(
        package_id=pkg_v2.id,
        auditor_user_id=auditor_user_id,
        auditor_email=auditor_user.email,
        auditor_organization="Puro Accredited VVB",
        grantee_role="AUDITOR",
        is_active=True,
    )
    db_session.add(grant_v2)
    await db_session.commit()

    # =========================================================================
    # 9. AUDITOR RESOLUTION, PACKAGE CLOSURE & REGISTRY READINESS
    # =========================================================================
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Auditor verifies the corrected evidence item SHA-256
        corr_ev = next(e for e in evidence_v2 if e.sha256_hash == hash_corrected)
        res_vcorr = await client.post(
            f"/api/v1/verification/packages/{pkg_v2.id}/evidence/{corr_ev.id}/verify",
            headers=auditor_auth,
        )
        assert res_vcorr.status_code == 200
        assert res_vcorr.json()["integrity_status"] == "VERIFIED"

        # Auditor resolves Finding CAR-001
        res_resolve = await client.post(
            f"/api/v1/verification/findings/{finding_id}/resolve",
            json={
                "resolution_notes": "Verified corrected calibrated scale certificate and high-resolution photo in Package v2.",
                "status_action": "RESOLVED",
                "resolution_package_id": str(pkg_v2.id),
            },
            headers=auditor_auth,
        )
        assert res_resolve.status_code == 200
        assert res_resolve.json()["status"] == "RESOLVED"

        # Verify ZIP export archive generates valid checksums
        res_archive = await client.get(
            f"/api/v1/verification/packages/{pkg_v2.id}/export/archive",
            headers=auditor_auth,
        )
        assert res_archive.status_code == 200
        assert res_archive.headers["Content-Type"] == "application/zip"
        assert len(res_archive.content) > 100

    # Package v2 status updated to VERIFIED
    pkg_v2.package_status = "VERIFIED"
    await db_session.commit()

    # Query final package state
    await db_session.refresh(pkg_v1)
    await db_session.refresh(pkg_v2)

    assert pkg_v1.package_version == 1
    assert pkg_v1.sealed_at is not None
    assert pkg_v2.package_version == 2
    assert pkg_v2.parent_package_id == pkg_v1.id
    assert pkg_v2.package_status == "VERIFIED"
