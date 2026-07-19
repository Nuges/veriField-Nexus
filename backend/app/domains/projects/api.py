from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.projects.repository import ProjectRepository
from app.domains.projects.schemas import (ProjectCreate, ProjectListResponse,
                                          ProjectResponse, ProjectUpdate)
from app.domains.projects.service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ProjectRepository(db)
    service = ProjectService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="User must belong to an organization to create projects.",
        )

    project = await service.create_project(payload, org_id)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    methodology_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ProjectRepository(db)

    org_id = current_user.organization_id

    projects, total = await repo.list_projects_paginated(
        organization_id=org_id,
        methodology_id=methodology_id,
        page=page,
        per_page=per_page,
        user_role=current_user.role,
    )

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects], total=total
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.abac import verify_abac_policy

    await verify_abac_policy(current_user, "read", "Project", project_id, db)

    repo = ProjectRepository(db)
    service = ProjectService(repo)

    org_id = (
        current_user.organization_id if current_user.role != "SUPER_ADMIN" else None
    )
    project = await service.get_project(project_id, org_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ProjectRepository(db)
    service = ProjectService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization."
        )

    updated = await service.update_project(project_id, payload, org_id)
    if not updated:
        raise HTTPException(
            status_code=404, detail="Project not found or unauthorized."
        )
    return ProjectResponse.model_validate(updated)


@router.post("/{project_id}/approve", response_model=ProjectResponse)
async def approve_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ProjectRepository(db)
    service = ProjectService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization."
        )

    approved = await service.approve_project(project_id, org_id)
    if not approved:
        raise HTTPException(
            status_code=404, detail="Project not found or unauthorized."
        )
    return ProjectResponse.model_validate(approved)
