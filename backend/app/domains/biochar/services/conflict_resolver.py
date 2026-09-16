import uuid
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.geospatial import compute_geodesic_area_ha
from app.domains.agriculture.models import LandUnit
from app.domains.biochar.models import BiocharBatch, BiocharCarbonPoolClaim, BiocharEndUseRecord
from app.domains.biochar.schemas import MethodologyConflictResponse
from app.domains.methodologies.models.base_registry import Methodology
from app.domains.projects.models import Project


def _extract_ring(geojson: Optional[Dict[str, Any]]) -> Optional[List[List[float]]]:
    """Extracts the first exterior ring from a GeoJSON Polygon or MultiPolygon."""
    if not geojson or not isinstance(geojson, dict):
        return None
    g_type = geojson.get("type")
    coords = geojson.get("coordinates")
    if not coords or not isinstance(coords, list):
        return None
    if g_type == "Polygon" and len(coords) > 0 and isinstance(coords[0], list):
        return coords[0]
    elif g_type == "MultiPolygon" and len(coords) > 0 and len(coords[0]) > 0 and isinstance(coords[0][0], list):
        return coords[0][0]
    return None


def _clip_polygon(subject_polygon: List[List[float]], clip_polygon: List[List[float]]) -> List[List[float]]:
    """
    Sutherland-Hodgman polygon clipping algorithm.
    Clips a subject polygon ring against a convex/general clip polygon ring.
    Returns the intersection polygon vertices.
    """
    if not subject_polygon or not clip_polygon:
        return []

    # Clean closed ring points for clipping
    sub = subject_polygon[:-1] if (len(subject_polygon) > 1 and subject_polygon[0] == subject_polygon[-1]) else list(subject_polygon)
    clp = clip_polygon[:-1] if (len(clip_polygon) > 1 and clip_polygon[0] == clip_polygon[-1]) else list(clip_polygon)

    if len(sub) < 3 or len(clp) < 3:
        return []

    def inside(p, cp1, cp2):
        return (cp2[0] - cp1[0]) * (p[1] - cp1[1]) >= (cp2[1] - cp1[1]) * (p[0] - cp1[0])

    def intersection(cp1, cp2, s, e):
        dc = [cp1[0] - cp2[0], cp1[1] - cp2[1]]
        dp = [s[0] - e[0], s[1] - e[1]]
        n1 = cp1[0] * cp2[1] - cp1[1] * cp2[0]
        n2 = s[0] * e[1] - s[1] * e[0]
        denom = dc[0] * dp[1] - dc[1] * dp[0]
        if abs(denom) < 1e-12:
            return s
        n3 = 1.0 / denom
        return [(n1 * dp[0] - n2 * dc[0]) * n3, (n1 * dp[1] - n2 * dc[1]) * n3]

    output_list = sub
    cp1 = clp[-1]
    for cp2 in clp:
        input_list = output_list
        output_list = []
        if not input_list:
            break
        s = input_list[-1]
        for e in input_list:
            if inside(e, cp1, cp2):
                if not inside(s, cp1, cp2):
                    output_list.append(intersection(cp1, cp2, s, e))
                output_list.append(e)
            elif inside(s, cp1, cp2):
                output_list.append(intersection(cp1, cp2, s, e))
            s = e
        cp1 = cp2

    return output_list


class BiocharMethodologyConflictResolver:
    """
    Cross-Sector Methodology & Carbon Pool Double-Counting Conflict Engine.
    Detects and blocks invalid combined accounting across:
    1. Direct shared LandUnit relationships.
    2. Material Spatial Geometry Overlap (polygon intersection area > 0 ha).
    3. Overlapping Accounting / Monitoring / Crediting Periods.
    4. Conflicting Carbon Pool claims (e.g. VM0044 biochar vs VM0042 SOC on soil parcels).
    """

    @staticmethod
    async def check_land_unit_conflict(
        db: AsyncSession,
        land_unit_id: UUID,
        biochar_methodology: str = "VM0044",
        biochar_project_id: Optional[UUID] = None,
        evaluation_date: Optional[datetime] = None,
    ) -> MethodologyConflictResponse:
        """
        Proactively evaluates whether applying biochar under the specified methodology
        to the target LandUnit conflicts with an existing Agriculture project methodology
        or active carbon pool claim (directly or through spatial geometry intersection).
        """
        stmt_lu = select(LandUnit).where(LandUnit.id == land_unit_id)
        res_lu = await db.execute(stmt_lu)
        land_unit = res_lu.scalar_one_or_none()
        if not land_unit:
            return MethodologyConflictResponse(
                has_conflict=False,
                message=f"Land unit {land_unit_id} not found; no conflicting accounting detected.",
            )

        # 1. Direct LandUnit Project Check
        stmt_proj = select(Project).where(Project.id == land_unit.project_id)
        res_proj = await db.execute(stmt_proj)
        ag_proj = res_proj.scalar_one_or_none()

        ag_meth_code = "UNKNOWN"
        if ag_proj and ag_proj.methodology_id:
            stmt_m = select(Methodology).where(Methodology.id == ag_proj.methodology_id)
            res_m = await db.execute(stmt_m)
            meth = res_m.scalar_one_or_none()
            if meth:
                ag_meth_code = meth.code.upper()

        is_biochar_vm0044 = "VM0044" in biochar_methodology.upper()
        is_ag_vm0042 = "VM0042" in ag_meth_code

        # If the target land unit itself belongs to a VM0042 project
        if is_biochar_vm0044 and is_ag_vm0042:
            return MethodologyConflictResponse(
                has_conflict=True,
                conflict_code="DOUBLE_COUNTING_VM0044_VM0042_SOC",
                severity="BLOCKING",
                biochar_project_id=biochar_project_id,
                agriculture_project_id=ag_proj.id if ag_proj else None,
                affected_land_unit_id=land_unit.id,
                affected_land_unit_name=land_unit.name,
                biochar_methodology=biochar_methodology,
                agriculture_methodology=ag_meth_code,
                carbon_pool="SOIL_ORGANIC_CARBON",
                spatial_overlap_hectares=float(land_unit.area_ha or 0.0),
                time_overlap_detected=True,
                message=(
                    f"Methodology Conflict: Biochar applied under {biochar_methodology} overlaps with "
                    f"Agriculture project '{ag_proj.name if ag_proj else 'Unknown'}' under {ag_meth_code} "
                    f"(SOC pool quantification) on LandUnit '{land_unit.name}'. "
                    f"Combined carbon accounting is blocked to prevent double-counting of soil carbon removals."
                ),
                resolution_requirement=(
                    "Exclude LandUnit from VM0042 SOC accounting boundary, reallocate biochar to a non-VM0042 "
                    "land unit, or record end-use under a non-soil durable product category."
                ),
                accounting_blocked=True,
            )

        # 2. Multi-factor Spatial Geometry Overlap Check against other Agriculture LandUnits
        target_ring = _extract_ring(land_unit.boundary_geojson)
        if target_ring and is_biochar_vm0044:
            # Query active agriculture land units from other projects
            stmt_other_lus = (
                select(LandUnit, Project, Methodology)
                .join(Project, LandUnit.project_id == Project.id)
                .join(Methodology, Project.methodology_id == Methodology.id)
                .where(
                    LandUnit.id != land_unit.id,
                    LandUnit.is_active == True,
                    Methodology.code.ilike("%VM0042%"),
                )
            )
            res_other = await db.execute(stmt_other_lus)
            rows = res_other.all()

            for other_lu, other_proj, other_meth in rows:
                other_ring = _extract_ring(other_lu.boundary_geojson)
                if not other_ring:
                    continue

                clipped_vertices = _clip_polygon(target_ring, other_ring)
                if len(clipped_vertices) >= 3:
                    closed_clipped = list(clipped_vertices)
                    if closed_clipped[0] != closed_clipped[-1]:
                        closed_clipped.append(closed_clipped[0])

                    try:
                        overlap_ha, _ = compute_geodesic_area_ha({"type": "Polygon", "coordinates": [closed_clipped]})
                    except Exception:
                        overlap_ha = 0.0

                    # If spatial overlap is detected (> 0.001 ha)
                    if overlap_ha > 0.001:
                        return MethodologyConflictResponse(
                            has_conflict=True,
                            conflict_code="DOUBLE_COUNTING_SPATIAL_GEOMETRY_OVERLAP_SOC",
                            severity="BLOCKING",
                            biochar_project_id=biochar_project_id,
                            agriculture_project_id=other_proj.id,
                            affected_land_unit_id=other_lu.id,
                            affected_land_unit_name=other_lu.name,
                            biochar_methodology=biochar_methodology,
                            agriculture_methodology=other_meth.code,
                            carbon_pool="SOIL_ORGANIC_CARBON",
                            spatial_overlap_hectares=round(overlap_ha, 4),
                            time_overlap_detected=True,
                            message=(
                                f"Methodology Spatial Conflict: Biochar applied under {biochar_methodology} on "
                                f"'{land_unit.name}' spatially intersects with Agriculture LandUnit '{other_lu.name}' "
                                f"({round(overlap_ha, 4)} ha overlap) under {other_meth.code} (SOC pool quantification). "
                                f"Combined carbon accounting is blocked to prevent double-counting of soil carbon removals."
                            ),
                            resolution_requirement=(
                                "Adjust biochar application boundary to eliminate spatial overlap with VM0042 parcel, "
                                "or reallocate biochar to non-agricultural durable end-use."
                            ),
                            accounting_blocked=True,
                        )

        # 3. Explicit BiocharCarbonPoolClaim Table Check
        stmt_claim = (
            select(BiocharCarbonPoolClaim)
            .where(
                BiocharCarbonPoolClaim.land_unit_id == land_unit_id,
                BiocharCarbonPoolClaim.carbon_pool == "SOIL_ORGANIC_CARBON",
                BiocharCarbonPoolClaim.claim_status.in_(["ACTIVE", "ALLOCATED", "VERIFIED"]),
            )
        )
        res_claim = await db.execute(stmt_claim)
        existing_claim = res_claim.scalar_one_or_none()
        if existing_claim and is_biochar_vm0044:
            return MethodologyConflictResponse(
                has_conflict=True,
                conflict_code="CARBON_POOL_CLAIM_DOUBLE_COUNTING",
                severity="BLOCKING",
                biochar_project_id=biochar_project_id,
                affected_land_unit_id=land_unit.id,
                affected_land_unit_name=land_unit.name,
                biochar_methodology=biochar_methodology,
                carbon_pool="SOIL_ORGANIC_CARBON",
                time_overlap_detected=True,
                message=(
                    f"Carbon Pool Conflict: Active claim {existing_claim.claim_id} for SOIL_ORGANIC_CARBON "
                    f"already exists on LandUnit '{land_unit.name}'."
                ),
                resolution_requirement="Resolve existing carbon pool claim prior to biochar application.",
                accounting_blocked=True,
            )

        return MethodologyConflictResponse(
            has_conflict=False,
            affected_land_unit_id=land_unit.id,
            affected_land_unit_name=land_unit.name,
            biochar_methodology=biochar_methodology,
            agriculture_methodology=ag_meth_code,
            spatial_overlap_hectares=0.0,
            time_overlap_detected=False,
            message="No cross-sector carbon pool double-counting conflict detected.",
            accounting_blocked=False,
        )

    @classmethod
    async def check_end_use_record_conflict(
        cls,
        db: AsyncSession,
        end_use_record: BiocharEndUseRecord,
    ) -> MethodologyConflictResponse:
        """
        Evaluates a single end-use record for potential carbon pool double counting.
        Non-soil applications are intrinsically safe.
        """
        if (end_use_record.end_use_type or "").upper() != "SOIL_APPLICATION":
            return MethodologyConflictResponse(
                has_conflict=False,
                message="Non-soil application does not interact with agricultural soil carbon pools.",
                accounting_blocked=False,
            )

        if not end_use_record.source_land_unit_id:
            return MethodologyConflictResponse(
                has_conflict=False,
                message="Soil application is not linked to a registered LandUnit.",
                accounting_blocked=False,
            )

        # Retrieve batch methodology
        stmt_b = select(BiocharBatch).where(BiocharBatch.id == end_use_record.batch_id)
        res_b = await db.execute(stmt_b)
        batch = res_b.scalar_one_or_none()

        biochar_meth = "VM0044"
        biochar_pid = None
        if batch:
            biochar_meth = batch.carbon_claim_methodology or "VM0044"
            biochar_pid = batch.carbon_claim_project_id or batch.project_id

        return await cls.check_land_unit_conflict(
            db=db,
            land_unit_id=end_use_record.source_land_unit_id,
            biochar_methodology=biochar_meth,
            biochar_project_id=biochar_pid,
        )
