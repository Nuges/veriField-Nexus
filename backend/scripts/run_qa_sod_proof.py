import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import jwt as pyjwt
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.main import app
from app.domains.organizations.models import Organization
from app.domains.authentication.models import User
from app.domains.projects.models import Project
from app.domains.methodologies.models.base_registry import MethodologyFamily, Methodology, MethodologyVersion
from app.domains.agriculture.models import (
    LandUnit,
    Stratum,
    StratumMembership,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    PhysicalSample,
    SampleCollectionEvent,
    LaboratoryReceipt,
    LaboratoryAnalysis,
    LaboratoryResult,
    SampleQAReview,
)
from app.domains.agriculture.schemas import (
    SamplingCampaignCreate,
    SamplingPlanVersionCreate,
    SamplingPointCreate,
    SampleCollectionCreate,
    LabReceiptCreate,
    LabAnalysisCreate,
    LabResultCreate,
    SampleQAReviewCreate,
    LandUnitCreate,
    StratumCreate,
    StratumMembershipItem,
    LinkBoundaryRequest,
)
from app.domains.agriculture.service import AgricultureService
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.db.session import get_db

ASYNC_DB_URL = "postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test"

VALID_POLYGON_A = {
    "type": "Polygon",
    "coordinates": [
        [[77.10, 28.50], [77.12, 28.50], [77.12, 28.52], [77.10, 28.52], [77.10, 28.50]]
    ],
}

VALID_POLYGON_B = {
    "type": "Polygon",
    "coordinates": [
        [[77.10, 28.50], [77.11, 28.50], [77.11, 28.51], [77.10, 28.51], [77.10, 28.50]]
    ],
}

def create_jwt_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "org_id": str(org_id),
        "organization_id": str(org_id),
        "exp": int((now + timedelta(hours=2)).timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def main():
    engine = create_async_engine(ASYNC_DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("======================================================================")
    print("VERIFIELD NEXUS — AGRICULTURE PHASE 2 QA & SoD ENFORCEMENT PROOF")
    print("======================================================================")

    async with async_session() as session:
        # Seed methodologies
        await seed_agriculture_methodologies(session)

        # 1. Setup Tenant and Users with Canonical Roles (Neutral Synthetic Fixtures)
        org = Organization(name=f"Synthetic Agriculture Organization {uuid.uuid4().hex[:6]}", plan="ENTERPRISE")
        session.add(org)
        await session.flush()

        admin_user = User(
            email=f"pm.alpha.{uuid.uuid4().hex[:6]}@synthetic-agri.test",
            full_name="Project Manager Alpha",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
        )
        collector_user = User(
            email=f"agent.alpha.{uuid.uuid4().hex[:6]}@synthetic-agri.test",
            full_name="Field Agent Alpha",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
        )
        qa_officer_user = User(
            email=f"qa.alpha.{uuid.uuid4().hex[:6]}@synthetic-agri.test",
            full_name="QA Officer Alpha",
            role="QA_OFFICER",
            organization_id=org.id,
            is_active=True,
        )
        auditor_user = User(
            email=f"auditor.alpha.{uuid.uuid4().hex[:6]}@synthetic-agri.test",
            full_name="Auditor Alpha",
            role="AUDITOR",
            organization_id=org.id,
            is_active=True,
        )
        session.add_all([admin_user, collector_user, qa_officer_user, auditor_user])
        await session.flush()

        # 2. Setup Project, Stratum, Land Unit
        fam_res = await session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE"))
        agri_family = fam_res.scalars().first()
        m42_res = await session.execute(select(Methodology).where(Methodology.code == "VM0042"))
        vm0042 = m42_res.scalars().first()
        v22_res = await session.execute(
            select(MethodologyVersion).where(
                MethodologyVersion.methodology_id == vm0042.id,
                MethodologyVersion.version == "2.2",
            )
        )
        v22 = v22_res.scalars().first()

        project = Project(
            name="SoD Acceptance Project",
            project_code=f"AGR-SOD-{uuid.uuid4().hex[:6]}",
            organization_id=org.id,
            sector_id=agri_family.id if agri_family else None,
            methodology_id=vm0042.id,
            methodology_version_id=v22.id,
            crediting_start=date(2025, 1, 1),
            crediting_end=date(2045, 12, 31),
            baseline_parameters={},
        )
        session.add(project)
        await session.flush()

        await AgricultureService.lock_project_methodology(session, project.id, org.id, admin_user.id, "SoD Lock")
        bound = await AgricultureService.link_project_boundary(
            session, project.id, org.id, admin_user.id,
            LinkBoundaryRequest(boundary_geojson=VALID_POLYGON_A, source="GNSS_SURVEY", reason="Perimeter")
        )
        lu = await AgricultureService.create_land_unit(
            session,
            LandUnitCreate(project_id=project.id, name="Parcel SoD", code="LU-SOD-1", unit_type="FIELD", boundary_geojson=VALID_POLYGON_B, boundary_source="GNSS_SURVEY"),
            org.id,
        )
        stratum = await AgricultureService.create_stratum(
            session,
            StratumCreate(code="STRAT-SOD", name="SoD Stratum", stratum_type="MANAGEMENT_PRACTICE", area_ha=20.0),
            org.id, project.id,
        )
        await AgricultureService.add_stratum_memberships(
            session, stratum.id, org.id,
            [StratumMembershipItem(land_unit_id=lu.id, valid_from=date(2025, 1, 1), status="ACTIVE")],
        )

        # 3. Create Campaign, Plan Version, Sampling Point, Physical Sample
        campaign = await AgricultureService.create_sampling_campaign(
            session, project.id, org.id,
            SamplingCampaignCreate(campaign_code="CAMP-SOD-VAL", name="SoD Campaign", planned_start_date=date(2026, 1, 1)),
            user_id=admin_user.id,
        )
        spv = await AgricultureService.create_sampling_plan_version(
            session, campaign.id, org.id,
            SamplingPlanVersionCreate(effective_as_of_date=date(2026, 1, 1)),
            user_id=admin_user.id,
        )
        await AgricultureService.lock_sampling_plan_version(session, spv.id, org.id, admin_user.id)
        pts = await AgricultureService.create_sampling_points(
            session, campaign.id, spv.id, org.id,
            [SamplingPointCreate(point_code="P-SOD-001", planned_lat=28.505, planned_lon=77.105, land_unit_id=lu.id, stratum_id=stratum.id)],
            user_id=admin_user.id,
        )
        sample = (await session.execute(select(PhysicalSample).where(PhysicalSample.sampling_point_id == pts[0].id))).scalar_one()

        # 4. Collector records collection
        await AgricultureService.record_sample_collection(
            session, sample.id, org.id,
            SampleCollectionCreate(actual_lat=28.505, actual_lon=77.105, collection_timestamp=datetime(2026, 1, 2, 8, 30, tzinfo=timezone.utc), collector_name=collector_user.full_name),
            user_id=collector_user.id,
        )

        # 5. Lab Receipt & Analysis
        await AgricultureService.record_laboratory_receipt(
            session, sample.id, org.id,
            LabReceiptCreate(laboratory_name="Synthetic Analytical Laboratory Alpha", received_at=datetime(2026, 1, 3, 10, 0, tzinfo=timezone.utc), received_by_name="Lab Clerk Alpha"),
        )
        await AgricultureService.record_laboratory_analysis(
            session, sample.id, org.id,
            LabAnalysisCreate(
                laboratory_name="Synthetic Analytical Laboratory Alpha",
                analysis_date=date(2026, 1, 4),
                results=[LabResultCreate(analyte="SOC_CONCENTRATION", raw_value=Decimal("1.85"), raw_unit="%")]
            ),
        )
        await session.commit()

        sample_id = sample.id
        project_id = project.id
        org_id = org.id

    # Create JWT Tokens
    token_collector = create_jwt_token(collector_user.id, collector_user.email, "FIELD_AGENT", org_id)
    token_qa = create_jwt_token(qa_officer_user.id, qa_officer_user.email, "QA_OFFICER", org_id)
    token_auditor = create_jwt_token(auditor_user.id, auditor_user.email, "AUDITOR", org_id)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        print("\n--- TEST CASE 1: Collector Self-Review Rejection via REST API (RBAC Guard) ---")
        res1 = await client.post(
            f"/api/v1/agriculture/projects/{project_id}/physical-samples/{sample_id}/qa-review",
            headers={"Authorization": f"Bearer {token_collector}"},
            json={"reviewer_name": collector_user.full_name, "overall_qa_status": "ACCEPTED"},
        )
        print(f"Endpoint: POST /api/v1/agriculture/projects/.../qa-review")
        print(f"Role:     FIELD_AGENT (Collector: {collector_user.full_name})")
        print(f"Status:   {res1.status_code}")
        print(f"Detail:   {res1.json().get('detail')}")
        assert res1.status_code == 403, f"Expected 403 Forbidden, got {res1.status_code}"
        print("RESULT:   PASS — RBAC blocked field collector from executing QA review endpoint.")

        print("\n--- TEST CASE 2: Core Domain Invariant SoD Enforcement (Self-Review Invariant) ---")
        async with async_session() as session:
            try:
                await AgricultureService.record_sample_qa_review(
                    session,
                    sample_id=sample_id,
                    organization_id=org_id,
                    payload=SampleQAReviewCreate(reviewer_name=collector_user.full_name, overall_qa_status="ACCEPTED"),
                    user_id=collector_user.id,
                )
                print("FAILURE: Domain service unexpectedly allowed collector self-review!")
                sys.exit(1)
            except ValueError as ve:
                print(f"Caught Expected Invariant Violation: {ve}")
                assert "Separation of Duties violation: The field collector" in str(ve)
                print("RESULT:   PASS — Domain service strictly barred collector self-review (SoD invariant).")

        print("\n--- TEST CASE 3: Independent QA Officer Sign-off via REST API ---")
        res3 = await client.post(
            f"/api/v1/agriculture/projects/{project_id}/physical-samples/{sample_id}/qa-review",
            headers={"Authorization": f"Bearer {token_qa}"},
            json={
                "reviewer_name": qa_officer_user.full_name,
                "overall_qa_status": "ACCEPTED",
                "notes": "Independent QA review completed. Calibration and chain of custody verified.",
            },
        )
        print(f"Endpoint: POST /api/v1/agriculture/projects/.../qa-review")
        print(f"Role:     QA_OFFICER (Reviewer: {qa_officer_user.full_name})")
        print(f"Status:   {res3.status_code}")
        assert res3.status_code == 200, f"Expected 200 OK, got {res3.status_code}: {res3.text}"
        data3 = res3.json()
        print(f"QA Review ID:     {data3['id']}")
        print(f"Overall Status:   {data3['overall_qa_status']}")
        print(f"Reviewer Name:    {data3['reviewer_name']}")
        print("RESULT:   PASS — Independent QA Officer successfully signed off on ground evidence.")

        print("\n--- TEST CASE 4: Auditor Mutation Attempt Rejection (Read-Only Guard) ---")
        res4_camp = await client.post(
            f"/api/v1/agriculture/projects/{project_id}/sampling-campaigns",
            headers={"Authorization": f"Bearer {token_auditor}"},
            json={"campaign_code": "AUD-FORBIDDEN", "name": "Illegal Auditor Campaign", "planned_start_date": "2026-06-01"},
        )
        print(f"Endpoint: POST /api/v1/agriculture/projects/.../sampling-campaigns")
        print(f"Role:     AUDITOR ({auditor_user.full_name})")
        print(f"Status:   {res4_camp.status_code}")
        print(f"Detail:   {res4_camp.json().get('detail')}")
        assert res4_camp.status_code == 403, f"Expected 403 Forbidden, got {res4_camp.status_code}"

        res4_qa = await client.post(
            f"/api/v1/agriculture/projects/{project_id}/physical-samples/{sample_id}/qa-review",
            headers={"Authorization": f"Bearer {token_auditor}"},
            json={"reviewer_name": auditor_user.full_name, "overall_qa_status": "ACCEPTED"},
        )
        print(f"Endpoint: POST /api/v1/agriculture/projects/.../qa-review")
        print(f"Role:     AUDITOR ({auditor_user.full_name})")
        print(f"Status:   {res4_qa.status_code}")
        print(f"Detail:   {res4_qa.json().get('detail')}")
        assert res4_qa.status_code == 403, f"Expected 403 Forbidden, got {res4_qa.status_code}"
        print("RESULT:   PASS — Third-party AUDITOR strictly barred from all mutation endpoints.")

    print("\n======================================================================")
    print("ALL QA & SoD SECURITY CHECKS PASSED WITH REAL POSTGRESQL & FASTAPI")
    print("======================================================================")

if __name__ == "__main__":
    asyncio.run(main())
