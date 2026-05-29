"""
=============================================================================
VeriField Nexus — GPS Validation Service (Cookstove Installation System)
=============================================================================
Adaptive GPS validation engine that:
1. Detects environment type (URBAN vs RURAL) based on asset density
2. Applies dynamic duplicate-detection radius for cookstove installations
3. Returns nearby duplicates with soft warnings (never hard blocks)

Radius Matrix (meters):
  Activity         | Urban   | Rural
  -----------------+---------+------
  CLEAN_COOKING    | 15      | 30
=============================================================================
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.activity import Activity


# ---------------------------------------------------------------------------
# Radius Configuration (meters)
# ---------------------------------------------------------------------------
RADIUS_MATRIX: Dict[str, Dict[str, float]] = {
    "CLEAN_COOKING":     {"URBAN": 15,  "RURAL": 30},
}

# How many existing assets within 200m makes it "urban"
URBAN_DENSITY_THRESHOLD = 5


class GPSValidator:
    """
    Validates GPS coordinates for new installations.
    
    Usage:
        validator = GPSValidator(db)
        result = await validator.check_duplicate(lat, lng, "CLEAN_COOKING")
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Public API
    # =========================================================================

    async def check_duplicate(
        self,
        latitude: float,
        longitude: float,
        activity_type: str,
        exclude_activity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if a new installation at (lat, lng) is a potential duplicate.
        
        Returns:
            {
                "environment_type": "URBAN" | "RURAL",
                "radius_used_m": float,
                "duplicate_flag": bool,
                "nearby_installations": [...],
                "message": str
            }
        """
        # Step 1: Detect environment
        environment = await self._detect_environment(latitude, longitude)

        # Step 2: Get dynamic radius
        activity_key = activity_type.upper()
        radius_config = RADIUS_MATRIX.get(activity_key, RADIUS_MATRIX["OTHER"])
        radius_m = radius_config[environment]

        # Step 3: Find nearby installations within radius
        nearby = await self._find_nearby(
            latitude, longitude, radius_m, activity_key, exclude_activity_id
        )

        duplicate_flag = len(nearby) > 0

        return {
            "environment_type": environment,
            "radius_used_m": radius_m,
            "duplicate_flag": duplicate_flag,
            "nearby_count": len(nearby),
            "nearby_installations": nearby[:5],  # Return max 5 nearest
            "message": (
                f"Similar {activity_type} installation found within {radius_m}m"
                if duplicate_flag
                else "No nearby duplicates detected"
            ),
        }

    # =========================================================================
    # Environment Detection
    # =========================================================================

    async def _detect_environment(
        self, latitude: float, longitude: float
    ) -> str:
        """
        Detect whether a location is URBAN or RURAL based on density
        of existing assets within a 200m radius.
        
        Logic: If there are >= URBAN_DENSITY_THRESHOLD assets within 200m,
        classify as URBAN. Otherwise RURAL.
        """
        # Convert 200m to approximate degree offset
        # 1 degree ≈ 111,320m at equator; for Nigeria (~6°N) it's ~110,500m
        degree_offset = 200 / 110500.0

        result = await self.db.execute(
            select(func.count(Activity.id)).where(
                Activity.latitude.isnot(None),
                Activity.longitude.isnot(None),
                Activity.latitude.between(
                    latitude - degree_offset, latitude + degree_offset
                ),
                Activity.longitude.between(
                    longitude - degree_offset, longitude + degree_offset
                ),
            )
        )
        count = result.scalar() or 0

        if count >= URBAN_DENSITY_THRESHOLD:
            return "URBAN"
        return "RURAL"

    # =========================================================================
    # Nearby Installation Finder
    # =========================================================================

    async def _find_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_m: float,
        activity_type: str,
        exclude_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find existing installations of the same activity type within
        the given radius. Returns a list of nearby installation summaries.
        """
        # Convert radius to degree offset
        degree_offset = radius_m / 110500.0

        conditions = [
            Activity.latitude.isnot(None),
            Activity.longitude.isnot(None),
            Activity.latitude.between(
                latitude - degree_offset, latitude + degree_offset
            ),
            Activity.longitude.between(
                longitude - degree_offset, longitude + degree_offset
            ),
            Activity.activity_type == activity_type,
            Activity.status != "rejected",
        ]

        if exclude_id:
            conditions.append(Activity.id != exclude_id)

        result = await self.db.execute(
            select(Activity).where(*conditions).limit(10)
        )
        activities = result.scalars().all()

        nearby = []
        for act in activities:
            distance_m = self._haversine_meters(
                latitude, longitude, act.latitude, act.longitude
            )
            if distance_m <= radius_m:
                nearby.append({
                    "id": str(act.id),
                    "activity_type": act.activity_type,
                    "distance_m": round(distance_m, 1),
                    "status": act.status,
                    "captured_at": act.captured_at.isoformat() if act.captured_at else None,
                })

        # Sort by distance
        nearby.sort(key=lambda x: x["distance_m"])
        return nearby

    # =========================================================================
    # Utility
    # =========================================================================

    @staticmethod
    def _haversine_meters(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance in meters between two GPS coordinates."""
        R = 6_371_000  # Earth radius in meters
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
