"""
=============================================================================
VeriField Nexus — Methodology Mismatch & Family Alignment Integration Test
=============================================================================
Verifies that if a request specifies a methodology from a DIFFERENT sector family
(e.g., HYBRID_ENERGY + AMS-II.G), the DashboardResolver automatically rejects
the cross-sector methodology and resolves the correct methodology for the family.
=============================================================================
"""

import asyncio, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_db, _init_fallback_db
from app.domains.workspaces.services.dashboard_resolver import DashboardResolverService

async def test_mismatch_resolution():
    print("=============================================================================")
    print("Executing Methodology Family Alignment & Cross-Sector Mismatch Test Suite")
    print("=============================================================================\n")

    await _init_fallback_db()
    async for db in get_db():
        resolver = DashboardResolverService(db)

        org_id = uuid.uuid4()
        # Test 1: HYBRID_ENERGY requested with AMS-II.G (Cookstoves methodology)
        res1 = await resolver.resolve_dashboard(organization_id=org_id, workspace_id="hybrid_energy", methodology_id="AMS-II.G")
        assert res1["workspace"]["code"] == "HYBRID_ENERGY"
        assert res1["methodology"]["code"] != "AMS-II.G", f"FAIL: Returned Cookstove methodology AMS-II.G for HYBRID_ENERGY!"
        print(f"✓ Test 1 Passed: HYBRID_ENERGY + AMS-II.G rejected Cookstove methodology, resolved {res1['methodology']['code']}")

        # Test 2: BIOCHAR requested with ACM0002 (Energy methodology)
        res2 = await resolver.resolve_dashboard(organization_id=org_id, workspace_id="biochar", methodology_id="ACM0002")
        assert res2["workspace"]["code"] == "BIOCHAR"
        assert res2["methodology"]["code"] != "ACM0002", f"FAIL: Returned Energy methodology ACM0002 for BIOCHAR!"
        print(f"✓ Test 2 Passed: BIOCHAR + ACM0002 rejected Energy methodology, resolved {res2['methodology']['code']}")

        # Test 3: EV_MOBILITY requested with VM0042 (Biochar methodology)
        res3 = await resolver.resolve_dashboard(organization_id=org_id, workspace_id="ev_mobility", methodology_id="VM0042")
        assert res3["workspace"]["code"] == "EV_MOBILITY"
        assert res3["methodology"]["code"] != "VM0042", f"FAIL: Returned Biochar methodology VM0042 for EV_MOBILITY!"
        print(f"✓ Test 3 Passed: EV_MOBILITY + VM0042 rejected Biochar methodology, resolved {res3['methodology']['code']}")

        # Test 4: COOKSTOVES requested with AMS-III.C (EV methodology)
        res4 = await resolver.resolve_dashboard(organization_id=org_id, workspace_id="cookstoves", methodology_id="AMS-III.C")
        assert res4["workspace"]["code"] == "COOKSTOVES"
        assert res4["methodology"]["code"] != "AMS-III.C", f"FAIL: Returned EV methodology AMS-III.C for COOKSTOVES!"
        print(f"✓ Test 4 Passed: COOKSTOVES + AMS-III.C rejected EV methodology, resolved {res4['methodology']['code']}")

        print("\n=============================================================================")
        print("ALL METHODOLOGY MISMATCH & FAMILY ALIGNMENT TESTS PASSED 100% CLEANLY!")
        print("=============================================================================\n")
        break

if __name__ == "__main__":
    asyncio.run(test_mismatch_resolution())
