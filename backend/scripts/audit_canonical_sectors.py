"""
VeriField Nexus — Primary Operating Sector Audit & Migration Script
Audits organizations, projects, access_requests, and methodology_families
against the canonical 5 operating sectors:
1. COOKSTOVES -> Clean Cookstoves
2. HYBRID_ENERGY -> Hybrid Energy & Mini-grids
3. BIOCHAR -> Biochar Carbon Removal
4. EV_MOBILITY -> EV Mobility
5. AGRICULTURE_LAND_USE -> Agriculture & Land Use
"""

import sys
import os
import json
import uuid
import asyncio
from typing import Dict, List, Any, Optional

from sqlalchemy import select, text
from app.db.session import async_session_factory
from app.core.sectors import (
    CanonicalSector,
    CANONICAL_SECTOR_CODES,
    CANONICAL_SECTOR_LABELS,
    CANONICAL_SECTOR_UUID_MAP,
    normalize_to_canonical_sector,
)


async def run_audit():
    print("=" * 80)
    print("VERIFIELD NEXUS — PRIMARY OPERATING SECTOR AUDIT REPORT")
    print("=" * 80)

    async with async_session_factory() as session:
        # 1. Methodology Families Audit
        print("\n[1] METHODOLOGY FAMILIES (DATABASE ROWS)")
        res_fams = await session.execute(text("SELECT id, code, name FROM methodology_families ORDER BY code ASC"))
        all_fams = res_fams.fetchall()
        print(f"Total Methodology Family Rows in DB: {len(all_fams)}")

        canonical_fams = []
        test_fams = []
        duplicate_fams = []

        seen_canonical_codes = set()
        for fid, code, name in all_fams:
            str_id = str(fid).lower()
            if code in CANONICAL_SECTOR_CODES:
                canonical_fams.append({"id": str_id, "code": code, "name": name})
                seen_canonical_codes.add(code)
            elif "TEST" in name.upper() or "FAM-" in code.upper():
                test_fams.append({"id": str_id, "code": code, "name": name})
            else:
                duplicate_fams.append({"id": str_id, "code": code, "name": name})

        print(f"  - Canonical Sector Rows: {len(canonical_fams)}")
        for cf in canonical_fams:
            print(f"    * {cf['code']} ({cf['name']}) -> UUID: {cf['id']}")
        print(f"  - Test Fixture Rows (e.g. 'Test Family'): {len(test_fams)}")
        print(f"  - Duplicate / Dynamic Rows (e.g. 'Biochar Removal Family'): {len(duplicate_fams)}")

        # 2. Projects Audit
        print("\n[2] PROJECTS AUDIT (projects.sector_id)")
        res_projs = await session.execute(
            text("SELECT id, name, sector_id FROM projects WHERE sector_id IS NOT NULL")
        )
        projs = res_projs.fetchall()
        print(f"Total Projects with sector_id: {len(projs)}")

        non_canonical_projects = []
        canonical_projects_count = 0
        for pid, pname, sid in projs:
            sid_str = str(sid).lower()
            if sid_str in CANONICAL_SECTOR_UUID_MAP:
                canonical_projects_count += 1
            else:
                non_canonical_projects.append({"id": str(pid), "name": pname, "sector_id": sid_str})

        print(f"  - Canonical Projects: {canonical_projects_count}")
        print(f"  - Non-Canonical Projects: {len(non_canonical_projects)}")
        if non_canonical_projects:
            print("  Listing non-canonical projects:")
            for p in non_canonical_projects[:10]:
                print(f"    * ID: {p['id']}, Name: {p['name']}, sector_id: {p['sector_id']}")

        # 3. Organizations Audit
        print("\n[3] ORGANIZATIONS AUDIT (organizations.licensed_sectors)")
        res_orgs = await session.execute(
            text("SELECT id, name, licensed_sectors FROM organizations WHERE licensed_sectors IS NOT NULL AND jsonb_array_length(licensed_sectors) > 0")
        )
        orgs = res_orgs.fetchall()
        print(f"Total Organizations with licensed_sectors: {len(orgs)}")

        org_audit_rows = []
        for oid, oname, lsecs in orgs:
            is_all_canonical = True
            recommended_mappings = []
            for sec in (lsecs or []):
                norm = normalize_to_canonical_sector(str(sec))
                if norm is None or norm.value != sec:
                    is_all_canonical = False
                    recommended_mappings.append((sec, norm.value if norm else "UNMAPPABLE"))
                else:
                    recommended_mappings.append((sec, sec))

            if not is_all_canonical:
                org_audit_rows.append({
                    "id": str(oid),
                    "name": oname,
                    "current": lsecs,
                    "mappings": recommended_mappings,
                })

        print(f"  - Fully Canonical Organizations: {len(orgs) - len(org_audit_rows)}")
        print(f"  - Organizations with Non-Canonical Sector Entries: {len(org_audit_rows)}")
        if org_audit_rows:
            print("  Detailed Non-Canonical Organizations:")
            print("  " + "-" * 75)
            print(f"  {'Record ID':<36} | {'Current Value':<20} | {'Recommended Mapping':<20}")
            print("  " + "-" * 75)
            for row in org_audit_rows[:15]:
                cur_str = ", ".join(str(x) for x in row["current"])
                rec_str = ", ".join(f"{x[0]}->{x[1]}" for x in row["mappings"])
                print(f"  {row['id']:<36} | {cur_str:<20} | {rec_str:<20}")
            print("  " + "-" * 75)

        # 4. Access Requests Audit
        print("\n[4] ACCESS REQUESTS AUDIT (access_requests.use_case)")
        res_ar = await session.execute(
            text("SELECT id, email, organization_name, use_case, status FROM access_requests")
        )
        ars = res_ar.fetchall()
        print(f"Total Access Requests: {len(ars)}")

        ar_audit_rows = []
        for arid, email, org_name, uc_json, status in ars:
            sid_val = None
            if uc_json:
                try:
                    data = json.loads(uc_json)
                    sid_val = data.get("sector_id")
                except Exception:
                    pass

            if sid_val is not None:
                norm = normalize_to_canonical_sector(str(sid_val))
                if norm is None:
                    ar_audit_rows.append({
                        "id": str(arid),
                        "email": email,
                        "org_name": org_name,
                        "current_sector_id": sid_val,
                        "status": status,
                        "is_canonical": False,
                        "recommended": "NONE",
                        "action": "Flag for manual review",
                    })
                elif norm.value != sid_val:
                    ar_audit_rows.append({
                        "id": str(arid),
                        "email": email,
                        "org_name": org_name,
                        "current_sector_id": sid_val,
                        "status": status,
                        "is_canonical": True,
                        "recommended": norm.value,
                        "action": "Legacy UUID alias maps cleanly to canonical code",
                    })

        print(f"  - Non-Canonical Access Requests: {len([r for r in ar_audit_rows if not r['is_canonical']])}")
        print(f"  - Canonical Aliases (e.g. UUID) Access Requests: {len([r for r in ar_audit_rows if r['is_canonical']])}")
        if ar_audit_rows:
            print("  Sample Access Requests with non-code or aliased sector values:")
            for r in ar_audit_rows[:10]:
                print(f"    * ID: {r['id']}, email: {r['email']}, current: {r['current_sector_id']}, recommended: {r['recommended']}, action: {r['action']}")

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE — NO DESTRUCTIVE DATA MUTATION WAS PERFORMED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_audit())
