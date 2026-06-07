"""
=============================================================================
VeriField Nexus — Project Management API
=============================================================================
Admin-only endpoints for managing carbon project configurations.
Projects are the top-level entity in the 3-layer MRV architecture:

    Project (config/methodology) → Site (captured data) → Calculation Engine

Endpoints:
    POST   /projects          → Create a new project
    GET    /projects          → List all projects (with filtering & pagination)
    GET    /projects/{id}     → Get project detail
    PUT    /projects/{id}     → Update a project
    DELETE /projects/{id}     → Soft-delete a project
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Dict, Any, List
from datetime import date, datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.security import require_admin
from app.models.project import Project
from app.models.carbon_calculation import CarbonCalculation
from app.models.user import User

router = APIRouter(prefix="/projects", tags=["Project Configuration"])


# =============================================================================
# Pydantic Request/Response Models
# =============================================================================

class ProjectCreate(BaseModel):
    """Create a new carbon project with methodology and baseline configuration."""
    project_code: Optional[str] = Field(
        None,
        description="Human-readable project code (e.g. VF-EN-001). Auto-generated if not provided.",
        max_length=20,
    )
    name: str = Field(..., description="Project name", min_length=2, max_length=200)
    sector: str = Field(
        "energy",
        description="Project sector: 'cookstove' or 'energy'",
    )
    country: str = Field(
        "Nigeria",
        description="Country where the project operates",
        max_length=100,
    )
    methodology_id: str = Field(
        ...,
        description="Carbon methodology ID (e.g. 'AMS-I.F', 'VM0050', 'ENERGY_DISPLACEMENT')",
    )
    baseline_source: str = Field(
        "diesel_generator",
        description="Baseline source: 'diesel_generator' or 'grid'",
    )
    diesel_emission_factor: float = Field(
        2.68,
        description="Diesel emission factor in kgCO2/L (IPCC default: 2.68)",
        ge=0.0,
    )
    grid_emission_factor: float = Field(
        0.7,
        description="Grid emission factor in kgCO2/kWh (default: 0.7)",
        ge=0.0,
    )
    crediting_start: Optional[date] = Field(
        None,
        description="Start date of the crediting period",
    )
    crediting_end: Optional[date] = Field(
        None,
        description="End date of the crediting period",
    )
    registry_id: Optional[str] = Field(
        None,
        description="External registry ID (e.g. Verra VCS project ID)",
    )
    baseline_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Methodology-specific baseline parameters (JSONB)",
    )


class ProjectUpdate(BaseModel):
    """Partial update payload for a project."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    sector: Optional[str] = None
    country: Optional[str] = None
    methodology_id: Optional[str] = None
    baseline_source: Optional[str] = None
    diesel_emission_factor: Optional[float] = Field(None, ge=0.0)
    grid_emission_factor: Optional[float] = Field(None, ge=0.0)
    crediting_start: Optional[date] = None
    crediting_end: Optional[date] = None
    registry_id: Optional[str] = None
    baseline_parameters: Optional[Dict[str, Any]] = None


# =============================================================================
# Helpers
# =============================================================================

def _serialize_project(proj: Project, include_stats: bool = False) -> Dict[str, Any]:
    """Convert a Project ORM instance to a serializable dict."""
    data = {
        "id": str(proj.id),
        "project_code": proj.project_code,
        "name": proj.name,
        "sector": proj.sector,
        "country": proj.country,
        "methodology_id": proj.methodology_id,
        "registry_id": proj.registry_id,
        "baseline_source": proj.baseline_source,
        "diesel_emission_factor": proj.diesel_emission_factor,
        "grid_emission_factor": proj.grid_emission_factor,
        "crediting_start": proj.crediting_start.isoformat() if proj.crediting_start else None,
        "crediting_end": proj.crediting_end.isoformat() if proj.crediting_end else None,
        "baseline_parameters": proj.baseline_parameters or {},
        "created_at": proj.created_at.isoformat() if proj.created_at else None,
        "updated_at": proj.updated_at.isoformat() if proj.updated_at else None,
    }
    return data


async def _generate_project_code(db: AsyncSession, sector: str) -> str:
    """
    Auto-generate a sequential project code like VF-EN-001 or VF-CK-001.
    Queries the highest existing code for the sector prefix and increments.
    """
    prefix = "VF-EN" if sector == "energy" else "VF-CK"

    result = await db.execute(
        select(Project.project_code)
        .where(Project.project_code.ilike(f"{prefix}-%"))
        .order_by(Project.project_code.desc())
        .limit(1)
    )
    last_code = result.scalar_one_or_none()

    if last_code:
        try:
            seq = int(last_code.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    return f"{prefix}-{seq:03d}"


# =============================================================================
# POST /api/v1/projects — Create Project
# =============================================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new carbon project",
)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Register a new carbon project with methodology and baseline configuration.

    This is an ADMIN-ONLY endpoint. Projects define the emission factors,
    methodology, and crediting period that all linked sites inherit.
    Mobile forms do NOT capture this data — it lives here on the backend.
    """
    # Validate sector
    valid_sectors = {"cookstove", "energy"}
    if payload.sector.lower() not in valid_sectors:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sector '{payload.sector}'. Must be one of: {', '.join(valid_sectors)}",
        )

    # Validate baseline_source
    valid_sources = {"diesel_generator", "grid"}
    if payload.baseline_source.lower() not in valid_sources:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid baseline_source '{payload.baseline_source}'. Must be one of: {', '.join(valid_sources)}",
        )

    # Validate crediting period
    if payload.crediting_start and payload.crediting_end:
        if payload.crediting_end <= payload.crediting_start:
            raise HTTPException(
                status_code=422,
                detail="crediting_end must be after crediting_start",
            )

    # Auto-generate project_code if not provided
    project_code = payload.project_code
    if not project_code:
        project_code = await _generate_project_code(db, payload.sector.lower())
    else:
        # Check for uniqueness
        existing = await db.execute(
            select(Project).where(Project.project_code == project_code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Project code '{project_code}' already exists",
            )

    # Create the project
    proj = Project(
        project_code=project_code,
        name=payload.name,
        sector=payload.sector.lower(),
        country=payload.country,
        methodology_id=payload.methodology_id,
        baseline_source=payload.baseline_source.lower(),
        diesel_emission_factor=payload.diesel_emission_factor,
        grid_emission_factor=payload.grid_emission_factor,
        crediting_start=payload.crediting_start,
        crediting_end=payload.crediting_end,
        registry_id=payload.registry_id,
        baseline_parameters=payload.baseline_parameters,
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)

    return {
        "status": "created",
        "project": _serialize_project(proj),
    }


# =============================================================================
# GET /api/v1/projects — List Projects
# =============================================================================

@router.get(
    "",
    summary="List all carbon projects",
)
async def list_projects(
    sector: Optional[str] = Query(None, description="Filter by sector: 'cookstove' or 'energy'"),
    methodology: Optional[str] = Query(None, alias="methodology_id", description="Filter by methodology ID"),
    country: Optional[str] = Query(None, description="Filter by country"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    List all carbon projects with optional filtering by sector, methodology,
    and country. Results are paginated.
    """
    query = select(Project)

    # Apply filters
    if sector:
        query = query.where(Project.sector == sector.lower())
    if methodology:
        query = query.where(Project.methodology_id == methodology)
    if country:
        query = query.where(Project.country.ilike(f"%{country}%"))

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Paginate
    query = (
        query.order_by(Project.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    projects = result.scalars().all()

    # Enrich with calculation stats per project
    items = []
    for proj in projects:
        proj_data = _serialize_project(proj)

        # Get calculation count and total tCO2e for this project
        stats_result = await db.execute(
            select(
                func.count(CarbonCalculation.id),
                func.coalesce(func.sum(CarbonCalculation.tco2e_generated), 0.0),
            ).where(CarbonCalculation.project_id == proj.id)
        )
        stats = stats_result.one()
        proj_data["total_calculations"] = stats[0]
        proj_data["total_tco2e"] = round(float(stats[1]), 4)

        items.append(proj_data)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),
    }


# =============================================================================
# GET /api/v1/projects/{project_id} — Project Detail
# =============================================================================

@router.get(
    "/{project_id}",
    summary="Get project detail",
)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Get detailed information about a specific carbon project including
    aggregated calculation statistics.
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    proj_data = _serialize_project(proj)

    # Aggregated stats
    stats_result = await db.execute(
        select(
            func.count(CarbonCalculation.id),
            func.coalesce(func.sum(CarbonCalculation.tco2e_generated), 0.0),
        ).where(CarbonCalculation.project_id == proj.id)
    )
    stats = stats_result.one()
    proj_data["total_calculations"] = stats[0]
    proj_data["total_tco2e"] = round(float(stats[1]), 4)

    # Status breakdown of calculations
    status_result = await db.execute(
        select(
            CarbonCalculation.status,
            func.count(CarbonCalculation.id),
        )
        .where(CarbonCalculation.project_id == proj.id)
        .group_by(CarbonCalculation.status)
    )
    status_breakdown = {row[0]: row[1] for row in status_result.all()}
    proj_data["calculation_status_breakdown"] = status_breakdown

    # Crediting period status
    today = date.today()
    if proj.crediting_start and proj.crediting_end:
        if today < proj.crediting_start:
            proj_data["crediting_status"] = "not_started"
        elif today > proj.crediting_end:
            proj_data["crediting_status"] = "expired"
        else:
            proj_data["crediting_status"] = "active"
            total_days = (proj.crediting_end - proj.crediting_start).days
            elapsed_days = (today - proj.crediting_start).days
            proj_data["crediting_progress_pct"] = round(
                (elapsed_days / total_days) * 100, 1
            ) if total_days > 0 else 0.0
    else:
        proj_data["crediting_status"] = "undefined"

    return proj_data


# =============================================================================
# PUT /api/v1/projects/{project_id} — Update Project
# =============================================================================

@router.put(
    "/{project_id}",
    summary="Update a carbon project",
)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Partially update a carbon project. Only provided fields are updated.
    Emission factors and crediting periods can be modified without affecting
    historical calculations (they are immutable in calculation_log).
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Apply only provided fields
    update_data = payload.model_dump(exclude_unset=True)

    if "sector" in update_data:
        valid_sectors = {"cookstove", "energy"}
        if update_data["sector"].lower() not in valid_sectors:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid sector. Must be one of: {', '.join(valid_sectors)}",
            )
        update_data["sector"] = update_data["sector"].lower()

    if "baseline_source" in update_data:
        valid_sources = {"diesel_generator", "grid"}
        if update_data["baseline_source"].lower() not in valid_sources:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid baseline_source. Must be one of: {', '.join(valid_sources)}",
            )
        update_data["baseline_source"] = update_data["baseline_source"].lower()

    if "baseline_parameters" in update_data:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(proj, "baseline_parameters")

    for field, value in update_data.items():
        setattr(proj, field, value)

    proj.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(proj)

    return {
        "status": "updated",
        "project": _serialize_project(proj),
    }


# =============================================================================
# DELETE /api/v1/projects/{project_id} — Delete Project
# =============================================================================

@router.delete(
    "/{project_id}",
    summary="Delete a carbon project",
)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Delete a carbon project. Fails if the project has associated calculations
    to prevent data loss. Remove calculations first if needed.
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check for associated calculations
    calc_count = await db.execute(
        select(func.count(CarbonCalculation.id))
        .where(CarbonCalculation.project_id == project_id)
    )
    count = calc_count.scalar() or 0
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete project with {count} associated calculation(s). Remove calculations first.",
        )

    await db.delete(proj)
    await db.commit()

    return {
        "status": "deleted",
        "project_id": str(project_id),
        "project_code": proj.project_code,
    }
