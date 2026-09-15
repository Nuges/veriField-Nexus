"""
=============================================================================
VeriField Nexus — Agriculture & Land Use REST API Router
=============================================================================
FastAPI router for Agriculture domain endpoints:
- Land Units (Parcels, Fields, Strata, Monitoring Plots)
- Soil Samples (Depths, lab analysis, VM0042 classification)
- Tree Observations (Field measurements, allometric biomass)
- Satellite Observations (Ingestion, spectral indices, SAR proxies)
- Model Runs (VT0014 Digital Soil Mapping, VMD0053 calibration)
- Verification Dossier & Cryptographic Sealing
=============================================================================
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.abac import ABACEngine
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.agriculture.schemas import (
    LandUnitCreate,
    LandUnitResponse,
    LandUnitUpdate,
    ModelRunResponse,
    SatelliteObservationCreate,
    SatelliteObservationResponse,
    SoilSampleCreate,
    SoilSampleResponse,
    TreeObservationBatchCreate,
    TreeObservationCreate,
    TreeObservationResponse,
    VerificationDossierResponse,
    VT0014ModelRunRequest,
)
from app.domains.agriculture.service import AgricultureService
from app.domains.authentication.models import User

router = APIRouter(prefix="/agriculture", tags=["Agriculture & Land Use MRV"])


# ─── Land Units ───

@router.post("/land-units", response_model=LandUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_land_unit(
    payload: LandUnitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(payload.project_id)

    org_id = current_user.organization_id
    if not org_id and current_user.role == "SUPER_ADMIN":
        # If super admin, find the project's organization
        proj = await AgricultureService.get_project_or_raise(db, payload.project_id, current_user.organization_id or payload.project_id)
        org_id = proj.organization_id

    try:
        unit = await AgricultureService.create_land_unit(db, payload, org_id)
        await db.commit()
        return unit
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/land-units", response_model=List[LandUnitResponse])
async def list_land_units(
    project_id: Optional[uuid.UUID] = Query(None),
    parent_id: Optional[uuid.UUID] = Query(None),
    unit_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no organization context.")

    return await AgricultureService.get_land_units(
        db=db,
        organization_id=org_id,
        project_id=project_id,
        parent_id=parent_id,
        unit_type=unit_type,
    )


@router.get("/land-units/{land_unit_id}", response_model=LandUnitResponse)
async def get_land_unit(
    land_unit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    unit = await AgricultureService.get_land_unit_by_id(db, land_unit_id, org_id)
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Land unit not found.")
    return unit


@router.put("/land-units/{land_unit_id}", response_model=LandUnitResponse)
async def update_land_unit(
    land_unit_id: uuid.UUID,
    payload: LandUnitUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    try:
        updated = await AgricultureService.update_land_unit(db, land_unit_id, payload, org_id)
        await db.commit()
        return updated
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/land-units/{land_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_land_unit(
    land_unit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    deleted = await AgricultureService.delete_land_unit(db, land_unit_id, org_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Land unit not found.")
    await db.commit()
    return None


# ─── Soil Samples ───

@router.post("/soil-samples", response_model=SoilSampleResponse, status_code=status.HTTP_201_CREATED)
async def create_soil_sample(
    payload: SoilSampleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(payload.project_id)

    org_id = current_user.organization_id
    try:
        sample = await AgricultureService.create_soil_sample(db, payload, org_id)
        await db.commit()
        return sample
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/soil-samples", response_model=List[SoilSampleResponse])
async def list_soil_samples(
    project_id: Optional[uuid.UUID] = Query(None),
    land_unit_id: Optional[uuid.UUID] = Query(None),
    compliance_classification: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    return await AgricultureService.get_soil_samples(
        db=db,
        organization_id=org_id,
        project_id=project_id,
        land_unit_id=land_unit_id,
        compliance_classification=compliance_classification,
    )


# ─── Tree Observations ───

@router.post("/tree-observations", response_model=TreeObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_tree_observation(
    payload: TreeObservationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(payload.project_id)

    org_id = current_user.organization_id
    try:
        obs = await AgricultureService.create_tree_observation(db, payload, org_id)
        await db.commit()
        return obs
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/tree-observations/batch", response_model=List[TreeObservationResponse], status_code=status.HTTP_201_CREATED)
async def batch_create_tree_observations(
    payload: TreeObservationBatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(payload.project_id)

    org_id = current_user.organization_id
    try:
        results = await AgricultureService.batch_create_tree_observations(
            db=db,
            project_id=payload.project_id,
            land_unit_id=payload.land_unit_id,
            observations=payload.observations,
            organization_id=org_id,
        )
        await db.commit()
        return results
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/tree-observations", response_model=List[TreeObservationResponse])
async def list_tree_observations(
    project_id: Optional[uuid.UUID] = Query(None),
    land_unit_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    return await AgricultureService.get_tree_observations(
        db=db,
        organization_id=org_id,
        project_id=project_id,
        land_unit_id=land_unit_id,
    )


# ─── Satellite Observations ───

@router.post("/satellite-observations", response_model=SatelliteObservationResponse, status_code=status.HTTP_201_CREATED)
async def ingest_satellite_observation(
    payload: SatelliteObservationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(payload.project_id)

    org_id = current_user.organization_id
    try:
        obs = await AgricultureService.ingest_satellite_observation(db, payload, org_id)
        await db.commit()
        return obs
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/satellite-observations", response_model=List[SatelliteObservationResponse])
async def list_satellite_observations(
    project_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    return await AgricultureService.get_satellite_observations(
        db=db,
        organization_id=org_id,
        project_id=project_id,
    )


# ─── VT0014 Soil Mapping Execution ───

@router.post("/model-runs/vt0014", response_model=ModelRunResponse, status_code=status.HTTP_201_CREATED)
async def run_vt0014_soil_mapping(
    payload: VT0014ModelRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(payload.project_id)

    org_id = current_user.organization_id
    try:
        run = await AgricultureService.run_vt0014_soil_mapping(db, payload, org_id)
        await db.commit()
        return run
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/model-runs", response_model=List[ModelRunResponse])
async def list_model_runs(
    project_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    return await AgricultureService.get_model_runs(
        db=db,
        organization_id=org_id,
        project_id=project_id,
    )


# ─── Verification Dossier ───

@router.post("/verification-dossier/{project_id}", response_model=VerificationDossierResponse)
async def generate_verification_dossier(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        dossier = await AgricultureService.generate_verification_dossier(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            user_id=current_user.id,
        )
        await db.commit()
        return dossier
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/summary/{project_id}", response_model=Dict[str, Any])
async def get_agriculture_project_summary(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    units = await AgricultureService.get_land_units(db, org_id, project_id=project_id)
    samples = await AgricultureService.get_soil_samples(db, org_id, project_id=project_id)
    trees = await AgricultureService.get_tree_observations(db, org_id, project_id=project_id)
    scenes = await AgricultureService.get_satellite_observations(db, org_id, project_id=project_id)
    model_runs = await AgricultureService.get_model_runs(db, org_id, project_id=project_id)

    total_area_ha = sum(u.area_ha for u in units)
    eligible_samples = [s for s in samples if s.compliance_classification == "EX_POST_QUANTIFICATION_ELIGIBLE"]
    calibration_samples = [s for s in samples if s.compliance_classification == "MODEL_CALIBRATION_ELIGIBLE"]
    ref_samples = [s for s in samples if s.compliance_classification == "REFERENCE_ONLY"]

    total_tree_biomass_kg = sum(t.derived_aboveground_biomass_kg or 0.0 for t in trees)
    total_tree_carbon_t_co2e = sum(t.derived_carbon_stock_t_co2e or 0.0 for t in trees)

    mean_soc_stock = None
    if eligible_samples:
        stocks = [s.computed_soc_stock_t_c_ha for s in eligible_samples if s.computed_soc_stock_t_c_ha is not None]
        if stocks:
            mean_soc_stock = round(sum(stocks) / len(stocks), 2)

    return {
        "project_id": str(project_id),
        "land_units_count": len(units),
        "total_area_ha": round(total_area_ha, 4),
        "soil_samples": {
            "total_count": len(samples),
            "ex_post_eligible_count": len(eligible_samples),
            "model_calibration_eligible_count": len(calibration_samples),
            "reference_only_count": len(ref_samples),
            "mean_soc_stock_t_c_ha": mean_soc_stock,
        },
        "tree_inventory": {
            "total_count": len(trees),
            "total_aboveground_biomass_kg": round(total_tree_biomass_kg, 2),
            "total_carbon_stock_t_co2e": round(total_tree_carbon_t_co2e, 4),
        },
        "earth_observation_scenes_count": len(scenes),
        "model_runs_count": len(model_runs),
    }
