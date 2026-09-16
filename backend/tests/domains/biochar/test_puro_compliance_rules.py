import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharLabAnalysis,
    FeedstockLot,
    FeedstockSource,
    ProductionFacility,
)
from app.domains.biochar.puro_models import (
    PuroAdditionalityAssessment,
    PuroBaselineAssessment,
    PuroCreditingPeriod,
    PuroEndUseCategory,
    PuroFacilityProfile,
    PuroMethodologyVersion,
    PuroMobileProductionSite,
    PuroNormativeDependency,
    PuroRuleDefinition,
    PuroSupplierProfile,
)
from app.domains.biochar.puro_rules import (
    METHODOLOGY_RULES_CATALOG,
    NORMATIVE_DEPENDENCIES,
    TABLE_3_2_CATEGORIES,
    seed_puro_biochar_normative_metadata,
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
async def test_puro_methodology_rule_coverage_and_normative_dependencies(db_session: AsyncSession):
    """Proves that all 11 methodology chapters have registered rules and dependencies."""
    await seed_puro_biochar_normative_metadata(db_session)

    # 1. Check methodology version
    stmt_v = select(PuroMethodologyVersion).where(PuroMethodologyVersion.code == "PURO_BIOCHAR_2025_V2")
    res_v = await db_session.execute(stmt_v)
    version = res_v.scalar_one()
    assert version.edition == "Edition 2025 v2"

    # 2. Check rule coverage across all 11 chapters
    stmt_r = select(PuroRuleDefinition).where(PuroRuleDefinition.methodology_version_id == version.id)
    res_r = await db_session.execute(stmt_r)
    rules = res_r.scalars().all()
    assert len(rules) >= len(METHODOLOGY_RULES_CATALOG)

    covered_sections = set(r.section_number for r in rules)
    for section_num in range(1, 12):
        assert section_num in covered_sections, f"Chapter {section_num} must be registered in rule definitions"

    # 3. Check Table 3.2 End Use Categories (all 28 categories per Edition 2025 V2)
    stmt_cat = select(PuroEndUseCategory)
    res_cat = await db_session.execute(stmt_cat)
    cats = res_cat.scalars().all()
    assert len(cats) == 28
    assert len(cats) == len(TABLE_3_2_CATEGORIES)
    expected_codes = set(c["category_code"] for c in TABLE_3_2_CATEGORIES)
    assert set(c.category_code for c in cats) == expected_codes

    # 4. Check Normative Dependencies
    stmt_dep = select(PuroNormativeDependency)
    res_dep = await db_session.execute(stmt_dep)
    deps = res_dep.scalars().all()
    assert len(deps) >= len(NORMATIVE_DEPENDENCIES)
    assert any(d.code == "PURO_GENERAL_RULES_V4" for d in deps)


@pytest.mark.asyncio
async def test_puro_supplier_profile_and_double_claim_prevention(db_session: AsyncSession):
    """Tests CO2 Removal Supplier registration, exclusive claim rights, and duplicate prevention."""
    await seed_puro_biochar_normative_metadata(db_session)

    suffix = uuid.uuid4().hex[:6]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Synthetic Puro Developer Org {suffix}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"puro_admin_{suffix}@synthetic-nexus.org",
        full_name="Puro Admin",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    proj_id = uuid.uuid4()
    proj = Project(id=proj_id, name=f"Puro CDR Project {suffix}", project_code=f"PUR-PROJ-{suffix.upper()}", organization_id=org_id)
    db_session.add(proj)

    fac_id = uuid.uuid4()
    fac = ProductionFacility(
        id=fac_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-PUR-{suffix.upper()}",
        facility_name="Puro Pyrolysis Facility",
        facility_status="NEW_OPERATIONAL",
    )
    db_session.add(fac)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. Register Supplier Profile with Exclusive Claim Rights
        res = await client.post(
            f"/api/v1/biochar/puro/projects/{proj_id}/supplier",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "supplier_legal_name": f"Synthetic Clean Biochar Ltd {suffix}",
                "registration_number": f"REG-9923-{suffix.upper()}",
                "jurisdiction_country": "Germany",
                "supplier_role": "PRODUCER",
                "claim_rights_status": "EXCLUSIVE_CLAIM_RIGHTS_ESTABLISHED",
                "authorization_agreement_ref": f"AGR-PUR-2025-{suffix.upper()}",
                "rights_declaration_doc_hash": "a" * 64,
                "contract_effective_date": "2025-01-01",
            },
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["supplier_role"] == "PRODUCER"
        assert data["claim_rights_status"] == "EXCLUSIVE_CLAIM_RIGHTS_ESTABLISHED"
        assert data["validation_state"] == "VALIDATED"

        # B. Duplicate registration attempt must fail
        res_dup = await client.post(
            f"/api/v1/biochar/puro/projects/{proj_id}/supplier",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "supplier_legal_name": "Competing Claim Entity Inc",
                "jurisdiction_country": "Germany",
            },
        )
        assert res_dup.status_code == 400


@pytest.mark.asyncio
async def test_puro_stationary_vs_mobile_facility_classification(db_session: AsyncSession):
    """Tests Stationary vs Mobile facility profiles, spatial extent and mobile sites."""
    await seed_puro_biochar_normative_metadata(db_session)

    suffix = uuid.uuid4().hex[:6]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Mobile Biochar Operator {suffix}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"mobile_op_{suffix}@synthetic-nexus.org",
        full_name="Mobile Operator",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    proj_id = uuid.uuid4()
    proj = Project(id=proj_id, name=f"Mobile Pyrolysis Project {suffix}", project_code=f"MOB-{suffix.upper()}", organization_id=org_id)
    db_session.add(proj)

    fac_id = uuid.uuid4()
    fac = ProductionFacility(
        id=fac_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-MOB-{suffix.upper()}",
        facility_name="Mobile Kiln Fleet Alpha",
        facility_status="NEW_OPERATIONAL",
    )
    db_session.add(fac)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. Register MOBILE facility profile with required spatial extent
        res = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/profile",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "facility_classification": "MOBILE",
                "host_country": "Finland",
                "spatial_extent_geojson": {
                    "type": "Polygon",
                    "coordinates": [[[24.0, 60.0], [26.0, 60.0], [26.0, 62.0], [24.0, 62.0], [24.0, 60.0]]],
                },
                "operating_status": "ACTIVE",
            },
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["facility_classification"] == "MOBILE"
        assert data["host_country"] == "Finland"

        # B. Register production site under the mobile facility
        res_site = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/mobile-sites",
            headers=headers,
            json={
                "site_code": f"SITE-FI-{suffix.upper()}",
                "site_name": "Uusimaa Forestry Clearing Site",
                "coordinates": "60.1699,24.9384",
                "owner_operator": "Nordic Agro Forestry Oy",
                "date_range_start": "2025-05-01",
                "date_range_end": "2025-08-31",
                "regulatory_permit_ref": "PERM-FI-2025-88",
            },
        )
        assert res_site.status_code == 201, res_site.text
        site_data = res_site.json()
        assert site_data["site_code"] == f"SITE-FI-{suffix.upper()}"


@pytest.mark.asyncio
async def test_puro_crediting_period_rules(db_session: AsyncSession):
    """Tests 10-year crediting period, max 2 renewals (3 periods max), and rejection of overlaps."""
    await seed_puro_biochar_normative_metadata(db_session)

    suffix = uuid.uuid4().hex[:6]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Crediting Period Test Org {suffix}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"crediting_admin_{suffix}@synthetic-nexus.org",
        full_name="Crediting Admin",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    proj_id = uuid.uuid4()
    proj = Project(id=proj_id, name=f"Crediting Project {suffix}", project_code=f"CP-{suffix.upper()}", organization_id=org_id)
    db_session.add(proj)

    fac_id = uuid.uuid4()
    fac = ProductionFacility(
        id=fac_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-CP-{suffix.upper()}",
        facility_name="Crediting Facility",
    )
    db_session.add(fac)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create Initial Period (10 years)
        res1 = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/crediting-periods",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "sequence_number": 1,
                "start_date": "2025-01-01",
                "end_date": "2034-12-31",
                "crediting_duration_years": 10,
                "renewal_type": "INITIAL_PERIOD",
            },
        )
        assert res1.status_code == 201, res1.text

        # 2. Rejection of overlapping period
        res_overlap = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/crediting-periods",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "sequence_number": 2,
                "start_date": "2030-01-01",  # Overlaps with 2025-2034!
                "end_date": "2039-12-31",
            },
        )
        assert res_overlap.status_code == 400
        assert "overlaps" in res_overlap.json()["detail"].lower()

        # 3. Create First Renewal (2035 to 2044)
        res2 = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/crediting-periods",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "sequence_number": 2,
                "start_date": "2035-01-01",
                "end_date": "2044-12-31",
                "renewal_type": "RENEWAL_1",
            },
        )
        assert res2.status_code == 201, res2.text

        # 4. Rejection of sequence_number > 3 (max 2 renewals)
        res_exceed = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/crediting-periods",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "sequence_number": 4,  # Exceeds maximum 2 renewals!
                "start_date": "2055-01-01",
                "end_date": "2064-12-31",
            },
        )
        assert res_exceed.status_code == 400
        assert "more than twice" in res_exceed.json()["detail"].lower()


@pytest.mark.asyncio
async def test_puro_baseline_scenario_locking(db_session: AsyncSession):
    """Tests baseline scenario recording (NEW, RETROFIT, CHARCOAL_REPURPOSE) and immutability."""
    await seed_puro_biochar_normative_metadata(db_session)

    suffix = uuid.uuid4().hex[:6]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Baseline Test Org {suffix}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"baseline_officer_{suffix}@synthetic-nexus.org",
        full_name="Baseline Officer",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    proj_id = uuid.uuid4()
    proj = Project(id=proj_id, name=f"Baseline Project {suffix}", project_code=f"BASE-{suffix.upper()}", organization_id=org_id)
    db_session.add(proj)

    fac_id = uuid.uuid4()
    fac = ProductionFacility(
        id=fac_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-BASE-{suffix.upper()}",
        facility_name="Baseline Facility",
    )
    db_session.add(fac)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. Register NEW_FACILITY baseline
        res = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/baseline",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "scenario": "NEW_FACILITY",
                "historical_char_production_tpy": 0.0,
                "baseline_removal_tco2e_per_year": 0.0,
                "baseline_land_use_evidence_type": "PRE_CONSTRUCTION_AUDIT",
                "land_use_evidence_ref": "DOC-BASE-PRE-001",
            },
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["scenario"] == "NEW_FACILITY"
        assert data["is_locked"] is True

        # B. Attempt to alter locked baseline must fail
        res_alter = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/baseline",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "scenario": "RETROFIT_FACILITY",
            },
        )
        assert res_alter.status_code == 400
        assert "locked" in res_alter.json()["detail"].lower()
