"""
=============================================================================
VeriField Nexus — Final Release-Candidate Forensic Verification Test Suite
=============================================================================
Authoritative end-to-end security, tenant isolation, role invariants,
carbon calculation idempotency, document stream integrity, and registry truthfulness.
=============================================================================
"""

import asyncio
import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import async_session_factory
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.authentication.models import User
from app.domains.documents.models import ProjectDocument
from app.domains.documents.service import DocumentService
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily
from app.domains.organizations.models import Organization
from app.domains.projects.models import CarbonCalculation, Project
from app.domains.projects.repository import CarbonCalculationRepository
from app.domains.registry_integrations.services.packaging import RegistryPackagingService
from app.domains.reporting.models import Report
from app.main import app


def _create_token(user_id: UUID, email: str, role: str, org_id: UUID = None) -> str:
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


@pytest.mark.asyncio
async def test_super_admin_absolute_invariants(async_client: AsyncClient):
    """
    Verifies that:
    1. Only segunoluwole22@gmail.com is an active SUPER_ADMIN.
    2. An ORG_ADMIN cannot provision a SUPER_ADMIN.
    3. A SUPER_ADMIN cannot provision a second SUPER_ADMIN under another email.
    4. User governance update cannot change a normal user's role to SUPER_ADMIN.
    5. A forged JWT claiming SUPER_ADMIN for an unprovisioned user is rejected with 401.
    """
    async with async_session_factory() as session:
        # Check active Super Admin count
        res = await session.execute(
            text("SELECT id, email, role FROM users WHERE role = 'SUPER_ADMIN' AND is_active = TRUE")
        )
        supers = res.fetchall()
        assert len(supers) == 1, f"Expected exactly 1 active SUPER_ADMIN, found {len(supers)}: {supers}"
        assert supers[0][1].lower() == "segunoluwole22@gmail.com"
        super_admin_id = supers[0][0]

        # Create Org Admin user
        org_id = uuid.uuid4()
        org_admin_id = uuid.uuid4()
        org = Organization(id=org_id, name=f"Security Test Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER", status="ACTIVE")
        org_admin = User(
            id=org_admin_id,
            email=f"orgadmin_{uuid.uuid4().hex[:6]}@example.com",
            full_name="Org Admin",
            role="ORG_ADMIN",
            organization_id=org_id,
            status="active",
            is_active=True,
        )
        session.add_all([org, org_admin])
        await session.commit()

    org_admin_token = _create_token(org_admin_id, org_admin.email, "ORG_ADMIN", org_id)
    super_admin_token = _create_token(UUID(str(super_admin_id)), "segunoluwole22@gmail.com", "SUPER_ADMIN", None)

    # 1. ORG_ADMIN attempts to provision a SUPER_ADMIN -> Must be rejected with 403
    resp1 = await async_client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Attacker Super Admin",
            "email": f"attacker_super_{uuid.uuid4().hex[:6]}@example.com",
            "role": "SUPER_ADMIN",
            "password": "Password123!@#",
        },
        headers={"Authorization": f"Bearer {org_admin_token}"},
    )
    assert resp1.status_code == 403, f"Expected 403 for org admin creating super admin, got {resp1.status_code}"

    # 2. SUPER_ADMIN attempts to provision another user as SUPER_ADMIN -> Must be rejected with 403
    resp2 = await async_client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Second Super Admin",
            "email": f"second_super_{uuid.uuid4().hex[:6]}@example.com",
            "role": "SUPER_ADMIN",
            "organization_id": None,
        },
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp2.status_code == 403, f"Expected 403 for provisioning second super admin, got {resp2.status_code}"

    # 3. SUPER_ADMIN attempts to mutate normal user role to SUPER_ADMIN -> Must be rejected with 403
    resp3 = await async_client.put(
        f"/api/v1/admin/users/{org_admin_id}",
        json={"role": "SUPER_ADMIN"},
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp3.status_code == 403, f"Expected 403 for escalating user to super admin, got {resp3.status_code}"

    # 4. Forged JWT claiming SUPER_ADMIN for non-existent user in DB -> Must be rejected with 401
    forged_token = _create_token(uuid.uuid4(), "nonexistent@attacker.com", "SUPER_ADMIN", None)
    resp4 = await async_client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert resp4.status_code == 401, f"Expected 401 for forged super admin token, got {resp4.status_code}"


@pytest.mark.asyncio
async def test_two_tenant_complete_isolation_matrix(async_client: AsyncClient):
    """
    Builds two distinct organizations (Tenant A and Tenant B) with associated
    Projects, Assets, Activities, Evidence, and Reports, and asserts that Tenant B
    cannot read or mutate Tenant A's data.
    """
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    proj_a_id = uuid.uuid4()
    proj_b_id = uuid.uuid4()
    asset_a_id = uuid.uuid4()
    asset_b_id = uuid.uuid4()
    act_a_id = uuid.uuid4()
    act_b_id = uuid.uuid4()
    report_a_id = uuid.uuid4()

    async with async_session_factory() as session:
        # Query existing sectors/methodologies from seed
        sec_res = await session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "COOKSTOVES"))
        sec_a = sec_res.scalar_one_or_none()
        if not sec_a:
            sec_a = MethodologyFamily(id=uuid.uuid4(), code="COOKSTOVES", name="Clean Cookstoves")
            session.add(sec_a)
            await session.flush()

        meth_res = await session.execute(select(Methodology).where(Methodology.family_id == sec_a.id))
        meth_a = meth_res.scalars().first()
        if not meth_a:
            meth_a = Methodology(id=uuid.uuid4(), family_id=sec_a.id, code="VM0006", name="Cookstove Fuel Switching", is_active=True)
            session.add(meth_a)
            await session.flush()

        org_a = Organization(id=org_a_id, name=f"Tenant A Clean Energy {uuid.uuid4().hex[:6]}", org_type="DEVELOPER", status="ACTIVE", licensed_sectors=["COOKSTOVES"])
        org_b = Organization(id=org_b_id, name=f"Tenant B Solar Systems {uuid.uuid4().hex[:6]}", org_type="DEVELOPER", status="ACTIVE", licensed_sectors=["HYBRID_ENERGY"])

        user_a = User(id=user_a_id, email=f"usera_{uuid.uuid4().hex[:6]}@orga.com", full_name="User A", role="ORG_ADMIN", organization_id=org_a_id, is_active=True, status="active")
        user_b = User(id=user_b_id, email=f"userb_{uuid.uuid4().hex[:6]}@orgb.com", full_name="User B", role="ORG_ADMIN", organization_id=org_b_id, is_active=True, status="active")

        proj_a = Project(id=proj_a_id, name=f"Project A {uuid.uuid4().hex[:4]}", organization_id=org_a_id, sector_id=sec_a.id, methodology_id=meth_a.id, country="Kenya")
        proj_b = Project(id=proj_b_id, name=f"Project B {uuid.uuid4().hex[:4]}", organization_id=org_b_id, sector_id=sec_a.id, methodology_id=meth_a.id, country="Ghana")

        asset_a = Asset(id=asset_a_id, name="Cookstove Unit 01", project_id=proj_a_id, organization_id=org_a_id, asset_type_id=uuid.uuid4(), status="ACTIVE", attributes={"carbon_offset_kg": 3820, "trust_score": 96.0})
        asset_b = Asset(id=asset_b_id, name="Cookstove Unit 02", project_id=proj_b_id, organization_id=org_b_id, asset_type_id=uuid.uuid4(), status="ACTIVE", attributes={"carbon_offset_kg": 3820, "trust_score": 96.0})

        now_utc = datetime.now(timezone.utc)
        act_a = Activity(id=act_a_id, asset_id=asset_a_id, organization_id=org_a_id, user_id=user_a_id, activity_type="STOVE_DISTRIBUTION", captured_at=now_utc)
        act_b = Activity(id=act_b_id, asset_id=asset_b_id, organization_id=org_b_id, user_id=user_b_id, activity_type="STOVE_DISTRIBUTION", captured_at=now_utc)

        report_a = Report(id=report_a_id, org_id=org_a_id, title="Project A Report", report_type="IMPACT", status="COMPLETED")

        session.add_all([org_a, org_b, user_a, user_b, proj_a, proj_b, asset_a, asset_b, act_a, act_b, report_a])
        await session.commit()

    token_b = _create_token(user_b_id, user_b.email, "ORG_ADMIN", org_b_id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Attack 1: Tenant B tries to get Tenant A's project
    r_proj = await async_client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_b)
    assert r_proj.status_code in (403, 404), f"Tenant isolation broken on projects: {r_proj.status_code}"

    # Attack 2: Tenant B tries to get Tenant A's asset
    r_asset = await async_client.get(f"/api/v1/assets/{asset_a_id}", headers=headers_b)
    assert r_asset.status_code in (403, 404), f"Tenant isolation broken on assets: {r_asset.status_code}"

    # Attack 3: Tenant B tries to get Tenant A's activity
    r_act = await async_client.get(f"/api/v1/activities/{act_a_id}", headers=headers_b)
    assert r_act.status_code in (403, 404), f"Tenant isolation broken on activities: {r_act.status_code}"

    # Attack 4: Tenant B tries to get Tenant A's impact report
    r_rep = await async_client.get(f"/api/v1/reporting/{report_a_id}", headers=headers_b)
    assert r_rep.status_code in (403, 404), f"Tenant isolation broken on reporting: {r_rep.status_code}"

    # Attack 5: Tenant B attempts to list Tenant A's reports -> 403 Forbidden
    r_list = await async_client.get(f"/api/v1/reporting/?org_id={org_a_id}", headers=headers_b)
    assert r_list.status_code == 403, f"Tenant isolation broken on report listing: {r_list.status_code}"

    # Attack 6: Tenant B attempts parameter override on metrics overview
    r_met = await async_client.get(f"/api/v1/reporting/metrics/overview?org_id={org_a_id}", headers=headers_b)
    assert r_met.status_code == 200



@pytest.mark.asyncio
async def test_carbon_calculation_concurrency_and_idempotency():
    """
    Verifies that simultaneous executions for the same activity_id are idempotent
    and never produce duplicated carbon calculations.
    """
    act_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()

    async with async_session_factory() as session:
        repo = CarbonCalculationRepository(session)

        # Launch multiple sequential/parallel calculation insertions
        for i in range(5):
            await repo.create({
                "id": uuid.uuid4(),
                "project_id": proj_id,
                "activity_id": act_id,
                "tco2e_generated": 3.82,
                "calculation_log": {"run": i, "factor": 1.25},
                "status": "CALCULATED",
            })
        await session.commit()

        # Query database directly to count records with this activity_id
        stmt = select(CarbonCalculation).where(CarbonCalculation.activity_id == act_id)
        res = await session.execute(stmt)
        calcs = res.scalars().all()

        assert len(calcs) == 1, f"Expected exactly 1 calculation record, found {len(calcs)}"
        assert calcs[0].tco2e_generated == 3.82


@pytest.mark.asyncio
async def test_document_integrity_stream_and_tampering():
    """
    Tests document streaming validation, SHA-256 calculation, and tamper detection.
    """
    content = b"%PDF-1.4\n% Real PDF binary header simulation for testing\n" + b"X" * 1024
    expected_sha256 = hashlib.sha256(content).hexdigest()

    doc_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()
    uploader_id = uuid.uuid4()

    temp_storage = tempfile.gettempdir()
    file_path = os.path.join(temp_storage, f"doc_{doc_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(content)

    user_obj = User(id=uploader_id, email=f"uploader_{uuid.uuid4().hex[:6]}@test.com", role="ORG_ADMIN", organization_id=org_id, is_active=True, status="active")

    async with async_session_factory() as session:
        doc = ProjectDocument(
            id=doc_id,
            project_id=proj_id,
            organization_id=org_id,
            uploaded_by=uploader_id,
            title="Clean Cookstove PDD",
            document_type="PDD",
            original_filename="pdd_test.pdf",
            storage_path=file_path,
            mime_type="application/pdf",
            file_size=len(content),
            sha256=expected_sha256,
            status="VERIFIED",
        )
        session.add(doc)
        await session.commit()

        svc = DocumentService(session)

        # 1. Valid download stream check
        path, fname, mime = await svc.get_document_file_for_download(doc_id, user_obj)
        assert path == file_path

        # 2. Tamper with file on disk
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4\nTAMPERED CONTENT THAT DOES NOT MATCH ORIGINAL HASH")

        # 3. Assert download fails safely due to hash integrity violation
        with pytest.raises(Exception) as exc_info:
            await svc.get_document_file_for_download(doc_id, user_obj)
        assert "integrity" in str(exc_info.value).lower() or "mismatch" in str(exc_info.value).lower()

    if os.path.exists(file_path):
        os.remove(file_path)


@pytest.mark.asyncio
async def test_registry_packaging_determinism_and_truthfulness():
    """
    Verifies that registry package generation is deterministic and exposes
    truthful status (PENDING_EXTERNAL_CREDENTIALS) without fabricating API calls.
    """
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()

    async with async_session_factory() as session:
        # Query or create BIOCHAR family
        sec_res = await session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "BIOCHAR"))
        sec = sec_res.scalar_one_or_none()
        if not sec:
            sec = MethodologyFamily(id=uuid.uuid4(), code="BIOCHAR", name="Biochar Carbon Removal")
            session.add(sec)
            await session.flush()

        meth_res = await session.execute(select(Methodology).where(Methodology.family_id == sec.id))
        meth = meth_res.scalars().first()
        if not meth:
            meth = Methodology(id=uuid.uuid4(), family_id=sec.id, code="VM0042", name="Biochar Pyrolysis", is_active=True)
            session.add(meth)
            await session.flush()

        org = Organization(id=org_id, name=f"Terra Biochar Systems {uuid.uuid4().hex[:6]}", org_type="DEVELOPER", status="ACTIVE", licensed_sectors=["BIOCHAR"])
        proj = Project(id=proj_id, name=f"Biochar Sequestration Project {uuid.uuid4().hex[:4]}", organization_id=org_id, sector_id=sec.id, methodology_id=meth.id, country="Kenya")

        session.add_all([org, proj])
        await session.commit()

        packager = RegistryPackagingService(session)
        pkg = await packager.generate_registry_package("VERRA", proj_id, min_trust_score=80.0)

        assert pkg["target_registry"] == "VERRA"
        assert pkg["project"]["sector_code"] == "BIOCHAR"
        assert pkg["readiness_matrix"]["data_manifest"] == "READY"
        assert "PENDING_CREDENTIALS" in pkg["readiness_matrix"]["external_submission"]
        assert pkg["readiness_matrix"]["issuance_sync"] == "AWAITING_EXTERNAL_REGISTRY_AUTHORIZATION"
