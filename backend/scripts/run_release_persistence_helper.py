#!/usr/bin/env python3
"""
=============================================================================
VeriField Nexus — Release Persistence Test Helper Script
=============================================================================
Sets up an isolated test organization with all 5 canonical sectors licensed
and all canonical methodologies permitted for end-to-end browser project creation.
Safely cleans up only its own created projects and organization.
"""

import asyncio
import json
import os
import sys
import uuid

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test"

from sqlalchemy import select, delete
from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash

ALL_SECTORS = [
    "AGRICULTURE_LAND_USE",
    "BIOCHAR",
    "COOKSTOVES",
    "HYBRID_ENERGY",
    "EV_MOBILITY",
]

ALL_METHODOLOGIES = [
    "VM0042", "VM0051", "VM0047", "VM0032",
    "VM0044", "PURO_BIOCHAR_2025", "BIOCHAR_C_SINK",
    "GS_MECD", "VM0050", "AMS_II_G",
    "AMS_I_F", "AMS_I_L", "ACM0002",
    "VM0038", "AMS_III_C"
]

CANONICAL_DEEPAK_ID = uuid.UUID("5688bb11-a431-4f53-b5da-2064436c3aef")


async def setup_test_tenant(tag: str = None) -> dict:
    if not tag:
        tag = uuid.uuid4().hex[:8]

    async with async_session_factory() as session:
        org_id = uuid.uuid4()
        org = Organization(
            id=org_id,
            name=f"Release Persistence Test Org {tag}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
            status="ACTIVE",
            max_installations=100,
            max_agents=10,
            api_calls_count=0,
            version=1,
            is_deleted=False,
            licensed_sectors=ALL_SECTORS,
            licensed_methodologies=ALL_METHODOLOGIES,
        )
        session.add(org)
        await session.flush()

        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=f"release.tester.{tag}@verifield-persistence.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name=f"Release Tester {tag}",
            role="ORG_ADMIN",
            organization_id=org_id,
            is_active=True,
            status="active",
        )
        session.add(user)
        await session.commit()

        token = AuthenticationService.generate_token_static(user)

        return {
            "organization_id": str(org.id),
            "organization_name": org.name,
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "token": token,
            "licensed_sectors": ALL_SECTORS,
            "licensed_methodologies": ALL_METHODOLOGIES,
            "tag": tag,
        }


async def cleanup_test_tenant(org_id_str: str) -> dict:
    org_id = uuid.UUID(org_id_str)
    assert org_id != CANONICAL_DEEPAK_ID, "FATAL SAFETY VIOLATION: Cannot delete Deepak Farm!"

    async with async_session_factory() as session:
        # Delete only projects belonging to this test organization
        await session.execute(
            delete(Project).where(
                Project.organization_id == org_id,
                Project.id != CANONICAL_DEEPAK_ID
            )
        )
        # Delete users and organization
        await session.execute(delete(User).where(User.organization_id == org_id))
        await session.execute(delete(Organization).where(Organization.id == org_id))
        await session.commit()

    return {"status": "cleaned", "organization_id": org_id_str}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: script.py [setup|cleanup] [tag|org_id]"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "setup":
        tag = sys.argv[2] if len(sys.argv) > 2 else None
        res = asyncio.run(setup_test_tenant(tag))
        print(json.dumps(res))
    elif cmd == "cleanup":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Must provide org_id to cleanup"}))
            sys.exit(1)
        res = asyncio.run(cleanup_test_tenant(sys.argv[2]))
        print(json.dumps(res))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)
