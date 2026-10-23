"""Both activity update routes enforce independent review, including legacy aliases."""
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.security import get_current_user
from app.core.rbac import has_permission, validate_separation_of_duties
from app.db.session import get_db
from app.domains.activities.repository import ActivityRepository

@pytest.mark.parametrize("role", ["SUPER_ADMIN", "ORG_ADMIN", "admin", "PROJECT_MANAGER", "FIELD_SUPERVISOR", "FIELD_AGENT", "QA_OFFICER", "AUDITOR", "COMPLIANCE_ADMIN", "REGISTRY_ADMIN", "FINANCE", "INVESTOR", "VIEWER"])
@pytest.mark.parametrize("method,suffix", [("PUT", ""), ("PATCH", "/status")])
@pytest.mark.asyncio
async def test_roles_cannot_verify_through_either_endpoint(role, method, suffix, monkeypatch):
    org_id, user_id, activity_id = uuid4(), uuid4(), uuid4()
    actor = SimpleNamespace(id=user_id, role=role, organization_id=org_id, is_active=True)
    existing = SimpleNamespace(id=activity_id, organization_id=org_id, user_id=uuid4())
    monkeypatch.setattr(ActivityRepository, "get_by_id", AsyncMock(return_value=existing))
    db = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none.return_value = existing
    db.execute.return_value = scalar
    async def database():
        yield db
    app.dependency_overrides[get_current_user] = lambda: actor
    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.test") as client:
            response = await client.request(method, f"/api/v1/activities/{activity_id}{suffix}", json={"status": "verified"})
        assert response.status_code == 403, response.text
        assert "VVB verifier" in response.text
        db.commit.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()

@pytest.mark.parametrize("role", ["SUPER_ADMIN", "ORG_ADMIN", "admin", "PROJECT_MANAGER", "FIELD_SUPERVISOR", "QA_OFFICER"])
def test_administrators_cannot_sign_as_independent_vvb(role):
    with pytest.raises(HTTPException) as exc:
        validate_separation_of_duties(SimpleNamespace(id=uuid4(), role=role), uuid4(), action="SIGN_OFF")
    assert exc.value.status_code == 403

def test_internal_quality_approval_is_not_independent_verification():
    for role in ["ORG_ADMIN", "admin", "FIELD_SUPERVISOR", "QA_OFFICER"]:
        assert has_permission(role, "activity:approve")
        assert not has_permission(role, "activity:verify")
    assert has_permission("vvb", "activity:verify")
