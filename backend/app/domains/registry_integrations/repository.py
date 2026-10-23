"""Shared read queries for registry evidence preparation."""

from uuid import UUID

from sqlalchemy import and_, false, or_, select

from app.domains.activities.models import Activity


def project_activity_statement(project_id: UUID, organization_id: UUID | None, asset_ids: list[UUID]):
    """Include explicit project records and unassigned legacy records on its assets.

    An organization is a tenant boundary, never a fallback project association.
    A record explicitly assigned to another project is excluded even if its asset
    points at this project.
    """
    scope = Activity.project_id == project_id
    if asset_ids:
        scope = or_(scope, and_(Activity.project_id.is_(None), Activity.asset_id.in_(asset_ids)))
    stmt = select(Activity).where(scope)
    return stmt.where(Activity.organization_id == organization_id) if organization_id else stmt.where(false())
