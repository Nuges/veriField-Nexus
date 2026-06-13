"""
=============================================================================
VeriField Nexus — Auth API Routes
=============================================================================
Handles user registration, login, and profile management.
Uses Supabase Auth for identity management with our PostgreSQL
database for extended user profiles.
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
import shutil

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserLogin,
    UserResponse, AuthResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# POST /api/v1/auth/register — Create new user account
# =============================================================================
@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a Supabase Auth account and a local user profile.",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Register a new user account.
    
    Flow:
    1. Create user in Supabase Auth (email or phone)
    2. Create matching user record in our PostgreSQL database
    3. Return JWT token + user profile
    """
    # Determine if registering with email or phone
    identifier = payload.email or payload.phone
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone is required",
        )

    # Register with Supabase Auth
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build Supabase auth request
            auth_data = {"password": payload.password}
            if payload.email:
                auth_data["email"] = payload.email
            if payload.phone:
                auth_data["phone"] = payload.phone

            response = await client.post(
                f"{settings.supabase_url}/auth/v1/signup",
                json=auth_data,
                headers={
                    "apikey": settings.supabase_key,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code not in (200, 201):
                error_detail = response.json().get("msg", "Registration failed")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Supabase Auth error: {error_detail}",
                )

            auth_result = response.json()
    except Exception as e:
        if type(e).__name__ == "RequestError":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Authentication service unavailable: {str(e)}",
            )
        raise

    # Extract Supabase user ID and token
    supabase_user_id = auth_result.get("id") or auth_result.get("user", {}).get("id")
    access_token = auth_result.get("access_token", "")
    expires_in = auth_result.get("expires_in", 3600)

    if not supabase_user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user ID from auth service",
        )

    # Create local user record - automatically scope to the registering admin's organization
    user = User(
        id=uuid.UUID(supabase_user_id) if isinstance(supabase_user_id, str) else supabase_user_id,
        email=payload.email,
        phone=payload.phone,
        full_name=payload.full_name,
        role=payload.role,
        organization=admin_user.organization or "VeriField",  # AUTO-CONNECTED INHERITANCE!
        sector=payload.sector or "cookstove",
        country=payload.country,
        project_type=payload.project_type,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        expires_in=expires_in,
    )


# ---------------------------------------------------------------------------
# Request Payload for Public Onboarding
# ---------------------------------------------------------------------------
from typing import Optional
from pydantic import BaseModel, Field

class OnboardPayload(BaseModel):
    email: str = Field(..., description="Developer admin email address")
    password: str = Field(..., min_length=8, description="Primary account password")
    full_name: str = Field(..., description="Developer's full name")
    organization_name: str = Field(..., description="Name of the carbon methodology developer organization")
    sector: str = Field(default="cookstove", description="Assigned sector: cookstove, energy, transport, afolu")
    country: Optional[str] = Field(None, description="Country of operations")
    project_type: Optional[str] = Field(None, description="Optional project subtype")


# Onboarding is restricted to Super Admin approval via access request pipeline.
# No public onboarding or direct signup is allowed. Public users must submit requests
# via POST /api/v1/access-requests, which are stored in the database for Super Admin review.
# Upon approval, the Super Admin provisions the organization and ORG_ADMIN user.


# =============================================================================
# POST /api/v1/auth/login — Authenticate user
# =============================================================================
@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email/phone and password",
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return a JWT token.
    Delegates authentication to Supabase Auth.
    Falls back to dev mode login when DEV_MODE=true and Supabase is unreachable.
    """
    identifier = payload.email or payload.phone
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone is required",
        )

    import httpx
    import asyncio
    import logging
    import jwt as pyjwt
    import time
    logger = logging.getLogger("verifield.auth")

    # Intercept login requests for users with local database passwords (like Super Admin or SaaS Org Admins)
    local_user = None
    try:
        result = await db.execute(select(User).where(User.email == identifier))
        local_user = result.scalar_one_or_none()
    except Exception as e:
        logger.warning(f"Error checking local user on login: {e}")

    if local_user and local_user.password_hash:
        from app.core.security import verify_password
        if not verify_password(payload.password, local_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Please check your email and password.",
            )
        
        if not local_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been disabled. Please contact the administrator.",
            )

        # Build secure local JWT token
        token_payload = {
            "sub": str(local_user.id),
            "email": local_user.email,
            "role": local_user.role,
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400,
            "dev_mode": settings.dev_mode,
        }
        jwt_secret = settings.jwt_secret or "verifield-dev-secret-key"
        encoded_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        return AuthResponse(
            user=UserResponse.model_validate(local_user),
            access_token=encoded_token,
            expires_in=86400,
        )
    
    # =========================================================================
    # DEV MODE: Skip Supabase entirely, use local auth
    # =========================================================================
    if settings.dev_mode:
        logger.info(f"DEV MODE: Local login for {identifier}")
        
        dev_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, identifier)
        user = None
        
        try:
            result = await asyncio.wait_for(
                db.execute(select(User).where(User.email == identifier)),
                timeout=20.0,
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    id=dev_user_id,
                    email=payload.email,
                    phone=payload.phone,
                    role="admin",
                    full_name=payload.email.split("@")[0].replace(".", " ").title() if payload.email else "Dev Admin",
                    status="active",
                    sector="cookstove",
                )
                db.add(user)
                await asyncio.wait_for(db.commit(), timeout=20.0)
                await db.refresh(user)
        except Exception as db_err:
            logger.warning(f"DEV MODE: DB unreachable ({type(db_err).__name__}), using virtual user")
            try:
                await db.rollback()
            except Exception as rb_err:
                logger.warning(f"DEV MODE session rollback failed: {rb_err}")
            # Create a virtual User-like object for the response
            from app.schemas.user import UserResponse as _UR
            user = None  # Will construct response manually below
        
        # Build response — either from DB user or virtual data
        if user is not None:
            user_resp = UserResponse.model_validate(user)
            user_sub = str(user.id)
            user_email = user.email
            user_role = user.role
        else:
            # Virtual user when DB is completely offline
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            user_sub = str(dev_user_id)
            user_email = payload.email or identifier
            user_role = "admin"
            user_resp = UserResponse(
                id=dev_user_id,
                email=user_email,
                full_name=payload.email.split("@")[0].replace(".", " ").title() if payload.email else "Dev Admin",
                role="admin",
                sector="cookstove",
                created_at=now,
                updated_at=now,
            )
        
        # Generate a local JWT token
        dev_token_payload = {
            "sub": user_sub,
            "email": user_email,
            "role": user_role,
            "dev_mode": True,
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400,
        }
        jwt_secret = settings.jwt_secret or "verifield-dev-secret-key"
        dev_token = pyjwt.encode(dev_token_payload, jwt_secret, algorithm="HS256")
        
        return AuthResponse(
            user=user_resp,
            access_token=dev_token,
            expires_in=86400,
        )
    
    # =========================================================================
    # PRODUCTION: Authenticate via Supabase Auth
    # =========================================================================
    supabase_succeeded = False
    auth_result = None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                auth_data = {"password": payload.password}
                if payload.email:
                    auth_data["email"] = payload.email
                if payload.phone:
                    auth_data["phone"] = payload.phone

                response = await client.post(
                    f"{settings.supabase_url}/auth/v1/token?grant_type=password",
                    json=auth_data,
                    headers={
                        "apikey": settings.supabase_key,
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code != 200:
                    try:
                        error_body = response.json()
                        error_code = error_body.get("error_code", "")
                        error_msg = error_body.get("msg", "")
                    except Exception:
                        error_code = ""
                        error_msg = ""
                    
                    logger.warning(f"Supabase auth error: {response.status_code} - {error_code}: {error_msg}")
                    
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid credentials. Please check your email and password.",
                    )

                auth_result = response.json()
                supabase_succeeded = True
                break
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Login attempt {attempt+1}/{max_retries} failed: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** (attempt + 1))
                continue
            
            # =========================================================
            # DEV MODE FALLBACK — offline login when Supabase is down
            # =========================================================
            if settings.dev_mode:
                logger.info(f"DEV MODE: Supabase unreachable, using offline login for {identifier}")
                
                # Find or create dev user in local database
                dev_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, identifier)
                result = await db.execute(select(User).where(User.email == identifier))
                user = result.scalar_one_or_none()
                
                if not user:
                    user = User(
                        id=dev_user_id,
                        email=payload.email,
                        phone=payload.phone,
                        role="admin",
                        full_name=payload.email.split("@")[0].replace(".", " ").title() if payload.email else "Dev Admin",
                        status="active",
                        sector="cookstove",
                    )
                    db.add(user)
                    await db.commit()
                    await db.refresh(user)
                
                # Generate a local JWT token (signed with jwt_secret)
                dev_token_payload = {
                    "sub": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "dev_mode": True,
                    "iat": int(time.time()),
                    "exp": int(time.time()) + 86400,  # 24h expiry
                }
                jwt_secret = settings.jwt_secret or "verifield-dev-secret-key"
                dev_token = pyjwt.encode(dev_token_payload, jwt_secret, algorithm="HS256")
                
                return AuthResponse(
                    user=UserResponse.model_validate(user),
                    access_token=dev_token,
                    expires_in=86400,
                )
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable. Please retry in a moment.",
            )

    # =========================================================================
    # Standard Supabase flow — get/create user in local DB
    # =========================================================================
    supabase_user_id = auth_result.get("user", {}).get("id")
    try:
        result = await asyncio.wait_for(
            db.execute(select(User).where(User.id == supabase_user_id)),
            timeout=15.0
        )
        user = result.scalar_one_or_none()
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection timeout. Please retry.",
        )

    if not user:
        user_email = payload.email or auth_result.get("user", {}).get("email")
        user = User(
            id=uuid.UUID(supabase_user_id) if isinstance(supabase_user_id, str) else supabase_user_id,
            email=user_email,
            phone=payload.phone,
            role="admin" if "admin" in (user_email or "").lower() else "field_agent",
            full_name="Admin User" if "admin" in (user_email or "").lower() else (
                user_email.split("@")[0].replace(".", " ").replace("_", " ").replace("-", " ").title() if user_email else "Field Agent"
            ),
            sector="cookstove",
        )
        db.add(user)
        try:
            await asyncio.wait_for(db.commit(), timeout=15.0)
            await db.refresh(user)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database write timeout. Please retry.",
            )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=auth_result.get("access_token", ""),
        expires_in=auth_result.get("expires_in", 3600),
    )


# =============================================================================
# GET /api/v1/auth/me — Get current user profile
# =============================================================================
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(user)


# =============================================================================
# PUT /api/v1/auth/profile — Update user profile
# =============================================================================
@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update user profile",
)
async def update_profile(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's profile fields."""
    db_user = await db.get(User, user.id)
    if not db_user:
        # If transient virtual user in DEV_MODE, register it in DB
        db_user = User(
            id=user.id,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            avatar_url=user.avatar_url,
            organization=user.organization,
        )
        db.add(db_user)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    await db.commit()
    await db.refresh(db_user)
    return UserResponse.model_validate(db_user)


@router.post(
    "/upload-avatar",
    summary="Upload user avatar image",
    description="Uploads a profile picture and returns the hosting static URL.",
)
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, JPEG, PNG, GIF, and WEBP images are supported.",
        )
    
    # Create unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    target_path = os.path.join("static", "avatars", unique_filename)
    
    # Save the file
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save uploaded file: {str(e)}",
        )
        
    # Build absolute URL using base_url
    base_url = str(request.base_url).rstrip("/")
    avatar_url = f"{base_url}/static/avatars/{unique_filename}"
    
    # Persist avatar_url in the database immediately
    db_user = await db.get(User, user.id)
    if not db_user:
        db_user = User(
            id=user.id,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            avatar_url=avatar_url,
            organization=user.organization,
        )
        db.add(db_user)
    else:
        db_user.avatar_url = avatar_url

    await db.commit()
    await db.refresh(db_user)
    
    return {"avatar_url": avatar_url}


class ChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


@router.post(
    "/change-password",
    summary="Change user password",
)
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified password change endpoint.
    - For users with local password_hash (Super Admin, Org Admins): updates hash locally.
    - For Supabase-auth users: updates via Supabase Admin API.
    - Clears requires_password_change flag for forced-reset flows.
    """
    import logging
    logger = logging.getLogger("verifield.auth")

    # ── Local password hash path (Super Admin, seeded Org Admins) ──
    if user.password_hash:
        from app.core.security import verify_password, get_password_hash

        # Validate old password if provided
        if payload.old_password is not None:
            if not verify_password(payload.old_password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incorrect current password",
                )

        user.password_hash = get_password_hash(payload.new_password)
        user.requires_password_change = False
        await db.commit()
        logger.info(f"Password rotated for local user {user.email}")
        return {"message": "Password rotated successfully"}

    # ── Supabase Auth path ──
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{settings.supabase_url}/auth/v1/admin/users/{user.id}",
                json={"password": payload.new_password},
                headers={
                    "apikey": settings.supabase_key,
                    "Authorization": f"Bearer {settings.supabase_key}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code not in (200, 201):
                error_detail = response.json().get("msg", "Password update failed")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Auth Service Error: {error_detail}",
                )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Auth server unreachable: {str(e)}",
        )
    
    # Clear the flag even for Supabase users
    user.requires_password_change = False
    await db.commit()
    return {"message": "Password successfully updated."}


# =============================================================================
# PATCH /api/v1/auth/users/{user_id}/status — Suspend/Revoke User (Admin)
# =============================================================================
from pydantic import BaseModel

class UserStatusUpdate(BaseModel):
    status: str

@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    summary="Update user status (Admin only)",
    description="Allows an admin to set a user's status to active, suspended, or revoked.",
)
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    if payload.status not in ("active", "suspended", "revoked"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'active', 'suspended', or 'revoked'.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.status = payload.status
    await db.commit()
    await db.refresh(target_user)
    return UserResponse.model_validate(target_user)


# =============================================================================
# DELETE /api/v1/auth/me — Delete current user account (Compliance)
# =============================================================================
@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Delete current user profile (Compliance)",
    description="Deletes the authenticated user's database profile and data for GDPR/App Store compliance.",
)
async def delete_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    GDPR & App Store compliance: Deletes the user profile and extended data from PostgreSQL.
    """
    await db.delete(user)
    await db.commit()
    return {"message": "Account successfully deleted."}


