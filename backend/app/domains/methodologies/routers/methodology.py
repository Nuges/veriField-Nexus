from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.methodologies.schemas.registry import (
    MethodologyCreate, MethodologySchema, MethodologyVersionCreate,
    MethodologyVersionSchema, MethodologyVersionStatusUpdate)
from app.domains.methodologies.services.forms import FormGenerationService
from app.domains.methodologies.services.methodology import MethodologyService

router = APIRouter()


@router.get("", response_model=List[MethodologySchema])
async def list_methodologies(db: AsyncSession = Depends(get_db)):
    service = MethodologyService(db)
    return await service.list_methodologies()


@router.post("/", response_model=MethodologySchema)
async def create_methodology(
    data: MethodologyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MethodologyService(db)
    meth = await service.create_methodology(data.model_dump())
    return await service.get_methodology(meth.id)


@router.post("/{methodology_id}/versions", response_model=MethodologyVersionSchema)
async def create_methodology_version(
    methodology_id: UUID,
    data: MethodologyVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    from app.domains.methodologies.services.dynamic_schema import \
        DynamicSchemaEngine

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
    from app.domains.methodologies.services.dynamic_schema import \
        DynamicSchemaEngine

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
