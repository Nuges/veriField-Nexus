import secrets

import string

import uuid

from typing import Optional



from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel

from sqlalchemy import text, select

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

from app.domains.organizations.models import Organization

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "ORG_ADMIN"):
        raise HTTPException(
            status_code=status_code.HTTP_403_FORBIDDEN if "status_code" in globals() else 403,
            detail="Access Denied: Administrative role required to view access requests."
        )
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
                if not isinstance(meta, dict):
                    meta = {"use_case": str(use_case_data)}
            except Exception:
                meta = {"use_case": str(use_case_data)}

        if isinstance(meta, dict):
            sector_id_str = meta.get("sector_id") or meta.get("sector")
            methodology_id_str = meta.get("methodology_id") or meta.get("methodology")
            use_case = meta.get("use_case")
            project_name = meta.get("project_name")

    # Resolve methodologies to populate licensed_methodologies and licensed_sectors
    licensed_methodologies = []
    licensed_sectors = []
    sec_row = None
    meth_row = None
    target_sec_id = None
    target_meth_id = None

    # Step 1: Resolve Sector from request metadata or use case text
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

        sec_is_uuid = False
        try:
            uuid.UUID(str(sector_id_str).strip())
            sec_is_uuid = True
        except (ValueError, TypeError, AttributeError):
            sec_is_uuid = False

        if sec_is_uuid:
            clean_sec = str(uuid.UUID(str(sector_id_str).strip()))
            hex_sec = clean_sec.replace("-", "")
            res_sec = await db.execute(
                text("SELECT id, code FROM methodology_families WHERE id = :val_uuid OR id = :hex_uuid"),
                {"val_uuid": clean_sec, "hex_uuid": hex_sec}
            )
        else:
            res_sec = await db.execute(
                text("""
                    SELECT id, code FROM methodology_families
                    WHERE UPPER(code) = UPPER(:val_code) OR UPPER(code) = UPPER(:alias)
                """),
                {"val_code": str(sector_id_str).strip(), "alias": alias_code or str(sector_id_str).strip()}
            )
        sec_row = res_sec.fetchone()

    if not sec_row:
        combined_text = f"{use_case or ''} {req.organization_name or ''} {str(use_case_data or '')}".lower()
        alias_code = None
        if "ev" in combined_text or "mobility" in combined_text or "electric" in combined_text:
            alias_code = "EV_MOBILITY"
        elif "hybrid" in combined_text or "energy" in combined_text or "solar" in combined_text:
            alias_code = "HYBRID_ENERGY"
        elif "biochar" in combined_text or "pyrolysis" in combined_text:
            alias_code = "BIOCHAR"
        elif "cook" in combined_text or "stove" in combined_text:
            alias_code = "COOKSTOVES"

        if alias_code:
            res_sec = await db.execute(
                text("SELECT id, code FROM methodology_families WHERE UPPER(code) = UPPER(:alias)"),
                {"alias": alias_code}
            )
            sec_row = res_sec.fetchone()

    if sec_row:
        target_sec_id = uuid.UUID(str(sec_row.id if hasattr(sec_row, "id") else sec_row[0]))
        sec_code_val = str(sec_row.code if hasattr(sec_row, "code") else sec_row[1])
        licensed_sectors.append(sec_code_val)

    # Step 2: Resolve Methodology & Enforce Sector-Methodology Invariant
    if methodology_id_str:
        meth_is_uuid = False
        try:
            uuid.UUID(str(methodology_id_str).strip())
            meth_is_uuid = True
        except (ValueError, TypeError, AttributeError):
            meth_is_uuid = False

        if meth_is_uuid:
            clean_meth = str(uuid.UUID(str(methodology_id_str).strip()))
            hex_meth = clean_meth.replace("-", "")
            res_meth = await db.execute(
                text("SELECT id, code, family_id, is_active FROM methodologies WHERE (id = :val_uuid OR id = :hex_uuid) AND is_active = TRUE"),
                {"val_uuid": clean_meth, "hex_uuid": hex_meth}
            )
        else:
            res_meth = await db.execute(
                text("SELECT id, code, family_id, is_active FROM methodologies WHERE UPPER(code) = UPPER(:val_code) AND is_active = TRUE"),
                {"val_code": str(methodology_id_str).strip()}
            )
        meth_row = res_meth.fetchone()
        if not meth_row:
            raise HTTPException(
                status_code=400,
                detail=f"Methodology '{methodology_id_str}' does not exist or is inactive."
            )

        meth_family_id = uuid.UUID(str(meth_row.family_id if hasattr(meth_row, "family_id") else meth_row[2]))
        if target_sec_id:
            if meth_family_id != target_sec_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Selected methodology does not belong to the selected sector."
                )
        else:
            target_sec_id = meth_family_id
            clean_sec_target = str(target_sec_id)
            hex_sec_target = clean_sec_target.replace("-", "")
            res_sec = await db.execute(
                text("SELECT id, code FROM methodology_families WHERE id = :val_uuid OR id = :hex_uuid"),
                {"val_uuid": clean_sec_target, "hex_uuid": hex_sec_target}
            )
            sec_row = res_sec.fetchone()
            if sec_row:
                sec_code_val = str(sec_row.code if hasattr(sec_row, "code") else sec_row[1])
                if sec_code_val not in licensed_sectors:
                    licensed_sectors.append(sec_code_val)

        target_meth_id = uuid.UUID(str(meth_row.id if hasattr(meth_row, "id") else meth_row[0]))
        meth_code_str = str(meth_row.code if hasattr(meth_row, "code") else meth_row[1])
        if meth_code_str not in licensed_methodologies:
            licensed_methodologies.append(meth_code_str)

    elif target_sec_id:
        # Resolve the primary active methodology belonging to that exact sector/methodology family
        dash_fid = str(uuid.UUID(str(target_sec_id)))
        clean_fid = dash_fid.replace("-", "")
        res_primary_meth = await db.execute(
            text("""
                SELECT id, code, family_id
                FROM methodologies
                WHERE (family_id = :dash_id OR family_id = :clean_id) AND is_active = TRUE
                ORDER BY created_at ASC
                LIMIT 1
            """),
            {"dash_id": dash_fid, "clean_id": clean_fid}
        )
        meth_row = res_primary_meth.fetchone()
        if meth_row:
            target_meth_id = uuid.UUID(str(meth_row.id if hasattr(meth_row, "id") else meth_row[0]))
            meth_code_str = str(meth_row.code if hasattr(meth_row, "code") else meth_row[1])
            if meth_code_str not in licensed_methodologies:
                licensed_methodologies.append(meth_code_str)
        else:
            target_meth_id = None


    try:
        # 3. Provision Organization atomically
        res_org = await db.execute(
            select(Organization).where(Organization.name == req.organization_name, Organization.is_deleted == False)
        )
        new_org = res_org.scalar_one_or_none()
        if not new_org:
            new_org = Organization(
                name=req.organization_name,
                org_type="DEVELOPER",
                metadata_context={"country": req.country, "use_case": use_case, "source_request": str(request_id)},
                plan="PROFESSIONAL",
                licensed_methodologies=licensed_methodologies,
                licensed_sectors=licensed_sectors,
                created_by=current_user.id,
                status="ACTIVE",
                max_installations=1000,
                max_agents=20
            )
            db.add(new_org)
            await db.flush()
        else:
            existing_methodologies = set(new_org.licensed_methodologies or [])
            existing_methodologies.update(licensed_methodologies)
            new_org.licensed_methodologies = list(existing_methodologies)

            existing_sectors = set(new_org.licensed_sectors or [])
            existing_sectors.update(licensed_sectors)
            new_org.licensed_sectors = list(existing_sectors)
            await db.flush()

        # 3.5 Provision default Project if both sector and active methodology exist
        from app.domains.projects.models import Project

        if target_sec_id and target_meth_id:
            proj_exists = await db.execute(
                select(Project.id).where(Project.organization_id == new_org.id)
            )
            if not proj_exists.first():
                sec_label = sec_row.code if sec_row else (licensed_sectors[0] if licensed_sectors else "Default")
                default_proj = Project(
                    name=project_name if project_name else f"{req.organization_name} - {sec_label} Project",
                    organization_id=new_org.id,
                    sector_id=target_sec_id,
                    methodology_id=target_meth_id,
                    country=req.country
                )
                db.add(default_proj)
                await db.flush()

        # 4. Provision User atomically
        from app.core.security import get_password_hash
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

        user_phone = req.phone
        if user_phone:
            existing_phone = await db.execute(
                select(User.id).where(User.phone == user_phone, User.email != req.email, User.is_deleted == False)
            )
            if existing_phone.scalar_one_or_none():
                user_phone = None

        res_usr = await db.execute(
            select(User).where(User.email == req.email, User.is_deleted == False)
        )
        new_user = res_usr.scalar_one_or_none()
        if not new_user:
            new_user = User(
                email=req.email,
                phone=user_phone,
                full_name=req.full_name,
                password_hash=get_password_hash(temp_password),
                role="ORG_ADMIN",
                organization=new_org.name,
                organization_id=new_org.id,
                country=req.country,
                requires_password_change=True,
                is_active=True,
                status="active",
                meta_data={"provisioned_from": str(request_id)}
            )
            db.add(new_user)
            await db.flush()
        else:
            new_user.organization = new_org.name
            new_user.organization_id = new_org.id
            new_user.role = "ORG_ADMIN"
            if user_phone:
                new_user.phone = user_phone
            new_user.password_hash = get_password_hash(temp_password)
            new_user.requires_password_change = True
            await db.flush()

        # 4.5 Auto-provision default Workspace Property
        from app.domains.workspaces.models import Property
        prop_exists = await db.execute(
            select(Property.id).where(Property.organization_id == new_org.id)
        )
        if not prop_exists.first():
            default_workspace = Property(
                name=f"{req.organization_name} Main Workspace",
                owner_id=new_user.id,
                organization_id=new_org.id,
                property_type="corporate",
                address=req.country
            )
            db.add(default_workspace)
            await db.flush()

        # 5. Create Notification
        try:
            from app.domains.notifications.models import Notification
            notif = Notification(
                user_id=new_user.id,
                title="Welcome to VeriField Nexus",
                message=f"Your organization {new_org.name} has been provisioned. Please log in and change your password.",
                type="SYSTEM_ALERT",
                metadata_json={"request_id": str(request_id)}
            )
            db.add(notif)
            await db.flush()
        except Exception:
            pass

        # 6. Update Request Status
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

        # Single atomic commit for the entire approval operation
        await db.commit()

        # 7. Publish audit event asynchronously
        try:
            await EventBus.publish(
                stream_name="access_events",
                event_type="AccessRequestApproved",
                payload={
                    "request_id": str(request_id),
                    "organization_id": str(new_org.id),
                    "user_id": str(new_user.id),
                    "licensed_methodologies": licensed_methodologies,
                    "licensed_sectors": licensed_sectors,
                },
                actor_id=str(current_user.id)
            )
        except Exception:
            pass

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
