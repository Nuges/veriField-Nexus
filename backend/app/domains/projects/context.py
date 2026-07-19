from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.projects.models import Project
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily
from app.domains.methodologies.providers.factory import MethodologyProviderFactory
from app.domains.jurisdictions.models import Jurisdiction

class MethodologyContext:
    """
    The immutable core runtime object for a Project in the CIOS architecture.
    Provides centralized access to Forms, Validators, Calculators, Evidence,
    Reporting, Exports, Compliance, and Dashboard logic, ensuring that 
    nothing bypasses the methodology-driven architecture.
    """
    def __init__(
        self,
        project: Project,
        methodology: Methodology,
        sector: MethodologyFamily,
        jurisdiction: Jurisdiction = None
    ):
        self.project = project
        self.methodology = methodology
        self.sector = sector
        self.jurisdiction = jurisdiction
        self.provider = MethodologyProviderFactory.get_provider(str(methodology.id))
        
    @classmethod
    async def load(cls, db: AsyncSession, project_id: UUID) -> "MethodologyContext":
        """Loads the complete immutable context for a project."""
        project = await db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
            
        methodology = await db.get(Methodology, project.methodology_id)
        if not methodology:
            raise ValueError("Methodology not found for this project")
            
        sector = await db.get(MethodologyFamily, methodology.family_id)
        
        jurisdiction = None
        if project.jurisdiction_id:
            jurisdiction = await db.get(Jurisdiction, project.jurisdiction_id)
            
        return cls(project, methodology, sector, jurisdiction)
        
    # --- Contextual Capabilities ---
    
    async def get_dashboard_analytics(self, db: AsyncSession) -> Dict[str, Any]:
        """Routes to the sector plugin for analytics."""
        return await self.provider.get_dashboard_analytics(db, self.project.id)
        
    async def validate_eligibility(self, data: Dict[str, Any]) -> bool:
        """Routes to the methodology provider for eligibility validation."""
        return await self.provider.validate_eligibility(self.project.id, data)
        
    async def calculate_carbon(self, data: Dict[str, Any]) -> float:
        """Executes the calculator engine specific to this context."""
        return await self.provider.calculate_emission_reduction(data)
        
    async def generate_monitoring_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generates reporting specific to this context."""
        return await self.provider.generate_monitoring_report(self.project.id, start_date, end_date)
