from datetime import date
from typing import Any, Dict, List, Optional, Union
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.core.security import get_current_user
from app.core.sectors import (
    CanonicalSector,
    CANONICAL_SECTOR_PRODUCTION_METHODOLOGIES,
    CANONICAL_SECTOR_LABELS,
    CANONICAL_SECTOR_UUID_MAP,
    DISALLOWED_PRIMARY_METHODOLOGY_CODES,
    UNCONFIGURED_METHODOLOGY_CODES,
    get_production_methodologies_for_sector,
    get_canonical_methodology_codes_for_sector,
    normalize_to_canonical_sector,
)
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.methodologies.models.base_registry import MethodologyFamily
from app.domains.methodologies.schemas.registry import (
    FamilySchema,
    MethodologyCreate,
    MethodologyRecommendationResponse,
    MethodologySchema,
    MethodologyVersionCreate,
    MethodologyVersionSchema,
    MethodologyVersionStatusUpdate,
    RegistrySchema,
)
from app.domains.methodologies.services.forms import FormGenerationService
from app.domains.methodologies.services.methodology import MethodologyService

router = APIRouter()


def _synthesize_canonical_methodology_schema(item: Dict[str, Any], sec: CanonicalSector) -> MethodologySchema:
    sec_uuid_str = {v: k for k, v in CANONICAL_SECTOR_UUID_MAP.items()}.get(sec, "9a7a4370-71e6-44f5-9870-975823b8ccb9")
    fam_uuid = UUID(sec_uuid_str)
    reg_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"registry.{item.get('registry_code', 'VERRA')}")
    meth_uuid = UUID(item["id"])
    ver_uuid = uuid.uuid5(meth_uuid, item.get("version", "1.0.0"))
    return MethodologySchema(
        id=meth_uuid,
        code=item["code"],
        name=item["name"],
        description=item.get("description"),
        registry=RegistrySchema(
            id=reg_uuid,
            code=item.get("registry_code", "VERRA"),
            name=item.get("registry_name", "Verra (VCS)"),
            description=None,
            is_active=True,
        ),
        family=FamilySchema(
            id=fam_uuid,
            code=sec.value,
            name=CANONICAL_SECTOR_LABELS.get(sec, sec.value),
            description=None,
            project_types=[],
        ),
        versions=[
            MethodologyVersionSchema(
                id=ver_uuid,
                version=item.get("version", "1.0.0"),
                status="ACTIVE",
                release_date=date(2024, 1, 1),
                retirement_date=None,
            )
        ],
        ui_config={},
        form_schema={},
        recommendation_rules={},
    )


@router.get("", response_model=List[MethodologySchema])
async def list_methodologies(
    sector: Optional[str] = Query(None),
    sector_id: Optional[str] = Query(None),
    family_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """
    List methodologies, scoped strictly to the requested canonical sector if provided.
    - If sector/sector_id/family_id is provided, only production-enabled primary methodologies
      for that canonical sector are returned (zero cross-sector leakage).
    - Unconfigured methodologies and supporting modules/tools (e.g. VT0014, VMD0053) are never returned.
    - If an invalid/unknown sector is requested, fails closed (returns []).
    """
    raw_filter = sector or sector_id or family_id
    filter_requested = raw_filter is not None and str(raw_filter).strip() != ""

    canonical_sector: Optional[CanonicalSector] = None

    if filter_requested:
        filter_str = str(raw_filter).strip()
        canonical_sector = normalize_to_canonical_sector(filter_str)

        # If not normalized directly, check if it's a UUID and lookup in DB methodology_families
        if not canonical_sector:
            try:
                target_uuid = UUID(filter_str)
                res_fam = await db.execute(
                    select(MethodologyFamily).where(
                        (MethodologyFamily.id == target_uuid)
                    )
                )
                fam = res_fam.scalars().first()
                if fam:
                    canonical_sector = normalize_to_canonical_sector(fam.code)
            except (ValueError, TypeError):
                pass

        # If a filter was requested but no valid canonical sector could be resolved: FAIL CLOSED
        if not canonical_sector:
            return []

    service = MethodologyService(db)

    # Scoped to a specific canonical sector
    if canonical_sector:
        allowed_codes = get_canonical_methodology_codes_for_sector(canonical_sector)

        # Query methodologies for this family from DB if the family exists in DB
        res_fam = await db.execute(
            select(MethodologyFamily).where(MethodologyFamily.code == canonical_sector.value)
        )
        fam_obj = res_fam.scalars().first()

        db_meths: List[Any] = []
        if fam_obj:
            db_meths = await service.list_methodologies(family_id=fam_obj.id, is_active=is_active)

        # Filter DB methodologies to strictly allowed primary codes
        filtered = [
            m for m in db_meths
            if m.code.upper() in allowed_codes
            and m.code.upper() not in DISALLOWED_PRIMARY_METHODOLOGY_CODES
            and m.code.upper() not in UNCONFIGURED_METHODOLOGY_CODES
        ]

        if filtered:
            return filtered

        # If DB has no active records for this canonical sector (e.g., unseeded AGRICULTURE_LAND_USE),
        # return synthesized production-enabled methodologies
        return [
            _synthesize_canonical_methodology_schema(m, canonical_sector)
            for m in get_production_methodologies_for_sector(canonical_sector)
        ]

    # No sector filter provided: return all active primary methodologies from DB
    all_db = await service.list_methodologies(family_id=None, is_active=is_active)
    result_list = [
        m for m in all_db
        if m.code.upper() not in DISALLOWED_PRIMARY_METHODOLOGY_CODES
        and m.code.upper() not in UNCONFIGURED_METHODOLOGY_CODES
    ]
    codes_present = {m.code.upper() for m in result_list}

    # Ensure VM0042 is surfaced even if unseeded in DB
    if "VM0042" not in codes_present:
        agri_meths = get_production_methodologies_for_sector(CanonicalSector.AGRICULTURE_LAND_USE)
        if agri_meths:
            result_list.append(_synthesize_canonical_methodology_schema(agri_meths[0], CanonicalSector.AGRICULTURE_LAND_USE))

    return result_list





@router.get("/families")

async def list_families(db: AsyncSession = Depends(get_db)):

    """Returns all methodology families (sectors)."""

    from app.domains.methodologies.models.base_registry import MethodologyFamily

    from sqlalchemy import select

    stmt = select(MethodologyFamily)

    res = await db.execute(stmt)

    families = res.scalars().all()

    return [{"id": str(f.id), "code": f.code, "name": f.name, "description": f.description, "project_types": f.project_types or []} for f in families]







@router.get("/recommend", response_model=MethodologyRecommendationResponse)

async def recommend_methodology(

    sector_id: UUID,

    project_type_id: str,

    country: str,

    db: AsyncSession = Depends(get_db),

):

    service = MethodologyService(db)

    return await service.recommend_methodologies(sector_id, project_type_id, country)





@router.post("/", response_model=MethodologySchema)

async def create_methodology(

    data: MethodologyCreate,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(require_permission("compliance:all")),

):

    service = MethodologyService(db)

    meth = await service.create_methodology(data.model_dump())

    return await service.get_methodology(meth.id)





@router.post("/{methodology_id}/versions", response_model=MethodologyVersionSchema)

async def create_methodology_version(

    methodology_id: UUID,

    data: MethodologyVersionCreate,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(require_permission("compliance:all")),

):

    service = MethodologyService(db)

    return await service.create_methodology_version(methodology_id, data.model_dump())





@router.put(

    "/{methodology_id}/versions/{version_id}/status",

    response_model=MethodologyVersionSchema,

)

async def update_version_status(

    methodology_id: UUID,

    version_id: UUID,

    data: MethodologyVersionStatusUpdate,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(require_permission("compliance:all")),

):

    service = MethodologyService(db)

    version = await service.update_version_status(

        version_id, data.status, data.retirement_date

    )

    if not version:

        raise HTTPException(status_code=404, detail="Version not found")

    return version





@router.get("/{methodology_id}/versions/active/schema")

async def get_active_version_schema(

    methodology_id: UUID,

    client_version: str = None,

    db: AsyncSession = Depends(get_db)

):

    """

    Returns the dynamic JSON schema for the active version of a methodology.

    Supports mobile offline caching by checking client_version against the active version.

    """

    service = MethodologyService(db)

    form_service = FormGenerationService(db)



    version = await service.get_active_version(methodology_id)

    if not version:

        raise HTTPException(

            status_code=404, detail="No active version found for this methodology"

        )



    if client_version and client_version == version.version:

        return {"status": "not_modified", "version": version.version}



    schema = await form_service.generate_schema_for_version(version.id)

    # Inject version into payload

    schema["_schema_version"] = version.version

    return schema





@router.get("/{methodology_id}/workspace-schema")

async def get_workspace_schema(

    methodology_id: UUID, db: AsyncSession = Depends(get_db)

):

    """

    Returns the COMPLETE workspace schema for a methodology.

    Includes forms, evidence requirements, calculation rules, validation rules, and workflow.

    The frontend renders the entire workspace from this schema.

    """

    from app.domains.methodologies.services.dynamic_schema import (
        DynamicSchemaEngine,
    )



    engine = DynamicSchemaEngine(db)

    schema = await engine.generate_workspace_schema(methodology_id)

    if "error" in schema:

        raise HTTPException(status_code=404, detail=schema["error"])

    return schema





@router.get("/{methodology_id}/evidence")

async def get_methodology_evidence(

    methodology_id: UUID, db: AsyncSession = Depends(get_db)

):

    """Returns the evidence requirements for a methodology."""

    from app.domains.methodologies.services.dynamic_schema import DynamicSchemaEngine

    from app.domains.methodologies.services.methodology import MethodologyService



    service = MethodologyService(db)

    version = await service.get_active_version(methodology_id)

    if not version:

        raise HTTPException(status_code=404, detail="No active version found")



    engine = DynamicSchemaEngine(db)

    return await engine._build_evidence_schema(version.id)





@router.get("/{methodology_id}/validators")

async def get_methodology_validators(

    methodology_id: UUID, db: AsyncSession = Depends(get_db)

):

    """Returns the validation rules for a methodology."""

    from app.domains.methodologies.services.dynamic_schema import DynamicSchemaEngine

    from app.domains.methodologies.services.methodology import MethodologyService



    service = MethodologyService(db)

    version = await service.get_active_version(methodology_id)

    if not version:

        raise HTTPException(status_code=404, detail="No active version found")



    engine = DynamicSchemaEngine(db)

    return await engine._build_validation_schema(version.id)





@router.get("/{methodology_id}/calculators")

async def get_methodology_calculators(

    methodology_id: UUID, db: AsyncSession = Depends(get_db)

):

    """Returns the calculation rules for a methodology."""

    from app.domains.methodologies.services.dynamic_schema import DynamicSchemaEngine

    from app.domains.methodologies.services.methodology import MethodologyService



    service = MethodologyService(db)

    version = await service.get_active_version(methodology_id)

    if not version:

        raise HTTPException(status_code=404, detail="No active version found")



    engine = DynamicSchemaEngine(db)

    return await engine._build_calculation_schema(version.id)





@router.post("/{methodology_id}/calculate")

async def execute_calculation(

    methodology_id: UUID,

    payload: Dict[str, Any],

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Executes calculation rules for a methodology against provided parameters.

    Returns computed results and full audit trail.

    """

    from app.domains.methodologies.calculation_engine import ExecutionEngine

    from app.domains.methodologies.services.dynamic_schema import (
        DynamicSchemaEngine,
    )



    schema_engine = DynamicSchemaEngine(db)

    schema = await schema_engine.generate_workspace_schema(methodology_id)

    if "error" in schema:

        raise HTTPException(status_code=404, detail=schema["error"])



    calc_rules = schema.get("calculation_rules", [])

    if not calc_rules:

        raise HTTPException(

            status_code=400, detail="No calculation rules defined for this methodology"

        )



    rules = [

        {"output_parameter": r["code"], "formula": r["formula"]} for r in calc_rules

    ]



    engine = ExecutionEngine()

    try:

        result = engine.execute(rules, payload)

        return result

    except RuntimeError as e:

        raise HTTPException(status_code=422, detail=str(e))
