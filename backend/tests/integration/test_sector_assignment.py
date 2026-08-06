import asyncio
import json
import uuid
from sqlalchemy import text, select
from app.db.session import get_db, _init_fallback_db
from app.domains.organizations.routers.access_requests import approve_access_request
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project

async def test_sector_assignment():
    await _init_fallback_db()
    async for db in get_db():
        # Clean existing test orgs/projects from previous partial runs
        await db.execute(text("DELETE FROM projects WHERE name = 'Metro EV Transit Project'"))
        await db.execute(text("DELETE FROM users WHERE email = 'ev_lead@example.com'"))
        await db.execute(text("DELETE FROM organizations WHERE name = 'EcoEV Mobility Corp'"))
        await db.execute(text("DELETE FROM access_requests WHERE email = 'ev_lead@example.com'"))
        await db.commit()

        # Get Super Admin user
        admin_res = await db.execute(select(User).where(User.email == 'admin@verifield.io'))
        sa_user = admin_res.scalar_one()

        # Get EV_MOBILITY sector
        sec_res = await db.execute(text("SELECT id, code FROM methodology_families WHERE code = 'EV_MOBILITY'"))
        ev_sec = sec_res.fetchone()
        ev_sec_id, ev_sec_code = str(ev_sec[0]), ev_sec[1]

        # Get EV methodology
        meth_res = await db.execute(text("SELECT id, code FROM methodologies WHERE family_id = :fid"), {"fid": ev_sec_id})
        ev_meth = meth_res.fetchone()
        ev_meth_id, ev_meth_code = str(ev_meth[0]), ev_meth[1]

        print(f"\n[1] Submitting Access Request for Sector: {ev_sec_code} (ID: {ev_sec_id}) & Methodology: {ev_meth_code} (ID: {ev_meth_id})...")

        # Create Access Request
        ar_id = str(uuid.uuid4())
        meta = {
            "use_case": "Electric Vehicle Fleet Decarbonization",
            "sector_id": ev_sec_id,
            "methodology_id": ev_meth_id,
            "project_name": "Metro EV Transit Project"
        }
        await db.execute(
            text("""
                INSERT INTO access_requests (id, full_name, email, phone, organization_name, country, use_case, status)
                VALUES (:id, 'EV Transport Lead', 'ev_lead@example.com', '+12345', 'EcoEV Mobility Corp', 'Kenya', :meta, 'PENDING')
            """),
            {"id": ar_id, "meta": json.dumps(meta)}
        )
        await db.commit()

        # Approve Access Request
        res = await approve_access_request(request_id=uuid.UUID(ar_id), current_user=sa_user, db=db)
        print(f"✓ Access Request Approved: Org ID {res['organization_id']}")

        # Verify Organization via ORM
        org_res = await db.execute(select(Organization).where(Organization.id == uuid.UUID(res["organization_id"])))
        org_data = org_res.scalar_one()
        print(f"✓ Provisioned Org -> Name: {org_data.name} | Licensed Sectors: {org_data.licensed_sectors} | Licensed Methodologies: {org_data.licensed_methodologies}")
        assert "EV_MOBILITY" in org_data.licensed_sectors, f"EV_MOBILITY missing from org licensed_sectors: {org_data.licensed_sectors}"

        # Verify Project via ORM
        proj_res = await db.execute(select(Project).where(Project.organization_id == org_data.id))
        proj_data = proj_res.scalar_one()
        print(f"✓ Provisioned Project -> Name: {proj_data.name} | Sector ID: {proj_data.sector_id} | Methodology ID: {proj_data.methodology_id}")
        assert uuid.UUID(str(proj_data.sector_id)) == uuid.UUID(ev_sec_id), f"Project Sector ID {proj_data.sector_id} != Requested Sector ID {ev_sec_id}"
        assert uuid.UUID(str(proj_data.methodology_id)) == uuid.UUID(ev_meth_id), f"Project Methodology ID {proj_data.methodology_id} != Requested Methodology ID {ev_meth_id}"

        print("\n=========================================================")
        print("EMPIRICAL PROOF: Provisioned Sector EXACTLY MATCHES!")
        print("=========================================================\n")

        # Cleanup test records
        await db.execute(text("DELETE FROM projects WHERE organization_id = :oid"), {"oid": str(org_data.id)})
        await db.execute(text("DELETE FROM users WHERE organization_id = :oid"), {"oid": str(org_data.id)})
        await db.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": str(org_data.id)})
        await db.execute(text("DELETE FROM access_requests WHERE id = :arid"), {"arid": ar_id})
        await db.commit()
        print("✓ Clean baseline restored.")
        break

asyncio.run(test_sector_assignment())
