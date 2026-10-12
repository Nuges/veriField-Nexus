#!/usr/bin/env python3
"""
VeriField Nexus — Tenant Closure Test Helper Script
===================================================
Provides isolated helper utilities for:
1. Fresh Agriculture tenant provisioning (0 projects, 0 activities, 0 devices).
2. Deepak Farm Admin authentication token retrieval.
3. Other sector tenant provisioning (Biochar, Cookstoves, Hybrid, EV).
4. Safe tenant cleanup.
"""

import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test"

from sqlalchemy import select, delete, func
from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.activities.models import Activity
from app.domains.agriculture.models import LandUnit, SoilSample, AgricultureNetGHGResult
from app.domains.verification.models import VerificationPackage
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash

CANONICAL_DEEPAK_ID = uuid.UUID("5688bb11-a431-4f53-b5da-2064436c3aef")
CANONICAL_DEEPAK_ORG = uuid.UUID("3008978d-3d24-49c4-ac0c-aeed69c59a7f")


async def setup_agri_tenant(tag: str = None) -> dict:
    if not tag:
        tag = uuid.uuid4().hex[:8]

    async with async_session_factory() as session:
        org_id = uuid.uuid4()
        org = Organization(
            id=org_id,
            name=f"Fresh Agri Tenant {tag}",
            status="ACTIVE",
            licensed_sectors=["AGRICULTURE_LAND_USE"],
            licensed_methodologies=[],
        )
        session.add(org)

        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=f"agri_clean_{tag}@example.com",
            full_name=f"Fresh Agri Admin {tag}",
            role="ORG_ADMIN",
            organization=org.name,
            organization_id=org_id,
            password_hash=get_password_hash("CleanAgriPass123!"),
            status="active",
            is_active=True,
            is_deleted=False,
        )
        session.add(user)
        await session.commit()

        token = AuthenticationService.generate_token_static(user)

        # Assert 0 database entities for this tenant
        p_cnt = (await session.execute(select(func.count(Project.id)).filter(Project.organization_id == org_id))).scalar()
        lu_cnt = (await session.execute(select(func.count(LandUnit.id)).filter(LandUnit.organization_id == org_id))).scalar()
        act_cnt = (await session.execute(select(func.count(Activity.id)).filter(Activity.organization_id == org_id))).scalar()
        pkg_cnt = (await session.execute(select(func.count(VerificationPackage.id)).filter(VerificationPackage.organization_id == org_id))).scalar()

        return {
            "organization_id": str(org_id),
            "organization_name": org.name,
            "user_id": str(user_id),
            "email": user.email,
            "role": user.role,
            "token": token,
            "licensed_sectors": ["AGRICULTURE_LAND_USE"],
            "licensed_methodologies": [],
            "tag": tag,
            "counts": {
                "projects": p_cnt,
                "land_units": lu_cnt,
                "activities": act_cnt,
                "verification_packages": pkg_cnt,
            }
        }


async def get_farm_user() -> dict:
    async with async_session_factory() as session:
        farm = (await session.execute(select(User).filter(User.email == "farm@gmail.com"))).scalar_one_or_none()
        if not farm:
            raise RuntimeError("farm@gmail.com does not exist!")

        token = AuthenticationService.generate_token_static(farm)
        return {
            "organization_id": str(farm.organization_id),
            "organization_name": farm.organization,
            "user_id": str(farm.id),
            "email": farm.email,
            "role": farm.role,
            "token": token,
            "licensed_sectors": ["AGRICULTURE_LAND_USE"],
            "licensed_methodologies": ["VM0042"],
        }


async def setup_sector_tenant(sector: str, tag: str = None) -> dict:
    if not tag:
        tag = uuid.uuid4().hex[:8]

    async with async_session_factory() as session:
        org_id = uuid.uuid4()
        org = Organization(
            id=org_id,
            name=f"Empty {sector} Org {tag}",
            status="ACTIVE",
            licensed_sectors=[sector],
            licensed_methodologies=[],
        )
        session.add(org)

        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=f"sector_{sector.lower()}_{tag}@example.com",
            full_name=f"Sector Admin {tag}",
            role="ORG_ADMIN",
            organization=org.name,
            organization_id=org_id,
            password_hash=get_password_hash("SectorPass123!"),
            status="active",
            is_active=True,
            is_deleted=False,
        )
        session.add(user)
        await session.commit()

        token = AuthenticationService.generate_token_static(user)
        return {
            "organization_id": str(org_id),
            "organization_name": org.name,
            "user_id": str(user_id),
            "email": user.email,
            "role": user.role,
            "token": token,
            "licensed_sectors": [sector],
            "licensed_methodologies": [],
            "tag": tag,
        }


async def cleanup_tenant(org_id_str: str) -> None:
    org_id = uuid.UUID(org_id_str)
    if org_id == CANONICAL_DEEPAK_ORG or org_id == CANONICAL_DEEPAK_ID:
        raise RuntimeError("CANNOT CLEANUP CANONICAL DEEPAK FARM!")

    async with async_session_factory() as session:
        await session.execute(delete(Activity).filter(Activity.organization_id == org_id))
        await session.execute(delete(Project).filter(Project.organization_id == org_id))
        await session.execute(delete(User).filter(User.organization_id == org_id))
        await session.execute(delete(Organization).filter(Organization.id == org_id))
        await session.commit()


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_tenant_closure_helper.py [setup_agri|get_farm|setup_sector <SECTOR>|cleanup <org_id>]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "setup_agri":
        res = asyncio.run(setup_agri_tenant())
        print(json.dumps(res))
    elif cmd == "get_farm":
        res = asyncio.run(get_farm_user())
        print(json.dumps(res))
    elif cmd == "setup_sector":
        sector = sys.argv[2]
        res = asyncio.run(setup_sector_tenant(sector))
        print(json.dumps(res))
    elif cmd == "cleanup":
        org_id = sys.argv[2]
        asyncio.run(cleanup_tenant(org_id))
        print(json.dumps({"cleaned": org_id}))


if __name__ == "__main__":
    main()
