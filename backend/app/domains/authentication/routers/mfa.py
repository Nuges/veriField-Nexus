"""

=============================================================================

VeriField Nexus — MFA API Routes

=============================================================================

Endpoints for TOTP multi-factor authentication setup, verification,

recovery, and management.

=============================================================================

"""



import logging

from datetime import datetime, timedelta, timezone

from typing import Optional



import jwt as pyjwt

from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession



from app.core.config import settings

from app.core.mfa import MFAService

from app.core.security import get_current_user

from app.db.session import get_db

from app.domains.authentication.models import User



logger = logging.getLogger("verifield.mfa.api")



router = APIRouter(prefix="/auth/mfa", tags=["Multi-Factor Authentication"])





# ============================================================================

# Schemas

# ============================================================================



class MFASetupResponse(BaseModel):

    secret: str

    provisioning_uri: str

    qr_code_base64: Optional[str] = None





class MFAVerifyRequest(BaseModel):

    code: str





class MFAVerifySetupRequest(BaseModel):

    code: str

    secret: str





class MFALoginVerifyRequest(BaseModel):

    mfa_token: str

    code: str





class MFARecoveryRequest(BaseModel):

    mfa_token: str

    recovery_code: str





class MFAStatusResponse(BaseModel):

    mfa_enabled: bool

    recovery_codes_remaining: int = 0





class MFASetupCompleteResponse(BaseModel):

    mfa_enabled: bool

    recovery_codes: list[str]

    message: str





class MFADisableRequest(BaseModel):

    code: str





# ============================================================================

# Helpers

# ============================================================================



def _get_user_mfa_data(user: User) -> dict:

    """Get MFA data from user's meta_data JSON field."""

    md = user.meta_data or {}

    return md.get("mfa", {})





async def _set_user_mfa_data(db: AsyncSession, user: User, mfa_data: dict):

    """Set MFA data in user's meta_data JSON field."""

    import json

    from sqlalchemy import text

    md = dict(user.meta_data or {})

    md["mfa"] = mfa_data

    await db.execute(

        text("UPDATE users SET meta_data = :md WHERE id = :uid OR email = :email"),

        {"md": json.dumps(md), "uid": str(user.id), "email": str(user.email)}

    )

    await db.commit()





def _generate_mfa_token(user_id: str) -> str:

    """Generate a short-lived JWT for MFA verification step."""

    jwt_secret = settings.jwt_secret or "verifield-dev-secret-key"

    payload = {

        "sub": user_id,

        "purpose": "mfa_verify",

        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),

    }

    return pyjwt.encode(payload, jwt_secret, algorithm="HS256")





def _decode_mfa_token(token: str) -> str:

    """Decode and validate an MFA verification token. Returns user_id."""

    jwt_secret = settings.jwt_secret or "verifield-dev-secret-key"

    try:

        payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])

        if payload.get("purpose") != "mfa_verify":

            raise HTTPException(status_code=401, detail="Invalid MFA token")

        return payload["sub"]

    except pyjwt.ExpiredSignatureError:

        raise HTTPException(status_code=401, detail="MFA verification window expired")

    except Exception:

        raise HTTPException(status_code=401, detail="Invalid MFA token")





# ============================================================================

# Routes

# ============================================================================



@router.get("/status", response_model=MFAStatusResponse)

async def mfa_status(

    current_user: User = Depends(get_current_user),

):

    """Check if MFA is enabled for the current user."""

    mfa_data = _get_user_mfa_data(current_user)

    enabled = mfa_data.get("enabled", False)

    codes = mfa_data.get("recovery_hashes", [])

    return MFAStatusResponse(

        mfa_enabled=enabled,

        recovery_codes_remaining=len(codes),

    )





@router.post("/setup", response_model=MFASetupResponse)

async def mfa_setup(

    current_user: User = Depends(get_current_user),

):

    """Generate a new TOTP secret and QR code for MFA enrollment."""

    mfa_data = _get_user_mfa_data(current_user)

    if mfa_data.get("enabled"):

        raise HTTPException(

            status_code=400,

            detail="MFA is already enabled. Disable it first to re-enroll.",

        )



    secret = MFAService.generate_secret()

    email = current_user.email or f"{current_user.id}@verifield.io"

    uri = MFAService.generate_provisioning_uri(secret, email)

    qr = MFAService.generate_qr_code_base64(uri)



    return MFASetupResponse(

        secret=secret,

        provisioning_uri=uri,

        qr_code_base64=qr,

    )





@router.post("/verify-setup", response_model=MFASetupCompleteResponse)

async def mfa_verify_setup(

    body: MFAVerifySetupRequest,

    current_user: User = Depends(get_current_user),

    db: AsyncSession = Depends(get_db),

):

    """

    Verify the initial TOTP code to activate MFA.

    Returns one-time display of recovery codes.

    """

    if not MFAService.verify_totp(body.secret, body.code):

        raise HTTPException(status_code=400, detail="Invalid verification code")



    # Generate recovery codes

    recovery_codes = MFAService.generate_recovery_codes()

    recovery_hashes = [MFAService.hash_recovery_code(c) for c in recovery_codes]



    mfa_data = {

        "enabled": True,

        "totp_secret": body.secret,

        "recovery_hashes": recovery_hashes,

        "enabled_at": datetime.now(timezone.utc).isoformat(),

    }

    await _set_user_mfa_data(db, current_user, mfa_data)



    logger.info(f"MFA enabled for user {current_user.id}")



    return MFASetupCompleteResponse(

        mfa_enabled=True,

        recovery_codes=recovery_codes,

        message="MFA is now active. Save your recovery codes securely — they will not be shown again.",

    )





@router.post("/verify")

async def mfa_verify_login(

    body: MFALoginVerifyRequest,

    db: AsyncSession = Depends(get_db),

):

    """

    Verify TOTP code during login. Called after password auth when MFA is enabled.

    Requires the short-lived mfa_token returned by the login endpoint.

    """

    user_id = _decode_mfa_token(body.mfa_token)



    result = await db.execute(select(User).where(User.id == user_id))

    user = result.scalar_one_or_none()

    if not user:

        raise HTTPException(status_code=404, detail="User not found")



    mfa_data = _get_user_mfa_data(user)

    if not mfa_data.get("enabled"):

        raise HTTPException(status_code=400, detail="MFA is not enabled for this user")



    secret = mfa_data.get("totp_secret", "")

    if not MFAService.verify_totp(secret, body.code):

        raise HTTPException(status_code=401, detail="Invalid MFA code")



    # MFA verified — issue full access token

    from app.domains.authentication.service import AuthenticationService



    token = AuthenticationService.generate_token_static(user)



    return {

        "access_token": token,

        "expires_in": 86400,

        "mfa_verified": True,

    }





@router.post("/recovery")

async def mfa_recovery(

    body: MFARecoveryRequest,

    db: AsyncSession = Depends(get_db),

):

    """

    Use a recovery code to bypass TOTP during login.

    Each recovery code can only be used once.

    """

    user_id = _decode_mfa_token(body.mfa_token)



    result = await db.execute(select(User).where(User.id == user_id))

    user = result.scalar_one_or_none()

    if not user:

        raise HTTPException(status_code=404, detail="User not found")



    mfa_data = _get_user_mfa_data(user)

    hashes = mfa_data.get("recovery_hashes", [])



    valid, remaining = MFAService.verify_recovery_code(body.recovery_code, hashes)

    if not valid:

        raise HTTPException(status_code=401, detail="Invalid recovery code")



    # Consume the recovery code

    mfa_data["recovery_hashes"] = remaining

    await _set_user_mfa_data(db, user, mfa_data)



    logger.info(

        f"Recovery code used for user {user.id}. "

        f"{len(remaining)} codes remaining."

    )



    # Issue full access token

    from app.domains.authentication.service import AuthenticationService



    token = AuthenticationService.generate_token_static(user)



    return {

        "access_token": token,

        "expires_in": 86400,

        "mfa_verified": True,

        "recovery_codes_remaining": len(remaining),

    }





@router.delete("/disable")

async def mfa_disable(

    body: MFADisableRequest,

    current_user: User = Depends(get_current_user),

    db: AsyncSession = Depends(get_db),

):

    """Disable MFA. Requires a valid TOTP code to confirm."""

    mfa_data = _get_user_mfa_data(current_user)

    if not mfa_data.get("enabled"):

        raise HTTPException(status_code=400, detail="MFA is not enabled")



    secret = mfa_data.get("totp_secret", "")

    if not MFAService.verify_totp(secret, body.code):

        raise HTTPException(status_code=401, detail="Invalid MFA code")



    await _set_user_mfa_data(db, current_user, {"enabled": False})

    logger.info(f"MFA disabled for user {current_user.id}")



    return {"mfa_enabled": False, "message": "MFA has been disabled"}
