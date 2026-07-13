from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select

from app.domains.projects.events import (publish_project_approved,
                                         publish_project_created)
from app.domains.projects.models import Project
from app.domains.projects.repository import ProjectRepository
from app.domains.projects.schemas import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository

    async def get_project(
        self, project_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[Project]:
        return await self.repository.get_by_id(project_id, organization_id)

    async def get_project_by_code(
        self, code: str, organization_id: Optional[UUID] = None
    ) -> Optional[Project]:
        return await self.repository.get_by_code(code, organization_id)

    async def list_projects(
        self, organization_id: UUID, methodology_id: Optional[UUID] = None
    ) -> List[Project]:
        return await self.repository.list_by_organization(
            organization_id, methodology_id
        )

    async def create_project(
        self, payload: ProjectCreate, organization_id: UUID
    ) -> Project:
        # Generate project code dynamically: e.g. VF-GP-001
        prefix = "GP"

        # Simple atomic counter using count + 1
        stmt = select(func.count(Project.id)).where(
            Project.methodology_id == payload.methodology_id
        )
        res = await self.repository.db.execute(stmt)
        count = res.scalar() or 0
        project_code = f"VF-{prefix}-{count + 1:03d}"

        from app.domains.jurisdictions.models import Jurisdiction

        jurisdiction_id = None
        if payload.country:
            j_stmt = select(Jurisdiction).where(
                func.lower(Jurisdiction.name) == func.lower(payload.country)
            )
            j_res = await self.repository.db.execute(j_stmt)
            jur = j_res.scalar_one_or_none()
            if jur:
                jurisdiction_id = jur.id

        project = Project(
            project_code=project_code,
            name=payload.name,
            country=payload.country,
            organization_id=organization_id,
            jurisdiction_id=jurisdiction_id,
            programme_id=payload.programme_id,
            methodology_id=payload.methodology_id,
            methodology_version_id=payload.methodology_version_id,
            registry_id=payload.registry_id,
            baseline_source=payload.baseline_source,
            diesel_emission_factor=payload.diesel_emission_factor,
            grid_emission_factor=payload.grid_emission_factor,
            crediting_start=payload.crediting_start,
            crediting_end=payload.crediting_end,
            baseline_parameters=payload.baseline_parameters or {},
            created_at=datetime.now(timezone.utc),
        )

        created = await self.repository.create(project)
        await publish_project_created(
            str(created.id), str(organization_id), str(created.methodology_id)
        )
        return created

    async def update_project(
        self, project_id: UUID, payload: ProjectUpdate, organization_id: UUID
    ) -> Optional[Project]:
        project = await self.repository.get_by_id(project_id, organization_id)
        if not project:
            return None

        if payload.name is not None:
            project.name = payload.name
        if payload.registry_id is not None:
            project.registry_id = payload.registry_id
        if payload.crediting_start is not None:
            project.crediting_start = payload.crediting_start
        if payload.crediting_end is not None:
            project.crediting_end = payload.crediting_end
        if payload.baseline_parameters is not None:
            project.baseline_parameters = payload.baseline_parameters

        return await self.repository.update(project)

    async def approve_project(
        self, project_id: UUID, organization_id: UUID
    ) -> Optional[Project]:
        project = await self.repository.get_by_id(project_id, organization_id)
        if not project:
            return None
        # Publish project approved event (triggers signature initialization in background)
        await publish_project_approved(str(project.id), str(organization_id))
        return project
