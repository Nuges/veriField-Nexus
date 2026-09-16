import uuid
from datetime import datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    FeedstockLot,
    FeedstockSource,
    ProductionFacility,
)
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
async def test_biochar_tenant_isolation_and_idor_protection(db_session: AsyncSession):
    """
    Mandatory Section 50: Test API-level IDOR & Tenant Isolation for Biochar.
    Tenant A resources must never be accessible or modifiable by Tenant B.
    """
    # Tenant A
    org_a = Organization(id=uuid.uuid4(), name=f"Tenant A Biochar Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org_a)
    user_a = User(
        id=uuid.uuid4(),
        email=f"user_a_{uuid.uuid4().hex[:6]}@tenant-a.org",
        full_name="User A",
        role="ORG_ADMIN",
        organization_id=org_a.id,
        is_active=True,
    )
    db_session.add(user_a)
    proj_a = Project(
        id=uuid.uuid4(),
        name="Project A",
        project_code=f"PRJ-A-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_a.id,
        country="Kenya",
    )
    db_session.add(proj_a)

    # Tenant B
    org_b = Organization(id=uuid.uuid4(), name=f"Tenant B Biochar Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org_b)
    user_b = User(
        id=uuid.uuid4(),
        email=f"user_b_{uuid.uuid4().hex[:6]}@tenant-b.org",
        full_name="User B",
        role="ORG_ADMIN",
        organization_id=org_b.id,
        is_active=True,
    )
    db_session.add(user_b)
    proj_b = Project(
        id=uuid.uuid4(),
        name="Project B",
        project_code=f"PRJ-B-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_b.id,
        country="Uganda",
    )
    db_session.add(proj_b)

    # Resource in Tenant A: Source and Batch
    src_a = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        project_id=proj_a.id,
        source_code=f"SRC-A-{uuid.uuid4().hex[:4].upper()}",
        source_name="Tenant A Coffee Husk Source",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="COFFEE_HUSK",
        origin_location="Region A",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="DECAY",
        sustainability_status="LOW_RISK",
    )
    db_session.add(src_a)

    batch_a = BiocharBatch(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        project_id=proj_a.id,
        batch_number=f"BATCH-A-{uuid.uuid4().hex[:6].upper()}",
        facility_name="Facility A",
        kiln_id="KILN-A",
        feedstock_type="COFFEE_HUSK",
        feedstock_weight_tonnes=10.0,
        moisture_content_pct=10.0,
        pyrolysis_temp_celsius=600.0,
        residence_time_minutes=30.0,
        biochar_yield_tonnes=3.0,
        fixed_carbon_pct=80.0,
        ash_content_pct=4.0,
        molar_h_c_ratio=0.35,
        status="PRODUCED",
    )
    db_session.add(batch_a)
    await db_session.commit()

    token_b = _create_token(user_b.id, user_b.email, user_b.role, org_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Tenant B requests Batch A directly by ID -> Must be 403 or 404
        res_get_batch = await client.get(f"/api/v1/biochar/batches/{batch_a.id}", headers=headers_b)
        assert res_get_batch.status_code in (403, 404), f"Expected 403 or 404, got {res_get_batch.status_code}"

        # 2. Tenant B lists batches -> Must NOT contain Batch A
        res_list = await client.get("/api/v1/biochar/batches", headers=headers_b)
        assert res_list.status_code == 200
        batch_ids = [b["id"] for b in res_list.json()]
        assert str(batch_a.id) not in batch_ids

        # 3. Tenant B lists sources -> Must NOT contain Source A
        res_sources = await client.get("/api/v1/biochar/sources", headers=headers_b)
        assert res_sources.status_code == 200
        source_ids = [s["id"] for s in res_sources.json()]
        assert str(src_a.id) not in source_ids

        # 4. Tenant B tries to create a lot using Tenant A's Source -> Must be rejected
        cross_lot_payload = {
            "project_id": str(proj_b.id),
            "source_id": str(src_a.id),
            "lot_number": f"LOT-CROSS-{uuid.uuid4().hex[:6].upper()}",
            "feedstock_type": "COFFEE_HUSK",
            "mass_received_tonnes": 20.0,
            "moisture_content_pct": 10.0,
        }
        res_cross = await client.post("/api/v1/biochar/lots", json=cross_lot_payload, headers=headers_b)
        # Lot's source belongs to Tenant A; Tenant B cannot associate Tenant A's source
        assert res_cross.status_code in (400, 403, 404)


@pytest.mark.asyncio
async def test_biochar_large_volume_pagination(db_session: AsyncSession):
    """
    Mandatory Section 52: Pagination test with 100+ lots and batches.
    Validates limit and offset without unbounded query returns.
    """
    org = Organization(id=uuid.uuid4(), name=f"Pagination Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)
    user = User(
        id=uuid.uuid4(),
        email=f"page_user_{uuid.uuid4().hex[:6]}@page-nexus.org",
        full_name="Page User",
        role="ORG_ADMIN",
        organization_id=org.id,
        is_active=True,
    )
    db_session.add(user)
    proj = Project(
        id=uuid.uuid4(),
        name="Pagination Project",
        project_code=f"PRJ-PAGE-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org.id,
        country="Kenya",
    )
    db_session.add(proj)

    source = FeedstockSource(
        id=uuid.uuid4(),
        organization_id=org.id,
        project_id=proj.id,
        source_code=f"SRC-PAGE-{uuid.uuid4().hex[:4].upper()}",
        source_name="Page Source",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="BAGASSE",
        origin_location="Kisumu",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="DECAY",
        sustainability_status="LOW_RISK",
    )
    db_session.add(source)

    # Bulk insert 105 Feedstock Lots
    lots = [
        FeedstockLot(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            source_id=source.id,
            lot_number=f"LOT-P-{i:04d}-{uuid.uuid4().hex[:4]}",
            feedstock_type="BAGASSE",
            mass_received_tonnes=10.0,
            moisture_content_pct=15.0,
            dry_mass_tonnes=8.5,
            allocated_mass_tonnes=0.0,
            created_at=datetime.now(timezone.utc),
        )
        for i in range(105)
    ]
    db_session.add_all(lots)
    await db_session.commit()

    token = _create_token(user.id, user.email, user.role, org.id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Page 1: limit 50, offset 0 -> exactly 50 items
        res_p1 = await client.get(f"/api/v1/biochar/lots?project_id={proj.id}&limit=50&offset=0", headers=headers)
        assert res_p1.status_code == 200
        p1_data = res_p1.json()
        assert len(p1_data) == 50

        # Page 2: limit 50, offset 50 -> exactly 50 items
        res_p2 = await client.get(f"/api/v1/biochar/lots?project_id={proj.id}&limit=50&offset=50", headers=headers)
        assert res_p2.status_code == 200
        p2_data = res_p2.json()
        assert len(p2_data) == 50

        # Page 3: limit 50, offset 100 -> exactly 5 items remaining
        res_p3 = await client.get(f"/api/v1/biochar/lots?project_id={proj.id}&limit=50&offset=100", headers=headers)
        assert res_p3.status_code == 200
        p3_data = res_p3.json()
        assert len(p3_data) == 5

        # Verify no overlap between page 1 and page 2
        p1_ids = {item["id"] for item in p1_data}
        p2_ids = {item["id"] for item in p2_data}
        assert len(p1_ids.intersection(p2_ids)) == 0
