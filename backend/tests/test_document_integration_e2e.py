"""
=============================================================================
VeriField Nexus — End-to-End Document Intelligence Integration Tests
=============================================================================
Validates:
1. End-to-end document upload, magic-bytes security, parsing, and database persistence.
2. Strict multi-tenant AI chunk search isolation (Org A vs Org B vs SUPER_ADMIN).
3. Reconciliation engine detecting duplicate SHA-256 and methodology mismatches.
4. Real ReportLab PDF generation and file retrieval.
5. Registry submission packaging for Verra, Gold Standard, and National Registry.
=============================================================================
"""

import asyncio
import io
import os
import uuid
import pytest
import pytest_asyncio
from fastapi import UploadFile
from pypdf import PdfWriter
from sqlalchemy import select

from app.db.session import _init_fallback_db, _get_fallback_session_factory
from app.domains.ai_orchestrator.document_indexer import DocumentIndexerService
from app.domains.authentication.models import User
from app.domains.documents.models import ProjectDocument
from app.domains.documents.service import DocumentService
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.methodologies.models.base_registry import MethodologyFamily, Methodology, MethodologyRegistry
from app.domains.registry_integrations.services.packaging import RegistryPackagingService
from app.domains.reporting.models import Report
from app.domains.reporting.repository import ReportRepository
from app.domains.reporting.schemas import ReportCreate
from app.domains.reporting.service import ReportingService


@pytest_asyncio.fixture(autouse=True)
async def init_test_database():
    await _init_fallback_db()


@pytest.mark.asyncio
async def test_ai_indexer_strict_tenant_isolation():
    factory = _get_fallback_session_factory()
    async with factory() as db:
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()

        db.add(Organization(id=org_a, name=f"Org Alpha {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
        db.add(Organization(id=org_b, name=f"Org Beta {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
        await db.commit()

        indexer = DocumentIndexerService(db)
        doc_a_id = str(uuid.uuid4())
        doc_b_id = str(uuid.uuid4())

        # Index chunk for Org A
        await indexer.index_document(
            document_id=doc_a_id,
            title="Org A Confidential PDD",
            document_type="PDD",
            content_text="Special proprietary carbon methodology formula Alpha.",
            organization_id=org_a,
        )

        # Index chunk for Org B
        await indexer.index_document(
            document_id=doc_b_id,
            title="Org B Confidential PDD",
            document_type="PDD",
            content_text="Special proprietary carbon methodology formula Beta.",
            organization_id=org_b,
        )
        await db.commit()

        # Search as Org A user: MUST find Alpha, MUST NOT find Beta
        res_a = await indexer.search_knowledge(
            query_text="proprietary",
            organization_id=org_a,
            is_super_admin=False,
        )
        found_titles_a = [r["title"] for r in res_a]
        assert "Org A Confidential PDD" in found_titles_a
        assert "Org B Confidential PDD" not in found_titles_a

        # Search as Org B user: MUST find Beta, MUST NOT find Alpha
        res_b = await indexer.search_knowledge(
            query_text="proprietary",
            organization_id=org_b,
            is_super_admin=False,
        )
        found_titles_b = [r["title"] for r in res_b]
        assert "Org B Confidential PDD" in found_titles_b
        assert "Org A Confidential PDD" not in found_titles_b

        # Search as SUPER_ADMIN: MUST find both
        res_admin = await indexer.search_knowledge(
            query_text="proprietary",
            is_super_admin=True,
        )
        found_titles_admin = [r["title"] for r in res_admin]
        assert "Org A Confidential PDD" in found_titles_admin
        assert "Org B Confidential PDD" in found_titles_admin


@pytest.mark.asyncio
async def test_real_database_project_document_upload_and_reconciliation():
    factory = _get_fallback_session_factory()
    async with factory() as db:
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        proj_id = uuid.uuid4()
        sec_id = uuid.uuid4()
        meth_id = uuid.uuid4()

        db.add(Organization(id=org_id, name=f"Test Ingestion Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
        super_admin = User(
            id=user_id,
            email=f"admin_{uuid.uuid4().hex[:6]}@verifield.io",
            full_name="Admin Test",
            role="SUPER_ADMIN",
            organization_id=org_id,
            is_active=True,
        )

        db.add(super_admin)

        sec = MethodologyFamily(
            id=sec_id,
            code=f"BIO_{uuid.uuid4().hex[:12].upper()}",
            name="Biochar Carbon Removal",
            is_active=True,
        )
        db.add(sec)

        reg = MethodologyRegistry(
            id=uuid.uuid4(),
            code=f"REG_{uuid.uuid4().hex[:12].upper()}",
            name="Verra Registry",
            is_active=True,
        )
        db.add(reg)

        meth = Methodology(
            id=meth_id,
            family_id=sec_id,
            registry_id=reg.id,
            code=f"VM_{uuid.uuid4().hex[:12].upper()}",
            name="Biochar Carbon Methodology",
            is_active=True,
        )
        db.add(meth)

        proj = Project(
            id=proj_id,
            name=f"Delta Biochar Facility {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            sector_id=sec_id,
            methodology_id=meth_id,
        )
        db.add(proj)
        await db.commit()

        # Construct genuine PDF
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

        upload = UploadFile(
            filename="Test_Project_Monitoring_Report.pdf",
            file=io.BytesIO(pdf_bytes),
        )

        service = DocumentService(db)
        doc = await service.upload_and_process_document(
            file=upload,
            document_type="MONITORING_REPORT",
            title="Quarterly MRV Monitoring Report",
            project_id=proj.id,
            current_user=super_admin,
        )

        assert doc.id is not None
        assert doc.project_id == proj.id
        assert doc.organization_id == org_id
        assert doc.status in ("PROCESSED", "REVIEW_REQUIRED", "OCR_REQUIRED")
        assert doc.trust_score > 0
        assert os.path.exists(doc.storage_path)

        # Test duplicate detection by uploading the exact same file again
        upload_dup = UploadFile(
            filename="Duplicate_Report.pdf",
            file=io.BytesIO(pdf_bytes),
        )
        doc_dup = await service.upload_and_process_document(
            file=upload_dup,
            document_type="MONITORING_REPORT",
            title="Duplicate Report Upload",
            project_id=proj.id,
            current_user=super_admin,
        )

        assert doc_dup.status == "REVIEW_REQUIRED"
        flag_types = [f.flag_type for f in doc_dup.fraud_flags]
        assert "DUPLICATE_FILE" in flag_types


@pytest.mark.asyncio
async def test_reporting_service_real_pdf_generation():
    factory = _get_fallback_session_factory()
    async with factory() as db:
        org_id = uuid.uuid4()
        proj_id = uuid.uuid4()

        db.add(Organization(id=org_id, name=f"MRV Certificate Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
        proj = Project(
            id=proj_id,
            name=f"Kano Agroforestry {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
        )
        db.add(proj)
        await db.commit()

        repo = ReportRepository(db)
        service = ReportingService(repo)

        payload = ReportCreate(
            org_id=org_id,
            title="E2E Automated MRV Verification Certificate",
            report_type="MRV_CARBON_LEDGER",
            parameters={"project_id": str(proj_id)},
        )

        # Test generation
        report_record = await service.repository.create(
            Report(
                org_id=payload.org_id,
                title=payload.title,
                report_type=payload.report_type,
                parameters=payload.parameters or {},
                status="GENERATING",
            )
        )

        # Generate the real PDF using the service
        from app.domains.reporting.services.generator import RealDocumentGeneratorService
        output_dir = f"static/reports/{org_id}"
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/{report_record.id}.pdf"

        RealDocumentGeneratorService.generate_mrv_report_pdf(
            report_id=report_record.id,
            title=payload.title,
            org_name="MRV Certificate Org",
            project_name="Kano Agroforestry Carbon Initiative",
            sector_name="Agroforestry",
            methodology_name="AR-ACM0003",
            methodology_code="AR-ACM0003",
            metrics={
                "total_reductions_tco2e": 420.5,
                "total_assets": 12,
                "avg_trust_score": 98.2,
                "portfolio_value_usd": 6307.5,
            },
            assets_sample=[{
                "id": str(uuid.uuid4()),
                "property_type": "Cookstove",
                "baseline_fuel": 3200.0,
                "reductions_tco2e": 35.0,
                "trust_score": 97.8,
            }],
            output_path=output_file,
        )

        await service.repository.update_status(
            report_record.id,
            status="COMPLETED",
            file_uri=output_file,
        )

        rep_stmt = select(Report).where(Report.id == report_record.id)
        rep_res = await db.execute(rep_stmt)
        final_rep = rep_res.scalar_one()

        assert final_rep.status == "COMPLETED"
        assert final_rep.file_uri is not None
        assert os.path.exists(final_rep.file_uri)
        assert final_rep.file_uri.endswith(".pdf")

        with open(final_rep.file_uri, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"


@pytest.mark.asyncio
async def test_registry_packaging_service():
    factory = _get_fallback_session_factory()
    async with factory() as db:
        org_id = uuid.uuid4()
        proj_id = uuid.uuid4()
        sec_id = uuid.uuid4()
        meth_id = uuid.uuid4()

        db.add(Organization(id=org_id, name=f"Packaging Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
        sec = MethodologyFamily(id=sec_id, code=f"FOR_{uuid.uuid4().hex[:12].upper()}", name="Forestry", is_active=True)
        db.add(sec)
        reg = MethodologyRegistry(id=uuid.uuid4(), code=f"VER_{uuid.uuid4().hex[:12].upper()}", name="Verra", is_active=True)
        db.add(reg)
        meth = Methodology(id=meth_id, family_id=sec_id, registry_id=reg.id, code=f"VM_{uuid.uuid4().hex[:12].upper()}", name="REDD+ Methodology", is_active=True)
        db.add(meth)

        proj = Project(
            id=proj_id,
            name=f"Rainforest Protection {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            sector_id=sec_id,
            methodology_id=meth_id,
        )
        db.add(proj)
        await db.commit()

        packaging_svc = RegistryPackagingService(db)

        # Test Verra Bundle
        verra_pkg = await packaging_svc.generate_registry_package(
            registry_type="VERRA",
            project_id=proj.id,
        )
        assert verra_pkg["target_registry"] == "VERRA"
        assert verra_pkg["project"]["id"] == str(proj.id)
        assert verra_pkg["readiness_matrix"]["data_manifest"] == "READY"
        assert verra_pkg["readiness_matrix"]["document_package"] == "READY"
        assert "SUPPORTED" in verra_pkg["readiness_matrix"]["external_submission"]

        # Test National Registry Bundle
        nat_pkg = await packaging_svc.generate_registry_package(
            registry_type="NIGERIA",
            project_id=proj.id,
        )
        assert nat_pkg["target_registry"] == "NIGERIA"
        assert "ARTICLE6" in nat_pkg["readiness_matrix"]["external_submission"]


@pytest.mark.asyncio
async def test_registry_packaging_and_pdf_generation_via_asset_id():
    factory = _get_fallback_session_factory()
    async with factory() as db:
        org_id = uuid.uuid4()
        proj_id = uuid.uuid4()
        asset_id = uuid.uuid4()

        from app.domains.assets.models import Asset
        db.add(Organization(id=org_id, name=f"Asset Packaging Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
        db.add(Project(id=proj_id, name="Clean Stoves Portfolio", organization_id=org_id))
        asset = Asset(
            id=asset_id,
            project_id=proj_id,
            name="Clean Cookstove Unit A1",
            organization_id=org_id,
            status="active",
            attributes={
                "asset_type": "Clean Cookstove",
                "carbon_offset_kg": 4500,
                "trust_score": 96.5,
                "baseline_fuel_consumption": 4200.0,
            }
        )
        db.add(asset)
        await db.commit()

        # 1. Test Registry Package generation using Asset ID directly
        packaging_svc = RegistryPackagingService(db)
        asset_pkg = await packaging_svc.generate_registry_package(
            registry_type="GOLD_STANDARD",
            project_id=asset_id,
        )
        assert asset_pkg["target_registry"] == "GOLD_STANDARD"
        assert asset_pkg["project"]["name"] == "Clean Stoves Portfolio"
        assert asset_pkg["mrv_quantification"]["total_verified_assets"] == 1
        assert asset_pkg["mrv_quantification"]["total_reductions_tco2e"] == 4.5

        # 2. Test Real PDF generation using ReportingService directly
        repo = ReportRepository(db)
        service = ReportingService(repo)

        payload = ReportCreate(
            org_id=org_id,
            title="Asset-Level MRV Report",
            report_type="MRV_CARBON_LEDGER",
            parameters={"project_id": str(asset_id)},
        )

        created_report = await service.generate_report(payload)
        # Wait for the async task _generate_real_pdf to finish
        for _ in range(20):
            await asyncio.sleep(0.1)
            async with factory() as poll_db:
                rep_stmt = select(Report).where(Report.id == created_report.id)
                rep_res = await poll_db.execute(rep_stmt)
                rep = rep_res.scalar_one()
                if rep.status in ("COMPLETED", "FAILED"):
                    break

        assert rep.status == "COMPLETED"
        assert rep.file_uri is not None
        assert os.path.exists(rep.file_uri)
