import secrets

import string

import uuid

from typing import Optional



from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel

from sqlalchemy import text

from sqlalchemy.ext.asyncio import AsyncSession



from app.core.event_bus import EventBus

from app.core.security import get_current_user

from app.db.session import get_db

from app.domains.authentication.models import User

from app.domains.authentication.repository import UserRepository

from app.domains.authentication.schemas import UserCreate

from app.domains.authentication.service import AuthenticationService

from app.domains.methodologies.services.resolver import MethodologyResolver

from app.domains.notifications.repository import NotificationRepository

from app.domains.notifications.schemas import NotificationCreate

from app.domains.notifications.service import NotificationService

from app.domains.organizations.repository import OrganizationRepository

from app.domains.organizations.schemas import OrganizationCreate

from app.domains.organizations.service import OrganizationService



router = APIRouter(tags=["Access Requests"])



class AccessRequestCreate(BaseModel):

    full_name: str

    email: str

    phone: Optional[str] = None

    organization_name: str

    country: Optional[str] = None

    use_case: Optional[str] = None

    sector_id: Optional[uuid.UUID] = None

    methodology_id: Optional[uuid.UUID] = None

    project_name: Optional[str] = None



@router.post("/access-requests")

async def create_access_request(

    payload: AccessRequestCreate,

    db: AsyncSession = Depends(get_db)

):

    try:

        # Check if email is already in access_requests

        res_ar = await db.execute(

            text("SELECT id FROM access_requests WHERE email = :email AND status IN ('PENDING', 'APPROVED')"),

            {"email": payload.email}

        )

        if res_ar.fetchone():

            raise HTTPException(status_code=400, detail="An access request with this email already exists.")



        # Check if email is already in users table

        res_usr = await db.execute(

            text("SELECT id FROM users WHERE email = :email"),

            {"email": payload.email}

        )

        if res_usr.fetchone():

            raise HTTPException(status_code=400, detail="An account with this email already exists.")



        import json

        metadata = {

            "use_case": payload.use_case,

            "sector_id": str(payload.sector_id) if payload.sector_id else None,

            "methodology_id": str(payload.methodology_id) if payload.methodology_id else None,

            "project_name": payload.project_name

        }



        new_id = str(uuid.uuid4())

        await db.execute(

            text("""

                INSERT INTO access_requests

                (id, full_name, email, phone, organization_name, country, use_case, status)

                VALUES

                (:id, :full_name, :email, :phone, :organization_name, :country, :use_case_json, 'PENDING')

            """),

            {

                "id": new_id,

                "full_name": payload.full_name,

                "email": payload.email,

                "phone": payload.phone,

                "organization_name": payload.organization_name,

                "country": payload.country,

                "use_case_json": json.dumps(metadata)

            }

        )

        await db.commit()

        return {"status": "success", "message": "Access request submitted successfully."}

    except HTTPException:

        await db.rollback()

        raise

    except Exception as e:

        await db.rollback()

        raise HTTPException(status_code=500, detail=str(e))



@router.get("/access-requests")

async def get_access_requests(

    status: Optional[str] = None,

    db: AsyncSession = Depends(get_db)

):

    try:

        query = "SELECT id, full_name, email, phone, organization_name, country, use_case, status, created_at, reviewed_by, reviewed_at FROM access_requests"

        params = {}

        if status:

            query += " WHERE status = :status"

            params["status"] = status



        query += """ ORDER BY 
            CASE status 
                WHEN 'PENDING' THEN 1 
                WHEN 'APPROVED' THEN 2 
                WHEN 'REJECTED' THEN 3 
                ELSE 4 
            END, created_at DESC"""



        result = await db.execute(text(query), params)

        rows = result.fetchall()



        # Build lookup maps for methodology families (sectors) and methodologies

        sec_res = await db.execute(text("SELECT id, code, name FROM methodology_families"))

        sec_map = {}

        for s_id, s_code, s_name in sec_res.fetchall():

            s_id_str = str(s_id).replace("-", "").lower()

            sec_map[s_id_str] = {"code": s_code, "name": s_name}

            sec_map[s_code.lower()] = {"code": s_code, "name": s_name}



        meth_res = await db.execute(text("SELECT id, code, name FROM methodologies"))

        meth_map = {}

        for m_id, m_code, m_name in meth_res.fetchall():

            m_id_str = str(m_id).replace("-", "").lower()

            meth_map[m_id_str] = {"code": m_code, "name": m_name}

            meth_map[m_code.lower()] = {"code": m_code, "name": m_name}



        items = []

        import json

        for row in rows:

            meta = {}

            if row.use_case:

                if isinstance(row.use_case, dict):

                    meta = row.use_case

                elif isinstance(row.use_case, str) and row.use_case.startswith("{"):

                    try:

                        meta = json.loads(row.use_case)

                    except Exception:

                        meta = {}



            s_id = meta.get("sector_id") or meta.get("sector")

            m_id = meta.get("methodology_id") or meta.get("methodology")



            norm_sid = str(s_id).replace("-", "").lower() if s_id else ""

            norm_mid = str(m_id).replace("-", "").lower() if m_id else ""



            sec_info = sec_map.get(norm_sid) if norm_sid else None

            meth_info = meth_map.get(norm_mid) if norm_mid else None



            sector_name = sec_info["name"] if sec_info else None

            sector_code = sec_info["code"] if sec_info else None

            methodology_name = meth_info["name"] if meth_info else None

            methodology_code = meth_info["code"] if meth_info else None



            items.append({

                "id": str(row.id) if row.id and str(row.id) != "None" else str(uuid.uuid4()),

                "full_name": row.full_name,

                "email": row.email,

                "phone": row.phone,

                "organization_name": row.organization_name,

                "country": row.country,

                "use_case": row.use_case,

                "sector_name": sector_name,

                "sector_code": sector_code,

                "methodology_name": methodology_name,

                "methodology_code": methodology_code,

                "status": row.status,

                "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else (str(row.created_at) if row.created_at else None),

                "reviewed_by": str(row.reviewed_by) if row.reviewed_by else None,

                "reviewed_at": row.reviewed_at.isoformat() if hasattr(row.reviewed_at, "isoformat") else (str(row.reviewed_at) if row.reviewed_at else None)

            })

        return items

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/admin/access-requests/{request_id}/approve")

async def approve_access_request(

    request_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user)

):

    """

    Approves a partner access request and fully provisions their workspace

    using entirely metadata-driven processes.

    """

    if current_user.role != "SUPER_ADMIN":

        raise HTTPException(status_code=403, detail="Only Super Admins can approve access requests.")



    # 1. Load request

    res = await db.execute(

        text("SELECT * FROM access_requests WHERE id = :id"),

        {"id": str(request_id)}

    )

    req = res.fetchone()

    if not req:

        raise HTTPException(status_code=404, detail="Access request not found.")

    if req.status != "PENDING":

        raise HTTPException(status_code=400, detail="Access request is already processed.")



    # 2. Extract metadata

    import json

    sector_id_str = None

    methodology_id_str = None

    use_case = None

    project_name = None



    use_case_data = req.use_case

    if use_case_data:

        if isinstance(use_case_data, dict):

            meta = use_case_data

        else:

            try:

                meta = json.loads(use_case_data)

            except:

                meta = {}



        if isinstance(meta, dict):

            sector_id_str = meta.get("sector_id")

            methodology_id_str = meta.get("methodology_id")

            use_case = meta.get("use_case")

            project_name = meta.get("project_name")



    # Resolve methodologies to populate licensed_methodologies

    # Resolve methodologies to populate licensed_methodologies and licensed_sectors

    licensed_methodologies = []

    licensed_sectors = []

    sec_row = None

    meth_row = None



    if methodology_id_str:

        res_meth = await db.execute(

            text("SELECT id, code, family_id FROM methodologies WHERE id = :val OR UPPER(code) = UPPER(:val)"),

            {"val": methodology_id_str}

        )

        meth_row = res_meth.fetchone()

        if meth_row:

            licensed_methodologies.append(meth_row.code)

            if not sector_id_str and meth_row.family_id:

                sector_id_str = str(meth_row.family_id)



    if sector_id_str:
        clean_sec = str(sector_id_str).strip().lower()
        alias_code = None
        if "hybrid" in clean_sec or "energy" in clean_sec or "solar" in clean_sec:
            alias_code = "HYBRID_ENERGY"
        elif "ev" in clean_sec or "mobility" in clean_sec or "electric" in clean_sec:
            alias_code = "EV_MOBILITY"
        elif "biochar" in clean_sec:
            alias_code = "BIOCHAR"
        elif "cook" in clean_sec or "stove" in clean_sec:
            alias_code = "COOKSTOVES"
        else:
            alias_code = clean_sec.upper()

        res_sec = await db.execute(
            text("""
                SELECT id, code FROM methodology_families 
                WHERE id = :val OR UPPER(code) = UPPER(:val) OR UPPER(code) = UPPER(:alias)
            """),
            {"val": sector_id_str, "alias": alias_code or sector_id_str}
        )
        sec_row = res_sec.fetchone()
        if sec_row:
            code_val = str(sec_row[1]) if len(sec_row) > 1 else str(sec_row.code)
            licensed_sectors.append(code_val)
        elif alias_code:
            licensed_sectors.append(alias_code)

    if not licensed_sectors and use_case:
        uc_clean = str(use_case).lower()
        if "hybrid" in uc_clean or "energy" in uc_clean or "solar" in uc_clean:
            licensed_sectors.append("HYBRID_ENERGY")
        elif "ev" in uc_clean or "mobility" in uc_clean or "electric" in uc_clean:
            licensed_sectors.append("EV_MOBILITY")
        elif "biochar" in uc_clean:
            licensed_sectors.append("BIOCHAR")
        elif "cook" in uc_clean or "stove" in uc_clean:
            licensed_sectors.append("COOKSTOVES")



    try:

        # 3. Provision Organization using OrganizationService

        org_repo = OrganizationRepository(db)

        org_service = OrganizationService(org_repo)



        new_org = await org_repo.get_by_name(req.organization_name)

        if not new_org:

            org_payload = OrganizationCreate(

                name=req.organization_name,

                org_type="DEVELOPER",

                metadata_context={"country": req.country, "use_case": use_case, "source_request": str(request_id)},

                plan="PROFESSIONAL",

                licensed_methodologies=licensed_methodologies

            )

            new_org = await org_service.create_org(org_payload, creator_id=current_user.id, db=db)



            # Explicitly set licensed_sectors (JSONB)

            new_org.licensed_sectors = licensed_sectors

            await db.flush()

        else:

            existing_methodologies = set(new_org.licensed_methodologies or [])

            existing_methodologies.update(licensed_methodologies)

            new_org.licensed_methodologies = list(existing_methodologies)



            existing_sectors = set(new_org.licensed_sectors or [])

            existing_sectors.update(licensed_sectors)

            new_org.licensed_sectors = list(existing_sectors)

            await db.flush()



        # 3.5 Auto-provision a default Project for the assigned sector & methodology

        from app.domains.projects.models import Project



        target_sec_id = None

        if sec_row:

            try:

                target_sec_id = uuid.UUID(str(sec_row.id))

            except Exception:

                target_sec_id = sec_row.id

        elif sector_id_str:

            try:

                target_sec_id = uuid.UUID(sector_id_str)

            except Exception:

                pass



        target_meth_id = None

        if meth_row:

            try:

                target_meth_id = uuid.UUID(str(meth_row.id))

            except Exception:

                target_meth_id = meth_row.id

        elif methodology_id_str:

            try:

                target_meth_id = uuid.UUID(methodology_id_str)

            except Exception:

                pass



        if target_sec_id or target_meth_id:

            proj_exists = await db.execute(

                text("SELECT id FROM projects WHERE organization_id = :org_id AND sector_id = :sec_id"),

                {"org_id": str(new_org.id), "sec_id": str(target_sec_id) if target_sec_id else None}

            )

            if not proj_exists.fetchone():

                sec_label = sec_row.code if sec_row else "Default"

                default_proj = Project(

                    name=project_name if project_name else f"{req.organization_name} - {sec_label} Project",

                    organization_id=new_org.id,

                    sector_id=target_sec_id,

                    methodology_id=target_meth_id,

                    country=req.country

                )

                db.add(default_proj)

                await db.flush()



        # 4. Provision User using AuthenticationService

        auth_repo = UserRepository(db)

        auth_service = AuthenticationService(auth_repo)



        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"

        temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))



        new_user = await auth_repo.get_by_email(req.email)

        if not new_user:

            user_payload = UserCreate(

                email=req.email,

                phone=req.phone,

                full_name=req.full_name,

                password=temp_password,

                role="ORG_ADMIN",

                organization=new_org.name,

                organization_id=new_org.id,

                country=req.country,

                meta_data={"provisioned_from": str(request_id)}

            )

            new_user = await auth_service.create_user(user_payload, actor_id=str(current_user.id))

        else:

            from app.core.security import get_password_hash

            await auth_service.update_user(

                new_user.id,

                {"password_hash": get_password_hash(temp_password), "requires_password_change": True},

                actor_id=str(current_user.id)

            )



        # 4.5 Auto-provision a default Workspace (Property)

        from app.domains.workspaces.models import Property

        prop_exists = await db.execute(

            text("SELECT id FROM properties WHERE organization_id = :org_id"),

            {"org_id": str(new_org.id)}

        )

        if not prop_exists.fetchone():

            default_workspace = Property(

                name=f"{req.organization_name} Main Workspace",

                owner_id=new_user.id,

                organization_id=new_org.id,

                property_type="corporate",

                address=req.country

            )

            db.add(default_workspace)

            await db.flush()



        # 5. Audit

        await EventBus.publish(

            stream_name="access_events",

            event_type="AccessRequestApproved",

            payload={

                "request_id": str(request_id),

                "organization_id": str(new_org.id),

                "user_id": str(new_user.id),

                "licensed_methodologies": licensed_methodologies

            },

            actor_id=str(current_user.id)

        )



        # 6. Notification (Soft fail if table doesn't exist)

        try:

            notif_repo = NotificationRepository(db)

            notif_service = NotificationService(notif_repo)

            await notif_service.create_notification(NotificationCreate(

                user_id=new_user.id,

                title="Welcome to VeriField Nexus",

                message=f"Your organization {new_org.name} has been provisioned. Please log in and change your password.",

                type="SYSTEM_ALERT",

                metadata_json={"request_id": str(request_id)}

            ))

        except Exception as notif_err:

            import logging

            logging.error(f"Failed to create notification: {notif_err}")



        # 7. Update Request Status

        await db.execute(

            text("""

                UPDATE access_requests

                SET status = 'APPROVED',

                    reviewed_by = :reviewed_by,

                    reviewed_at = CURRENT_TIMESTAMP

                WHERE id = :id

            """),

            {"id": str(request_id), "reviewed_by": str(current_user.id)}

        )



        await db.commit()



        # 8. Return strictly required response

        return {

            "message": "Access request approved and workspace provisioned.",

            "status": "APPROVED",

            "organization_id": str(new_org.id),

            "organization_name": new_org.name,

            "user_id": str(new_user.id),

            "org_admin_email": new_user.email,

            "temporary_password": temp_password,

            "licensed_methodologies": licensed_methodologies,

            "requires_password_change": True,

            "workspace": "provisioned"

        }

    except Exception as e:

        await db.rollback()

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/admin/access-requests/{request_id}/reject")

async def reject_access_request(

    request_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user)

):

    if current_user.role != "SUPER_ADMIN":

        raise HTTPException(status_code=403, detail="Only Super Admins can reject access requests.")



    # 1. Load request

    res = await db.execute(

        text("SELECT * FROM access_requests WHERE id = :id"),

        {"id": str(request_id)}

    )

    req = res.fetchone()

    if not req:

        raise HTTPException(status_code=404, detail="Access request not found.")

    if req.status != "PENDING":

        raise HTTPException(status_code=400, detail="Access request is already processed.")



    try:

        # Update Request Status

        await db.execute(

            text("""

                UPDATE access_requests

                SET status = 'REJECTED',

                    reviewed_by = :reviewed_by,

                    reviewed_at = CURRENT_TIMESTAMP

                WHERE id = :id

            """),

            {"id": str(request_id), "reviewed_by": str(current_user.id)}

        )



        await db.commit()



        return {

            "message": "Access request rejected.",

            "status": "REJECTED"

        }

    except Exception as e:

        await db.rollback()

        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/admin/access-requests/{request_id}")

async def delete_access_request(

    request_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user)

):

    if current_user.role != "SUPER_ADMIN":

        raise HTTPException(status_code=403, detail="Only Super Admins can delete access requests.")



    # 1. Check if request exists

    res = await db.execute(

        text("SELECT id FROM access_requests WHERE id = :id"),

        {"id": str(request_id)}

    )

    if not res.fetchone():

        raise HTTPException(status_code=404, detail="Access request not found.")



    try:

        # Delete Request

        await db.execute(

            text("DELETE FROM access_requests WHERE id = :id"),

            {"id": str(request_id)}

        )



        await db.commit()



        return {

            "message": "Access request deleted successfully."

        }

    except Exception as e:

        await db.rollback()

        raise HTTPException(status_code=500, detail=str(e))
