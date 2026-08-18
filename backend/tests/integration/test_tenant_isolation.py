"""
=============================================================================
VeriField Nexus — Multi-Tenant Isolation Integration Test
=============================================================================
Verifies that:
1. Organization A (Energy) cannot query or resolve Organization B's (Biochar) projects/assets.
2. DashboardResolver filtering by organization_id isolates telemetry and asset metrics.
=============================================================================
"""

import asyncio, os, sys, uuid
from sqlalchemy import text, select

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_db, _init_fallback_db
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.assets.models import Asset
from app.domains.workspaces.services.dashboard_resolver import DashboardResolverService

import pytest

@pytest.mark.asyncio
async def test_tenant_isolation():

    print("=============================================================================")
    print("Executing Multi-Tenant Isolation Integration Test Suite")
    print("=============================================================================\n")

    await _init_fallback_db()
    async for db in get_db():
        org_a_id = uuid.uuid4()
        org_b_id = uuid.uuid4()

        org_a = Organization(id=org_a_id, name=f"Solar Energy Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER", licensed_sectors=["HYBRID_ENERGY"])
        org_b = Organization(id=org_b_id, name=f"Terra Biochar Inc {uuid.uuid4().hex[:6]}", org_type="DEVELOPER", licensed_sectors=["BIOCHAR"])

        proj_a = Project(id=uuid.uuid4(), name="Energy Project A", organization_id=org_a_id, sector_id=uuid.uuid4())
        proj_b = Project(id=uuid.uuid4(), name="Biochar Project B", organization_id=org_b_id, sector_id=uuid.uuid4())

        asset_a = Asset(id=uuid.uuid4(), name="Solar Inverter 01", organization_id=org_a_id, project_id=proj_a.id, asset_type_id=uuid.uuid4(), status="ACTIVE")
        asset_b = Asset(id=uuid.uuid4(), name="Biochar Kiln 01", organization_id=org_b_id, project_id=proj_b.id, asset_type_id=uuid.uuid4(), status="ACTIVE")

        db.add_all([org_a, org_b, proj_a, proj_b, asset_a, asset_b])
        await db.commit()

        # Test 1: Query Projects for Org A
        res_a_proj = (await db.execute(select(Project).where(Project.organization_id == org_a_id))).scalars().all()
        assert len(res_a_proj) == 1
        assert res_a_proj[0].name == "Energy Project A"
        print("✓ Test 1 Passed: Project query for Org A returned ONLY Org A projects")

        # Test 2: Query Assets for Org B
        res_b_asset = (await db.execute(select(Asset).where(Asset.organization_id == org_b_id))).scalars().all()
        assert len(res_b_asset) == 1
        assert res_b_asset[0].name == "Biochar Kiln 01"
        print("✓ Test 2 Passed: Asset query for Org B returned ONLY Org B assets")

        # Test 3: DashboardResolver metric aggregation for Org A
        resolver = DashboardResolverService(db)
        dash_a = await resolver.resolve_dashboard(organization_id=org_a_id, workspace_id="hybrid_energy", methodology_id="ACM0002")
        assert len(dash_a["assets"]) == 1 and dash_a["assets"][0]["name"] == "Solar Inverter 01", f"Expected Solar Inverter 01 for Org A, got {dash_a['assets']}"

        dash_b = await resolver.resolve_dashboard(organization_id=org_b_id, workspace_id="biochar", methodology_id="VM0042")
        assert len(dash_b["assets"]) == 1 and dash_b["assets"][0]["name"] == "Biochar Kiln 01", f"Expected Biochar Kiln 01 for Org B, got {dash_b['assets']}"
        print("✓ Test 3 Passed: DashboardResolver aggregated metrics separately per organization_id")

        # Cleanup
        await db.execute(text("DELETE FROM assets WHERE organization_id IN (:a, :b)"), {"a": str(org_a_id), "b": str(org_b_id)})
        await db.execute(text("DELETE FROM projects WHERE organization_id IN (:a, :b)"), {"a": str(org_a_id), "b": str(org_b_id)})
        await db.execute(text("DELETE FROM organizations WHERE id IN (:a, :b)"), {"a": str(org_a_id), "b": str(org_b_id)})
        await db.commit()

        print("\n=============================================================================")
        print("ALL MULTI-TENANT ISOLATION TESTS PASSED 100% CLEANLY!")
        print("=============================================================================\n")
        break

if __name__ == "__main__":
    asyncio.run(test_tenant_isolation())
