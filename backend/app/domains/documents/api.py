"""
=============================================================================
VeriField Nexus — Document Intelligence API Router
=============================================================================
Provides endpoints for document upload, retrieval, download, fraud flag inspection,
and version tracking with strict multi-tenant authorization.
=============================================================================
"""

from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.documents.models import DocumentFraudFlag, ProjectDocument
from app.domains.documents.schemas import (
    DocumentFraudFlagResponse,
    DocumentUploadResponse,
    ProjectDocumentResponse,
)
from app.domains.documents.service import DocumentService

router = APIRouter(tags=["Document Intelligence"])


@router.post("/projects/{project_id}/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_document(
    project_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads, parses, validates, and indexes a project document (PDD, Monitoring Report, etc.).
    Automatically inherits organization_id, project_id, sector_id, and methodology_id.
    """
    # Restrict roles permitted to upload supporting documentation
    allowed_roles = {"SUPER_ADMIN", "ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "QA_OFFICER", "FIELD_SUPERVISOR"}
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to upload project documents.",
        )

    service = DocumentService(db)
    doc = await service.upload_and_process_document(
        file=file,
        document_type=document_type,
        title=title,
        project_id=project_id,
        current_user=current_user,
    )

    msg = "Document uploaded and parsed successfully."
    if doc.status == "REVIEW_REQUIRED":
        msg = f"Document uploaded with {len(doc.fraud_flags)} integrity/reconciliation flags requiring review."
    elif doc.status == "OCR_REQUIRED":
        msg = "Document is scanned image-only PDF. Marked OCR_REQUIRED."

    return {
        "document": doc,
        "message": msg,
        "processing_status": doc.status,
    }


@router.get("/projects/{project_id}/documents", response_model=List[ProjectDocumentResponse])
async def list_project_documents(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all documents associated with a project."""
    service = DocumentService(db)
    return await service.list_project_documents(project_id, current_user)


@router.get("/documents/{document_id}", response_model=ProjectDocumentResponse)
async def get_document_details(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves metadata, trust scores, and extracted facts for a document."""
    service = DocumentService(db)
    doc = await service.get_document(document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Securely downloads an authenticated project document."""
    service = DocumentService(db)
    filepath, filename, mime_type = await service.get_document_file_for_download(document_id, current_user)

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.get("/documents/{document_id}/fraud-flags", response_model=List[DocumentFraudFlagResponse])
async def get_document_fraud_flags(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns reconciliation and fraud audit flags for a document."""
    service = DocumentService(db)
    doc = await service.get_document(document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    stmt = select(DocumentFraudFlag).where(DocumentFraudFlag.document_id == document_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/documents/{document_id}/versions", response_model=List[ProjectDocumentResponse])
async def get_document_versions(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns all historical versions of a document."""
    service = DocumentService(db)
    doc = await service.get_document(document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Find root document
    root_id = doc.parent_document_id or doc.id

    stmt = (
        select(ProjectDocument)
        .where(
            (ProjectDocument.id == root_id) |
            (ProjectDocument.parent_document_id == root_id) |
            (ProjectDocument.title == doc.title) & (ProjectDocument.project_id == doc.project_id)
        )
        .order_by(desc(ProjectDocument.version))
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())
