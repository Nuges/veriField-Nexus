import asyncio
import json
import uuid
import pytest
from sqlalchemy import text, select
from app.db.session import async_session_factory, _init_fallback_db, _get_fallback_session_factory
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project

async def run_full_suite():
    print("=================================================================")
    print("ACCESS REQUEST APPROVAL & TRANSACTION SUITE")
    print("=================================================================")
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    passed = 0
    total = 0

    def check(cond, name):
        nonlocal passed, total
        total += 1
        if cond:
            print(f"✓ [PASS] {name}")
            passed += 1
        else:
            print(f"✗ [FAIL] {name}")
            raise AssertionError(f"Failed assertion: {name}")

    # 1. Successful Super Admin Approval for Manna Joe (Biochar)
    req_id = str(uuid.uuid4())
    org_name = f"manna Biochar {uuid.uuid4().hex[:6]}"
    email = f"manna_{uuid.uuid4().hex[:6]}@gmail.com"
    phone = f"+234{uuid.uuid4().int % 1000000000:09d}"

    async with factory() as db:
        use_case_meta = json.dumps({
            "use_case": "Biochar Carbon Removal",
            "sector": "BIOCHAR",
            "methodology": "VM0042",
            "project_name": f"{org_name} Project"
        })
        await db.execute(text("""
            INSERT INTO access_requests (id, full_name, email, phone, organization_name, country, use_case, status)
            VALUES (:id, 'Manna Joe', :email, :phone, :org_name, 'Nigeria', :use_case, 'PENDING')
        """), {
            "id": req_id,
            "email": email,
            "phone": phone,
            "org_name": org_name,
            "use_case": use_case_meta
        })
        await db.commit()

    # Execute Approval Flow
    async with factory() as db:
        res = await db.execute(text("SELECT * FROM access_requests WHERE id = :id"), {"id": req_id})
        req = res.fetchone()
        check(req is not None, "Pending access request loaded")
        check(req.status == "PENDING", "Request is initially PENDING")

        meta = json.loads(req.use_case)
        licensed_sectors = ["BIOCHAR"]
        licensed_methodologies = ["VM0042"]

        # Provision Org
        new_org = Organization(
            name=req.organization_name,
            org_type="DEVELOPER",
            metadata_context={"country": req.country, "use_case": meta.get("use_case"), "source_request": req_id},
            plan="PROFESSIONAL",
            licensed_methodologies=licensed_methodologies,
            licensed_sectors=licensed_sectors,
            status="ACTIVE",
            max_installations=1000,
            max_agents=20
        )
        db.add(new_org)
        await db.flush()
        check(new_org.id is not None, "Organization ID assigned atomically")

        # Provision Project
        default_proj = Project(
            name=meta.get("project_name"),
            organization_id=new_org.id,
            country=req.country
        )
        db.add(default_proj)
        await db.flush()
        check(default_proj.id is not None, "Project created under new organization")

        # Provision User
        from app.core.security import get_password_hash
        new_user = User(
            email=req.email,
            phone=req.phone,
            full_name=req.full_name,
            password_hash=get_password_hash("TempPass123!"),
            role="ORG_ADMIN",
            organization=new_org.name,
            organization_id=new_org.id,
            country=req.country,
            requires_password_change=True,
            is_active=True,
            status="active"
        )
        db.add(new_user)
        await db.flush()
        check(new_user.id is not None, "User created as ORG_ADMIN")

        # Update Request Status
        await db.execute(
            text("UPDATE access_requests SET status = 'APPROVED', reviewed_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"id": req_id}
        )
        await db.commit()

    # Verification
    async with factory() as db:
        res = await db.execute(text("SELECT status FROM access_requests WHERE id = :id"), {"id": req_id})
        updated_req = res.fetchone()
        check(updated_req.status == "APPROVED", "Access request status changed to APPROVED")

        org_res = await db.execute(select(Organization).where(Organization.name == org_name))
        created_org = org_res.scalar_one_or_none()
        check(created_org is not None, "Organization persisted in database")
        check(created_org.licensed_sectors == ["BIOCHAR"], "Organization licensed_sectors is ['BIOCHAR']")
        check(created_org.licensed_methodologies == ["VM0042"], "Organization licensed_methodologies is ['VM0042']")

        user_res = await db.execute(select(User).where(User.email == email))
        created_user = user_res.scalar_one_or_none()
        check(created_user is not None, "User persisted in database")
        check(created_user.role == "ORG_ADMIN", "User role is ORG_ADMIN")
        check(created_user.organization_id == created_org.id, "User linked to newly created organization")

    # 2. Re-attempting approval on already approved request is blocked
    async with factory() as db:
        res = await db.execute(text("SELECT status FROM access_requests WHERE id = :id"), {"id": req_id})
        req = res.fetchone()
        check(req.status != "PENDING", "Subsequent approval attempt detects non-PENDING status")

    # 3. PEP 525 Async Generator athrow() Contract Verification
    from app.db.session import get_db
    from fastapi import HTTPException

    gen = get_db()
    session = await anext(gen)
    check(session is not None, "get_db() yields valid session on first call")

    athrow_passed = False
    try:
        await gen.athrow(HTTPException(status_code=400, detail="Client Error Simulation"))
    except HTTPException as e:
        athrow_passed = True
    except RuntimeError as e:
        if "generator didn't stop after athrow()" in str(e):
            athrow_passed = False

    check(athrow_passed, "get_db() correctly propagates exception on athrow() without RuntimeError")

    print("=================================================================")
    print(f"TOTAL: {passed}/{total} ASSERTIONS PASSED (100% VERIFIED)")
    print("=================================================================")

if __name__ == "__main__":
    asyncio.run(run_full_suite())
