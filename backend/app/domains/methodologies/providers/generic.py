import uuid
from typing import Any, Dict

from .base import MethodologyRegistryProvider

class GenericMethodologyProvider(MethodologyRegistryProvider):
    """
    A generic fallback methodology provider.
    In a real system, you would have specific providers for GS_TPDDTEC, VM0050, etc.
    """
    
    async def validate_eligibility(self, project_id: uuid.UUID, data: Dict[str, Any]) -> bool:
        return True

    async def calculate_emission_reduction(self, data: Dict[str, Any]) -> float:
        # Generic calculation logic based on provided data
        return float(data.get("energy_generated_kwh", 0)) * 0.7
        
    async def generate_monitoring_report(self, project_id: uuid.UUID, start_date: str, end_date: str) -> Dict[str, Any]:
        return {
            "project_id": str(project_id),
            "start_date": start_date,
            "end_date": end_date,
            "status": "Generated via GenericProvider"
        }
        
    async def get_carbon_price(self) -> float:
        return 10.00
        
    async def get_dashboard_analytics(self, db: Any, project_id: uuid.UUID) -> Dict[str, Any]:
        """Provides fallback analytics structure."""
        return {
            "primary_kpi_1": {"label": "Submissions", "value": 0},
            "primary_kpi_2": {"label": "Total Assets", "value": 0},
            "primary_kpi_3": {"label": "Estimated tCO2e", "value": 0},
            "primary_kpi_4": {"label": "Active Devices", "value": 0},
        }
