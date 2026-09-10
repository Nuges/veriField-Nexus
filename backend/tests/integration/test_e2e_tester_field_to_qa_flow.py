import uuid
import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
import jwt

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import async_session_factory
from app.domains.activities.models import Activity
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


def create_test_token(user_id, role, email="test@example.com", org_id=None):
    payload = {"sub": str(user_id), "role": role, "email": email}
    if org_id:
        payload["organization_id"] = str(org_id)
    return jwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_e2e_tester_field_to_qa_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with async_session_factory() as session:
            org_id = uuid.uuid4()
            org = Organization(
                id=org_id,
                name=f"E2E Test Org {org_id.hex[:6]}",
                org_type="DEVELOPER",
                status="ACTIVE",
            )
            session.add(org)

            pw = get_password_hash("TestPassword123!")

            agent_id = uuid.uuid4()
            agent = User(
                id=agent_id,
                email=f"tester_agent_{agent_id.hex[:6]}@example.com",
                full_name="External Tester Agent",
                role="FIELD_AGENT",
                status="active",
                is_active=True,
                organization_id=org_id,
                password_hash=pw,
            )

            qa_id = uuid.uuid4()
            qa = User(
                id=qa_id,
                email=f"tester_qa_{qa_id.hex[:6]}@example.com",
                full_name="Assigned QA Officer",
                role="QA_OFFICER",
                status="active",
                is_active=True,
                organization_id=org_id,
                password_hash=pw,
            )

            proj_id = uuid.uuid4()
            proj = Project(
                id=proj_id,
                name="E2E Controlled Cookstoves Project",
                project_code=f"E2E-{proj_id.hex[:6].upper()}",
                organization_id=org_id,
                baseline_parameters={"data_classification": "TEST", "is_test": True},
            )

            session.add_all([agent, qa, proj])
            await session.commit()

        token_agent = create_test_token(agent_id, "FIELD_AGENT", org_id=org_id)
        token_qa = create_test_token(qa_id, "QA_OFFICER", org_id=org_id)

        headers_agent = {"Authorization": f"Bearer {token_agent}"}
        headers_qa = {"Authorization": f"Bearer {token_qa}"}

        # Step 1: External tester submits activity
        submit_payload = {
            "activity_type": "cookstove_distribution",
            "project_id": str(proj_id),
            "activity_data": {
                "stove_id": f"STV-{uuid.uuid4().hex[:6].upper()}",
                "fuel_type": "biomass_pellet",
                "household_id": "HH-NGA-9921",
                "data_classification": "TEST",
                "is_test": True,
            },
            "description": "Controlled field test installation for external QA verification",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "latitude": 9.0765,
            "longitude": 7.3986,
            "gps_accuracy": 4.5,
        }

        res_create = await client.post(
            "/api/v1/activities",
            json=submit_payload,
            headers=headers_agent,
        )
        assert res_create.status_code == 201, f"Create failed: {res_create.text}"
        activity_data = res_create.json()
        activity_id = activity_data["id"]
        assert activity_data["status"] == "pending"

        # Step 2: Submitting agent attempts self-approval -> BLOCKED
        res_self_approve = await client.put(
            f"/api/v1/activities/{activity_id}",
            json={"status": "verified", "validation_status": "approved"},
            headers=headers_agent,
        )
        assert res_self_approve.status_code == 403

        # Step 3: QA Officer reviews activity details
        res_get = await client.get(
            f"/api/v1/activities/{activity_id}",
            headers=headers_qa,
        )
        assert res_get.status_code == 200
        assert res_get.json()["status"] in ("pending", "review")

        # Step 4: QA Officer verifies activity
        res_verify = await client.patch(
            f"/api/v1/activities/{activity_id}/status",
            json={"status": "verified"},
            headers=headers_qa,
        )
        assert res_verify.status_code == 200
        assert res_verify.json()["status"] == "verified"

        # Step 5: Verify persistence in database
        async with async_session_factory() as session:
            act_db = await session.get(Activity, (uuid.UUID(activity_id), org_id, datetime.fromisoformat(activity_data["created_at"].replace("Z", "+00:00"))))
            if not act_db:
                from sqlalchemy import select
                stmt = select(Activity).where(Activity.id == uuid.UUID(activity_id))
                res = await session.execute(stmt)
                act_db = res.scalar_one_or_none()
            assert act_db is not None
            assert act_db.status == "verified"
