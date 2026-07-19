from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.activities.models import Activity


class ActivityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, activity_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[Activity]:
        stmt = (
            select(Activity)
            .options(selectinload(Activity.user))
            .where(Activity.id == activity_id)
        )
        if organization_id:
            stmt = stmt.where(Activity.organization_id == organization_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_client_id(
        self, client_id: str, organization_id: Optional[UUID] = None
    ) -> Optional[Activity]:
        stmt = (
            select(Activity)
            .options(selectinload(Activity.user))
            .where(Activity.client_id == client_id)
        )
        if organization_id:
            stmt = stmt.where(Activity.organization_id == organization_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, status: Optional[str] = None
    ) -> List[Activity]:
        stmt = select(Activity).where(Activity.organization_id == organization_id)
        if status:
            stmt = stmt.where(Activity.status == status)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_activities_paginated(
        self,
        organization_id: Optional[UUID],
        activity_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None,
        property_id: Optional[UUID] = None,
        asset_id: Optional[UUID] = None,
        date_from=None,  # datetime object
        date_to=None,  # datetime object
        min_trust: Optional[float] = None,
        max_trust: Optional[float] = None,
        duplicate_only: Optional[bool] = None,
        methodology_id: Optional[UUID] = None,
        page: int = 1,
        per_page: int = 20,
        user_role: Optional[str] = None,
        requesting_user_id: Optional[UUID] = None,
    ) -> tuple[List[Activity], int]:
        from sqlalchemy import and_, func
        from sqlalchemy.orm import selectinload

        from app.domains.authentication.models import User as UserModel

        # Base query with loaded user relation for agent_name
        query = (
            select(Activity)
            .join(UserModel, Activity.user_id == UserModel.id)
            .options(selectinload(Activity.user))
        )
        count_query = select(func.count(Activity.id)).join(
            UserModel, Activity.user_id == UserModel.id
        )

        conditions = []
        # Multi-tenancy Scoping
        if user_role == "SUPER_ADMIN":
            if user_id:
                conditions.append(Activity.user_id == user_id)
        elif user_role == "admin" or user_role == "ORG_ADMIN":
            if organization_id:
                conditions.append(Activity.organization_id == organization_id)
            if user_id:
                conditions.append(Activity.user_id == user_id)
        else:
            # Field Agent or other roles scope to own submissions
            if requesting_user_id:
                conditions.append(Activity.user_id == requesting_user_id)

        if activity_type:
            conditions.append(Activity.activity_type == activity_type)
        if status:
            conditions.append(Activity.status == status)
        if property_id:
            conditions.append(Activity.property_id == property_id)
        if asset_id:
            conditions.append(Activity.asset_id == asset_id)
        if date_from:
            conditions.append(Activity.captured_at >= date_from)
        if date_to:
            conditions.append(Activity.captured_at <= date_to)
        if min_trust is not None:
            conditions.append(Activity.trust_score >= min_trust)
        if max_trust is not None:
            conditions.append(Activity.trust_score <= max_trust)
        if duplicate_only:
            conditions.append(Activity.duplicate_flag)
        if methodology_id:
            from app.domains.projects.models import Project

            query = query.join(Project, Activity.project_id == Project.id)
            count_query = count_query.join(Project, Activity.project_id == Project.id)
            conditions.append(Project.methodology_id == methodology_id)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Count total
        count_res = await self.db.execute(count_query)
        total = count_res.scalar() or 0

        # Paginate and sort
        offset = (page - 1) * per_page
        query = (
            query.order_by(Activity.created_at.desc()).offset(offset).limit(per_page)
        )

        res = await self.db.execute(query)
        items = list(res.scalars().all())

        return items, total

    async def create(self, activity: Activity) -> Activity:
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def update(self, activity: Activity) -> Activity:
        await self.db.commit()
        await self.db.refresh(activity)
        return activity
