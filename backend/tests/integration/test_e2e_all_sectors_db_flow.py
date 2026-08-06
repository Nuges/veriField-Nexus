"""
=============================================================================
VeriField Nexus — Comprehensive All-Sector Database & Resolver Integration Test
=============================================================================
Tests the complete database pipeline for ALL 4 SECTORS:
1. Access Request creation in DB
2. Super Admin approval (approve_access_request)
3. DB Organization & User verification
4. UserResponse schema serialization
5. DashboardResolverService metric & metadata resolution
=============================================================================
"""

import asyncio
import json
import uuid
import sys
import os
from sqlalchemy import text, select

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_db, _init_fallback_db
from app.domains.organizations.routers.access_requests import approve_access_request
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.authentication.schemas import UserResponse
from app.domains.workspaces.services.dashboard_resolver import DashboardResolverService

SECTOR_CONFIGS = [
    {
        "name": "Clean Cookstoves",
        "sector_code": "COOKSTOVES",
        "meth_code": "AMS-II.G",
        "org_name": "Alliance Clean Cooking Org",
        "email": "test_cook@example.com",
        "expected_ws_code": "COOKSTOVES",
        "expected_kpi_label": "TOTAL CO₂ REDUCED"
    },
    {
        "name": "Hybrid Energy & Mini-grids",
        "sector_code": "HYBRID_ENERGY",
        "meth_code": "ACM0002",
        "org_name": "Solar MiniGrid Systems Corp",
        "email": "test_energy@example.com",
        "expected_ws_code": "HYBRID_ENERGY",
        "expected_kpi_label": "TOTAL CO₂ DISPLACED"
    },
    {
        "name": "Biochar Carbon Removal",
        "sector_code": "BIOCHAR",
        "meth_code": "VM0042",
        "org_name": "Terra Biochar Sink Ltd",
        "email": "test_biochar@example.com",
        "expected_ws_code": "BIOCHAR",
        "expected_kpi_label": "CARBON REMOVED"
    },
    {
        "name": "EV Mobility",
        "sector_code": "EV_MOBILITY",
        "meth_code": "AMS-III.C",
        "org_name": "EcoEV Transit Fleet Inc",
        "email": "test_ev@example.com",
        "expected_ws_code": "EV_MOBILITY",
        "expected_kpi_label": "CO₂ DISPLACED"
    }
]

async def test_all_sectors_db_pipeline():
    print("=============================================================================")
    print("Executing All-Sector Database Persistence & Resolver Pipeline Integration Test")
    print("=============================================================================\n")

    await _init_fallback_db()
    async for db in get_db():
        # Get Super Admin user
        admin_res = await db.execute(select(User).where(User.email == 'admin@verifield.io'))
        sa_user = admin_res.scalars().first()
        if not sa_user:
            # Create a mock super admin in test DB if missing
            sa_user = User(
                id=uuid.uuid4(),
                email='admin@verifield.io',
                full_name='Super Admin',
                role='SUPER_ADMIN'
            )
            db.add(sa_user)
            await db.commit()

        resolver = DashboardResolverService(db)

        for cfg in SECTOR_CONFIGS:
            sec_name = cfg["name"]
            sec_code = cfg["sector_code"]
            meth_code = cfg["meth_code"]
            email = cfg["email"]
            org_name = cfg["org_name"]

            print(f"--- TESTING SECTOR: {sec_name} ({sec_code}) ---")

            # 1. Look up sector family and methodology in DB
            sec_res = await db.execute(
                text("SELECT id, code FROM methodology_families WHERE UPPER(code) = UPPER(:c)"),
                {"c": sec_code}
            )
            sec_row = sec_res.fetchone()
            sec_id = str(sec_row[0]) if sec_row else str(uuid.uuid4())

            meth_res = await db.execute(
                text("SELECT id, code FROM methodologies WHERE UPPER(code) = UPPER(:c)"),
                {"c": meth_code}
            )
            meth_row = meth_res.fetchone()
            meth_id = str(meth_row[0]) if meth_row else str(uuid.uuid4())

            # 2. Insert Access Request into DB
            ar_id = str(uuid.uuid4())
            meta = {
                "use_case": f"{sec_name} Project",
                "sector_id": sec_id,
                "methodology_id": meth_id,
                "project_name": f"{org_name} Pilot Project"
            }
            phone = f"+12345{SECTOR_CONFIGS.index(cfg)}"
            await db.execute(
                text("""
                    INSERT INTO access_requests (id, full_name, email, phone, organization_name, country, use_case, status)
                    VALUES (:id, 'Sector Admin', :email, :phone, :org_name, 'Global', :meta, 'PENDING')
                """),
                {"id": ar_id, "email": email, "phone": phone, "org_name": org_name, "meta": json.dumps(meta)}
            )
            await db.commit()

            # 3. Execute Super Admin Approval Flow
            app_res = await approve_access_request(request_id=uuid.UUID(ar_id), current_user=sa_user, db=db)
            org_id = app_res["organization_id"]

            # 4. Verify DB Persistence for Organization & User
            org_db = (await db.execute(select(Organization).where(Organization.id == uuid.UUID(org_id)))).scalar_one()
            user_db = (await db.execute(select(User).where(User.email == email))).scalar_one()

            assert sec_code in org_db.licensed_sectors, f"FAIL: {sec_code} missing from org.licensed_sectors: {org_db.licensed_sectors}"
            print(f"✓ DB Persistence verified: Org licensed_sectors = {org_db.licensed_sectors}")

            # 5. Verify UserResponse Serialization
            user_resp = UserResponse.model_validate(user_db)
            assert sec_code in user_resp.licensed_sectors, f"FAIL: {sec_code} missing from UserResponse: {user_resp.licensed_sectors}"
            assert user_resp.licensed_sectors != ["COOKSTOVES"] or sec_code == "COOKSTOVES", f"FAIL: Defaulted to Cookstoves!"
            print(f"✓ Auth UserResponse verified: licensed_sectors = {user_resp.licensed_sectors}")

            # 6. Verify DashboardResolverService Output
            dash = await resolver.resolve_dashboard(
                organization_id=org_db.id,
                workspace_id=sec_code.lower(),
                methodology_id=meth_code
            )

            resolved_ws_code = dash["workspace"]["code"]
            resolved_ws_name = dash["workspace"]["name"]
            first_kpi_label = dash["kpis"][0]["label"]

            assert resolved_ws_code == cfg["expected_ws_code"], f"FAIL: Expected ws code {cfg['expected_ws_code']}, got {resolved_ws_code}"
            assert first_kpi_label == cfg["expected_kpi_label"], f"FAIL: Expected KPI label {cfg['expected_kpi_label']}, got {first_kpi_label}"
            print(f"✓ DashboardResolver verified: workspace.code = '{resolved_ws_code}' | name = '{resolved_ws_name}' | KPI[0] = '{first_kpi_label}'\n")

            # Cleanup test records
            await db.execute(text("DELETE FROM projects WHERE organization_id = :oid"), {"oid": str(org_id)})
            await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user_db.id)})
            await db.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": str(org_id)})
            await db.execute(text("DELETE FROM access_requests WHERE id = :arid"), {"arid": ar_id})
            await db.commit()

        print("=============================================================================")
        print("ALL 4 SECTORS PASSED DB PERSISTENCE, APPROVAL & DASHBOARD RESOLVER SUITE!")
        print("=============================================================================\n")
        break

if __name__ == "__main__":
    asyncio.run(test_all_sectors_db_pipeline())
