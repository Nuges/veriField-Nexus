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
from app.domains.projects.models import Project, CarbonCalculation
from app.domains.verification.models import VerificationTask
from app.main import app


def create_test_token(user_id, role, email="test@example.com", org_id=None):
    payload = {"sub": str(user_id), "role": role, "email": email}
    if org_id:
        payload["organization_id"] = str(org_id)
    return jwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_sod_and_security_negative_suite():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with async_session_factory() as session:
            org_a_id = uuid.uuid4()
            org_b_id = uuid.uuid4()

            org_a = Organization(
                id=org_a_id,
                name=f"Org A Test {org_a_id.hex[:6]}",
                org_type="DEVELOPER",
                status="ACTIVE",
            )
            org_b = Organization(
                id=org_b_id,
                name=f"Org B Test {org_b_id.hex[:6]}",
                org_type="DEVELOPER",
                status="ACTIVE",
            )
            session.add_all([org_a, org_b])

            pw = get_password_hash("TestPassword123!")

            agent_a_id = uuid.uuid4()
            agent_a = User(
                id=agent_a_id,
                email=f"agent_a_{agent_a_id.hex[:6]}@example.com",
                full_name="Agent Alpha",
                role="FIELD_AGENT",
                status="active",
                is_active=True,
                organization_id=org_a_id,
                password_hash=pw,
            )

            qa_a_id = uuid.uuid4()
            qa_a = User(
                id=qa_a_id,
                email=f"qa_a_{qa_a_id.hex[:6]}@example.com",
                full_name="QA Officer Alpha",
                role="QA_OFFICER",
                status="active",
                is_active=True,
                organization_id=org_a_id,
                password_hash=pw,
            )

            verifier_b_id = uuid.uuid4()
            verifier_b = User(
                id=verifier_b_id,
                email=f"verifier_b_{verifier_b_id.hex[:6]}@example.com",
                full_name="Verifier Beta",
                role="VERIFIER",
                status="active",
                is_active=True,
                organization_id=org_b_id,
                password_hash=pw,
            )

            proj_prod_id = uuid.uuid4()
            proj_prod = Project(
                id=proj_prod_id,
                name="Prod Clean Cookstoves Project",
                project_code=f"PRJ-{proj_prod_id.hex[:6].upper()}",
                organization_id=org_a_id,
                baseline_parameters={"data_classification": "PRODUCTION", "is_test": False},
            )

            proj_test_id = uuid.uuid4()
            proj_test = Project(
                id=proj_test_id,
                name="Pilot Test Cookstoves Project",
                project_code=f"TST-{proj_test_id.hex[:6].upper()}",
                organization_id=org_a_id,
                baseline_parameters={"data_classification": "TEST", "is_test": True},
            )

            act_a_id = uuid.uuid4()
            act_a = Activity(
                id=act_a_id,
                organization_id=org_a_id,
                user_id=agent_a_id,
                activity_type="cookstove_distribution",
                activity_data={"stove_id": "STV-001", "is_test": False},
                captured_at=datetime.now(timezone.utc),
                status="pending",
                validation_status="pending",
                trust_score=92.0,
            )

            task_a_id = uuid.uuid4()
            task_a = VerificationTask(
                id=task_a_id,
                project_id=proj_prod_id,
                verifier_id=agent_a_id,
                status="ASSIGNED",
                findings={"notes": "Auditing project documents"},
            )

            session.add_all([agent_a, qa_a, verifier_b, proj_prod, proj_test, act_a, task_a])
            await session.commit()

        token_agent_a = create_test_token(agent_a_id, "FIELD_AGENT", org_id=org_a_id)
        token_qa_a = create_test_token(qa_a_id, "QA_OFFICER", org_id=org_a_id)
        token_verifier_b = create_test_token(verifier_b_id, "VERIFIER", org_id=org_b_id)

        headers_agent_a = {"Authorization": f"Bearer {token_agent_a}"}
        headers_qa_a = {"Authorization": f"Bearer {token_qa_a}"}
        headers_verifier_b = {"Authorization": f"Bearer {token_verifier_b}"}

        # Test 1: Field Agent attempting to approve own submission (SoD) on PUT
        res1 = await client.put(
            f"/api/v1/activities/{act_a_id}",
            json={"status": "verified", "validation_status": "approved"},
            headers=headers_agent_a,
        )
        assert res1.status_code == 403

        # Test 2: Field Agent attempting to approve own submission on PATCH /status
        res2 = await client.patch(
            f"/api/v1/activities/{act_a_id}/status",
            json={"status": "verified"},
            headers=headers_agent_a,
        )
        assert res2.status_code == 403

        # Test 3: QA Officer approving another agent submission (Permitted)
        res3 = await client.patch(
            f"/api/v1/activities/{act_a_id}/status",
            json={"status": "verified"},
            headers=headers_qa_a,
        )
        assert res3.status_code == 200
        assert res3.json()["status"] == "verified"

        # Test 4: Verification Task IDOR / BOLA check
        res4 = await client.get(
            f"/api/v1/verification/tasks/{task_a_id}",
            headers=headers_verifier_b,
        )
        assert res4.status_code == 403

        res5 = await client.patch(
            f"/api/v1/verification/tasks/{task_a_id}",
            json={"status": "COMPLETED"},
            headers=headers_verifier_b,
        )
        assert res5.status_code == 403

        # Test 5: Ledger Minting on TEST/DEMO project rejection
        token_super_admin = create_test_token("00000000-0000-0000-0000-000000000001", "SUPER_ADMIN", email="segunoluwole22@gmail.com")
        headers_super_admin = {"Authorization": f"Bearer {token_super_admin}"}

        res7 = await client.post(
            "/api/v1/ledger/mint",
            json={"project_id": str(proj_test_id), "volume_tco2e": 15.0},
            headers=headers_super_admin,
        )
        assert res7.status_code == 400
        assert "Cannot mint carbon credits for non-production project" in res7.json().get("detail", "")

        # Test 6: Registry Package exclusion on TEST project
        res8 = await client.get(
            f"/api/v1/registry/package/VERRA/{proj_test_id}",
            headers=headers_super_admin,
        )
        assert res8.status_code == 404
        assert "Cannot generate official registry package for non-production project" in res8.json().get("detail", "")
