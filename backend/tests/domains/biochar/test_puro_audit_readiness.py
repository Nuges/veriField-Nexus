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
    ProductionFacility,
)
from app.domains.biochar.puro_models import (
    PuroAdditionalityAssessment,
    PuroAuditFinding,
    PuroAuditWorkflow,
    PuroBaselineAssessment,
    PuroCreditingPeriod,
    PuroEndUseCategory,
    PuroEndUseRecordLink,
    PuroFacilityProfile,
    PuroMonitoringPlan,
    PuroOutputReport,
    PuroSupplierProfile,
)
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
async def test_puro_audit_workflow_and_findings_lifecycle(db_session: AsyncSession):
    """Tests Facility Audit & Output Audit creation, findings logging, and findings closure."""
    await seed_puro_biochar_normative_metadata(db_session)

    suffix = uuid.uuid4().hex[:6]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Audit Workflow Org {suffix}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"lead_auditor_{suffix}@synthetic-nexus.org",
        full_name="Lead Auditor",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    proj_id = uuid.uuid4()
    proj = Project(id=proj_id, name=f"Audit Target Project {suffix}", project_code=f"AUD-{suffix.upper()}", organization_id=org_id)
    db_session.add(proj)

    fac_id = uuid.uuid4()
    fac = ProductionFacility(
        id=fac_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-AUD-{suffix.upper()}",
        facility_name="Audit Target Facility",
    )
    db_session.add(fac)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create Production Facility Audit
        res_audit = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/audits",
            headers=headers,
            json={
                "facility_id": str(fac_id),
                "audit_type": "PRODUCTION_FACILITY_AUDIT",
                "auditor_organization": "Accredited VVB Carbon Verification Services",
                "lead_auditor_name": "Dr. Sarah Jenkins, Lead Auditor",
                "scheduled_date": "2025-06-15",
            },
        )
        assert res_audit.status_code == 201, res_audit.text
        audit_data = res_audit.json()
        audit_id = audit_data["id"]
        assert audit_data["audit_status"] == "AUDIT_SCHEDULED"

        # 2. Log Audit Finding (Minor non-conformity) directly via manager
        from app.domains.biochar.services.puro_compliance import PuroAuditManager
        finding = await PuroAuditManager.log_audit_finding(
            db=db_session,
            audit_id=uuid.UUID(audit_id),
            rule_ref="PURO-BIOCHAR-9.1",
            finding_type="NON_CONFORMITY_MINOR",
            description="Pyrolysis temperature thermocouple calibration certificate expired 3 days prior to audit.",
            response_due_date=date(2025, 7, 15),
        )
        assert finding.status == "OPEN"

        # 3. Resolve Finding with corrective action evidence
        resolved = await PuroAuditManager.resolve_audit_finding(
            db=db_session,
            finding_id=finding.id,
            evidence_of_closure_ref=f"CAL-CERT-ISO17025-{suffix.upper()}.PDF",
        )
        assert resolved.status == "CLOSED"
        assert resolved.closed_at is not None


@pytest.mark.asyncio
async def test_puro_output_report_assembly_and_ledger_seal(db_session: AsyncSession):
    """Tests building a Puro Output Report and sealing it in the cryptographic ledger."""
    await seed_puro_biochar_normative_metadata(db_session)

    suffix = uuid.uuid4().hex[:6]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Report Packaging Org {suffix}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"report_admin_{suffix}@synthetic-nexus.org",
        full_name="Report Admin",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    proj_id = uuid.uuid4()
    proj = Project(id=proj_id, name=f"Reporting Project {suffix}", project_code=f"REP-{suffix.upper()}", organization_id=org_id)
    db_session.add(proj)

    fac_id = uuid.uuid4()
    fac = ProductionFacility(
        id=fac_id,
        organization_id=org_id,
        project_id=proj_id,
        facility_code=f"FAC-REP-{suffix.upper()}",
        facility_name="Reporting Facility Plant",
    )
    db_session.add(fac)

    # Add a crediting period
    cp_id = uuid.uuid4()
    cp = PuroCreditingPeriod(
        id=cp_id,
        organization_id=org_id,
        facility_id=fac_id,
        sequence_number=1,
        start_date=date(2025, 1, 1),
        end_date=date(2034, 12, 31),
    )
    db_session.add(cp)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post(
            f"/api/v1/biochar/puro/facilities/{fac_id}/output-reports?monitoring_period_id=2025-Q1&crediting_period_id={cp_id}",
            headers=headers,
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["report_status"] == "AUDITED_SEALED"
        assert len(data["manifest_hash"]) == 64
        assert "PUR-REP-" in data["report_number"]


@pytest.mark.asyncio
async def test_puro_registry_readiness_blockers_and_truthful_labels(db_session: AsyncSession):
    """Tests registry readiness engine evaluates real blockers and displays truthful non-issuance states."""
    await seed_puro_biochar_normative_metadata(db_session)

    suffix = uuid.uuid4().hex[:6]
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Readiness Evaluation Org {suffix}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"compliance_eval_{suffix}@synthetic-nexus.org",
        full_name="Compliance Evaluator",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    # 1. Project with missing facility registration -> Must report BLOCKED
    proj_empty_id = uuid.uuid4()
    proj_empty = Project(id=proj_empty_id, name=f"Empty Project {suffix}", project_code=f"EMP-{suffix.upper()}", organization_id=org_id)
    db_session.add(proj_empty)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res_empty = await client.get(
            f"/api/v1/biochar/puro/projects/{proj_empty_id}/readiness",
            headers=headers,
        )
        assert res_empty.status_code == 200, res_empty.text
        data_empty = res_empty.json()
        assert data_empty["readiness_state"] == "BLOCKED"
        assert "FACILITY_REGISTRATION_MISSING" in data_empty["active_blockers"]
        assert data_empty["issuance_status"] == "NOT_ISSUED"
        assert data_empty["quantification_status"] == "NOT_CONFIGURED"

        # 2. Project with facility but missing supplier rights, baseline, etc. -> In progress with blockers
        proj_partial_id = uuid.uuid4()
        proj_partial = Project(id=proj_partial_id, name=f"Partial Project {suffix}", project_code=f"PART-{suffix.upper()}", organization_id=org_id)
        db_session.add(proj_partial)

        fac_partial = ProductionFacility(
            organization_id=org_id,
            project_id=proj_partial_id,
            facility_code=f"FAC-PART-{suffix.upper()}",
            facility_name="Partial Facility",
        )
        db_session.add(fac_partial)
        await db_session.commit()

        res_partial = await client.get(
            f"/api/v1/biochar/puro/projects/{proj_partial_id}/readiness",
            headers=headers,
        )
        assert res_partial.status_code == 200, res_partial.text
        data_partial = res_partial.json()
        # Must list real blockers
        assert any("SUPPLIER_RIGHTS_INCOMPLETE" in b for b in data_partial["active_blockers"])
        assert any("FACILITY_CLASSIFICATION_INCOMPLETE" in b for b in data_partial["active_blockers"])
        assert any("BASELINE_INCOMPLETE" in b for b in data_partial["active_blockers"])
        assert any("FACILITY_AUDIT_REQUIRED" in b for b in data_partial["active_blockers"])
        # Truthful labels
        assert data_partial["issuance_status"] == "NOT_ISSUED"
        assert data_partial["overall_capability_status"] in ("PRODUCTION_READY_WITH_LIMITATION", "BLOCKED")
