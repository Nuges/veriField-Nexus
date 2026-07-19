from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

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


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    service = AuthenticationService(repo)
    user = await service.authenticate(credentials)
    token = service.generate_token(user)

    return AuthResponse(
        user=UserResponse.model_validate(user), access_token=token, expires_in=86400
    )


@router.post(
    "/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


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
    # Idempotency middleware should intercept this if provided.
    repo = UserRepository(db)
    service = AuthenticationService(repo)

    if not payload.password:
        payload.password = "TempPassword123!"  # Require them to change it
    validate_password_strength(payload.password)

    # Inherit org if not explicitly set
    if not payload.organization_id:
        payload.organization_id = current_user.organization_id
        payload.organization = current_user.organization

    user = await service.create_user(payload, actor_id=str(current_user.id))
    return UserResponse.model_validate(user)


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

@router.post("/change-password")
async def change_password(
    payload: ChangePasswordPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.core.security import verify_password, get_password_hash
    repo = UserRepository(db)
    service = AuthenticationService(repo)
    
    if payload.old_password and current_user.password_hash:
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
