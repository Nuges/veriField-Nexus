"""
=============================================================================
VeriField Nexus — Authoritative Registry Document Generation & Adversarial Test Suite
=============================================================================
Tests:
1. Adversarial Test: Incomplete/Zero-Data Project (Strictly BLOCKED, Zero False Claims)
2. Document Renderer: Multi-Format PDF & DOCX Binary Integrity & SHA-256 Digests
3. Article 6 Authorization State Machine & Gating Verification
4. Section 15 Package Generation (15_registry_documents/ with PDF/DOCX/JSON)
5. Multi-Tenant IDOR Security & Authorization Enforcement (403 Forbidden)
6. Dynamic Multi-Standard Support (NCCC, Article 6.2, Article 6.4, Verra, Gold Standard)
=============================================================================
"""

import io
import json
import uuid
import zipfile
from datetime import date, datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.db.session import _get_fallback_session_factory, _init_fallback_db, get_db
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.authentication.models import User
from app.domains.documents.models import ProjectDocument
from app.domains.evidence.models import Evidence
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily, MethodologyRegistry
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.registry_integrations.services.document_renderer import RegistryDocumentRenderer
from app.domains.registry_integrations.services.package_builder import ComprehensivePackageBuilder
from app.domains.registry_integrations.services.readiness_engine import AuthorizationStatus, RegistryReadinessEngine
from app.domains.registry_integrations.services.template_registry import TemplateRegistry
from app.main import app


@pytest.mark.asyncio
async def test_adversarial_zero_data_project_strictly_blocked():
    """
    Adversarial Gate Test:
    Project in Nigeria with Hybrid Energy methodology linked, developer populated,
    BUT zero assets, zero activity data, zero evidence, no stakeholder records, no safeguards, no authorization.

    EXPECTATION:
    - Article 6 Authorization MUST NOT be 'CONFIRMED' or 'AUTHORIZED'.
    - Must output 'PENDING_HOST_COUNTRY_AUTHORIZATION' or 'NOT_STARTED'.
    - Readiness status MUST be 'BLOCKED'.
    - Document readiness completeness MUST be 'INCOMPLETE' / 'NOT_READY'.
    """
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    meth_id = uuid.uuid4()
    sec_id = uuid.uuid4()
    reg_id = uuid.uuid4()

    async with factory() as session:
        org = Organization(id=org_id, name=f"Solaris Grid Dev {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
        reg = MethodologyRegistry(id=reg_id, code=f"UNFCCC_{uuid.uuid4().hex[:4]}", name="UNFCCC Clean Development")
        sec = MethodologyFamily(id=sec_id, code=f"ENERGY_{uuid.uuid4().hex[:4]}", name="Hybrid Energy & Mini-grids")
        meth = Methodology(id=meth_id, code=f"AMS_I_L_{uuid.uuid4().hex[:4]}", name="Electrification of rural communities", registry_id=reg_id, family_id=sec_id)
        proj = Project(
            id=proj_id,
            name=f"Adversarial Zero Data Mini-Grid {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            sector_id=sec_id,
            methodology_id=meth_id,
            country="Nigeria",
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2035, 12, 31),
        )
        session.add_all([org, reg, sec, meth, proj])
        await session.commit()

        engine = RegistryReadinessEngine(session)

        # 1. Evaluate for Article 6.2
        r_a6 = await engine.evaluate_readiness(project_id=proj_id, target_standard="ARTICLE6_2")
        assert r_a6["readiness_status"] == "BLOCKED"
        assert r_a6["authorization_status"] == "NOT_STARTED"
        assert "HOST_COUNTRY_AUTHORIZATION_MISSING" in r_a6["blocking_items"]
        assert "ZERO_ASSETS_ENROLLED" in r_a6["blocking_items"]
        assert "ZERO_ACTIVITY_DATA" in r_a6["blocking_items"]
        assert "ZERO_EVIDENCE_ATTACHED" in r_a6["blocking_items"]
        assert "STAKEHOLDER_CONSULTATION_MISSING" in r_a6["blocking_items"]
        assert "ESG_SAFEGUARDS_MISSING" in r_a6["blocking_items"]
        assert r_a6["readiness_status"] != "SUBMISSION_READY"

        # Check pillar 9 details
        p9_details = " ".join(r_a6["pillar_breakdown"]["article_6_readiness"]["details"])
        assert "CONFIRMED" not in p9_details
        assert "PENDING_HOST_COUNTRY_AUTHORIZATION" in p9_details

        # Check document-level readiness
        for doc in r_a6["document_readiness"]:
            assert doc["completeness_status"] == "INCOMPLETE"
            assert doc["submission_status"] == "NOT_READY"
            assert len(doc["blocking_requirements"]) > 0


@pytest.mark.asyncio
async def test_document_renderer_pdf_and_docx():
    """Verify publication-grade rendering of PDF and DOCX documents with correct metadata and headers."""
    renderer = RegistryDocumentRenderer()
    sample_data = {
        "id": str(uuid.uuid4()),
        "name": "Kano Clean Cooking Programme",
        "project_code": "PRJ-KANO-COOK-01",
        "country": "Nigeria",
        "registry_id": None,
        "developer_name": "West Africa Clean Energy Ltd",
        "methodology_code": "VMR0006",
        "sector_name": "Clean Cooking & Household Energy",
        "asset_count": 25,
        "activity_count": 150,
        "total_tco2e": 48.75,
        "qa_qc_rate": 96.0,
        "authorization_status": "DRAFT",
        "authorization_reference": "PENDING_OFFICIAL_FILING",
        "stakeholder_completed": True,
        "safeguards_cleared": True,
        "submission_status": "DRAFT (INTERNAL REVIEW)",
    }

    # 1. Render PDF for VCS_PROJECT_DESCRIPTION
    pdf_bytes, pdf_name, pdf_hash = renderer.render_document(
        document_id="VCS_PROJECT_DESCRIPTION", project_data=sample_data, format_type="pdf"
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert pdf_name.endswith(".pdf")
    assert len(pdf_hash) == 64

    # 2. Render DOCX for VCS_MONITORING_REPORT
    docx_bytes, docx_name, docx_hash = renderer.render_document(
        document_id="VCS_MONITORING_REPORT", project_data=sample_data, format_type="docx"
    )
    assert docx_bytes.startswith(b"PK")  # ZIP-based docx header
    assert docx_name.endswith(".docx")
    assert len(docx_hash) == 64

    # 3. Render NCCC No-Objection Certificate Application
    nccc_pdf, nccc_name, _ = renderer.render_document(
        document_id="NCCC_NOC_APPLICATION", project_data=sample_data, format_type="pdf"
    )
    assert nccc_pdf.startswith(b"%PDF")
    assert "NCCC_NOC_APPLICATION" in nccc_name


@pytest.mark.asyncio
async def test_package_builder_with_section_15():
    """Verify comprehensive package builder includes section 00-14 and section 15_registry_documents/."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    meth_id = uuid.uuid4()
    sec_id = uuid.uuid4()
    reg_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    async with factory() as session:
        org = Organization(id=org_id, name=f"Enugu Solar Mini-Grid Co {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
        reg = MethodologyRegistry(id=reg_id, code=f"VERRA_{uuid.uuid4().hex[:4]}", name="Verra VCS Registry")
        sec = MethodologyFamily(id=sec_id, code=f"SOLAR_{uuid.uuid4().hex[:4]}", name="Renewable Energy")
        meth = Methodology(id=meth_id, code=f"AMS_I_F_{uuid.uuid4().hex[:4]}", name="Renewable Electricity for Captive Use", registry_id=reg_id, family_id=sec_id)
        proj = Project(
            id=proj_id,
            name=f"Enugu Rural Solar Mini-Grid {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            sector_id=sec_id,
            methodology_id=meth_id,
            country="Nigeria",
        )
        asset = Asset(id=asset_id, project_id=proj_id, organization_id=org_id, name="Solar Array Inverter 01")
        act = Activity(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            asset_id=asset_id,
            activity_type="solar_generation",
            trust_score=95.0,
            activity_data={"emission_reduction_kg": 12500.0},
            captured_at=datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
        )
        session.add_all([org, reg, sec, meth, proj, asset, act])
        await session.commit()

        builder = ComprehensivePackageBuilder(session)
        zip_bytes, zip_filename, manifest = await builder.build_package_zip(project_id=proj_id, standard="VERRA")

        # Open and inspect the ZIP archive in memory
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            file_list = zf.namelist()

            # Verify standard sections 00..14 exist
            assert "00_manifest/manifest.json" in file_list
            assert "01_project/project_metadata.json" in file_list
            assert "04_monitoring/parameter_timeseries.csv" in file_list
            assert "14_cryptographic_integrity/sha256_package_checksum.json" in file_list

            # Verify section 15_registry_documents exists and contains rendered outputs
            verra_docs = [f for f in file_list if f.startswith("15_registry_documents/VERRA/")]
            assert len(verra_docs) > 0

            # Verify presence of PDF, DOCX, and JSON structured specifications
            assert any(f.endswith(".pdf") for f in verra_docs)
            assert any(f.endswith(".docx") for f in verra_docs)
            assert any(f.endswith(".json") for f in verra_docs)

            # Verify manifest includes Section 15 documents
            manifest_file_paths = [entry["path"] for entry in manifest["files"]]
            assert any(p.startswith("15_registry_documents/VERRA/") for p in manifest_file_paths)


@pytest.mark.asyncio
async def test_multi_tenant_document_download_security():
    """Security Test: Tenant A attempts to download Tenant B's generated registry document (403 Forbidden)."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    proj_b_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        email=f"attacker_{uuid.uuid4().hex[:6]}@tenant-a.com",
        full_name="Attacker A",
        role="COMPLIANCE_ADMIN",
        organization_id=org_a_id,
        is_active=True,
    )
    proj_b = Project(
        id=proj_b_id,
        name=f"Tenant B Project {uuid.uuid4().hex[:6]}",
        organization_id=org_b_id,
        country="Nigeria",
    )

    async with factory() as session:
        session.add_all([
            Organization(id=org_a_id, name=f"Tenant A Org {uuid.uuid4().hex[:6]}"),
            Organization(id=org_b_id, name=f"Tenant B Org {uuid.uuid4().hex[:6]}"),
            user_a,
            proj_b,
        ])
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    try:
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: user_a

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Tenant A attempts to fetch Tenant B's document
            res = await client.get(f"/api/v1/registry/documents/VERRA/{proj_b_id}/VCS_PROJECT_DESCRIPTION?format=pdf")
            assert res.status_code == 403
            assert "Forbidden" in res.json()["detail"]

            # Tenant A attempts to download Tenant B's package zip
            res_pkg = await client.get(f"/api/v1/registry/package-download/VERRA/{proj_b_id}")
            assert res_pkg.status_code == 403
            assert "Forbidden" in res_pkg.json()["detail"]
    finally:
        app.dependency_overrides.clear()
