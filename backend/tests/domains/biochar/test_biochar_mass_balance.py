import uuid
from datetime import datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


def _create_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id) if org_id else None,
        "iat": now,
        "exp": now + timedelta(hours=2),
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_biochar_mass_balance_and_over_allocation_protection(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Synthetic Biochar Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"mb_auditor_{uuid.uuid4().hex[:6]}@synthetic-nexus.org",
        full_name="Synthetic Mass Balance Auditor",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name="Synthetic Industrial Biochar Plant Beta",
        project_code=f"SYN-MB-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        country="Brazil",
    )
    db_session.add(project)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create Batch of 20.0 tonnes biochar output
        batch_payload = {
            "project_id": str(project_id),
            "batch_number": f"BATCH-MB-{uuid.uuid4().hex[:6].upper()}",
            "facility_name": "Synthetic Facility Beta",
            "kiln_id": "KILN-02",
            "feedstock_type": "WOOD_RESIDUES",
            "feedstock_weight_tonnes": 60.0,
            "moisture_content_pct": 12.0,
            "pyrolysis_temp_celsius": 600.0,
            "residence_time_minutes": 40.0,
            "biochar_yield_tonnes": 20.0,
            "fixed_carbon_pct": 82.0,
            "ash_content_pct": 4.0,
            "molar_h_c_ratio": 0.32,
            "carbon_claim_registry": "PURO_STANDARD",
            "carbon_claim_methodology": "PURO_BIOCHAR_2025",
        }
        res_batch = await client.post("/api/v1/biochar/batches", json=batch_payload, headers=headers)
        assert res_batch.status_code == 201, res_batch.text
        batch_id = res_batch.json()["id"]

        # 2. Record Storage Event with 0.5 tonnes documented loss
        stor_payload = {
            "batch_id": batch_id,
            "storage_facility_name": "Beta Warehouse 1",
            "storage_location": "Zone C",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "quantity_stored_tonnes": 19.5,
            "loss_or_damage_tonnes": 0.5,
        }
        res_stor = await client.post("/api/v1/biochar/storage-events", json=stor_payload, headers=headers)
        assert res_stor.status_code == 201, res_stor.text

        # 3. Record Terminal End-Use of 12.0 tonnes
        eu_payload = {
            "project_id": str(project_id),
            "batch_id": batch_id,
            "end_use_type": "NON_SOIL_APPLICATION",
            "applied_quantity_tonnes": 12.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "product_category": "ASPHALT_ADDITIVE",
            "recipient_organization": "Synthetic Roadways Infrastructure",
            "durability_classification": "INFRASTRUCTURE_ASPHALT",
        }
        res_eu = await client.post("/api/v1/biochar/end-uses", json=eu_payload, headers=headers)
        assert res_eu.status_code == 201, res_eu.text

        # 4. Check Mass Balance Reconciliation:
        # produced = 20.0 t
        # terminal_end_use = 12.0 t
        # documented_losses = 0.5 t
        # remaining inventory = 7.5 t
        # total reconciled = 20.0 t -> RECONCILED
        res_mb = await client.get(f"/api/v1/biochar/batches/{batch_id}/mass-balance", headers=headers)
        assert res_mb.status_code == 200, res_mb.text
        mb_data = res_mb.json()
        assert mb_data["original_produced_mass_tonnes"] == 20.0
        assert mb_data["terminal_end_use_tonnes"] == 12.0
        assert mb_data["documented_losses_tonnes"] == 0.5
        assert mb_data["is_valid"] is True
        assert mb_data["status"] == "RECONCILED"

        # 5. Over-Allocation Protection:
        # Attempting to allocate 10.0 tonnes terminal end-use when only 7.5 tonnes remain (20 - 12 - 0.5 = 7.5)
        # MUST fail closed with 400 Bad Request!
        over_eu_payload = {
            "project_id": str(project_id),
            "batch_id": batch_id,
            "end_use_type": "NON_SOIL_APPLICATION",
            "applied_quantity_tonnes": 10.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "product_category": "CONCRETE_READYMIX",
            "recipient_organization": "Synthetic Construction Ltd",
        }
        res_over = await client.post("/api/v1/biochar/end-uses", json=over_eu_payload, headers=headers)
        assert res_over.status_code == 400, res_over.text
        assert "Mass balance violation" in res_over.json()["detail"]


@pytest.mark.asyncio
async def test_concurrent_allocation_real_db(db_session: AsyncSession):
    """
    Mandatory Section 14: Concurrency & Row-Locking Test.
    Batch available = 10.000 t
    Transaction A attempts to allocate 7.0 t
    Transaction B attempts to allocate 5.0 t simultaneously
    Exactly one succeeds (201 Created), the other fails (400 Bad Request).
    Final allocated mass must NEVER exceed 10.0 t.
    """
    import asyncio

    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Concurrent Biochar Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"concurrency_operator_{uuid.uuid4().hex[:6]}@synthetic-nexus.org",
        full_name="Concurrency Operator",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name="Concurrent Biochar Project",
        project_code=f"SYN-CONC-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        country="Kenya",
    )
    db_session.add(project)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create a fresh batch with 10.000 t yield
        batch_payload = {
            "project_id": str(project_id),
            "batch_number": f"BATCH-CONC-{uuid.uuid4().hex[:6].upper()}",
            "facility_name": "Concurrent Pyrolysis Hub",
            "kiln_id": "KILN-CONC",
            "feedstock_type": "COFFEE_HUSK",
            "feedstock_weight_tonnes": 30.0,
            "moisture_content_pct": 10.0,
            "pyrolysis_temp_celsius": 650.0,
            "residence_time_minutes": 45.0,
            "biochar_yield_tonnes": 10.0,
            "fixed_carbon_pct": 80.0,
            "ash_content_pct": 5.0,
            "molar_h_c_ratio": 0.35,
        }
        res_batch = await client.post("/api/v1/biochar/batches", json=batch_payload, headers=headers)
        assert res_batch.status_code == 201, res_batch.text
        batch_id = res_batch.json()["id"]

        # Prepare simultaneous allocations: 7.0 t and 5.0 t
        payload_a = {
            "project_id": str(project_id),
            "batch_id": batch_id,
            "end_use_type": "NON_SOIL_APPLICATION",
            "applied_quantity_tonnes": 7.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "product_category": "CONCRETE_ADDITIVE",
            "recipient_organization": "Client A Infrastructure",
        }
        payload_b = {
            "project_id": str(project_id),
            "batch_id": batch_id,
            "end_use_type": "NON_SOIL_APPLICATION",
            "applied_quantity_tonnes": 5.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "product_category": "FILTRATION_CARBON",
            "recipient_organization": "Client B Waterworks",
        }

        # Fire simultaneously
        res_a, res_b = await asyncio.gather(
            client.post("/api/v1/biochar/end-uses", json=payload_a, headers=headers),
            client.post("/api/v1/biochar/end-uses", json=payload_b, headers=headers),
            return_exceptions=False,
        )

        status_codes = [res_a.status_code, res_b.status_code]
        assert 201 in status_codes, f"Expected one successful allocation, got: {status_codes}"
        assert 400 in status_codes, f"Expected one failed allocation, got: {status_codes}"

        # Verify exact failure detail
        failed_res = res_a if res_a.status_code == 400 else res_b
        assert "Mass balance violation" in failed_res.json()["detail"]

        # Final check on batch mass balance: total allocated must never exceed 10.0 t
        res_mb = await client.get(f"/api/v1/biochar/batches/{batch_id}/mass-balance", headers=headers)
        assert res_mb.status_code == 200, res_mb.text
        mb = res_mb.json()
        assert mb["terminal_end_use_tonnes"] <= 10.0
        assert mb["is_valid"] is True
        assert mb["status"] == "RECONCILED"

