import asyncio
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from fastapi import HTTPException

from app.db.session import _init_fallback_db, _get_fallback_session_factory, get_db
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.methodologies.models.base_registry import MethodologyFamily, Methodology, MethodologyRegistry
from app.domains.projects.service import ProjectService
from app.domains.projects.repository import ProjectRepository
from app.domains.projects.schemas import ProjectCreate

@pytest.mark.asyncio
async def test_sector_role_and_multi_tenant_integrity():
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    async with factory() as db:
        # 1. Fetch or seed Registry
        res_reg = await db.execute(select(MethodologyRegistry).limit(1))
        reg = res_reg.scalar_one_or_none()
        if not reg:
            reg = MethodologyRegistry(
                id=uuid.uuid4(),
                code="VERRA",
                name="Verra Registry",
                is_active=True,
            )
            db.add(reg)
            await db.flush()

        # 2. Fetch or seed Methodology Families (Sectors/Sections)
        res_bio = await db.execute(select(MethodologyFamily).where(MethodologyFamily.code == "BIOCHAR"))
        sec_biochar = res_bio.scalar_one_or_none()
        if not sec_biochar:
            sec_biochar = MethodologyFamily(
                id=uuid.uuid4(),
                code="BIOCHAR",
                name="Biochar Carbon Removal",
                is_active=True,
            )
            db.add(sec_biochar)
            await db.flush()

        res_energy = await db.execute(select(MethodologyFamily).where(MethodologyFamily.code == "HYBRID_ENERGY"))
        sec_energy = res_energy.scalar_one_or_none()
        if not sec_energy:
            sec_energy = MethodologyFamily(
                id=uuid.uuid4(),
                code="HYBRID_ENERGY",
                name="Hybrid Solar & Clean Energy",
                is_active=True,
            )
            db.add(sec_energy)
            await db.flush()

        # 3. Fetch or seed Methodologies
        res_meth1 = await db.execute(select(Methodology).where(Methodology.code == "VM0042"))
        meth_vm0042 = res_meth1.scalar_one_or_none()
        if not meth_vm0042:
            meth_vm0042 = Methodology(
                id=uuid.uuid4(),
                code="VM0042",
                name="Methodology for Improved Agricultural Land Management",
                registry_id=reg.id,
                family_id=sec_biochar.id,
                is_active=True,
            )
            db.add(meth_vm0042)
            await db.flush()

        res_meth2 = await db.execute(select(Methodology).where(Methodology.code == "ACM0002"))
        meth_acm0002 = res_meth2.scalar_one_or_none()
        if not meth_acm0002:
            meth_acm0002 = Methodology(
                id=uuid.uuid4(),
                code="ACM0002",
                name="Grid-connected electricity generation from renewable sources",
                registry_id=reg.id,
                family_id=sec_energy.id,
                is_active=True,
            )
            db.add(meth_acm0002)
            await db.flush()

        # 4. Seed Organizations
        org_biochar_id = uuid.uuid4()
        org_energy_id = uuid.uuid4()

        org_biochar = Organization(
            id=org_biochar_id,
            name=f"Biochar Works {uuid.uuid4().hex[:6]}",
            org_type="DEVELOPER",
            plan="PROFESSIONAL",
            licensed_sectors=["BIOCHAR"],
            licensed_methodologies=["VM0042"],
            status="ACTIVE",
            max_installations=100,
            max_agents=10,
            api_calls_count=0,
            version=1,
            is_deleted=False,
        )
        org_energy = Organization(
            id=org_energy_id,
            name=f"Solar Energy {uuid.uuid4().hex[:6]}",
            org_type="DEVELOPER",
            plan="PROFESSIONAL",
            licensed_sectors=["HYBRID_ENERGY"],
            licensed_methodologies=["ACM0002"],
            status="ACTIVE",
            max_installations=100,
            max_agents=10,
            api_calls_count=0,
            version=1,
            is_deleted=False,
        )
        db.add_all([org_biochar, org_energy])
        await db.flush()

        # 5. Seed Users
        super_admin = User(
            id=uuid.uuid4(),
            email=f"superadmin_{uuid.uuid4().hex[:6]}@verifield.com",
            full_name="Platform Super Admin",
            role="SUPER_ADMIN",
            organization_id=None,
            is_active=True,
            status="active",
        )
        org_admin_biochar = User(
            id=uuid.uuid4(),
            email=f"admin_bio_{uuid.uuid4().hex[:6]}@biocharworks.com",
            full_name="Biochar Admin",
            role="ORG_ADMIN",
            organization_id=org_biochar_id,
            is_active=True,
            status="active",
        )
        org_admin_energy = User(
            id=uuid.uuid4(),
            email=f"admin_sol_{uuid.uuid4().hex[:6]}@solarenergy.com",
            full_name="Solar Admin",
            role="ORG_ADMIN",
            organization_id=org_energy_id,
            is_active=True,
            status="active",
        )
        db.add_all([super_admin, org_admin_biochar, org_admin_energy])
        await db.commit()

        # --- Invariant 1: Sector -> Section -> Methodology Invariant ---
        assert meth_vm0042.family_id == sec_biochar.id
        assert meth_acm0002.family_id == sec_energy.id
        assert meth_vm0042.family_id != sec_energy.id

        # --- Invariant 2: Project Creation Invariant in ProjectService ---
        repo = ProjectRepository(db)
        svc = ProjectService(repo)

        # 2a. Biochar Org creates valid Biochar project (Allowed)
        p1 = await svc.create_project(
            ProjectCreate(
                name="Biochar Project 1",
                methodology_id=meth_vm0042.id,
                country="Kenya",
            ),
            organization_id=org_biochar_id,
        )
        assert p1.organization_id == org_biochar_id
        assert p1.sector_id == sec_biochar.id

        # 2b. Biochar Org attempts to create Hybrid Energy Project (DENIED - 403)
        with pytest.raises(HTTPException) as exc_info:
            await svc.create_project(
                ProjectCreate(
                    name="Illegal Cross-Sector Solar Project",
                    methodology_id=meth_acm0002.id,
                    country="Kenya",
                ),
                organization_id=org_biochar_id,
            )
        assert exc_info.value.status_code == 403
        assert "not licensed for sector HYBRID_ENERGY" in str(exc_info.value.detail)

        # 2c. Solar Org creates valid Solar project (Allowed)
        p2 = await svc.create_project(
            ProjectCreate(
                name="Solar Farm Project 1",
                methodology_id=meth_acm0002.id,
                country="Nigeria",
            ),
            organization_id=org_energy_id,
        )
        assert p2.organization_id == org_energy_id
        assert p2.sector_id == sec_energy.id

        # 2d. Solar Org attempts to create Biochar Project (DENIED - 403)
        with pytest.raises(HTTPException) as exc_info2:
            await svc.create_project(
                ProjectCreate(
                    name="Illegal Cross-Sector Biochar Project",
                    methodology_id=meth_vm0042.id,
                    country="Nigeria",
                ),
                organization_id=org_energy_id,
            )
        assert exc_info2.value.status_code == 403
        assert "not licensed for sector BIOCHAR" in str(exc_info2.value.detail)
