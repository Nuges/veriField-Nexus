"""

=============================================================================

VeriField Nexus — SSO API Routes

=============================================================================

Enterprise Single Sign-On endpoints supporting OIDC authorization code flow.

=============================================================================

"""



import logging

import secrets

from typing import Optional



from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession



from app.core.config import settings

from app.core.security import get_current_user

from app.core.sso import SSOProviderFactory

from app.db.session import get_db

from app.domains.authentication.models import User

from app.domains.authentication.service import AuthenticationService



logger = logging.getLogger("verifield.sso.api")



router = APIRouter(prefix="/auth/sso", tags=["Enterprise SSO"])





# ============================================================================

# Schemas

# ============================================================================



class SSOAuthorizeResponse(BaseModel):

    authorization_url: str

    state: str

    provider: str





class SSOCallbackRequest(BaseModel):

    code: str

    state: str

    redirect_uri: str





class SSOProviderInfo(BaseModel):

    name: str

    display_name: str

    icon: Optional[str] = None





class SSOConfigureRequest(BaseModel):

    provider_name: str

    client_id: str

    client_secret: str

    discovery_url: str

    domain_whitelist: list[str] = []

    auto_create_users: bool = True

    default_role: str = "field_agent"





PROVIDER_DISPLAY = {

    "microsoft": {"display_name": "Microsoft Entra ID", "icon": "microsoft"},

    "google": {"display_name": "Google Workspace", "icon": "google"},

    "okta": {"display_name": "Okta", "icon": "okta"},

    "auth0": {"display_name": "Auth0", "icon": "auth0"},

}





# ============================================================================

# Routes

# ============================================================================



@router.get("/providers")

async def list_sso_providers():

    """List available SSO providers that have been configured."""

    available = SSOProviderFactory.list_available_providers()

    providers = []

    for name in available:

        meta = PROVIDER_DISPLAY.get(name, {"display_name": name.title(), "icon": None})

        providers.append(SSOProviderInfo(name=name, **meta))

    return {"providers": providers}





@router.get("/{provider}/authorize", response_model=SSOAuthorizeResponse)

async def sso_authorize(

    provider: str,

    redirect_uri: str = "http://localhost:3000/login",

):

    """

    Initiate SSO login. Returns the IdP authorization URL to redirect the user.

    """

    try:

        sso = SSOProviderFactory.get_provider(provider)

    except ValueError as e:

        raise HTTPException(status_code=400, detail=str(e))



    state = secrets.token_urlsafe(32)



    try:

        auth_url = await sso.get_authorization_url(state, redirect_uri)

    except Exception as e:

        logger.error(f"SSO authorize error for {provider}: {e}")

        raise HTTPException(

            status_code=502,

            detail=f"Failed to connect to {provider} identity provider",

        )



    return SSOAuthorizeResponse(

        authorization_url=auth_url,

        state=state,

        provider=provider,

    )





@router.post("/{provider}/callback")

async def sso_callback(

    provider: str,

    body: SSOCallbackRequest,

    db: AsyncSession = Depends(get_db),

):

    """

    Handle SSO callback. Exchanges the authorization code for user info,

    finds or creates the local user, and returns a VeriField JWT.

    """

    try:

        sso = SSOProviderFactory.get_provider(provider)

    except ValueError as e:

        raise HTTPException(status_code=400, detail=str(e))



    # Exchange code for user information

    try:

        sso_user = await sso.exchange_code(body.code, body.redirect_uri)

    except Exception as e:

        logger.error(f"SSO callback error for {provider}: {e}")

        raise HTTPException(

            status_code=401,

            detail="SSO authentication failed. Please try again.",

        )



    if not sso_user.email:

        raise HTTPException(

            status_code=400,

            detail="SSO provider did not return an email address",

        )



    # Find or create local user

    result = await db.execute(select(User).where(User.email == sso_user.email))

    user = result.scalar_one_or_none()



    if user is None:

        # Auto-create user from SSO

        from app.core.security import get_password_hash



        user = User(

            email=sso_user.email,

            full_name=sso_user.full_name or sso_user.email.split("@")[0].title(),

            role="field_agent",

            status="active",

            avatar_url=sso_user.avatar_url,

            password_hash=get_password_hash(secrets.token_urlsafe(32)),

        )



        # Store SSO provider info in meta_data

        user.meta_data = {

            "sso_provider": provider,

            "sso_provider_user_id": sso_user.provider_user_id,

            "sso_email_verified": sso_user.email_verified,

        }



        db.add(user)

        await db.commit()

        await db.refresh(user)

        logger.info(f"Created new user from SSO ({provider}): {sso_user.email}")

    else:

        # Update SSO metadata on existing user

        md = dict(user.meta_data or {})

        md["sso_provider"] = provider

        md["sso_provider_user_id"] = sso_user.provider_user_id

        md["sso_last_login"] = __import__("datetime").datetime.now(

            __import__("datetime").timezone.utc

        ).isoformat()

        user.meta_data = md



        if sso_user.avatar_url and not user.avatar_url:

            user.avatar_url = sso_user.avatar_url



        await db.commit()



    if user.status != "active":

        raise HTTPException(

            status_code=403,

            detail=f"Account is {user.status}. Contact your administrator.",

        )



    # Generate VeriField JWT

    token = AuthenticationService.generate_token_static(user)



    from app.domains.authentication.schemas import UserResponse



    return {

        "user": UserResponse.model_validate(user),

        "access_token": token,

        "expires_in": 86400,

        "sso_provider": provider,

    }
