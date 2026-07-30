"""

=============================================================================

VeriField Nexus — Enterprise SSO / OIDC Provider Abstraction

=============================================================================

Config-driven identity layer for enterprise SSO. Supports OIDC discovery,

authorization code flow, and pluggable providers (Microsoft Entra, Google,

Okta, or any OIDC-compliant IdP).

=============================================================================

"""



import logging

from abc import ABC, abstractmethod

from typing import Any, Dict, List, Optional

from uuid import UUID



import httpx



from app.core.config import settings



logger = logging.getLogger("verifield.sso")





class SSOUserInfo:

    """Normalized user information from an SSO provider."""



    def __init__(

        self,

        email: str,

        full_name: str,

        provider: str,

        provider_user_id: str,

        email_verified: bool = False,

        avatar_url: Optional[str] = None,

        organization_hint: Optional[str] = None,

        raw_claims: Optional[Dict[str, Any]] = None,

    ):

        self.email = email

        self.full_name = full_name

        self.provider = provider

        self.provider_user_id = provider_user_id

        self.email_verified = email_verified

        self.avatar_url = avatar_url

        self.organization_hint = organization_hint

        self.raw_claims = raw_claims or {}





class SSOProvider(ABC):

    """Abstract base class for SSO identity providers."""



    @abstractmethod

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:

        """Return the URL to redirect the user for authentication."""

        ...



    @abstractmethod

    async def exchange_code(self, code: str, redirect_uri: str) -> SSOUserInfo:

        """Exchange an authorization code for user information."""

        ...



    @abstractmethod

    def get_provider_name(self) -> str:

        """Return the provider name identifier."""

        ...





class OIDCProvider(SSOProvider):

    """

    Generic OpenID Connect provider. Supports any OIDC-compliant IdP

    via discovery endpoint (/.well-known/openid-configuration).

    """



    def __init__(

        self,

        provider_name: str,

        client_id: str,

        client_secret: str,

        discovery_url: str,

        scopes: Optional[List[str]] = None,

    ):

        self.provider_name = provider_name

        self.client_id = client_id

        self.client_secret = client_secret

        self.discovery_url = discovery_url

        self.scopes = scopes or ["openid", "email", "profile"]

        self._discovery_cache: Optional[Dict[str, Any]] = None



    def get_provider_name(self) -> str:

        return self.provider_name



    async def _discover(self) -> Dict[str, Any]:

        """Fetch and cache the OIDC discovery document."""

        if self._discovery_cache:

            return self._discovery_cache

        async with httpx.AsyncClient(timeout=15.0) as client:

            resp = await client.get(self.discovery_url)

            resp.raise_for_status()

            self._discovery_cache = resp.json()

            return self._discovery_cache



    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:

        """Build the OIDC authorization URL."""

        discovery = await self._discover()

        auth_endpoint = discovery["authorization_endpoint"]

        scope_str = " ".join(self.scopes)

        params = {

            "client_id": self.client_id,

            "redirect_uri": redirect_uri,

            "response_type": "code",

            "scope": scope_str,

            "state": state,

        }

        query = "&".join(f"{k}={httpx.URL('', params={k: v}).params[k]}" for k, v in params.items())

        return f"{auth_endpoint}?{query}"



    async def exchange_code(self, code: str, redirect_uri: str) -> SSOUserInfo:

        """Exchange authorization code for tokens and extract user info."""

        discovery = await self._discover()

        token_endpoint = discovery["token_endpoint"]

        userinfo_endpoint = discovery.get("userinfo_endpoint")



        # Exchange code for tokens

        async with httpx.AsyncClient(timeout=15.0) as client:

            token_resp = await client.post(

                token_endpoint,

                data={

                    "grant_type": "authorization_code",

                    "code": code,

                    "redirect_uri": redirect_uri,

                    "client_id": self.client_id,

                    "client_secret": self.client_secret,

                },

            )

            token_resp.raise_for_status()

            token_data = token_resp.json()



        access_token = token_data.get("access_token", "")



        # Get user info from the userinfo endpoint

        user_data = {}

        if userinfo_endpoint and access_token:

            async with httpx.AsyncClient(timeout=15.0) as client:

                info_resp = await client.get(

                    userinfo_endpoint,

                    headers={"Authorization": f"Bearer {access_token}"},

                )

                if info_resp.status_code == 200:

                    user_data = info_resp.json()



        # Extract standard OIDC claims

        email = user_data.get("email", "")

        name = user_data.get("name", "")

        if not name:

            given = user_data.get("given_name", "")

            family = user_data.get("family_name", "")

            name = f"{given} {family}".strip() or email.split("@")[0]



        return SSOUserInfo(

            email=email,

            full_name=name,

            provider=self.provider_name,

            provider_user_id=user_data.get("sub", ""),

            email_verified=user_data.get("email_verified", False),

            avatar_url=user_data.get("picture"),

            organization_hint=email.split("@")[-1] if email else None,

            raw_claims=user_data,

        )





# ============================================================================

# Pre-configured provider templates

# ============================================================================



PROVIDER_TEMPLATES: Dict[str, Dict[str, str]] = {

    "microsoft": {

        "discovery_url": "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",

    },

    "google": {

        "discovery_url": "https://accounts.google.com/.well-known/openid-configuration",

    },

    "okta": {

        # Requires org-specific URL: https://{org}.okta.com/.well-known/openid-configuration

        "discovery_url": "",

    },

    "auth0": {

        # Requires tenant-specific URL: https://{tenant}.auth0.com/.well-known/openid-configuration

        "discovery_url": "",

    },

}





class SSOProviderFactory:

    """Factory for creating SSO providers from configuration."""



    _providers: Dict[str, SSOProvider] = {}



    @classmethod

    def get_provider(

        cls,

        provider_name: str,

        client_id: Optional[str] = None,

        client_secret: Optional[str] = None,

        discovery_url: Optional[str] = None,

    ) -> SSOProvider:

        """

        Get or create an SSO provider by name.

        Falls back to environment variables for configuration:

          SSO_{PROVIDER}_CLIENT_ID

          SSO_{PROVIDER}_CLIENT_SECRET

          SSO_{PROVIDER}_DISCOVERY_URL

        """

        cache_key = provider_name.lower()

        if cache_key in cls._providers:

            return cls._providers[cache_key]



        import os



        prefix = f"SSO_{provider_name.upper()}"

        cid = client_id or os.environ.get(f"{prefix}_CLIENT_ID", "")

        csecret = client_secret or os.environ.get(f"{prefix}_CLIENT_SECRET", "")

        disc = discovery_url or os.environ.get(f"{prefix}_DISCOVERY_URL", "")



        # Fall back to template discovery URL

        if not disc and provider_name.lower() in PROVIDER_TEMPLATES:

            disc = PROVIDER_TEMPLATES[provider_name.lower()].get("discovery_url", "")



        if not cid or not csecret or not disc:

            raise ValueError(

                f"SSO provider '{provider_name}' is not configured. "

                f"Set {prefix}_CLIENT_ID, {prefix}_CLIENT_SECRET, and "

                f"{prefix}_DISCOVERY_URL environment variables."

            )



        provider = OIDCProvider(

            provider_name=cache_key,

            client_id=cid,

            client_secret=csecret,

            discovery_url=disc,

        )

        cls._providers[cache_key] = provider

        return provider



    @classmethod

    def list_available_providers(cls) -> List[str]:

        """List SSO provider names that have valid configuration."""

        import os



        available = []

        for name in PROVIDER_TEMPLATES:

            prefix = f"SSO_{name.upper()}"

            if os.environ.get(f"{prefix}_CLIENT_ID"):

                available.append(name)

        return available
