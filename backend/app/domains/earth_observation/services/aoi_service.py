"""
=============================================================================
VeriField Nexus — Area of Interest (AOI) & Boundary Service
=============================================================================
Manages project and land-unit boundaries for Earth Observation:
- Area of Interest (AOI) resolution and lifecycle.
- Immutable boundary versioning (ProjectBoundaryVersion) tracking historical geometry.
- Truthful spatial state reporting: returns "NO_AOI" when no boundary is defined.
- Geodesic area, perimeter, and bounding box computation via GeospatialEngine.
=============================================================================
"""

import hashlib
import json
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from geoalchemy2.shape import from_shape
from app.domains.earth_observation.models import EOAreaOfInterest, ProjectBoundaryVersion
from app.domains.earth_observation.services.geospatial_engine import geospatial_engine

logger = logging.getLogger(__name__)


class AOIService:
    """
    Manages Earth Observation Areas of Interest (AOIs) and versioned boundaries.
    """

    @staticmethod
    def _compute_geometry_hash(geometry: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash of geometry coordinates."""
        canonical = json.dumps(geometry.get("coordinates", []), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def get_project_active_aoi(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[EOAreaOfInterest]:
        """
        Retrieves the currently active AOI for a project, or None.
        """
        stmt = (
            select(EOAreaOfInterest)
            .where(
                EOAreaOfInterest.project_id == project_id,
                EOAreaOfInterest.organization_id == organization_id,
                EOAreaOfInterest.is_active == True,
            )
            .order_by(desc(EOAreaOfInterest.created_at))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    get_active_aoi = get_project_active_aoi

    async def get_aoi_by_id(
        self,
        db: AsyncSession,
        aoi_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[EOAreaOfInterest]:
        """
        Fetches an AOI by primary key within organization boundary.
        """
        stmt = select(EOAreaOfInterest).where(
            EOAreaOfInterest.id == aoi_id,
            EOAreaOfInterest.organization_id == organization_id,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def set_project_boundary(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        geometry_geojson: Dict[str, Any],
        name: str = "Project Boundary",
        source: str = "DECLARED",
        reason: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[EOAreaOfInterest, ProjectBoundaryVersion]:
        """
        Validates, computes spatial properties, registers a new boundary version,
        and establishes an active AOI record.
        """
        # Validate and normalize
        normalized_geom = geospatial_engine.validate_and_normalize_geojson(geometry_geojson)
        area_m2, area_ha, perimeter_m = geospatial_engine.calculate_geodesic_polygon_area_perimeter(normalized_geom)
        min_lon, min_lat, max_lon, max_lat = geospatial_engine.calculate_bounding_box(normalized_geom)
        centroid_lon = round((min_lon + max_lon) / 2.0, 6)
        centroid_lat = round((min_lat + max_lat) / 2.0, 6)

        bbox_dict = {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        }

        # Query existing boundary versions to determine next version number
        v_stmt = (
            select(ProjectBoundaryVersion)
            .where(
                ProjectBoundaryVersion.project_id == project_id,
                ProjectBoundaryVersion.organization_id == organization_id,
            )
            .order_by(desc(ProjectBoundaryVersion.version_number))
        )
        v_result = await db.execute(v_stmt)
        latest_ver = v_result.scalars().first()
        next_ver_num = (latest_ver.version_number + 1) if latest_ver else 1

        # Compute authoritative geometry element
        shape_geom = geospatial_engine.geometry_to_shape(normalized_geom)
        geom_wkb = from_shape(shape_geom, srid=4326)

        # Create new boundary version record
        boundary_version = ProjectBoundaryVersion(
            organization_id=organization_id,
            project_id=project_id,
            version_number=next_ver_num,
            effective_date=date.today(),
            boundary_geojson=normalized_geom,
            geom=geom_wkb,
            source=source,
            reason=reason or f"Boundary update v{next_ver_num}",
            area_ha=area_ha,
            perimeter_m=perimeter_m,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            crs="EPSG:4326",
            created_by_id=user_id,
        )
        db.add(boundary_version)
        await db.flush()

        # Deactivate previous active AOIs for this project
        existing_aois_stmt = select(EOAreaOfInterest).where(
            EOAreaOfInterest.project_id == project_id,
            EOAreaOfInterest.organization_id == organization_id,
            EOAreaOfInterest.is_active == True,
        )
        existing_aois = (await db.execute(existing_aois_stmt)).scalars().all()
        for aoi in existing_aois:
            aoi.is_active = False

        # Create new active AOI
        aoi = EOAreaOfInterest(
            organization_id=organization_id,
            project_id=project_id,
            name=name,
            aoi_type="PROJECT_BOUNDARY",
            boundary_version_id=boundary_version.id,
            geometry_geojson=normalized_geom,
            geom=geom_wkb,
            bbox=bbox_dict,
            area_ha=area_ha,
            crs="EPSG:4326",
            is_active=True,
        )
        db.add(aoi)
        await db.commit()
        await db.refresh(aoi)
        await db.refresh(boundary_version)

        logger.info(
            "Project %s boundary configured: AOI %s, Version %s, Area %.2f ha",
            project_id,
            aoi.id,
            next_ver_num,
            area_ha,
        )
        return aoi, boundary_version

    async def list_boundary_history(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[ProjectBoundaryVersion]:
        """Lists historical boundary versions for an audit trail."""
        stmt = (
            select(ProjectBoundaryVersion)
            .where(
                ProjectBoundaryVersion.project_id == project_id,
                ProjectBoundaryVersion.organization_id == organization_id,
            )
            .order_by(desc(ProjectBoundaryVersion.version_number))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


aoi_service = AOIService()
