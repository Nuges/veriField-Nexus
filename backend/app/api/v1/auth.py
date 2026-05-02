"""
=============================================================================
VeriField Nexus — Auth API Routes
=============================================================================
Handles user registration, login, and profile management.
Uses Supabase Auth for identity management with our PostgreSQL
database for extended user profiles.
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import uuid

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_user
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
        async with httpx.AsyncClient() as client:
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
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unavailable: {str(e)}",
        )

    # Extract Supabase user ID and token
    supabase_user_id = auth_result.get("id") or auth_result.get("user", {}).get("id")
    access_token = auth_result.get("access_token", "")
    expires_in = auth_result.get("expires_in", 3600)

    if not supabase_user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user ID from auth service",
        )

    # Create local user record
    user = User(
        id=uuid.UUID(supabase_user_id) if isinstance(supabase_user_id, str) else supabase_user_id,
        email=payload.email,
        phone=payload.phone,
        full_name=payload.full_name,
        role=payload.role,
        organization=payload.organization,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        expires_in=expires_in,
    )


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
    """
    identifier = payload.email or payload.phone
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone is required",
        )

    try:
        async with httpx.AsyncClient() as client:
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
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )

            auth_result = response.json()
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    # Get user from our database
    supabase_user_id = auth_result.get("user", {}).get("id")
    result = await db.execute(select(User).where(User.id == supabase_user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-create local profile if authenticated via Supabase but missing locally
        import uuid
        user_email = payload.email or auth_result.get("user", {}).get("email")
        user = User(
            id=uuid.UUID(supabase_user_id) if isinstance(supabase_user_id, str) else supabase_user_id,
            email=user_email,
            phone=payload.phone,
            role="admin" if "admin" in (user_email or "").lower() else "field_agent",
            full_name="Admin User" if "admin" in (user_email or "").lower() else "Field Agent",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

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
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)
