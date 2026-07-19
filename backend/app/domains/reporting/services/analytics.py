import uuid
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.projects.models import CarbonCalculation

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_dashboard_metrics(
        self, 
        org_id: Optional[uuid.UUID] = None, 
        project_id: Optional[uuid.UUID] = None,
        jurisdiction_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dynamically aggregates metrics via Sector Plugin (Methodology Provider).
        """
        if not project_id:
            # Global or Org level fallback if project is not specified
            return await self._get_fallback_dashboard_metrics(org_id)
            
        # Get project context
        from app.domains.projects.context import MethodologyContext
        
        try:
            context = await MethodologyContext.load(self.db, project_id)
            return await context.get_dashboard_analytics(self.db)
        except ValueError:
            return await self._get_fallback_dashboard_metrics(org_id)
        
    async def _get_fallback_dashboard_metrics(self, org_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Original fallback aggregation when no project context exists."""
        act_query = select(func.count(Activity.id))
        ver_query = select(func.count(Activity.id)).where(Activity.status == "verified")
        ast_query = select(func.count(Asset.id))
        cbn_query = select(func.sum(CarbonCalculation.tco2e_generated))
        
        if org_id:
            act_query = act_query.where(Activity.organization_id == org_id)
            ver_query = ver_query.where(Activity.organization_id == org_id)
            ast_query = ast_query.where(Asset.organization_id == org_id)
            
        total_sub = await self.db.scalar(act_query) or 0
        total_ver = await self.db.scalar(ver_query) or 0
        total_ast = await self.db.scalar(ast_query) or 0
        total_cbn = await self.db.scalar(cbn_query) or 0.0

        return {
            "primary_kpi_1": {"label": "Total Submissions", "value": total_sub},
            "primary_kpi_2": {"label": "Verified Submissions", "value": total_ver},
            "primary_kpi_3": {"label": "Total Assets", "value": total_ast},
            "primary_kpi_4": {"label": "Est. tCO2e", "value": round(float(total_cbn), 2)}
        }

    async def get_global_analytics(self) -> Dict[str, Any]:
        """Provides high-level CIOS platform metrics."""
        from app.domains.organizations.models import Organization
        from sqlalchemy import text
        
        # 1. Total installations (activities)
        total_sub = await self.db.scalar(select(func.count(Activity.id))) or 0

        # 2. Avg Trust
        avg_trust = await self.db.scalar(select(func.avg(Activity.trust_score))) or 0.0

        # 3. tCO2
        tco2 = await self.db.scalar(select(func.sum(CarbonCalculation.tco2e_generated))) or 0.0

        # 4. Active Orgs
        active_orgs = await self.db.scalar(select(func.count(Organization.id)).where(Organization.status == "ACTIVE")) or 0

        # 5. Methodologies (group by activity type)
        res_meth = await self.db.execute(text("SELECT activity_type, COUNT(*) FROM activities GROUP BY activity_type"))
        methodologies = {r[0]: r[1] for r in res_meth.all()}

        return {
            "installations": total_sub,
            "avgTrust": round(float(avg_trust), 1),
            "tCO2": round(float(tco2), 2),
            "activeOrgs": active_orgs,
            "methodologies": methodologies
        }
