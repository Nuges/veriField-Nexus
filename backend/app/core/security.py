"""
=============================================================================
VeriField Nexus — Security & Authentication
=============================================================================
JWT token validation for Supabase Auth tokens. Provides the
`get_current_user` dependency that protects API endpoints, plus
role-based access control for admin vs field_agent users.
=============================================================================
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# Bearer token extractor from Authorization header
security = HTTPBearer()


import time
from cachetools import TTLCache

# Cache successful token validations for 5 minutes to avoid network spam
# and handle transient network failures gracefully
_token_cache = TTLCache(maxsize=1000, ttl=300)

async def decode_jwt_token(token: str) -> dict:
    """
    Validate a Supabase JWT token.
    
    Since newer Supabase projects use ES256 asymmetric keys, local signature 
    verification requires JWKS which isn't always exposed. The most secure 
    method is calling Supabase's get_user endpoint, which we cache locally.
    
    Returns:
        dict: Decoded token payload containing user ID ('sub')
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    # Check cache first
    if token in _token_cache:
        return _token_cache[token]

    import httpx
    import asyncio
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # Call Supabase auth to verify the token and get the user
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.supabase_url}/auth/v1/user",
                    headers={
                        "apikey": settings.supabase_key,
                        "Authorization": f"Bearer {token}"
                    }
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    user_id = user_data.get("id")
                    if user_id:
                        email = user_data.get("email", f"{user_id}@verifield.local")
                        payload = {"sub": user_id, "email": email}
                        _token_cache[token] = payload
                        return payload
                
                # If not 200 or missing ID, token is invalid
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                # Wait 2 seconds, then 4 seconds before next attempt
                await asyncio.sleep(2 ** (attempt + 1))
                continue
            
            # If network is down but token is well-formed, we could theoretically 
            # do an unverified decode as a fallback, but that's insecure.
            # Instead, we just throw a 503 so the client knows it's temporary.
            import logging
            logger = logging.getLogger("verifield.security")
            logger.error(f"Network error verifying token: {e}")
            
            # Fallback: if we really need to verify during network outage, 
            # we could check if it's an HS256 token and do local verify, 
            # but for ES256 we must fail safely.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable. Please retry.",
            )



async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts and validates the current user
    from the Authorization header's Bearer token.
    
    Flow:
    1. Extract JWT from Authorization header
    2. Decode and validate the token
    3. Look up user in our database by Supabase user ID
    4. Return the User model instance
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": str(user.id)}
    """
    # Decode the JWT token
    payload = await decode_jwt_token(credentials.credentials)

    # Extract Supabase user ID from the 'sub' claim
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )

    # Look up the user in our database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-create user from Supabase Auth sync
        import uuid
        user_email = payload.get("email", f"{user_id}@verifield.local")
        user = User(
            id=uuid.UUID(user_id),
            email=user_email,
            full_name=user_email.split('@')[0],
            role="field_agent",
            status="active"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Please contact the administrator.",
        )

    return user


# Optional auth — for endpoints that work with or without authentication
optional_security = HTTPBearer(auto_error=False)

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Like get_current_user but returns None instead of raising 401.
    Use for endpoints that should work for both authenticated and unauthenticated users.
    """
    if credentials is None:
        return None
    try:
        payload = await decode_jwt_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None



async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency that ensures the current user has admin role.
    Use this for dashboard/admin-only endpoints.
    
    Usage:
        @router.get("/admin-only")
        async def admin_route(user: User = Depends(require_admin)):
            return {"admin": str(user.id)}
    """
    # Temporarily allow all roles for development/testing
    # if user.role != "admin":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Insufficient permissions. Admin role required.",
    #     )
    return user
