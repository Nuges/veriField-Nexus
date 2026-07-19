from abc import ABC, abstractmethod
from typing import Any, Dict, List
import uuid

class JurisdictionBoundaryProvider(ABC):
    """
    Interface for providing and resolving jurisdictional boundaries.
    Must support resolving hierarchical relations: Country -> State -> Region -> LGA -> Custom Polygon.
    """
    
    @abstractmethod
    async def load_boundary(self, source_path: str) -> Dict[str, Any]:
        """Load boundary data from a data source (GeoJSON, Shapefile, WMS, PostGIS, etc.)"""
        pass

    @abstractmethod
    async def get_boundary_by_code(self, code: str) -> Dict[str, Any]:
        """Return the spatial boundary GeoJSON/Geometry for a specific jurisdiction code."""
        pass
        
    @abstractmethod
    async def contains_point(self, code: str, lat: float, lng: float) -> bool:
        """Check if a specific coordinate falls inside the jurisdiction boundary."""
        pass
        
    @abstractmethod
    async def get_hierarchy(self, code: str) -> List[Dict[str, Any]]:
        """Return the hierarchical lineage of the jurisdiction."""
        pass
