from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.projects.models import Project


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, project_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[Project]:
        stmt = select(Project).where(Project.id == project_id)
        if organization_id:
            stmt = stmt.where(Project.organization_id == organization_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(
        self, code: str, organization_id: Optional[UUID] = None
    ) -> Optional[Project]:
        stmt = select(Project).where(Project.project_code == code)
        if organization_id:
            stmt = stmt.where(Project.organization_id == organization_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, methodology_id: Optional[UUID] = None
    ) -> List[Project]:
        stmt = select(Project).where(Project.organization_id == organization_id)
        if methodology_id:
            stmt = stmt.where(Project.methodology_id == methodology_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_projects_paginated(
        self,
        organization_id: Optional[UUID],
        methodology_id: Optional[UUID] = None,
        page: int = 1,
        per_page: int = 100,
        user_role: Optional[str] = None,
    ) -> tuple[List[Project], int]:
        from sqlalchemy import func

        stmt = select(Project)
        count_stmt = select(func.count(Project.id))

        conditions = []
        if user_role != "SUPER_ADMIN":
            if organization_id:
                conditions.append(Project.organization_id == organization_id)
            else:
                conditions.append(Project.organization_id is None)

        if methodology_id:
            conditions.append(Project.methodology_id == methodology_id)

        if conditions:
            from sqlalchemy import and_

            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        # Count total
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        # Paginate and sort
        offset = (page - 1) * per_page
        stmt = stmt.order_by(Project.created_at.desc()).offset(offset).limit(per_page)

        res = await self.db.execute(stmt)
        items = list(res.scalars().all())

        return items, total

    async def list_all(self) -> List[Project]:
        stmt = select(Project)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, project: Project) -> Project:
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(self, project: Project) -> Project:
        await self.db.commit()
        await self.db.refresh(project)
        return project

class CarbonCalculationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, calc_dict: dict) -> "app.domains.projects.models.CarbonCalculation":
        from app.domains.projects.models import CarbonCalculation
        calc = CarbonCalculation(**calc_dict)
        self.db.add(calc)
        await self.db.flush()
        return calc

    async def get_by_id(self, calc_id: UUID) -> Optional["app.domains.projects.models.CarbonCalculation"]:
        from app.domains.projects.models import CarbonCalculation
        stmt = select(CarbonCalculation).where(CarbonCalculation.id == calc_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_project(self, project_id: UUID) -> List["app.domains.projects.models.CarbonCalculation"]:
        from app.domains.projects.models import CarbonCalculation
        stmt = select(CarbonCalculation).where(CarbonCalculation.project_id == project_id).order_by(CarbonCalculation.executed_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
