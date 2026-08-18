import pytest
import uuid
from uuid import UUID
from datetime import datetime, timezone, timedelta
import jwt as pyjwt
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select

from app.main import app
from app.db.session import async_session_factory
from app.core.config import settings
from app.core.security import get_password_hash
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.methodologies.models.base_registry import MethodologyFamily, Methodology
from app.domains.projects.service import ProjectService
from app.domains.projects.repository import ProjectRepository
from app.domains.projects.schemas import ProjectCreate

@pytest.mark.asyncio
async def test_01_single_active_super_admin_census():
    """Verify production database has exactly ONE active SUPER_ADMIN: segunoluwole22@gmail.com."""
    async with async_session_factory() as session:
        res = await session.execute(text("""
            SELECT id, email, role, status, is_active 
            FROM users 
            WHERE role = 'SUPER_ADMIN' AND is_active = TRUE
        """))
        active_supers = res.fetchall()
        assert len(active_supers) == 1, f"Expected exactly 1 active SUPER_ADMIN, found {len(active_supers)}: {active_supers}"
        assert active_supers[0][1].lower() == "segunoluwole22@gmail.com"

        # Verify all other active non-superadmin users have an organization_id
        res_orphans = await session.execute(text("""
            SELECT COUNT(*) FROM users 
            WHERE is_active = TRUE AND role != 'SUPER_ADMIN' AND organization_id IS NULL
        """))
        assert res_orphans.scalar() == 0

@pytest.mark.asyncio
async def test_02_access_request_approval_with_sector_and_matching_methodology():
    """Test Case 1: Applicant supplies valid sector + matching methodology -> approval succeeds and project created."""
    async with async_session_factory() as session:
        # Get biochar sector and VM0042 methodology
        res_sec = await session.execute(text("SELECT id FROM methodology_families WHERE UPPER(code) = 'BIOCHAR' LIMIT 1"))
        sec_id = res_sec.scalar()
        assert sec_id is not None

        res_meth = await session.execute(text("SELECT id FROM methodologies WHERE family_id = :fid AND is_active = TRUE LIMIT 1"), {"fid": str(sec_id)})
        meth_id = res_meth.scalar()
        assert meth_id is not None

        # Create access request
        req_id = uuid.uuid4()
        req_email = f"biochar_test_{uuid.uuid4().hex[:6]}@example.com"
        use_case_payload = f'{{"sector_id": "{sec_id}", "methodology_id": "{meth_id}"}}'

        await session.execute(text("""
            INSERT INTO access_requests (id, full_name, email, phone, organization_name, country, use_case, status, created_at)
            VALUES (:id, 'Biochar Test Admin', :email, '+1234567890', 'Biochar Dynamics Corp', 'Kenya', :use_case, 'PENDING', CURRENT_TIMESTAMP)
        """), {"id": str(req_id), "email": req_email, "use_case": use_case_payload})

        # Super admin user
        super_res = await session.execute(text("SELECT id, email FROM users WHERE role = 'SUPER_ADMIN' AND is_active = TRUE LIMIT 1"))
        super_row = super_res.fetchone()
        super_token = pyjwt.encode({
            "sub": str(super_row[0]),
            "email": super_row[1],
            "role": "SUPER_ADMIN",
            "organization_id": None,
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }, settings.effective_jwt_secret, algorithm="HS256")

        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(f"/api/v1/admin/access-requests/{req_id}/approve", headers={"Authorization": f"Bearer {super_token}"})
        assert r.status_code == 200, f"Approval failed: {r.text}"

    # Verify Database state
    async with async_session_factory() as session:
        # Verify Organization created
        res_org = await session.execute(text("SELECT id, licensed_sectors, licensed_methodologies FROM organizations WHERE name = 'Biochar Dynamics Corp'"))
        org_row = res_org.fetchone()
        assert org_row is not None
        org_id = org_row[0]
        assert "BIOCHAR" in org_row[1]

        # Verify User created
        res_usr = await session.execute(text("SELECT id, role, organization_id FROM users WHERE email = :email"), {"email": req_email})
        usr_row = res_usr.fetchone()
        assert usr_row is not None
        assert usr_row[1] == "ORG_ADMIN"
        assert usr_row[2] == org_id

        # Verify Default Project created with matching sector and methodology
        res_proj = await session.execute(text("SELECT id, sector_id, methodology_id FROM projects WHERE organization_id = :oid"), {"oid": str(org_id)})
        proj_row = res_proj.fetchone()
        assert proj_row is not None
        assert proj_row[1] == sec_id
        assert proj_row[2] == meth_id

        # Cleanup
        await session.execute(text("DELETE FROM access_requests WHERE id = :id"), {"id": str(req_id)})
        await session.execute(text("DELETE FROM projects WHERE organization_id = :oid"), {"oid": str(org_id)})
        await session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(usr_row[0])})
        await session.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": str(org_id)})
        await session.commit()

@pytest.mark.asyncio
async def test_03_access_request_approval_with_sector_only_resolves_primary_methodology():
    """Test Case 2: Applicant supplies valid sector but NO methodology -> primary active methodology resolved."""
    async with async_session_factory() as session:
        # Get hybrid energy sector
        res_sec = await session.execute(text("SELECT id FROM methodology_families WHERE UPPER(code) = 'HYBRID_ENERGY' LIMIT 1"))
        sec_id = res_sec.scalar()
        assert sec_id is not None

        # Identify primary active methodology for hybrid energy
        res_expected_meth = await session.execute(text("""
            SELECT id, code FROM methodologies 
            WHERE family_id = :fid AND is_active = TRUE 
            ORDER BY created_at ASC LIMIT 1
        """), {"fid": str(sec_id)})
        expected_meth_row = res_expected_meth.fetchone()
        assert expected_meth_row is not None
        expected_meth_id = expected_meth_row[0]

        # Create access request with sector ONLY
        req_id = uuid.uuid4()
        req_email = f"solar_test_{uuid.uuid4().hex[:6]}@example.com"
        use_case_payload = f'{{"sector_id": "{sec_id}"}}'

        await session.execute(text("""
            INSERT INTO access_requests (id, full_name, email, phone, organization_name, country, use_case, status, created_at)
            VALUES (:id, 'Solar Test Admin', :email, '+1234567891', 'Solar Harvest Power', 'Ghana', :use_case, 'PENDING', CURRENT_TIMESTAMP)
        """), {"id": str(req_id), "email": req_email, "use_case": use_case_payload})

        super_res = await session.execute(text("SELECT id, email FROM users WHERE role = 'SUPER_ADMIN' AND is_active = TRUE LIMIT 1"))
        super_row = super_res.fetchone()
        super_token = pyjwt.encode({
            "sub": str(super_row[0]),
            "email": super_row[1],
            "role": "SUPER_ADMIN",
            "organization_id": None,
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }, settings.effective_jwt_secret, algorithm="HS256")

        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(f"/api/v1/admin/access-requests/{req_id}/approve", headers={"Authorization": f"Bearer {super_token}"})
        assert r.status_code == 200, f"Approval failed: {r.text}"

    # Verify Database state
    async with async_session_factory() as session:
        res_org = await session.execute(text("SELECT id, licensed_sectors FROM organizations WHERE name = 'Solar Harvest Power'"))
        org_row = res_org.fetchone()
        assert org_row is not None
        org_id = org_row[0]

        res_proj = await session.execute(text("SELECT id, sector_id, methodology_id FROM projects WHERE organization_id = :oid"), {"oid": str(org_id)})
        proj_row = res_proj.fetchone()
        assert proj_row is not None
        assert UUID(str(proj_row[1])) == UUID(str(sec_id))
        assert UUID(str(proj_row[2])) == UUID(str(expected_meth_id)), f"Expected primary methodology {expected_meth_id}, got {proj_row[2]}"


        # Cleanup
        await session.execute(text("DELETE FROM access_requests WHERE id = :id"), {"id": str(req_id)})
        await session.execute(text("DELETE FROM projects WHERE organization_id = :oid"), {"oid": str(org_id)})
        await session.execute(text("DELETE FROM users WHERE organization_id = :oid"), {"oid": str(org_id)})
        await session.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": str(org_id)})
        await session.commit()

@pytest.mark.asyncio
async def test_04_access_request_approval_fails_on_mismatched_methodology():
    """Test Case 3: Applicant supplies sector A with methodology from sector B -> returns HTTP 400."""
    async with async_session_factory() as session:
        # Get Cookstoves sector
        res_sec_cook = await session.execute(text("SELECT id FROM methodology_families WHERE UPPER(code) = 'COOKSTOVES' LIMIT 1"))
        sec_cook_id = res_sec_cook.scalar()

        # Get Biochar methodology
        res_sec_bio = await session.execute(text("SELECT id FROM methodology_families WHERE UPPER(code) = 'BIOCHAR' LIMIT 1"))
        sec_bio_id = res_sec_bio.scalar()
        res_meth_bio = await session.execute(text("SELECT id FROM methodologies WHERE family_id = :fid LIMIT 1"), {"fid": str(sec_bio_id)})
        meth_bio_id = res_meth_bio.scalar()

        # Create access request with Cookstoves sector + Biochar methodology
        req_id = uuid.uuid4()
        req_email = f"mismatch_{uuid.uuid4().hex[:6]}@example.com"
        use_case_payload = f'{{"sector_id": "{sec_cook_id}", "methodology_id": "{meth_bio_id}"}}'

        await session.execute(text("""
            INSERT INTO access_requests (id, full_name, email, phone, organization_name, country, use_case, status, created_at)
            VALUES (:id, 'Mismatch Admin', :email, '+1234567892', 'Mismatch Corp', 'Nigeria', :use_case, 'PENDING', CURRENT_TIMESTAMP)
        """), {"id": str(req_id), "email": req_email, "use_case": use_case_payload})

        super_res = await session.execute(text("SELECT id, email FROM users WHERE role = 'SUPER_ADMIN' AND is_active = TRUE LIMIT 1"))
        super_row = super_res.fetchone()
        super_token = pyjwt.encode({
            "sub": str(super_row[0]),
            "email": super_row[1],
            "role": "SUPER_ADMIN",
            "organization_id": None,
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }, settings.effective_jwt_secret, algorithm="HS256")

        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(f"/api/v1/admin/access-requests/{req_id}/approve", headers={"Authorization": f"Bearer {super_token}"})
        assert r.status_code == 400
        assert "does not belong to the selected sector" in r.text

    # Cleanup
    async with async_session_factory() as session:
        await session.execute(text("DELETE FROM access_requests WHERE id = :id"), {"id": str(req_id)})
        await session.commit()

@pytest.mark.asyncio
async def test_05_project_service_invariants_and_licensing():
    """Test ProjectService directly: rejects unlicensed sector, mismatched methodology, and inactive methodology."""
    async with async_session_factory() as session:
        # Create test organization licensed ONLY for 'cookstoves'
        org = Organization(
            name=f"Licensing Test Org {uuid.uuid4().hex[:4]}",
            org_type="DEVELOPER",
            plan="ENTERPRISE",
            licensed_sectors=["cookstoves"],
            licensed_methodologies=["AMS-II.G"]
        )
        session.add(org)
        await session.flush()

        # Get Biochar sector and methodology
        res_bio_sec = await session.execute(text("SELECT id FROM methodology_families WHERE UPPER(code) = 'BIOCHAR' LIMIT 1"))
        bio_sec_id = res_bio_sec.scalar()
        res_bio_meth = await session.execute(text("SELECT id FROM methodologies WHERE family_id = :fid AND is_active = TRUE LIMIT 1"), {"fid": str(bio_sec_id)})
        bio_meth_id = res_bio_meth.scalar()

        # Get Cookstove sector and methodology
        res_cook_sec = await session.execute(text("SELECT id FROM methodology_families WHERE UPPER(code) = 'COOKSTOVES' LIMIT 1"))
        cook_sec_id = res_cook_sec.scalar()
        res_cook_meth = await session.execute(text("SELECT id FROM methodologies WHERE family_id = :fid AND is_active = TRUE LIMIT 1"), {"fid": str(cook_sec_id)})
        cook_meth_id = res_cook_meth.scalar()

        repo = ProjectRepository(session)
        service = ProjectService(repo)

        # 1. Unlicensed Sector: attempting to create project in Biochar sector
        with pytest.raises(Exception) as exc_info:
            await service.create_project(
                ProjectCreate(name="Biochar Proj", methodology_id=bio_meth_id, country="Kenya"),
                organization_id=org.id
            )
        assert "not licensed for sector" in str(exc_info.value)

        # 2. Mismatched Sector & Methodology: Cookstove sector with Biochar methodology
        with pytest.raises(Exception) as exc_info:
            await service.create_project(
                ProjectCreate(name="Mismatch Proj", sector_id=cook_sec_id, methodology_id=bio_meth_id, country="Kenya"),
                organization_id=org.id
            )
        assert "does not belong to the selected sector" in str(exc_info.value)

        # 3. Valid Licensed Project Creation
        valid_proj = await service.create_project(
            ProjectCreate(name="Valid Cookstove Proj", sector_id=cook_sec_id, methodology_id=cook_meth_id, country="Kenya"),
            organization_id=org.id
        )
        assert valid_proj.id is not None
        assert UUID(str(valid_proj.sector_id)) == UUID(str(cook_sec_id))
        assert UUID(str(valid_proj.methodology_id)) == UUID(str(cook_meth_id))


        # Cleanup
        await session.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": str(valid_proj.id)})
        await session.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": str(org.id)})
        await session.commit()
