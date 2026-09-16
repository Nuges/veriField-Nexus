import uuid
from datetime import date, datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.authentication.models import User
from app.domains.biochar.models import FeedstockSource, ProductionFacility
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
async def test_biochar_standards_eligibility_engine(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Eligibility Testing Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"eligibility_analyst_{uuid.uuid4().hex[:6]}@synthetic-nexus.org",
        full_name="Synthetic Eligibility Analyst",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    # 1. Project A: Existing Operational Facility (Ineligible under VM0044 v1.2, Eligible under Puro)
    proj_a_id = uuid.uuid4()
    proj_a = Project(
        id=proj_a_id,
        name="Synthetic Existing Facility Project",
        project_code=f"PROJ-EX-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        country="Germany",
    )
    db_session.add(proj_a)

    fac_existing = ProductionFacility(
        organization_id=org_id,
        project_id=proj_a_id,
        facility_code=f"FAC-EX-{uuid.uuid4().hex[:4].upper()}",
        facility_name="Legacy Operational Kiln Plant",
        facility_status="EXISTING_OPERATIONAL",
        technology_type="SLOW_PYROLYSIS",
    )
    db_session.add(fac_existing)

    src_a = FeedstockSource(
        organization_id=org_id,
        project_id=proj_a_id,
        source_code=f"SRC-EX-{uuid.uuid4().hex[:4].upper()}",
        source_name="Sustainable Forestry Sawmill Offcuts",
        source_type="FORESTRY_RESIDUE",
        biomass_type="WOOD_CHIPS",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="DECAY",
    )
    db_session.add(src_a)

    # 2. Project B: New Operational Facility (Eligible under VM0044 v1.2)
    proj_b_id = uuid.uuid4()
    proj_b = Project(
        id=proj_b_id,
        name="Synthetic Greenfield Facility Project",
        project_code=f"PROJ-NEW-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        country="Uganda",
    )
    db_session.add(proj_b)

    fac_new = ProductionFacility(
        organization_id=org_id,
        project_id=proj_b_id,
        facility_code=f"FAC-NEW-{uuid.uuid4().hex[:4].upper()}",
        facility_name="Greenfield Continuous Pyrolyzer Unit",
        facility_status="NEW_OPERATIONAL",
        technology_type="SLOW_PYROLYSIS",
    )
    db_session.add(fac_new)

    src_b = FeedstockSource(
        organization_id=org_id,
        project_id=proj_b_id,
        source_code=f"SRC-NEW-{uuid.uuid4().hex[:4].upper()}",
        source_name="Post-Harvest Maize Stover Supply",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="CROP_RESIDUE",
        waste_status="CONFIRMED_WASTE_BIOMASS",
        baseline_fate="OPEN_BURNING",
    )
    db_session.add(src_b)

    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. Evaluate Project A against Verra VM0044 v1.2 -> Ineligible because facility is EXISTING_OPERATIONAL
        res_v_a = await client.get(
            f"/api/v1/biochar/projects/{proj_a_id}/eligibility?target_standard=VERRA&target_methodology=VM0044&methodology_version=v1.2",
            headers=headers,
        )
        assert res_v_a.status_code == 200, res_v_a.text
        data_v_a = res_v_a.json()
        assert data_v_a["facility_criteria_met"] is False
        assert data_v_a["eligibility_status"] == "INELIGIBLE"
        assert any("requires a new biochar production facility" in b for b in data_v_a["blocking_findings"])

        # B. Evaluate Project A against Puro Standard 2025 v2 -> Accepted because Puro permits existing facilities
        res_p_a = await client.get(
            f"/api/v1/biochar/projects/{proj_a_id}/eligibility?target_standard=PURO_STANDARD&target_methodology=PURO_BIOCHAR_2025&methodology_version=Edition_2025_v2",
            headers=headers,
        )
        assert res_p_a.status_code == 200, res_p_a.text
        data_p_a = res_p_a.json()
        assert data_p_a["facility_criteria_met"] is True
        assert data_p_a["eligibility_status"] == "POTENTIALLY_ELIGIBLE"
        assert data_p_a["additionality_status"] == "PURO_ADDITIONALITY_ACCEPTED"

        # C. Evaluate Project B against Verra VM0044 v1.2 -> Meets new facility and waste feedstock criteria
        res_v_b = await client.get(
            f"/api/v1/biochar/projects/{proj_b_id}/eligibility?target_standard=VERRA&target_methodology=VM0044&methodology_version=v1.2",
            headers=headers,
        )
        assert res_v_b.status_code == 200, res_v_b.text
        data_v_b = res_v_b.json()
        assert data_v_b["facility_criteria_met"] is True
        assert data_v_b["feedstock_criteria_met"] is True
        assert data_v_b["eligibility_status"] == "POTENTIALLY_ELIGIBLE"
        assert data_v_b["additionality_status"] == "ACTIVITY_METHOD_ADDITIONALITY"

        # D. Evaluate Gold Standard PARC -> Inactive / Under Development
        res_gs = await client.get(
            f"/api/v1/biochar/projects/{proj_b_id}/eligibility?target_standard=GOLD_STANDARD&target_methodology=GS_PARC",
            headers=headers,
        )
        assert res_gs.status_code == 200, res_gs.text
        data_gs = res_gs.json()
        assert data_gs["eligibility_status"] == "NOT_SUPPORTED"
        assert "under development" in data_gs["blocking_findings"][0].lower()

        # E. Evaluate India CCTS -> Inactive / No active methodology
        res_ccts = await client.get(
            f"/api/v1/biochar/projects/{proj_b_id}/eligibility?target_standard=INDIA_CCTS",
            headers=headers,
        )
        assert res_ccts.status_code == 200, res_ccts.text
        data_ccts = res_ccts.json()
        assert data_ccts["eligibility_status"] == "NOT_SUPPORTED"
        assert "has not published an approved methodology" in data_ccts["blocking_findings"][0]

        # F. Evaluate VM0044 v2.0 -> Watchlist
        res_v2 = await client.get(
            f"/api/v1/biochar/projects/{proj_b_id}/eligibility?target_standard=VERRA&target_methodology=VM0044&methodology_version=v2.0",
            headers=headers,
        )
        assert res_v2.status_code == 200, res_v2.text
        data_v2 = res_v2.json()
        assert data_v2["eligibility_status"] == "WATCHLIST"
        assert "public consultation" in data_v2["blocking_findings"][0]
