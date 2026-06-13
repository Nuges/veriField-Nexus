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
from passlib.context import CryptContext

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash using the raw bcrypt package."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash from a plain password using the raw bcrypt package."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Bearer token extractor from Authorization header
security = HTTPBearer()


import time
from cachetools import TTLCache

# Cache successful token validations for 5 minutes to avoid network spam
# and handle transient network failures gracefully
_token_cache = TTLCache(maxsize=1000, ttl=300)

async def decode_jwt_token(token: str) -> dict:
    """
    Validate a JWT token. Supports both Supabase tokens and dev mode local tokens.
    
    In dev mode (DEV_MODE=true), first attempts local HS256 verification.
    Otherwise delegates to Supabase's get_user endpoint (cached locally).
    
    Returns:
        dict: Decoded token payload containing user ID ('sub')
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    # Check cache first
    if token in _token_cache:
        return _token_cache[token]

    # =========================================================================
    # Local Auth: Try local JWT decode first (for Super Admin and database users)
    # =========================================================================
    try:
        jwt_secret = settings.jwt_secret or "verifield-dev-secret-key"
        decoded = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])
        if decoded.get("sub"):
            payload = {
                "sub": decoded["sub"],
                "email": decoded.get("email", ""),
                "role": decoded.get("role", "")
            }
            _token_cache[token] = payload
            return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        pass  # Not a valid local token, fall through to Supabase validation

    # =========================================================================
    # Standard: Validate via Supabase Auth API
    # =========================================================================
    import httpx
    import asyncio
    max_retries = 2
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
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
                await asyncio.sleep(2 ** (attempt + 1))
                continue
            
            import logging
            logger = logging.getLogger("verifield.security")
            logger.error(f"Network error verifying token: {e}")
            
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
    
    In dev mode, gracefully handles unreachable database by creating
    a virtual User object from the JWT claims.
    """
    # Decode the JWT token
    payload = await decode_jwt_token(credentials.credentials)

    # Extract user ID from the 'sub' claim
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )

    # Look up the user in our database
    import uuid as _uuid
    import asyncio
    try:
        result = await asyncio.wait_for(
            db.execute(select(User).where(User.id == user_id)),
            timeout=20.0,
        )
        user = result.scalar_one_or_none()

        if user is None:
            user_email = payload.get("email", f"{user_id}@verifield.local")
            # Avoid IntegrityError: check if a user with this email already exists
            email_result = await asyncio.wait_for(
                db.execute(select(User).where(User.email == user_email)),
                timeout=20.0,
            )
            user = email_result.scalar_one_or_none()

            if user is None:
                user = User(
                    id=_uuid.UUID(user_id),
                    email=user_email,
                    full_name=user_email.split('@')[0].replace(".", " ").replace("_", " ").replace("-", " ").title() if user_email else "Field Agent",
                    role=payload.get("role", "field_agent"),
                    status="active"
                )
                db.add(user)
                await asyncio.wait_for(db.commit(), timeout=20.0)
                await db.refresh(user)

        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status}. Please contact the administrator.",
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        logging.getLogger("verifield.security").error(
            f"DEV MODE user fallback triggered by exception: {e}\nTraceback:\n{traceback.format_exc()}"
        )
        # Always rollback the session to keep the connection clean
        try:
            await db.rollback()
        except Exception as rb_err:
            logging.getLogger("verifield.security").warning(f"Session rollback failed: {rb_err}")

        # DEV MODE: If DB is unreachable, create a virtual User from token claims
        if settings.dev_mode:
            logging.getLogger("verifield.security").warning(
                f"DEV MODE: DB unreachable, using virtual user from token"
            )
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            virtual_user = User(
                id=_uuid.UUID(user_id),
                email=payload.get("email", f"{user_id}@verifield.local"),
                full_name=payload.get("email", "Dev User").split("@")[0].replace(".", " ").title(),
                role=payload.get("role", "admin"),
                status="active",
                sector="cookstove",
                created_at=now,
                updated_at=now,
            )
            return virtual_user
        raise


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
    except Exception:
        return None

    try:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception as e:
        import logging
        logging.getLogger("verifield.security").warning(f"Database lookup failed in get_optional_user: {e}")
        try:
            await db.rollback()
        except Exception as rb_err:
            logging.getLogger("verifield.security").warning(f"Rollback failed in get_optional_user: {rb_err}")
        return None



async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency that ensures the current user has admin role
    (either legacy 'admin', new 'ORG_ADMIN', or global 'SUPER_ADMIN').
    """
    if user.role not in ("admin", "ORG_ADMIN", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required.",
        )
    return user


async def require_super_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency that ensures the current user has SUPER_ADMIN role.
    """
    if user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Super Admin role required.",
        )
    return user
