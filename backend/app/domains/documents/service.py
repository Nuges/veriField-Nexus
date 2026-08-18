"""
=============================================================================
VeriField Nexus — Document Intelligence & Ingestion Service
=============================================================================
Orchestrates secure file upload, storage, parsing (PDF/DOCX/OCR), structured
fact extraction, MRV reconciliation, fraud flag tracking, and tenant-scoped indexing.
=============================================================================
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.ai_orchestrator.document_indexer import DocumentIndexerService
from app.domains.authentication.models import User
from app.domains.documents.models import DocumentFraudFlag, ProjectDocument
from app.domains.documents.parsers.docx_parser import DOCXParserService
from app.domains.documents.parsers.ocr_engine import OCREngineService
from app.domains.documents.parsers.pdd_parser import PDDParserService
from app.domains.documents.parsers.pdf_parser import PDFParserService
from app.domains.documents.reconciliation import DocumentReconciliationEngine
from app.domains.documents.security import DocumentSecurityValidator
from app.domains.projects.models import Project

logger = logging.getLogger("verifield.documents.service")

STORAGE_BASE_DIR = os.path.join("static", "documents")


class DocumentService:
    """End-to-end document processing and management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.reconciliation_engine = DocumentReconciliationEngine(db)
        self.indexer_service = DocumentIndexerService(db)

    async def upload_and_process_document(
        self,
        file: UploadFile,
        document_type: str,
        title: Optional[str],
        project_id: Optional[UUID],
        current_user: User,
    ) -> ProjectDocument:
        """
        Executes end-to-end document ingestion:
        1. Binary security & magic bytes validation
        2. Cryptographic SHA-256 calculation
        3. Secure organized object storage
        4. Version determination
        5. Deep text & table parsing (PDF / DOCX)
        6. OCR fallback detection
        7. PDD metadata & fact extraction
        8. Sector/methodology & MRV reconciliation
        9. Fraud flag logging & trust score calculation
        10. Tenant-scoped AI chunk indexing
        """
        # 1. Security validation
        content, clean_filename, mime_type, sha256_hash = await DocumentSecurityValidator.validate_and_read(file)

        # 2. Authorization & Invariant inheritance
        org_id = current_user.organization_id
        if not org_id and current_user.role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: User must belong to an organization to upload documents.",
            )

        sector_id = None
        methodology_id = None

        if project_id:
            proj_stmt = select(Project).where(Project.id == project_id)
            proj_res = await self.db.execute(proj_stmt)
            project = proj_res.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            if current_user.role != "SUPER_ADMIN" and project.organization_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Cannot upload documents to another organization's project.",
                )

            # Inherit project context
            org_id = project.organization_id
            sector_id = project.sector_id
            methodology_id = project.methodology_id
        elif not org_id and current_user.role == "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Super Admin must associate document with a valid project or organization.",
            )

        # 3. Secure file storage
        doc_uuid = uuid.uuid4()
        ext = os.path.splitext(clean_filename)[1].lower()
        relative_dir = os.path.join(str(org_id), str(project_id or "global"))
        target_dir = os.path.join(STORAGE_BASE_DIR, relative_dir)
        os.makedirs(target_dir, exist_ok=True)

        storage_filename = f"{doc_uuid}{ext}"
        storage_path = os.path.join(target_dir, storage_filename)

        with open(storage_path, "wb") as f:
            f.write(content)

        # 4. Versioning check
        doc_title = (title or os.path.splitext(clean_filename)[0]).strip()
        version = 1
        parent_id = None

        if project_id:
            prev_stmt = (
                select(ProjectDocument)
                .where(
                    ProjectDocument.project_id == project_id,
                    ProjectDocument.title == doc_title,
                )
                .order_by(desc(ProjectDocument.version))
            )
            prev_res = await self.db.execute(prev_stmt)
            prev_doc = prev_res.scalars().first()
            if prev_doc:
                version = prev_doc.version + 1
                parent_id = prev_doc.id

        # 5. Create Document Record
        document = ProjectDocument(
            id=doc_uuid,
            organization_id=org_id,
            project_id=project_id,
            sector_id=sector_id,
            methodology_id=methodology_id,
            document_type=document_type.upper(),
            title=doc_title,
            original_filename=clean_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=len(content),
            sha256=sha256_hash,
            status="PROCESSING",
            parser_status="PENDING",
            extraction_status="PENDING",
            verification_status="UNVERIFIED",
            trust_score=100.0,
            trust_breakdown={},
            extracted_data={},
            version=version,
            parent_document_id=parent_id,
            uploaded_by=current_user.id,
        )
        self.db.add(document)
        await self.db.flush()

        # 6. Parse Content
        full_text = ""
        pages_data: List[Dict[str, Any]] = []
        is_scanned = False

        try:
            if ext == ".pdf":
                pdf_res = PDFParserService.parse_pdf(content)
                full_text = pdf_res["full_text"]
                pages_data = pdf_res["pages"]
                is_scanned = pdf_res["is_scanned"]
                document.parser_status = "PARSED"

                if is_scanned:
                    ocr_res = OCREngineService.process_scanned_pdf(content)
                    if ocr_res["ocr_performed"]:
                        full_text = ocr_res["full_text"]
                        pages_data = ocr_res["pages"]
                        document.parser_status = "OCR_PARSED"
                    else:
                        document.status = "OCR_REQUIRED"
                        document.parser_status = "OCR_REQUIRED"
                        logger.info(f"Document {doc_uuid} marked OCR_REQUIRED: {ocr_res.get('error_reason')}")

            elif ext in (".docx", ".xlsx"):
                docx_res = DOCXParserService.parse_docx(content)
                full_text = docx_res["full_text"]
                document.parser_status = "PARSED"

            elif ext in (".csv", ".txt"):
                full_text = content.decode("utf-8", errors="ignore")
                document.parser_status = "PARSED"

        except Exception as e:
            logger.error(f"Failed to parse document {doc_uuid}: {e}")
            document.parser_status = "FAILED"
            document.status = "FAILED"
            await self.db.commit()
            return document

        # 7. Extract PDD Facts & Structure
        extracted_facts: Dict[str, Any] = {}
        if full_text:
            try:
                extracted_facts = PDDParserService.extract_pdd_facts(full_text, document_type=document.document_type)
                document.extracted_data = extracted_facts
                document.extraction_status = "EXTRACTED"
            except Exception as e:
                logger.error(f"Failed structured extraction for document {doc_uuid}: {e}")
                document.extraction_status = "PARTIAL"

        # 8. Reconcile against Project & DB Invariants
        recon_result = await self.reconciliation_engine.reconcile_document(document, extracted_facts)
        document.trust_score = recon_result["trust_score"]
        document.trust_breakdown = recon_result["trust_breakdown"]

        for flag in recon_result["fraud_flags"]:
            self.db.add(flag)

        if recon_result["fraud_flags"]:
            document.status = "REVIEW_REQUIRED"
            document.verification_status = "FLAGGED"
        elif document.status != "OCR_REQUIRED":
            document.status = "PROCESSED"
            document.verification_status = "RECONCILED"

        # 9. Tenant-Scoped Semantic Indexing
        if full_text:
            try:
                await self.indexer_service.index_document(
                    document_id=str(document.id),
                    title=document.title,
                    document_type=document.document_type,
                    content_text=full_text,
                    organization_id=document.organization_id,
                    project_id=str(document.project_id) if document.project_id else None,
                    sector_id=str(document.sector_id) if document.sector_id else None,
                    methodology_id=str(document.methodology_id) if document.methodology_id else None,
                    pages_data=pages_data,
                )
            except Exception as e:
                logger.error(f"Failed to index chunks for document {doc_uuid}: {e}")

        await self.db.commit()
        loaded = await self.get_document(doc_uuid, current_user)
        return loaded or document


    async def get_document(self, document_id: UUID, current_user: User) -> Optional[ProjectDocument]:
        stmt = (
            select(ProjectDocument)
            .options(selectinload(ProjectDocument.fraud_flags))
            .where(ProjectDocument.id == document_id)
        )
        res = await self.db.execute(stmt)
        doc = res.scalar_one_or_none()

        if not doc:
            return None

        if current_user.role != "SUPER_ADMIN":
            if doc.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Cannot access documents belonging to another organization.",
                )

        return doc

    async def list_project_documents(
        self,
        project_id: UUID,
        current_user: User,
    ) -> List[ProjectDocument]:
        # Validate project tenant access
        if current_user.role != "SUPER_ADMIN":
            proj_stmt = select(Project).where(Project.id == project_id)
            proj_res = await self.db.execute(proj_stmt)
            proj = proj_res.scalar_one_or_none()
            if not proj or proj.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Access to this project's documentation is denied.",
                )

        stmt = (
            select(ProjectDocument)
            .options(selectinload(ProjectDocument.fraud_flags))
            .where(ProjectDocument.project_id == project_id)
            .order_by(desc(ProjectDocument.created_at))
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_document_file_for_download(
        self,
        document_id: UUID,
        current_user: User,
    ) -> Tuple[str, str, str]:
        """
        Validates authorization and returns: (absolute_file_path, original_filename, mime_type)
        """
        doc = await self.get_document(document_id, current_user)
        if not os.path.exists(doc.storage_path):
            raise HTTPException(status_code=404, detail="Physical document file missing from storage.")

        # Cryptographic Hash Integrity Verification on download
        expected_hash = getattr(doc, "sha256", None) or getattr(doc, "sha256_hash", None)
        if expected_hash:
            import hashlib
            try:
                with open(doc.storage_path, "rb") as f:
                    disk_hash = hashlib.sha256(f.read()).hexdigest()
                if disk_hash != expected_hash:
                    logger.error(
                        f"CRITICAL INTEGRITY FAILURE: Document {doc.id} hash on disk ({disk_hash}) "
                        f"does not match recorded ledger hash ({expected_hash}). File may be tampered."
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Cryptographic verification failed: Document content integrity mismatch."
                    )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error reading document for integrity check {doc.id}: {e}")
                raise HTTPException(status_code=500, detail="Document integrity check error.")

        return doc.storage_path, doc.original_filename, doc.mime_type

