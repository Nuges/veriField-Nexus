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
    GLOBAL_METHODOLOGY_CATALOG,
    resolve_methodology_code,
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

    ui_cfg = dict(item.get("ui_config", {}))
    support_val = item.get("verifield_support_state")
    ui_cfg.setdefault("verifield_support_state", getattr(support_val, "value", str(support_val) if support_val else "CATALOG_ONLY"))
    ui_cfg.setdefault("calculation_support_status", item.get("calculation_support_status", "NOT_IMPLEMENTED"))
    ui_cfg.setdefault("applicability_summary", item.get("applicability_summary", ""))
    ui_cfg.setdefault("stable_identifier", item.get("stable_identifier", ""))
    ui_cfg.setdefault("subsector", item.get("subsector", ""))
    ui_cfg.setdefault("current_version", item.get("version", "1.0.0"))
    ui_cfg.setdefault("supported_versions", item.get("supported_versions", [item.get("version", "1.0.0")]))
    ui_cfg.setdefault("historical_versions", item.get("historical_versions", []))
    ui_cfg.setdefault("valid_from", item.get("valid_from"))
    ui_cfg.setdefault("selectable_for_new_projects", item.get("selectable_for_new_projects", True))
    ui_cfg.setdefault("official_source_url", item.get("official_source_url"))
    ui_cfg.setdefault("source_authority", item.get("source_authority"))
    ui_cfg.setdefault("last_verified_at", item.get("last_verified_at"))

    cur_ver = item.get("version", "1.0.0")
    version_schemas: List[MethodologyVersionSchema] = [
        MethodologyVersionSchema(
            id=uuid.uuid5(meth_uuid, cur_ver),
            version=cur_ver,
            status=item.get("registry_status", "ACTIVE").lower(),
            release_date=date.fromisoformat(item["valid_from"]) if item.get("valid_from") else date(2024, 1, 1),
            retirement_date=None,
        )
    ]
    for sup_ver in item.get("supported_versions", []):
        if sup_ver != cur_ver:
            version_schemas.append(
                MethodologyVersionSchema(
                    id=uuid.uuid5(meth_uuid, sup_ver),
                    version=sup_ver,
                    status="active",
                    release_date=date(2023, 1, 1),
                    retirement_date=None,
                )
            )
    for hist_ver in item.get("historical_versions", []):
        version_schemas.append(
            MethodologyVersionSchema(
                id=uuid.uuid5(meth_uuid, hist_ver),
                version=hist_ver,
                status="historical",
                release_date=date(2020, 1, 1),
                retirement_date=date(2024, 1, 1),
            )
        )

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
        versions=version_schemas,
        ui_config=ui_cfg,
        form_schema={},
        recommendation_rules={},
    )


def _registry_matches(schema_reg_code: Optional[str], filter_reg: str) -> bool:
    if not schema_reg_code:
        return False
    c1 = schema_reg_code.strip().upper()
    c2 = filter_reg.strip().upper()
    if c1 == c2:
        return True
    verra_set = {"VERRA", "VCS"}
    if c1 in verra_set and c2 in verra_set:
        return True
    gs_set = {"GOLD_STANDARD", "GS"}
    if c1 in gs_set and c2 in gs_set:
        return True
    cdm_set = {"CDM", "UNFCCC_CDM", "UNFCCC"}
    if c1 in cdm_set and c2 in cdm_set:
        return True
    puro_set = {"PURO_STANDARD", "PURO"}
    if c1 in puro_set and c2 in puro_set:
        return True
    csi_set = {"CSI", "EBC"}
    if c1 in csi_set and c2 in csi_set:
        return True
    return False


def _enrich_methodology_schema(m: Any) -> MethodologySchema:
    """Enriches a DB Methodology model or MethodologySchema with Global Catalog metadata."""
    schema = m if isinstance(m, MethodologySchema) else MethodologySchema.model_validate(m)
    resolved_code = resolve_methodology_code(schema.code) or schema.code.upper()
    if resolved_code in GLOBAL_METHODOLOGY_CATALOG:
        cat = GLOBAL_METHODOLOGY_CATALOG[resolved_code]
        schema.code = cat["code"]
        schema.name = cat["name"]
        ui_cfg = dict(schema.ui_config or {})
        support_val = cat.get("verifield_support_state")
        ui_cfg.setdefault("verifield_support_state", getattr(support_val, "value", str(support_val) if support_val else "CATALOG_ONLY"))
        ui_cfg.setdefault("calculation_support_status", cat.get("calculation_support_status", "NOT_IMPLEMENTED"))
        ui_cfg.setdefault("applicability_summary", cat.get("applicability_summary", ""))
        ui_cfg.setdefault("stable_identifier", cat.get("stable_identifier", ""))
        ui_cfg.setdefault("subsector", cat.get("subsector", ""))
        ui_cfg.setdefault("current_version", cat.get("version", "1.0.0"))
        ui_cfg.setdefault("supported_versions", cat.get("supported_versions", [cat.get("version", "1.0.0")]))
        ui_cfg.setdefault("historical_versions", cat.get("historical_versions", []))
        ui_cfg.setdefault("valid_from", cat.get("valid_from"))
        ui_cfg.setdefault("selectable_for_new_projects", cat.get("selectable_for_new_projects", True))
        ui_cfg.setdefault("official_source_url", cat.get("official_source_url"))
        ui_cfg.setdefault("source_authority", cat.get("source_authority"))
        ui_cfg.setdefault("last_verified_at", cat.get("last_verified_at"))
        schema.ui_config = ui_cfg
    return schema


@router.get("", response_model=List[MethodologySchema])
async def list_methodologies(
    sector: Optional[str] = Query(None),
    sector_id: Optional[str] = Query(None),
    family_id: Optional[str] = Query(None),
    registry: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """
    List methodologies, scoped strictly to the requested canonical sector and/or registry if provided.
    - If sector/sector_id/family_id is provided, only primary catalog methodologies
      for that canonical sector are returned (zero cross-sector leakage).
    - If registry is provided, filters by registry code (e.g. VERRA, GOLD_STANDARD, CDM, PURO_STANDARD, CSI).
    - Supporting modules/tools (e.g. VT0014, VMD0053, VMD0049) are strictly excluded.
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

        results: List[MethodologySchema] = []
        found_codes = set()
        for m in db_meths:
            resolved = resolve_methodology_code(m.code) or m.code.upper()
            if resolved in allowed_codes and resolved not in DISALLOWED_PRIMARY_METHODOLOGY_CODES and resolved not in found_codes:
                results.append(_enrich_methodology_schema(m))
                found_codes.add(resolved)

        # Merge synthesized catalog entries for any canonical methodologies not present in DB
        for item in get_production_methodologies_for_sector(canonical_sector):
            c_code = item["code"].upper()
            if c_code not in found_codes:
                results.append(_synthesize_canonical_methodology_schema(item, canonical_sector))
                found_codes.add(c_code)

        if registry:
            results = [m for m in results if m.registry and _registry_matches(m.registry.code, registry)]

        return results

    # No sector filter provided: return all active production methodologies across canonical sectors
    all_production_codes = {
        code
        for sec in CanonicalSector
        for code in get_canonical_methodology_codes_for_sector(sec)
    }
    all_db = await service.list_methodologies(family_id=None, is_active=is_active)
    result_list: List[MethodologySchema] = []
    found_codes = set()
    for m in all_db:
        resolved = resolve_methodology_code(m.code) or m.code.upper()
        if resolved in all_production_codes and resolved not in DISALLOWED_PRIMARY_METHODOLOGY_CODES and resolved not in found_codes:
            result_list.append(_enrich_methodology_schema(m))
            found_codes.add(resolved)

    for sec in CanonicalSector:
        for item in get_production_methodologies_for_sector(sec):
            c_code = item["code"].upper()
            if c_code not in found_codes:
                result_list.append(_synthesize_canonical_methodology_schema(item, sec))
                found_codes.add(c_code)

    if registry:
        result_list = [m for m in result_list if m.registry and _registry_matches(m.registry.code, registry)]

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


@router.get("/{id_or_code}", response_model=MethodologySchema)
async def get_methodology_by_id_or_code(
    id_or_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a methodology by database UUID, stable code, or stale UUID alias.
    """
    raw = id_or_code.strip()
    resolved_code = resolve_methodology_code(raw) or raw.upper()
    service = MethodologyService(db)

    # 1. Try DB by UUID if raw is UUID
    meth = None
    try:
        raw_uuid = UUID(raw)
        meth = await service.get_methodology(raw_uuid)
    except (ValueError, TypeError):
        pass

    # 2. Try DB by code
    if not meth:
        meth = await service.get_methodology_by_code(resolved_code)

    if meth:
        return _enrich_methodology_schema(meth)

    # 3. If in GLOBAL_METHODOLOGY_CATALOG, synthesize schema
    if resolved_code in GLOBAL_METHODOLOGY_CATALOG:
        cat = GLOBAL_METHODOLOGY_CATALOG[resolved_code]
        return _synthesize_canonical_methodology_schema(cat, cat["sector"])

    raise HTTPException(status_code=404, detail=f"Methodology '{id_or_code}' not found.")


@router.get("/{id_or_code}/versions")
async def get_methodology_versions(
    id_or_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Returns all versions for a methodology."""
    meth = await get_methodology_by_id_or_code(id_or_code, db)
    return meth.versions


@router.get("/{id_or_code}/applicability")
async def get_methodology_applicability(
    id_or_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Returns structured applicability guidance for a methodology."""
    raw = id_or_code.strip()
    code = resolve_methodology_code(raw) or raw.upper()
    cat = GLOBAL_METHODOLOGY_CATALOG.get(code)

    summary = cat.get("applicability_summary") if cat else None
    subsector = cat.get("subsector") if cat else None

    return {
        "identifier": id_or_code,
        "code": code,
        "name": cat.get("name") if cat else code,
        "subsector": subsector,
        "applicability_summary": summary or "General sector land/activity management applicability.",
        "eligible_activities": [subsector] if subsector else [],
        "verifield_support_state": getattr(cat.get("verifield_support_state"), "value", cat.get("verifield_support_state", "CATALOG_ONLY")) if cat else "CATALOG_ONLY",
    }


@router.get("/{id_or_code}/capabilities")
async def get_methodology_capabilities(
    id_or_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Returns platform capability status for a methodology."""
    raw = id_or_code.strip()
    code = resolve_methodology_code(raw) or raw.upper()
    cat = GLOBAL_METHODOLOGY_CATALOG.get(code)

    verifield_support = getattr(cat.get("verifield_support_state"), "value", cat.get("verifield_support_state", "CATALOG_ONLY")) if cat else "CATALOG_ONLY"
    calc_status = cat.get("calculation_support_status", "NOT_IMPLEMENTED") if cat else "NOT_IMPLEMENTED"
    mrv_status = cat.get("mrv_support_status", "NOT_IMPLEMENTED") if cat else "NOT_IMPLEMENTED"

    return {
        "identifier": id_or_code,
        "code": code,
        "current_version": cat.get("version", "1.0") if cat else "1.0",
        "supported_versions": cat.get("supported_versions", [cat.get("version", "1.0")]) if cat else [],
        "historical_versions": cat.get("historical_versions", []) if cat else [],
        "valid_from": cat.get("valid_from") if cat else None,
        "selectable_for_new_projects": cat.get("selectable_for_new_projects", True) if cat else False,
        "official_source_url": cat.get("official_source_url") if cat else None,
        "source_authority": cat.get("source_authority") if cat else None,
        "last_verified_at": cat.get("last_verified_at") if cat else None,
        "verifield_support_state": verifield_support,
        "calculation_engine_enabled": calc_status == "ENABLED",
        "mrv_workflow_enabled": mrv_status == "ENABLED",
        "project_onboarding_enabled": verifield_support in ("FULL", "MRV_ONLY"),
        "stable_identifier": cat.get("stable_identifier") if cat else f"VERRA:{code}:1.0",
        "notes": "Verified calculation engine active." if calc_status == "ENABLED" else "VeriField calculation engine for this methodology is not yet enabled.",
        "calculation_engine_notes": "Verified calculation engine active." if calc_status == "ENABLED" else "VeriField calculation engine for this methodology is not yet enabled.",
    }
