#!/usr/bin/env python3
"""
=============================================================================
VeriField Nexus — Tenant Data Isolation Live E2E Helper Script
=============================================================================
Creates an isolated fresh organization with ORG_ADMIN role, licensed to
AGRICULTURE_LAND_USE, with:
- 0 projects
- 0 land units
- 0 activities
- 0 devices
- 0 telemetry
- 0 verification tasks
- 0 anomalies

Generates valid JWT tokens for live browser testing and cleans up safely.
=============================================================================
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
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test"

from sqlalchemy import select, delete
from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash


async def setup_fresh_tenant(tag: str = None, role: str = "ORG_ADMIN") -> dict:
    if not tag:
        tag = uuid.uuid4().hex[:8]

    async with async_session_factory() as session:
        # Create fresh Organization
        org = Organization(
            id=uuid.uuid4(),
            name=f"Fresh Agri Tenant {tag}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
            status="ACTIVE",
            max_installations=100,
            max_agents=5,
            api_calls_count=0,
            version=1,
            is_deleted=False,
        )
        session.add(org)
        await session.flush()

        # Create fresh user with specified role
        user = User(
            id=uuid.uuid4(),
            email=f"fresh.{role.lower()}.{tag}@agri-isolated.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name=f"Fresh Agriculture {role} {tag}",
            role=role,
            organization_id=org.id,
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
            "sector": "AGRICULTURE_LAND_USE",
            "tag": tag,
        }


async def cleanup_fresh_tenant(org_id_str: str) -> dict:
    org_id = uuid.UUID(org_id_str)
    async with async_session_factory() as session:
        await session.execute(delete(User).where(User.organization_id == org_id))
        await session.execute(delete(Organization).where(Organization.id == org_id))
        await session.commit()
    return {"status": "cleaned", "organization_id": org_id_str}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: script.py [setup|cleanup] [tag|org_id] [role]"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "setup":
        tag = sys.argv[2] if len(sys.argv) > 2 else None
        role = sys.argv[3] if len(sys.argv) > 3 else "ORG_ADMIN"
        result = asyncio.run(setup_fresh_tenant(tag, role=role))
        print(json.dumps(result))
    elif cmd == "cleanup":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Must provide org_id to cleanup"}))
            sys.exit(1)
        org_id = sys.argv[2]
        result = asyncio.run(cleanup_fresh_tenant(org_id))
        print(json.dumps(result))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)
