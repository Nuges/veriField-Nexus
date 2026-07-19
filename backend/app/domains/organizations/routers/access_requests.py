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
    sector: Optional[str] = None

@router.post("/access-requests")
async def create_access_request(
    payload: AccessRequestCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        await db.execute(
            text("""
                INSERT INTO access_requests 
                (full_name, email, phone, organization_name, country, use_case, status) 
                VALUES 
                (:full_name, :email, :phone, :organization_name, :country, :use_case, 'PENDING')
            """),
            {
                "full_name": payload.full_name,
                "email": payload.email,
                "phone": payload.phone,
                "organization_name": payload.organization_name,
                "country": payload.country,
                "use_case": payload.use_case,
            }
        )
        await db.commit()
        return {"status": "success", "message": "Access request submitted successfully."}
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
            
        query += " ORDER BY created_at DESC"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        return [
            {
                "id": str(row.id),
                "full_name": row.full_name,
                "email": row.email,
                "phone": row.phone,
                "organization_name": row.organization_name,
                "country": row.country,
                "use_case": row.use_case,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "reviewed_by": str(row.reviewed_by) if row.reviewed_by else None,
                "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None
            }
            for row in rows
        ]
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
        text("SELECT * FROM access_requests WHERE id = :id FOR UPDATE"), 
        {"id": request_id}
    )
    req = res.fetchone()
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found.")
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Access request is already processed.")

    # 2. Resolve metadata (Methodologies) based on category (sector or use_case)
    resolver = MethodologyResolver(db)
    category_text = getattr(req, "sector", getattr(req, "use_case", ""))
    licensed_methodologies = await resolver.resolve_from_context(category_text)

    try:
        # 3. Provision Organization using OrganizationService
        org_repo = OrganizationRepository(db)
        org_service = OrganizationService(org_repo)
        
        new_org = await org_repo.get_by_name(req.organization_name)
        if not new_org:
            org_payload = OrganizationCreate(
                name=req.organization_name,
                org_type="DEVELOPER",
                metadata_context={"country": req.country, "use_case": req.use_case, "source_request": str(request_id)},
                plan="PROFESSIONAL",
                licensed_methodologies=licensed_methodologies
            )
            new_org = await org_service.create_org(org_payload, creator_id=current_user.id, db=db)
        
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
            {"id": request_id, "reviewed_by": current_user.id}
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
        text("SELECT * FROM access_requests WHERE id = :id FOR UPDATE"), 
        {"id": request_id}
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
            {"id": request_id, "reviewed_by": current_user.id}
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
        text("SELECT id FROM access_requests WHERE id = :id FOR UPDATE"), 
        {"id": request_id}
    )
    if not res.fetchone():
        raise HTTPException(status_code=404, detail="Access request not found.")

    try:
        # Delete Request
        await db.execute(
            text("DELETE FROM access_requests WHERE id = :id"),
            {"id": request_id}
        )
        
        await db.commit()
        
        return {
            "message": "Access request deleted successfully."
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


