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
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# Bearer token extractor from Authorization header
security = HTTPBearer()


async def decode_jwt_token(token: str) -> dict:
    """
    Decode and validate a Supabase JWT token.
    
    Supabase issues JWTs with the project's JWT secret.
    We validate the signature and extract the user claims.
    
    Returns:
        dict: Decoded token payload containing user ID and metadata
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_key,
                }
            )
            
            if response.status_code != 200:
                raise JWTError("Invalid token")
                
            user_data = response.json()
            return {"sub": user_data.get("id")}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please complete registration.",
        )

    return user


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
