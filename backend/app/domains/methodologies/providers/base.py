from abc import ABC, abstractmethod
from typing import Any, Dict
import uuid

class MethodologyRegistryProvider(ABC):
    """
    Abstract interface for Methodology calculations and logic.
    Instead of hardcoding VM0050 or TPDDTEC, we route through this provider.
    """
    
    @abstractmethod
    async def validate_eligibility(self, project_id: uuid.UUID, data: Dict[str, Any]) -> bool:
        """Validate if a project meets methodology requirements."""
        pass

    @abstractmethod
    async def calculate_emission_reduction(self, data: Dict[str, Any]) -> float:
        """Calculate carbon offset value based on methodology algorithms."""
        pass
        
    @abstractmethod
    async def generate_monitoring_report(self, project_id: uuid.UUID, start_date: str, end_date: str) -> Dict[str, Any]:
        """Compile a methodology-compliant monitoring report."""
        pass
        
    @abstractmethod
    async def get_carbon_price(self) -> float:
        """Dynamically resolve carbon unit price based on methodology and registry."""
        pass
        
    @abstractmethod
    async def get_dashboard_analytics(self, db: Any, project_id: uuid.UUID) -> Dict[str, Any]:
        """Dynamically fetch dashboard KPIs via the sector plugin analytics provider."""
        pass
