import uuid
from datetime import date, datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.authentication.models import User
from app.domains.biochar.models import BiocharBatch, ProductionFacility
from app.domains.biochar.puro_rules import seed_puro_biochar_normative_metadata
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
async def test_puro_tenant_isolation_and_idor_prevention(db_session: AsyncSession):
    """
    Tests multi-tenant isolation and IDOR protection between two synthetic organizations.
    User in Organization A must NOT be able to read or mutate Organization B's Puro resources.
    """
    await seed_puro_biochar_normative_metadata(db_session)

    suffix_a = uuid.uuid4().hex[:6]
    suffix_b = uuid.uuid4().hex[:6]

    # 1. Organization A
    org_a_id = uuid.uuid4()
    org_a = Organization(id=org_a_id, name=f"Synthetic Tenant Alpha {suffix_a}", org_type="DEVELOPER")
    db_session.add(org_a)

    user_a_id = uuid.uuid4()
    user_a = User(
        id=user_a_id,
        email=f"operator_a_{suffix_a}@synthetic-tenant-alpha.org",
        full_name="Operator Alpha",
        role="ORG_ADMIN",
        organization_id=org_a_id,
        is_active=True,
    )
    db_session.add(user_a)

    proj_a_id = uuid.uuid4()
    proj_a = Project(id=proj_a_id, name=f"Project Alpha {suffix_a}", project_code=f"PROJ-A-{suffix_a.upper()}", organization_id=org_a_id)
    db_session.add(proj_a)

    fac_a_id = uuid.uuid4()
    fac_a = ProductionFacility(
        id=fac_a_id,
        organization_id=org_a_id,
        project_id=proj_a_id,
        facility_code=f"FAC-A-{suffix_a.upper()}",
        facility_name="Facility Alpha",
    )
    db_session.add(fac_a)

    # 2. Organization B
    org_b_id = uuid.uuid4()
    org_b = Organization(id=org_b_id, name=f"Synthetic Tenant Beta {suffix_b}", org_type="DEVELOPER")
    db_session.add(org_b)

    user_b_id = uuid.uuid4()
    user_b = User(
        id=user_b_id,
        email=f"operator_b_{suffix_b}@synthetic-tenant-beta.org",
        full_name="Operator Beta",
        role="ORG_ADMIN",
        organization_id=org_b_id,
        is_active=True,
    )
    db_session.add(user_b)

    proj_b_id = uuid.uuid4()
    proj_b = Project(id=proj_b_id, name=f"Project Beta {suffix_b}", project_code=f"PROJ-B-{suffix_b.upper()}", organization_id=org_b_id)
    db_session.add(proj_b)

    fac_b_id = uuid.uuid4()
    fac_b = ProductionFacility(
        id=fac_b_id,
        organization_id=org_b_id,
        project_id=proj_b_id,
        facility_code=f"FAC-B-{suffix_b.upper()}",
        facility_name="Facility Beta",
    )
    db_session.add(fac_b)

    batch_b_id = uuid.uuid4()
    batch_b = BiocharBatch(
        id=batch_b_id,
        organization_id=org_b_id,
        project_id=proj_b_id,
        batch_number=f"BATCH-B-{suffix_b.upper()}",
        facility_name="Facility Beta",
        kiln_id="K-01",
        feedstock_type="WOOD_CHIPS",
        feedstock_weight_tonnes=10.0,
        moisture_content_pct=15.0,
        pyrolysis_temp_celsius=500.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=3.5,
    )
    db_session.add(batch_b)
    await db_session.commit()

    # User A headers
    token_a = _create_token(user_a_id, user_a.email, user_a.role, org_a_id)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. User A attempts to view Project B's readiness -> Must be 403 Forbidden
        res_readiness = await client.get(
            f"/api/v1/biochar/puro/projects/{proj_b_id}/readiness",
            headers=headers_a,
        )
        assert res_readiness.status_code == 403

        # B. User A attempts to register a supplier profile on Project B -> Must be 403 Forbidden
        res_supplier = await client.post(
            f"/api/v1/biochar/puro/projects/{proj_b_id}/supplier",
            headers=headers_a,
            json={
                "facility_id": str(fac_b_id),
                "supplier_legal_name": "Intruder Supplier",
                "jurisdiction_country": "Germany",
            },
        )
        assert res_supplier.status_code == 403

        # C. User A attempts to register facility profile on Facility B -> Must be 403 Forbidden
        res_fac_prof = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_b_id}/profile",
            headers=headers_a,
            json={
                "facility_id": str(fac_b_id),
                "facility_classification": "STATIONARY",
                "host_country": "Germany",
            },
        )
        assert res_fac_prof.status_code == 403

        # D. User A attempts to register crediting period on Facility B -> Must be 403 Forbidden
        res_cp = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_b_id}/crediting-periods",
            headers=headers_a,
            json={
                "facility_id": str(fac_b_id),
                "sequence_number": 1,
                "start_date": "2025-01-01",
                "end_date": "2034-12-31",
            },
        )
        assert res_cp.status_code == 403

        # E. User A attempts to execute quantification on Batch B -> Must be 403 Forbidden
        res_quant = await client.post(
            f"/api/v1/biochar/puro/batches/{batch_b_id}/quantification",
            headers=headers_a,
            json={
                "batch_id": str(batch_b_id),
                "soil_temperature_celsius": 15.0,
            },
        )
        assert res_quant.status_code == 403
