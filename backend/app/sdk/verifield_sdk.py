"""

=============================================================================

VeriField Nexus — Official Python SDK Client

=============================================================================

Provides a clean, type-annotated client interface for interacting with the

VeriField Nexus climate MRV platform backend APIs.

=============================================================================

"""



from typing import Any, Dict, Optional

import httpx

from app.main import app





class VeriFieldClient:

    """Official Python SDK Client for VeriField Nexus APIs."""



    def __init__(self, base_url: str = "http://testserver"):

        self.base_url = base_url.rstrip("/")

        self.access_token: Optional[str] = None

        self.transport = httpx.ASGITransport(app=app)



    def _get_headers(self) -> Dict[str, str]:

        headers = {"Content-Type": "application/json"}

        if self.access_token:

            headers["Authorization"] = f"Bearer {self.access_token}"

        return headers



    async def login(self, email: str, password: str) -> Dict[str, Any]:

        """Authenticate user and acquire JWT access token."""

        url = "/api/v1/auth/login"

        async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:

            res = await client.post(url, json={"email": email, "password": password})

            res.raise_for_status()

            data = res.json()

            self.access_token = data.get("access_token")

            return data



    async def signup(self, email: str, full_name: str, password: str, role: str = "FIELD_AGENT", organization: Optional[str] = None) -> Dict[str, Any]:

        """Register a new user account."""

        url = "/api/v1/auth/signup"

        payload = {

            "email": email,

            "full_name": full_name,

            "password": password,

            "role": role,

            "organization": organization

        }

        async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:

            res = await client.post(url, json=payload)

            res.raise_for_status()

            return res.json()



    async def create_project(self, name: str, country: str = "Kenya", registry_id: str = "VERRA", baseline_source: str = "firewood") -> Dict[str, Any]:

        """Create a new registered project."""

        url = "/api/v1/projects"

        payload = {

            "name": name,

            "country": country,

            "registry_id": registry_id,

            "baseline_source": baseline_source

        }

        async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:

            res = await client.post(url, json=payload, headers=self._get_headers())

            res.raise_for_status()

            return res.json()



    async def list_projects(self) -> Dict[str, Any]:

        """List all projects in current organization."""

        url = "/api/v1/projects"

        async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:

            res = await client.get(url, headers=self._get_headers())

            res.raise_for_status()

            return res.json()



    async def create_asset(self, project_id: str, name: str, latitude: float = -0.0917, longitude: float = 34.7680) -> Dict[str, Any]:

        """Create an asset associated with a project."""

        url = "/api/v1/assets"

        payload = {

            "project_id": project_id,

            "name": name,

            "latitude": latitude,

            "longitude": longitude

        }

        async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:

            res = await client.post(url, json=payload, headers=self._get_headers())

            res.raise_for_status()

            return res.json()



    async def create_activity(self, client_id: str, activity_type: str, asset_id: str, activity_data: Dict[str, Any], status: str = "verified") -> Dict[str, Any]:

        """Submit a field activity record."""

        url = "/api/v1/activities"

        payload = {

            "client_id": client_id,

            "activity_type": activity_type,

            "status": status,

            "captured_at": "2026-07-28T21:00:00Z",

            "asset_id": asset_id,

            "notes": "SDK field submission",

            "activity_data": activity_data

        }

        async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:

            res = await client.post(url, json=payload, headers=self._get_headers())

            res.raise_for_status()

            return res.json()



    async def upload_evidence(self, activity_id: str, evidence_type: str, file_uri: str, file_hash: str, metadata_json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

        """Upload evidence package."""

        url = "/api/v1/evidence"

        payload = {

            "activity_id": activity_id,

            "evidence_type": evidence_type,

            "file_uri": file_uri,

            "file_hash": file_hash,

            "metadata_json": metadata_json or {}

        }

        async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:

            res = await client.post(url, json=payload, headers=self._get_headers())

            res.raise_for_status()

            return res.json()



    async def ask_ai(self, query: str) -> Dict[str, Any]:

        """Query the AI Trust Engine Orchestrator."""

        url = "/api/v1/ai/chat"

        async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:

            res = await client.post(url, json={"query": query}, headers=self._get_headers())

            res.raise_for_status()

            return res.json()
