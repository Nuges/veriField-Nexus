from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.activities.models import Activity
from app.domains.authentication.models import User
from app.domains.methodologies.models.base_registry import Methodology
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


class ABACEngine:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user

    async def _check_org(self, target_org_id: Optional[UUID]):
        if self.user.role == "SUPER_ADMIN":
            return
        if not target_org_id or target_org_id != self.user.organization_id:
            raise HTTPException(
                status_code=403, detail="ABAC: Organization boundary violation."
            )

    async def _check_methodology_license(self, methodology_id: str, org_id: UUID):
        # Checks if organization has the license for the given methodology
        org_result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = org_result.scalar_one_or_none()
        if org and org.metadata_context and "licensed_sectors" in org.metadata_context:
            meth_result = await self.db.execute(
                select(Methodology).where(Methodology.code == methodology_id)
            )
            meth = meth_result.scalar_one_or_none()
            if meth and meth.family:
                sector = meth.family.code.lower()
                if (
                    sector not in org.metadata_context["licensed_sectors"]
                    and "all" not in org.metadata_context["licensed_sectors"]
                ):
                    pass  # Log warning or raise error depending on strictness
        return True

    async def enforce_project_access(self, project_id: UUID):
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        await self._check_org(project.organization_id)
        if project.methodology_id:
            await self._check_methodology_license(
                project.methodology_id, project.organization_id
            )
        return project

    async def enforce_activity_access(
        self, activity_id: UUID, require_mutable: bool = False
    ):
        result = await self.db.execute(
            select(Activity).where(Activity.id == activity_id)
        )
        activity = result.scalar_one_or_none()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        await self._check_org(activity.organization_id)

        if require_mutable and getattr(activity, "is_locked", False):
            raise HTTPException(
                status_code=403,
                detail="ABAC: Resource is locked in current workflow state.",
            )

        if getattr(activity, "project_id", None):
            await self.enforce_project_access(activity.project_id)

        return activity


def get_abac_engine(db: AsyncSession, current_user: User) -> ABACEngine:
    return ABACEngine(db, current_user)
