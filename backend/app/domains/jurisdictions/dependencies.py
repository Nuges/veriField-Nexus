import logging
import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# from app.domains.projects.models import Project # Assuming we'd import this to check dependencies

logger = logging.getLogger("verifield.jurisdictions.dependencies")


class JurisdictionDependencyAnalyzer:
    """
    Analyzes downstream dependencies of a jurisdiction before allowing state mutations (Archive, Delete, Suspend).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_dependencies(self, jurisdiction_id: uuid.UUID) -> Dict[str, Any]:
        """
        Returns a dictionary detailing all active dependencies.
        """
        logger.info(f"Running dependency analysis for jurisdiction {jurisdiction_id}")

        from sqlalchemy import func

        from app.domains.jurisdictions.models import ComplianceFramework
        from app.domains.projects.models import Project

        # Real dependency analysis
        stmt_proj = (
            select(func.count())
            .select_from(Project)
            .where(Project.jurisdiction_id == jurisdiction_id)
        )
        active_projects = await self.db.scalar(stmt_proj) or 0

        stmt_fw = (
            select(func.count())
            .select_from(ComplianceFramework)
            .where(ComplianceFramework.jurisdiction_id == jurisdiction_id)
        )
        active_frameworks = await self.db.scalar(stmt_fw) or 0

        has_dependencies = active_projects > 0 or active_frameworks > 0

        return {
            "has_dependencies": has_dependencies,
            "impact_summary": {
                "active_projects": active_projects,
                "active_frameworks": active_frameworks,
            },
            "can_safely_delete": not has_dependencies,
            "recommendation": "ARCHIVE" if has_dependencies else "DELETE",
        }
