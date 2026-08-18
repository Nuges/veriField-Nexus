from typing import List, Optional

from uuid import UUID

from pydantic import BaseModel



from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status

from sqlalchemy.ext.asyncio import AsyncSession



from app.core.rate_limit import rate_limit
from app.core.rbac import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.authentication.repository import UserRepository
from app.domains.authentication.schemas import (AuthResponse, UserCreate,
                                                UserLogin, UserResponse,
                                                UserUpdate)
from app.domains.authentication.service import AuthenticationService
from app.domains.authentication.validators import validate_password_strength

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", dependencies=[Depends(rate_limit(limit=15, window_seconds=60, key_prefix="login"))])
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        repo = UserRepository(db)
        service = AuthenticationService(repo)
        user = await service.authenticate(credentials)

        # Check MFA status
        mfa_data = (user.meta_data or {}).get("mfa", {})
        if mfa_data.get("enabled"):
            from app.domains.authentication.routers.mfa import _generate_mfa_token
            mfa_token = _generate_mfa_token(str(user.id))
            return {
                "mfa_required": True,
                "mfa_token": mfa_token,
                "user": {"id": str(user.id), "email": user.email, "full_name": user.full_name},
            }

        # No MFA — issue full token
        token = service.generate_token(user)
        user_dto = UserResponse.model_validate(user).model_dump(mode="json")

        return {
            "user": user_dto,
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 86400,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login internal error: {str(e)}"
        )





@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(limit=10, window_seconds=60, key_prefix="signup"))]
)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):

    repo = UserRepository(db)

    service = AuthenticationService(repo)

    validate_password_strength(payload.password)



    # Use "system" as actor since they are signing up themselves

    user = await service.create_user(payload, actor_id="system")

    token = service.generate_token(user)



    return AuthResponse(

        user=UserResponse.model_validate(user), access_token=token, expires_in=86400

    )





class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
@router.put("/profile", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, update
    values_to_update = {}
    if payload.full_name is not None:
        values_to_update["full_name"] = payload.full_name.strip()
    if payload.avatar_url is not None:
        values_to_update["avatar_url"] = payload.avatar_url.strip()
    if payload.phone is not None:
        values_to_update["phone"] = payload.phone.strip()

    if values_to_update:
        stmt = (
            update(User)
            .where((User.id == current_user.id) | (User.email == current_user.email))
            .values(**values_to_update)
        )
        await db.execute(stmt)
        await db.commit()

    stmt_select = select(User).where((User.id == current_user.id) | (User.email == current_user.email))
    res = await db.execute(stmt_select)
    user = res.scalar_one_or_none()
    if not user:
        user = current_user
        for k, v in values_to_update.items():
            setattr(user, k, v)
    return UserResponse.model_validate(user)


@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    import os
    import uuid
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG, GIF, and WEBP images are supported.",
        )
    # Check max size 5MB
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Avatar image file exceeds 5MB limit.")
    os.makedirs(os.path.join("static", "avatars"), exist_ok=True)
    unique_filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}{file_ext}"
    target_path = os.path.join("static", "avatars", unique_filename)
    with open(target_path, "wb") as f:
        f.write(content)
    return {"avatar_url": f"/static/avatars/{unique_filename}"}





@router.get("/users", response_model=List[UserResponse])

async def list_users(

    limit: int = Query(100, ge=1, le=1000),

    offset: int = Query(0, ge=0),

    current_user: User = Depends(require_permission("org:read")),

    db: AsyncSession = Depends(get_db),

):

    repo = UserRepository(db)

    service = AuthenticationService(repo)

    if current_user.role == "SUPER_ADMIN":

        users = await service.list_all_users(limit, offset)

    elif not current_user.organization_id:

        return []

    else:

        users = await service.list_users(current_user.organization_id, limit, offset)

    return [UserResponse.model_validate(u) for u in users]





@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)

async def create_user(

    payload: UserCreate,

    x_idempotency_key: Optional[str] = Header(None),

    current_user: User = Depends(require_permission("team:manage")),

    db: AsyncSession = Depends(get_db),

):

    from app.domains.organizations.routers.governance import provision_user_account



    meta_dict = payload.meta_data or {}
    if payload.organization and "organization" not in meta_dict:
        meta_dict["organization"] = payload.organization

    res = await provision_user_account(
        db=db,
        actor_user=current_user,
        full_name=payload.full_name,
        email=payload.email or f"user_{uuid.uuid4().hex[:6]}@verifield.io",
        role=payload.role or "field_agent",
        organization_id=payload.organization_id or current_user.organization_id,
        phone=payload.phone,
        custom_password=payload.password,
        meta_data=meta_dict,
    )
    return UserResponse.model_validate(res["user"])





@router.put("/users/{user_id}", response_model=UserResponse)

async def update_user(

    user_id: UUID,

    payload: UserUpdate,

    x_idempotency_key: Optional[str] = Header(None),

    current_user: User = Depends(require_permission("team:manage")),

    db: AsyncSession = Depends(get_db),

):

    repo = UserRepository(db)

    service = AuthenticationService(repo)



    # Ensure they are in the same org

    target = await service.get_user(user_id)

    print(

        f"DEBUG: current_user.role={current_user.role}, target.org_id={target.organization_id}, current_user.org_id={current_user.organization_id}"

    )

    if (

        current_user.role != "SUPER_ADMIN"

        and target.organization_id != current_user.organization_id

    ):

        raise HTTPException(

            status_code=403, detail="Cannot modify user from different organization."

        )



    updates = payload.model_dump(exclude_unset=True)

    updated = await service.update_user(user_id, updates, actor_id=str(current_user.id))

    return UserResponse.model_validate(updated)





@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)

async def delete_user(

    user_id: UUID,

    current_user: User = Depends(require_permission("team:manage")),

    db: AsyncSession = Depends(get_db),

):

    repo = UserRepository(db)

    service = AuthenticationService(repo)



    target = await service.get_user(user_id)

    if (

        current_user.role != "SUPER_ADMIN"

        and target.organization_id != current_user.organization_id

    ):

        raise HTTPException(

            status_code=403, detail="Cannot modify user from different organization."

        )



    await service.delete_user(user_id, actor_id=str(current_user.id))

    return None





class ChangePasswordPayload(BaseModel):

    old_password: Optional[str] = None

    new_password: str



@router.post(
    "/change-password",
    dependencies=[Depends(rate_limit(limit=10, window_seconds=60, key_prefix="change_pwd"))]
)
async def change_password(

    payload: ChangePasswordPayload,

    current_user: User = Depends(get_current_user),

    db: AsyncSession = Depends(get_db)

):

    from app.core.security import verify_password, get_password_hash

    repo = UserRepository(db)

    service = AuthenticationService(repo)



    # For established users, verify old password.
    # When requires_password_change is True (new account / first login rotation), old_password check is waived.
    if current_user.password_hash and not getattr(current_user, "requires_password_change", False):
        if not payload.old_password:
            raise HTTPException(status_code=400, detail="Old password is required.")
        if not verify_password(payload.old_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid old password.")



    validate_password_strength(payload.new_password)

    hashed_pw = get_password_hash(payload.new_password)



    await service.update_user(

        current_user.id,

        {"password_hash": hashed_pw, "requires_password_change": False},

        actor_id=str(current_user.id)

    )

    return {"status": "success", "message": "Password changed successfully."}



class ResetPasswordPayload(BaseModel):

    password: str



@router.post("/users/{user_id}/reset-password")

async def force_reset_password(

    user_id: UUID,

    payload: ResetPasswordPayload,

    current_user: User = Depends(require_permission("team:manage")),

    db: AsyncSession = Depends(get_db)

):

    from app.core.security import get_password_hash

    repo = UserRepository(db)

    service = AuthenticationService(repo)

    target = await service.get_user(user_id)

    if current_user.role != "SUPER_ADMIN" and target.organization_id != current_user.organization_id:

        raise HTTPException(status_code=403, detail="Cannot modify user from different organization.")



    validate_password_strength(payload.password)

    hashed_pw = get_password_hash(payload.password)



    updated = await service.update_user(user_id, {"password_hash": hashed_pw, "requires_password_change": True}, actor_id=str(current_user.id))

    return {"status": "success", "message": "Password reset successfully."}
