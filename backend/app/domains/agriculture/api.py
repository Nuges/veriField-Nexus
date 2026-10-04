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
from decimal import Decimal
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.abac import ABACEngine
from app.core.rbac import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.agriculture.schemas import (
    ColumnMappingConfig,
    CustodyEventCreate,
    CustodyEventResponse,
    EligibleMeasurementSetResponse,
    FoundationReadinessResponse,
    GroundEvidenceReadinessResponse,
    LabAnalysisCreate,
    LabAnalysisResponse,
    LabReceiptCreate,
    LabReceiptResponse,
    LabResultCreate,
    LabResultRevisionCreate,
    LabResultResponse,
    LaboratoryImportBatchResponse,
    LaboratoryImportCommitRequest,
    LaboratoryImportCommitResponse,
    LaboratoryImportRowResponse,
    LaboratoryImportValidateRequest,
    LaboratoryImportValidationResponse,
    QuantificationInputSnapshotCreate,
    QuantificationInputSnapshotResponse,
    QuantificationReadinessResponse,
    PrerequisiteEvaluationResponse,
    PrerequisiteEvaluateRequest,
    PrerequisiteLockRequest,
    AgriculturePrerequisiteAssessmentResponse,
    LandUnitCreate,
    LandUnitResponse,
    LandUnitUpdate,
    LinkBoundaryRequest,
    LockMethodologyRequest,
    ManagementRecordCreate,
    ManagementRecordResponse,
    ManagementRecordUpdate,
    ModelRunResponse,
    PhysicalSampleResponse,
    ProjectFoundationResponse,
    SampleCollectionCreate,
    SampleCollectionResponse,
    SampleQAReviewCreate,
    SampleQAReviewResponse,
    SamplingCampaignCreate,
    SamplingCampaignResponse,
    SamplingCampaignUpdate,
    SamplingPlanLockRequest,
    SamplingPlanVersionCreate,
    SamplingPlanVersionResponse,
    SamplingPointBatchCreate,
    SamplingPointCreate,
    SamplingPointResponse,
    SatelliteObservationCreate,
    SatelliteObservationResponse,
    SoilSampleCreate,
    SoilSampleResponse,
    StratumCreate,
    StratumMembershipAddRequest,
    StratumResponse,
    StratumUpdate,
    TreeObservationBatchCreate,
    TreeObservationCreate,
    TreeObservationResponse,
    VerificationDossierResponse,
    VT0014ModelRunRequest,
    AgricultureSOCLayerResultResponse,
    AgricultureSOCStockResultResponse,
    AgricultureSOCStockSnapshotResponse,
    SOCStockEvaluateRequest,
    SOCStockCalculateRequest,
    SOCStockEvaluationResponse,
    AgricultureSOCChangeResultResponse,
    SOCChangeEvaluateRequest,
    SOCChangeFinalizeRequest,
    SOCChangeEvaluationResponse,
    AgricultureVintageGHGResultResponse,
    AgricultureNetGHGResultResponse,
    NetGHGEvaluateRequest,
    NetGHGFinalizeRequest,
    NetGHGEvaluationResponse,
)
from app.domains.agriculture.soil.soc_change_calculator import SOCChangeCalculationError
from app.domains.agriculture.quantification.net_ghg_calculator import NetGHGCalculationError
from app.domains.agriculture.service import AgricultureService
from app.domains.authentication.models import User

router = APIRouter(prefix="/agriculture", tags=["Agriculture & Land Use MRV"])


# ─── Land Units ───

@router.post("/land-units", response_model=LandUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_land_unit(
    payload: LandUnitCreate,
    current_user: User = Depends(require_permission("project:update")),
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
    current_user: User = Depends(require_permission("project:read")),
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
    current_user: User = Depends(require_permission("project:read")),
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
    current_user: User = Depends(require_permission("project:update")),
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
    current_user: User = Depends(require_permission("project:update")),
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


# ─── Phase 1: Project Foundation & Readiness Endpoints ───

@router.get("/projects/{project_id}/foundation", response_model=ProjectFoundationResponse)
async def get_project_foundation(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        return await AgricultureService.get_project_foundation(db, project_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/projects/{project_id}/lock-methodology", response_model=Dict[str, Any])
async def lock_project_methodology(
    project_id: uuid.UUID,
    payload: Optional[LockMethodologyRequest] = None,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    notes = payload.notes if payload else None
    try:
        snapshot = await AgricultureService.lock_project_methodology(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            user_id=current_user.id,
            notes=notes,
        )
        await db.commit()
        return snapshot
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/projects/{project_id}/link-boundary", status_code=status.HTTP_201_CREATED)
async def link_project_boundary(
    project_id: uuid.UUID,
    payload: LinkBoundaryRequest,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        pbv = await AgricultureService.link_project_boundary(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            user_id=current_user.id,
            payload=payload,
        )
        await db.commit()
        return {
            "id": str(pbv.id),
            "project_id": str(pbv.project_id),
            "version_number": pbv.version_number,
            "effective_date": pbv.effective_date.isoformat(),
            "area_ha": pbv.area_ha,
            "perimeter_m": pbv.perimeter_m,
            "source": pbv.source,
            "reason": pbv.reason,
            "crs": pbv.crs,
            "boundary_geojson": pbv.boundary_geojson,
        }
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/foundation-readiness", response_model=FoundationReadinessResponse)
async def get_foundation_readiness(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        return await AgricultureService.evaluate_foundation_readiness(db, project_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ─── Phase 1: Strata Endpoints ───

@router.get("/projects/{project_id}/strata", response_model=List[StratumResponse])
async def list_project_strata(
    project_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None, description="Evaluate stratum memberships and area as of this date"),
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.get_strata(db, org_id, project_id, as_of_date=as_of_date)


@router.post("/projects/{project_id}/strata", response_model=StratumResponse, status_code=status.HTTP_201_CREATED)
async def create_project_stratum(
    project_id: uuid.UUID,
    payload: StratumCreate,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        stratum = await AgricultureService.create_stratum(db, payload, org_id, project_id=project_id)
        await db.commit()
        res = await AgricultureService.get_stratum_by_id(db, stratum.id, org_id)
        return res
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/strata/{stratum_id}", response_model=StratumResponse)
async def get_project_stratum(
    project_id: uuid.UUID,
    stratum_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None, description="Evaluate stratum memberships and area as of this date"),
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    stratum = await AgricultureService.get_stratum_by_id(db, stratum_id, org_id, as_of_date=as_of_date)
    if not stratum or stratum["project_id"] != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stratum not found in project.")
    return stratum


@router.put("/projects/{project_id}/strata/{stratum_id}", response_model=StratumResponse)
async def update_project_stratum(
    project_id: uuid.UUID,
    stratum_id: uuid.UUID,
    payload: StratumUpdate,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        updated = await AgricultureService.update_stratum(db, stratum_id, payload, org_id)
        await db.commit()
        return updated
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/projects/{project_id}/strata/{stratum_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_stratum(
    project_id: uuid.UUID,
    stratum_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    deleted = await AgricultureService.delete_stratum(db, stratum_id, org_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stratum not found.")
    await db.commit()
    return None


@router.post("/projects/{project_id}/strata/{stratum_id}/members", response_model=StratumResponse)
async def add_stratum_members(
    project_id: uuid.UUID,
    stratum_id: uuid.UUID,
    payload: StratumMembershipAddRequest,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        res = await AgricultureService.add_stratum_memberships(
            db=db,
            stratum_id=stratum_id,
            organization_id=org_id,
            memberships=payload.memberships,
        )
        await db.commit()
        return res
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── Phase 1: Management Records Endpoints ───

@router.get("/projects/{project_id}/management-records", response_model=List[ManagementRecordResponse])
async def list_project_management_records(
    project_id: uuid.UUID,
    land_unit_id: Optional[uuid.UUID] = Query(None),
    practice_category: Optional[str] = Query(None),
    record_type: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("activity:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.get_management_records(
        db=db,
        organization_id=org_id,
        project_id=project_id,
        land_unit_id=land_unit_id,
        practice_category=practice_category,
        record_type=record_type,
    )


@router.post("/projects/{project_id}/management-records", response_model=ManagementRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_project_management_record(
    project_id: uuid.UUID,
    payload: ManagementRecordCreate,
    current_user: User = Depends(require_permission("activity:create")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        record = await AgricultureService.create_management_record(
            db=db,
            payload=payload,
            organization_id=org_id,
            user_id=current_user.id,
            project_id=project_id,
        )
        await db.commit()
        return record
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/management-records/{record_id}", response_model=ManagementRecordResponse)
async def get_project_management_record(
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(require_permission("activity:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    record = await AgricultureService.get_management_record_by_id(db, record_id, org_id)
    if not record or record.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Management record not found in project.")
    return record


@router.put("/projects/{project_id}/management-records/{record_id}", response_model=ManagementRecordResponse)
async def update_project_management_record(
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ManagementRecordUpdate,
    current_user: User = Depends(require_permission("activity:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        record = await AgricultureService.update_management_record(db, record_id, payload, org_id)
        await db.commit()
        return record
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/projects/{project_id}/management-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_management_record(
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(require_permission("activity:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    deleted = await AgricultureService.delete_management_record(db, record_id, org_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Management record not found.")
    await db.commit()
    return None


# ─── Phase 2: Ground Sampling, Chain of Custody & Laboratory Evidence Endpoints ───

@router.get("/projects/{project_id}/sampling-campaigns", response_model=List[SamplingCampaignResponse])
async def list_sampling_campaigns(
    project_id: uuid.UUID,
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.get_sampling_campaigns(
        db=db,
        project_id=project_id,
        organization_id=org_id,
        status=status,
    )


@router.post("/projects/{project_id}/sampling-campaigns", response_model=SamplingCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_sampling_campaign(
    project_id: uuid.UUID,
    payload: SamplingCampaignCreate,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        campaign = await AgricultureService.create_sampling_campaign(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            payload=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return await AgricultureService.get_sampling_campaign_by_id(db, campaign.id, org_id)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/sampling-campaigns/{campaign_id}", response_model=SamplingCampaignResponse)
async def get_sampling_campaign(
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    campaign = await AgricultureService.get_sampling_campaign_by_id(db, campaign_id, org_id)
    if not campaign or campaign["project_id"] != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sampling campaign not found in project.")
    return campaign


@router.put("/projects/{project_id}/sampling-campaigns/{campaign_id}", response_model=SamplingCampaignResponse)
async def update_sampling_campaign(
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
    payload: SamplingCampaignUpdate,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        await AgricultureService.update_sampling_campaign(
            db=db,
            campaign_id=campaign_id,
            organization_id=org_id,
            payload=payload,
        )
        await db.commit()
        return await AgricultureService.get_sampling_campaign_by_id(db, campaign_id, org_id)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/sampling-campaigns/{campaign_id}/plan-versions", response_model=List[SamplingPlanVersionResponse])
async def list_sampling_plan_versions(
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.get_sampling_plan_versions(db, campaign_id, org_id)


@router.post("/projects/{project_id}/sampling-campaigns/{campaign_id}/plan-versions", response_model=SamplingPlanVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_sampling_plan_version(
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
    payload: SamplingPlanVersionCreate,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        spv = await AgricultureService.create_sampling_plan_version(
            db=db,
            campaign_id=campaign_id,
            organization_id=org_id,
            payload=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return spv
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/projects/{project_id}/sampling-campaigns/{campaign_id}/plan-versions/{version_id}/lock", response_model=SamplingPlanVersionResponse)
async def lock_sampling_plan_version(
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: Optional[SamplingPlanLockRequest] = None,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    notes = payload.notes if payload else None
    try:
        spv = await AgricultureService.lock_sampling_plan_version(
            db=db,
            plan_version_id=version_id,
            organization_id=org_id,
            user_id=current_user.id,
            notes=notes,
        )
        await db.commit()
        return spv
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/sampling-campaigns/{campaign_id}/points", response_model=List[SamplingPointResponse])
async def list_sampling_points(
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
    plan_version_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permission("activity:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.get_sampling_points(
        db=db,
        campaign_id=campaign_id,
        organization_id=org_id,
        plan_version_id=plan_version_id,
    )


@router.post("/projects/{project_id}/sampling-campaigns/{campaign_id}/plan-versions/{version_id}/points", response_model=List[SamplingPointResponse], status_code=status.HTTP_201_CREATED)
async def create_sampling_points(
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: SamplingPointBatchCreate,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        await AgricultureService.create_sampling_points(
            db=db,
            campaign_id=campaign_id,
            plan_version_id=version_id,
            organization_id=org_id,
            points=payload.points,
            user_id=current_user.id,
        )
        await db.commit()
        return await AgricultureService.get_sampling_points(
            db=db,
            campaign_id=campaign_id,
            organization_id=org_id,
            plan_version_id=version_id,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/physical-samples", response_model=List[PhysicalSampleResponse])
async def list_physical_samples(
    project_id: uuid.UUID,
    campaign_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("activity:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.get_physical_samples(
        db=db,
        project_id=project_id,
        organization_id=org_id,
        campaign_id=campaign_id,
        status=status,
    )


@router.get("/projects/{project_id}/physical-samples/{sample_id}", response_model=PhysicalSampleResponse)
async def get_physical_sample(
    project_id: uuid.UUID,
    sample_id: uuid.UUID,
    current_user: User = Depends(require_permission("activity:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    sample = await AgricultureService.get_physical_sample_by_id(db, sample_id, org_id)
    if not sample or sample.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical sample not found in project.")
    return sample


@router.post("/projects/{project_id}/physical-samples/{sample_id}/collection", response_model=SampleCollectionResponse, status_code=status.HTTP_201_CREATED)
async def record_sample_collection(
    project_id: uuid.UUID,
    sample_id: uuid.UUID,
    payload: SampleCollectionCreate,
    current_user: User = Depends(require_permission("activity:create")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        ev = await AgricultureService.record_sample_collection(
            db=db,
            sample_id=sample_id,
            organization_id=org_id,
            payload=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return ev
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/projects/{project_id}/physical-samples/{sample_id}/custody-events", response_model=CustodyEventResponse, status_code=status.HTTP_201_CREATED)
async def record_sample_custody_event(
    project_id: uuid.UUID,
    sample_id: uuid.UUID,
    payload: CustodyEventCreate,
    current_user: User = Depends(require_permission("activity:create")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        ev = await AgricultureService.record_custody_event(
            db=db,
            sample_id=sample_id,
            organization_id=org_id,
            payload=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return ev
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/projects/{project_id}/physical-samples/{sample_id}/lab-receipt", response_model=LabReceiptResponse, status_code=status.HTTP_201_CREATED)
async def record_sample_laboratory_receipt(
    project_id: uuid.UUID,
    sample_id: uuid.UUID,
    payload: LabReceiptCreate,
    current_user: User = Depends(require_permission("activity:create")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        receipt = await AgricultureService.record_laboratory_receipt(
            db=db,
            sample_id=sample_id,
            organization_id=org_id,
            payload=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return receipt
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/projects/{project_id}/physical-samples/{sample_id}/lab-analyses", response_model=LabAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def record_sample_laboratory_analysis(
    project_id: uuid.UUID,
    sample_id: uuid.UUID,
    payload: LabAnalysisCreate,
    current_user: User = Depends(require_permission("activity:create")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        analysis = await AgricultureService.record_laboratory_analysis(
            db=db,
            sample_id=sample_id,
            organization_id=org_id,
            payload=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return analysis
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/projects/{project_id}/laboratory-results/{result_id}/revise", response_model=LabResultResponse)
async def revise_laboratory_result(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    payload: LabResultRevisionCreate,
    current_user: User = Depends(require_permission("activity:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        revised = await AgricultureService.revise_laboratory_result(
            db=db,
            result_id=result_id,
            organization_id=org_id,
            payload=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return revised
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/projects/{project_id}/physical-samples/{sample_id}/qa-review", response_model=SampleQAReviewResponse)
async def record_sample_qa_review(
    project_id: uuid.UUID,
    sample_id: uuid.UUID,
    payload: SampleQAReviewCreate,
    current_user: User = Depends(require_permission("activity:verify")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    try:
        review = await AgricultureService.record_sample_qa_review(
            db=db,
            sample_id=sample_id,
            organization_id=org_id,
            payload=payload,
            user_id=current_user.id,
        )
        await db.commit()
        return review
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/ground-evidence-readiness", response_model=GroundEvidenceReadinessResponse)
async def get_ground_evidence_readiness(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.evaluate_ground_evidence_readiness(db, project_id, org_id)


# ─── Phase 3A: Quantification Readiness & Calculation Input Contract ─────────

@router.get("/projects/{project_id}/quantification-readiness", response_model=QuantificationReadinessResponse)
async def get_quantification_readiness(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.evaluate_quantification_readiness(db, project_id, org_id)


@router.get("/projects/{project_id}/eligible-measurements", response_model=EligibleMeasurementSetResponse)
async def get_eligible_measurements(
    project_id: uuid.UUID,
    campaign_id: Optional[uuid.UUID] = Query(None, description="Optional filter by sampling campaign"),
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.evaluate_eligible_measurements(
        db, project_id, org_id, campaign_id=campaign_id
    )


@router.post(
    "/projects/{project_id}/quantification-input-snapshots",
    response_model=QuantificationInputSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_quantification_input_snapshot(
    project_id: uuid.UUID,
    payload: QuantificationInputSnapshotCreate,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    # Strict Segregation of Duties: FIELD_AGENT cannot lock official quantification snapshots
    user_role = (current_user.role or "").upper()
    if user_role == "FIELD_AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field agent role is unauthorized to lock official quantification input snapshots. Segregation of duties enforced.",
        )

    try:
        snapshot = await AgricultureService.create_quantification_input_snapshot(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            user_role=user_role,
            organization_id=current_user.organization_id,
            payload=payload,
        )
        await db.commit()
        return snapshot
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/quantification-input-snapshots",
    response_model=List[QuantificationInputSnapshotResponse],
)
async def list_quantification_input_snapshots(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.list_quantification_input_snapshots(db, project_id, org_id)


@router.get(
    "/projects/{project_id}/quantification-input-snapshots/{snapshot_id}",
    response_model=QuantificationInputSnapshotResponse,
)
async def get_quantification_input_snapshot(
    project_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    org_id = current_user.organization_id
    return await AgricultureService.get_quantification_input_snapshot(
        db, project_id, snapshot_id, org_id
    )


# =============================================================================
# PHASE 3B-0: METHODOLOGY PREREQUISITE ENDPOINTS
# =============================================================================

@router.get(
    "/projects/{project_id}/prerequisites/readiness",
    response_model=PrerequisiteEvaluationResponse,
)
async def get_prerequisites_readiness(
    project_id: uuid.UUID,
    run_power_analysis: bool = Query(False),
    target_mdd: Optional[float] = Query(None),
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = current_user.organization_id
    return await AgricultureService.evaluate_methodology_prerequisites(
        db=db,
        project_id=project_id,
        organization_id=org_id,
        run_power_analysis=run_power_analysis,
        mdd=target_mdd,
    )


@router.post(
    "/projects/{project_id}/prerequisites/evaluate",
    response_model=PrerequisiteEvaluationResponse,
)
async def evaluate_prerequisites(
    project_id: uuid.UUID,
    payload: Optional[PrerequisiteEvaluateRequest] = None,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = current_user.organization_id
    run_pa = payload.run_power_analysis if payload else False
    mdd = payload.target_mdd if payload else None
    sub_date = payload.submission_date if payload else None
    early_mode = payload.early_adoption_mode if payload else None
    as_of = payload.as_of_date if payload else None
    return await AgricultureService.evaluate_methodology_prerequisites(
        db=db,
        project_id=project_id,
        organization_id=org_id,
        run_power_analysis=run_pa,
        mdd=mdd,
        submission_date=sub_date,
        early_adoption_mode=early_mode,
        as_of_date=as_of,
    )


@router.post(
    "/projects/{project_id}/prerequisites/lock",
    response_model=AgriculturePrerequisiteAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def lock_prerequisite_assessment(
    project_id: uuid.UUID,
    payload: PrerequisiteLockRequest,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    # Segregation of Duties: FIELD_AGENT forbidden from locking assessments (§55)
    user_role = (current_user.role or "").upper()
    if user_role == "FIELD_AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field agent role is unauthorized to lock official methodology prerequisite assessments. Segregation of duties enforced.",
        )

    try:
        assessment = await AgricultureService.lock_prerequisite_assessment(
            db=db,
            project_id=project_id,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            user_role=user_role,
            snapshot_id=payload.snapshot_id,
            notes=payload.notes,
            run_power_analysis=payload.run_power_analysis,
            target_mdd=payload.target_mdd,
            submission_date=payload.submission_date,
            early_adoption_mode=payload.early_adoption_mode,
            as_of_date=payload.as_of_date,
        )
        await db.commit()
        return assessment
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/prerequisites/assessments",
    response_model=List[AgriculturePrerequisiteAssessmentResponse],
)
async def list_prerequisite_assessments(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = current_user.organization_id
    return await AgricultureService.list_prerequisite_assessments(db, project_id, org_id)


@router.get(
    "/projects/{project_id}/prerequisites/assessments/{assessment_id}",
    response_model=AgriculturePrerequisiteAssessmentResponse,
)
async def get_prerequisite_assessment(
    project_id: uuid.UUID,
    assessment_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = current_user.organization_id
    return await AgricultureService.get_prerequisite_assessment(db, project_id, assessment_id, org_id)


@router.get(
    "/projects/{project_id}/prerequisites/vcs-resolution",
    response_model=Dict[str, Any],
)
async def get_vcs_resolution(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    eval_res = await AgricultureService.evaluate_methodology_prerequisites(
        db, project_id, current_user.organization_id
    )
    return eval_res["dimensions"]["VCS_PROGRAM_RULESET"]["details"]


@router.get(
    "/projects/{project_id}/prerequisites/route-map",
    response_model=Dict[str, Any],
)
async def get_quantification_route_map(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    eval_res = await AgricultureService.evaluate_methodology_prerequisites(
        db, project_id, current_user.organization_id
    )
    return eval_res["dimensions"]["QUANTIFICATION_ROUTE"]["details"]


# =============================================================================
# LABORATORY BULK DATA IMPORT ENDPOINTS
# =============================================================================

from app.domains.agriculture.laboratory_import_service import LaboratoryImportService
from app.domains.agriculture.models import LaboratoryImportBatch, LaboratoryImportRow
from app.domains.projects.models import Project
from sqlalchemy import select, and_


async def _resolve_org_id(db: AsyncSession, project_id: uuid.UUID, current_user: User) -> uuid.UUID:
    if current_user.organization_id:
        return current_user.organization_id
    proj = await db.scalar(select(Project).where(Project.id == project_id))
    if proj and proj.organization_id:
        return proj.organization_id
    return project_id


@router.get("/projects/{project_id}/laboratory-import/template")
async def download_laboratory_import_template(
    project_id: uuid.UUID,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Downloads a pre-formatted Laboratory Ingestion Template (CSV or XLSX)
    populated with standard agronomic MRV test cases and guidance.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    content, filename, media_type = LaboratoryImportService.generate_template(file_format=format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/projects/{project_id}/laboratory-import/upload",
    response_model=LaboratoryImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_laboratory_bulk_file(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    laboratory_name: Optional[str] = Query(None),
    sampling_campaign_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Securely uploads a CSV or XLSX laboratory report file.
    Validates magic bytes, hashes payload (SHA-256), archives immutable Evidence,
    stages raw rows, and auto-detects column mappings.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        batch = await LaboratoryImportService.upload_file(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            user_id=current_user.id,
            file=file,
            laboratory_name=laboratory_name,
            sampling_campaign_id=sampling_campaign_id,
        )
        await db.commit()
        return batch
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/laboratory-import/batches",
    response_model=List[LaboratoryImportBatchResponse],
)
async def list_laboratory_import_batches(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all bulk laboratory import batches associated with the project.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    stmt = (
        select(LaboratoryImportBatch)
        .where(
            and_(
                LaboratoryImportBatch.project_id == project_id,
                LaboratoryImportBatch.organization_id == org_id,
            )
        )
        .order_by(LaboratoryImportBatch.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/projects/{project_id}/laboratory-import/batches/{batch_id}",
    response_model=LaboratoryImportBatchResponse,
)
async def get_laboratory_import_batch(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves detailed metadata, validation summary, and processing status of an import batch.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    stmt = select(LaboratoryImportBatch).where(
        and_(
            LaboratoryImportBatch.id == batch_id,
            LaboratoryImportBatch.project_id == project_id,
            LaboratoryImportBatch.organization_id == org_id,
        )
    )
    batch = (await db.execute(stmt)).scalars().first()
    if not batch:
        raise HTTPException(status_code=404, detail="Laboratory import batch not found.")
    return batch


@router.get(
    "/projects/{project_id}/laboratory-import/batches/{batch_id}/rows",
    response_model=List[LaboratoryImportRowResponse],
)
async def list_laboratory_import_rows(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    validation_status: Optional[str] = Query(None, description="Filter by VALID, WARNING, ERROR, SKIPPED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists staged or validated rows for a specific laboratory import batch.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    conditions = [
        LaboratoryImportRow.import_batch_id == batch_id,
        LaboratoryImportRow.project_id == project_id,
        LaboratoryImportRow.organization_id == org_id,
    ]
    if validation_status:
        conditions.append(LaboratoryImportRow.validation_status == validation_status.upper())

    stmt = (
        select(LaboratoryImportRow)
        .where(and_(*conditions))
        .order_by(LaboratoryImportRow.source_row_number.asc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "/projects/{project_id}/laboratory-import/batches/{batch_id}/validate",
    response_model=LaboratoryImportValidationResponse,
)
async def validate_laboratory_import_batch(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    payload: LaboratoryImportValidateRequest,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers or re-runs validation over staged rows using updated column mappings or parameters.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        batch, rows = await LaboratoryImportService.validate_batch(
            db=db,
            batch_id=batch_id,
            organization_id=org_id,
            mapping_config=payload.mapping_config,
            laboratory_name=payload.laboratory_name,
            sampling_campaign_id=payload.sampling_campaign_id,
        )
        await db.commit()

        # Build preview rows (up to 25 rows)
        preview_rows = rows[:25]
        return LaboratoryImportValidationResponse(
            batch_id=batch.id,
            status=batch.status,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            warning_rows=batch.warning_rows,
            error_rows=batch.error_rows,
            can_commit=batch.valid_rows > 0 and (batch.error_rows == 0 or True),
            preview_rows=preview_rows,
            error_summary=batch.error_summary or [],
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/projects/{project_id}/laboratory-import/batches/{batch_id}/commit",
    response_model=LaboratoryImportCommitResponse,
)
async def commit_laboratory_import_batch(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    payload: LaboratoryImportCommitRequest,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Transactionally commits validated rows into canonical LaboratoryAnalysis
    and LaboratoryResult records. Updates PhysicalSample status to ANALYZED.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        result = await LaboratoryImportService.commit_batch(
            db=db,
            batch_id=batch_id,
            organization_id=org_id,
            user_id=current_user.id,
            import_valid_only=payload.import_valid_only,
            laboratory_name=payload.laboratory_name,
            notes=payload.notes,
            import_as_revision=payload.import_as_revision,
            revision_reason=payload.revision_reason,
        )
        await db.commit()
        return LaboratoryImportCommitResponse(**result)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/laboratory-import/batches/{batch_id}/errors.csv")
async def export_laboratory_import_errors_csv(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports validation error/warning rows as a CSV file with CSV formula injection mitigation.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    content, filename = await LaboratoryImportService.export_errors_csv(
        db=db,
        batch_id=batch_id,
        organization_id=org_id,
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# PHASE 3B-1: SOC STOCK & EQUIVALENT SOIL MASS (ESM) ENDPOINTS
# =============================================================================

from app.domains.agriculture.soil.soc_stock_calculator import SOCStockCalculationError


@router.post(
    "/projects/{project_id}/soc-stock/evaluate",
    response_model=SOCStockEvaluationResponse,
)
async def evaluate_soc_stock(
    project_id: uuid.UUID,
    payload: SOCStockEvaluateRequest,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates measured SOC stock and Equivalent Soil Mass (ESM) normalization.
    Read-only preview calculation without database mutation.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        res = await AgricultureService.evaluate_soc_stock(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            prerequisite_assessment_id=payload.prerequisite_assessment_id,
            snapshot_id=payload.snapshot_id,
            measurement_period_type=payload.measurement_period_type or "MONITORING",
            reference_depth_cm=payload.reference_depth_cm or Decimal("30.00"),
            reference_soil_mass_t_ha=payload.reference_soil_mass_t_ha,
            esm_algorithm=payload.esm_algorithm or "LAYER_MASS_PROPORTIONING",
        )
        return res
    except (ValueError, SOCStockCalculationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/projects/{project_id}/soc-stock/calculate",
    response_model=AgricultureSOCStockResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def calculate_soc_stock(
    project_id: uuid.UUID,
    payload: SOCStockCalculateRequest,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates and transactionally persists authoritative measured SOC stock and ESM results.
    Segregation of Duties: FIELD_AGENT cannot finalize authoritative calculations.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    user_role = (current_user.role or "").upper()
    if user_role == "FIELD_AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field agent role is unauthorized to finalize authoritative SOC stock calculations. Segregation of duties enforced.",
        )

    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        result = await AgricultureService.calculate_and_persist_authoritative_soc_stock(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            user_id=current_user.id,
            user_role=user_role,
            prerequisite_assessment_id=payload.prerequisite_assessment_id,
            snapshot_id=payload.snapshot_id,
            measurement_period_type=payload.measurement_period_type,
            reference_depth_cm=payload.reference_depth_cm,
            reference_soil_mass_t_ha=payload.reference_soil_mass_t_ha,
            esm_algorithm=payload.esm_algorithm,
            notes=payload.notes,
        )
        await db.commit()
        return result
    except (ValueError, SOCStockCalculationError) as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/soc-stock/results",
    response_model=List[AgricultureSOCStockResultResponse],
)
async def list_soc_stock_results(
    project_id: uuid.UUID,
    measurement_period_type: Optional[str] = Query(None, description="Filter by BASELINE or MONITORING"),
    aggregation_level: Optional[str] = Query(None, description="Filter by SAMPLE_POINT, STRATUM, PROJECT"),
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists measured SOC stock and ESM normalization results for a project.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    return await AgricultureService.list_soc_stock_results(
        db=db,
        project_id=project_id,
        organization_id=org_id,
        measurement_period_type=measurement_period_type,
        aggregation_level=aggregation_level,
    )


@router.get(
    "/projects/{project_id}/soc-stock/results/{result_id}",
    response_model=AgricultureSOCStockResultResponse,
)
async def get_soc_stock_result(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves an individual SOC stock result with component layers.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    return await AgricultureService.get_soc_stock_result(
        db=db,
        project_id=project_id,
        result_id=result_id,
        organization_id=org_id,
    )


@router.get(
    "/projects/{project_id}/soc-stock/results/{result_id}/components",
    response_model=Dict[str, Any],
)
async def get_soc_stock_result_components(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full component breakdown, layer table, and cryptographic proof for an SOC stock result.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    return await AgricultureService.get_soc_stock_result_components(
        db=db,
        project_id=project_id,
        result_id=result_id,
        organization_id=org_id,
    )


# =============================================================================
# PHASE 3B-2: SOC STOCK CHANGE & UNCERTAINTY QUANTIFICATION ENDPOINTS
# =============================================================================

@router.post(
    "/projects/{project_id}/soc-change/evaluate",
    response_model=SOCChangeEvaluationResponse,
)
async def evaluate_soc_stock_change(
    project_id: uuid.UUID,
    payload: SOCChangeEvaluateRequest,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates annualized baseline and project scenario SOC stock changes, stoichiometric 44/12
    conversion, sampling variance, and VM0042 Eq. 74 uncertainty deduction.
    Non-mutating preview endpoint.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        res = await AgricultureService.evaluate_soc_stock_change(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            baseline_stock_result_id=payload.baseline_stock_result_id,
            monitoring_stock_result_id=payload.monitoring_stock_result_id,
            prerequisite_assessment_id=payload.prerequisite_assessment_id,
            laboratory_method=payload.laboratory_method or "DRY_COMBUSTION",
            lab_qa_verified=payload.lab_qa_verified if payload.lab_qa_verified is not None else True,
            active_lab_proficiency=payload.active_lab_proficiency if payload.active_lab_proficiency is not None else True,
        )
        return {
            "project_id": project_id,
            "status": "EVALUATED",
            "baseline_stock_result_id": payload.baseline_stock_result_id,
            "monitoring_stock_result_id": payload.monitoring_stock_result_id,
            "elapsed_years": Decimal(res["elapsed_years_val"]),
            "t_start": datetime.fromisoformat(res["t_start"]),
            "t_final": datetime.fromisoformat(res["t_final"]),
            "total_project_area_ha": Decimal(res["total_project_area_ha"]),
            "delta_soc_project_t_c_ha_yr": Decimal(res["delta_soc_project_t_c_ha_yr"]),
            "delta_soc_baseline_t_c_ha_yr": Decimal(res["delta_soc_baseline_t_c_ha_yr"]),
            "delta_soc_net_t_c_ha_yr": Decimal(res["delta_soc_net_t_c_ha_yr"]),
            "delta_co2_net_tco2e_ha_yr": Decimal(res["delta_co2_net_tco2e_ha_yr"]),
            "total_net_delta_co2_tco2e_yr": Decimal(res["total_net_delta_co2_tco2e_yr"]),
            "baseline_soc_change_tco2e_yr": Decimal(res["baseline_soc_change_tco2e_yr"]),
            "project_soc_change_tco2e_yr": Decimal(res["project_soc_change_tco2e_yr"]),
            "qa2_net_soc_effect_tco2e_yr": Decimal(res["qa2_net_soc_effect_tco2e_yr"]),
            "uncertainty_adjusted_soc_effect_tco2e_yr": Decimal(res["uncertainty_adjusted_soc_effect_tco2e_yr"]),
            "sign_indicator": res.get("sign_indicator", 1),
            "eq44_eq45_status": res.get("eq44_eq45_status", "PARTIALLY_CONFIGURED_SOC_ONLY"),
            "df_estimator": res.get("df_estimator", "DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR"),
            "adjusted_net_delta_co2_tco2e_yr": Decimal(res["adjusted_net_delta_co2_tco2e_yr"]),
            "degrees_of_freedom": res["degrees_of_freedom"],
            "student_t_value_0667": Decimal(res["student_t_value_0667"]),
            "relative_uncertainty_pct": Decimal(res["relative_uncertainty_pct"]),
            "uncertainty_deduction_pct": Decimal(res["uncertainty_deduction_pct"]),
            "uncertainty_deduction_fraction": Decimal(res["uncertainty_deduction_fraction"]),
            "uncertainty_status": res["uncertainty_status"],
            "measurement_error_status": res["measurement_error_status"],
            "strata_results": res["strata_results"],
            "blocking_reasons": res.get("blocking_reasons", []),
            "evaluation_hash": res["evaluation_hash"],
        }
    except (ValueError, SOCChangeCalculationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/projects/{project_id}/soc-change/finalize",
    response_model=AgricultureSOCChangeResultResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/projects/{project_id}/soc-change/calculate",
    response_model=AgricultureSOCChangeResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def finalize_soc_stock_change(
    project_id: uuid.UUID,
    payload: SOCChangeFinalizeRequest,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Authoritatively calculates and persists scenario SOC stock change, stoichiometric 44/12
    CO2 conversion, sampling variance, and VM0042 Eq. 74 uncertainty deduction.
    Segregation of Duties: FIELD_AGENT cannot finalize authoritative calculations.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    user_role = (current_user.role or "").upper()
    if user_role == "FIELD_AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field agent role is unauthorized to finalize authoritative SOC stock change. Segregation of duties enforced.",
        )

    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        result = await AgricultureService.finalize_soc_stock_change(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            user_id=current_user.id,
            user_role=user_role,
            baseline_stock_result_id=payload.baseline_stock_result_id,
            monitoring_stock_result_id=payload.monitoring_stock_result_id,
            prerequisite_assessment_id=payload.prerequisite_assessment_id,
            laboratory_method=payload.laboratory_method or "DRY_COMBUSTION",
            lab_qa_verified=payload.lab_qa_verified if payload.lab_qa_verified is not None else True,
            active_lab_proficiency=payload.active_lab_proficiency if payload.active_lab_proficiency is not None else True,
            notes=payload.notes,
        )
        await db.commit()
        return result
    except (ValueError, SOCChangeCalculationError) as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/soc-change/results",
    response_model=List[AgricultureSOCChangeResultResponse],
)
async def list_soc_change_results(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists authoritative scenario SOC stock change and uncertainty results for a project.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    return await AgricultureService.list_soc_change_results(
        db=db,
        project_id=project_id,
        organization_id=org_id,
    )


@router.get(
    "/projects/{project_id}/soc-change/results/{result_id}",
    response_model=AgricultureSOCChangeResultResponse,
)
async def get_soc_change_result(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves an individual authoritative SOC stock change and uncertainty deduction result.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    return await AgricultureService.get_soc_change_result(
        db=db,
        project_id=project_id,
        result_id=result_id,
        organization_id=org_id,
    )


@router.get(
    "/projects/{project_id}/soc-change/results/{result_id}/components",
    response_model=Dict[str, Any],
)
async def get_soc_change_result_components(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full component breakdown, variance decomposition, and cryptographic proof for an SOC change result.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    res = await AgricultureService.get_soc_change_result(
        db=db,
        project_id=project_id,
        result_id=result_id,
        organization_id=org_id,
    )

    return {
        "result_id": str(res.id),
        "result_code": res.result_code,
        "methodology_version": res.methodology_version,
        "corrections_clarifications_version": res.corrections_clarifications_version,
        "calculation_engine_version": res.calculation_engine_version,
        "quantification_approach": res.quantification_approach,
        "t_start": res.t_start.isoformat(),
        "t_final": res.t_final.isoformat(),
        "elapsed_years": str(res.elapsed_years),
        "esm_algorithm": res.esm_algorithm,
        "reference_soil_mass_t_ha": str(res.reference_soil_mass_t_ha),
        "reference_depth_cm": str(res.reference_depth_cm),
        "total_project_area_ha": str(res.total_project_area_ha),
        "baseline_mean_soc_t_c_per_ha": str(res.baseline_mean_soc_t_c_per_ha),
        "monitoring_mean_soc_t_c_per_ha": str(res.monitoring_mean_soc_t_c_per_ha),
        "delta_soc_project_t_c_ha_yr": str(res.delta_soc_project_t_c_ha_yr),
        "delta_soc_baseline_t_c_ha_yr": str(res.delta_soc_baseline_t_c_ha_yr),
        "delta_soc_net_t_c_ha_yr": str(res.delta_soc_net_t_c_ha_yr),
        "delta_co2_project_tco2e_ha_yr": str(res.delta_co2_project_tco2e_ha_yr),
        "delta_co2_baseline_tco2e_ha_yr": str(res.delta_co2_baseline_tco2e_ha_yr),
        "delta_co2_net_tco2e_ha_yr": str(res.delta_co2_net_tco2e_ha_yr),
        "total_project_delta_co2_tco2e_yr": str(res.total_project_delta_co2_tco2e_yr),
        "total_baseline_delta_co2_tco2e_yr": str(res.total_baseline_delta_co2_tco2e_yr),
        "total_net_delta_co2_tco2e_yr": str(res.total_net_delta_co2_tco2e_yr),
        "co2_to_c_ratio": str(res.co2_to_c_ratio),
        "variance_delta_soc_project": str(res.variance_delta_soc_project),
        "variance_delta_soc_baseline": str(res.variance_delta_soc_baseline),
        "total_variance_delta_soc": str(res.total_variance_delta_soc),
        "standard_error_delta_soc_t_c_ha_yr": str(res.standard_error_delta_soc_t_c_ha_yr),
        "standard_error_tco2e_yr": str(res.standard_error_tco2e_yr),
        "degrees_of_freedom": res.degrees_of_freedom,
        "student_t_value_0667": str(res.student_t_value_0667),
        "relative_uncertainty_pct": str(res.relative_uncertainty_pct),
        "allowable_uncertainty_pct": str(res.allowable_uncertainty_pct),
        "uncertainty_deduction_pct": str(res.uncertainty_deduction_pct),
        "uncertainty_deduction_fraction": str(res.uncertainty_deduction_fraction),
        "adjusted_net_delta_co2_tco2e_yr": str(res.adjusted_net_delta_co2_tco2e_yr),
        "measurement_error_status": res.measurement_error_status,
        "measurement_error_router": res.measurement_error_router,
        "strata_results": res.strata_results,
        "component_breakdown": res.component_breakdown,
        "carbon_accounting_status": res.carbon_accounting_status,
        "ledger_status": res.ledger_status,
        "result_status": res.result_status,
        "calculation_hash": res.calculation_hash,
        "input_snapshot_hash": res.input_snapshot_hash,
    }


# =============================================================================
# PHASE 3B-3: NET GHG REDUCTIONS & REMOVALS + VCU READINESS ENDPOINTS
# =============================================================================

@router.post(
    "/projects/{project_id}/net-ghg/evaluate",
    response_model=NetGHGEvaluationResponse,
)
async def evaluate_net_ghg(
    project_id: uuid.UUID,
    payload: NetGHGEvaluateRequest,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates project-level Net GHG Reductions & Removals, Table 5 Applicability,
    Leakage Allocation, and Section 8.7 VCU Readiness under VM0042 v2.2 + 11 June 2026 C&C.
    Read-only preview endpoint.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        res = await AgricultureService.evaluate_net_ghg_reductions_and_removals(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            prerequisite_assessment_id=payload.prerequisite_assessment_id,
            soc_change_result_id=payload.soc_change_result_id,
            verification_period_start=payload.verification_period_start,
            verification_period_end=payload.verification_period_end,
            applicability_overrides=payload.applicability_overrides,
            fossil_fuel_activities_bsl=payload.fossil_fuel_activities_bsl,
            fossil_fuel_activities_wp=payload.fossil_fuel_activities_wp,
            liming_activity_bsl=payload.liming_activity_bsl,
            liming_activity_wp=payload.liming_activity_wp,
            fertilizer_activities_bsl=payload.fertilizer_activities_bsl,
            fertilizer_activities_wp=payload.fertilizer_activities_wp,
            nfixing_activities_bsl=payload.nfixing_activities_bsl,
            nfixing_activities_wp=payload.nfixing_activities_wp,
            manure_activities_bsl=payload.manure_activities_bsl,
            manure_activities_wp=payload.manure_activities_wp,
            enteric_activities_bsl=payload.enteric_activities_bsl,
            enteric_activities_wp=payload.enteric_activities_wp,
            burning_activities_bsl=payload.burning_activities_bsl,
            burning_activities_wp=payload.burning_activities_wp,
            methanogenesis_bsl=payload.methanogenesis_bsl,
            methanogenesis_wp=payload.methanogenesis_wp,
            woody_pool_data=payload.woody_pool_data,
            leakage_data=payload.leakage_data,
            npr_rating_pct=payload.npr_rating_pct,
            risk_assessment_id=payload.risk_assessment_id,
            annual_vintages_input=payload.annual_vintages_input,
            notes=payload.notes,
        )
        return res
    except (ValueError, NetGHGCalculationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/projects/{project_id}/net-ghg/finalize",
    response_model=AgricultureNetGHGResultResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/projects/{project_id}/net-ghg/calculate",
    response_model=AgricultureNetGHGResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def finalize_net_ghg(
    project_id: uuid.UUID,
    payload: NetGHGFinalizeRequest,
    current_user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Authoritatively finalizes and persists Net GHG Reductions & Removals, Leakage Allocation,
    and Section 8.7 VCU Readiness.
    Segregation of Duties: FIELD_AGENT cannot finalize.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    user_role = (current_user.role or "").upper()
    if user_role == "FIELD_AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field agent role is unauthorized to finalize authoritative Net GHG quantification. Segregation of duties enforced.",
        )

    org_id = await _resolve_org_id(db, project_id, current_user)

    try:
        result = await AgricultureService.finalize_net_ghg_reductions_and_removals(
            db=db,
            project_id=project_id,
            organization_id=org_id,
            user_id=current_user.id,
            user_role=user_role,
            prerequisite_assessment_id=payload.prerequisite_assessment_id,
            soc_change_result_id=payload.soc_change_result_id,
            verification_period_start=payload.verification_period_start,
            verification_period_end=payload.verification_period_end,
            applicability_overrides=payload.applicability_overrides,
            fossil_fuel_activities_bsl=payload.fossil_fuel_activities_bsl,
            fossil_fuel_activities_wp=payload.fossil_fuel_activities_wp,
            liming_activity_bsl=payload.liming_activity_bsl,
            liming_activity_wp=payload.liming_activity_wp,
            fertilizer_activities_bsl=payload.fertilizer_activities_bsl,
            fertilizer_activities_wp=payload.fertilizer_activities_wp,
            nfixing_activities_bsl=payload.nfixing_activities_bsl,
            nfixing_activities_wp=payload.nfixing_activities_wp,
            manure_activities_bsl=payload.manure_activities_bsl,
            manure_activities_wp=payload.manure_activities_wp,
            enteric_activities_bsl=payload.enteric_activities_bsl,
            enteric_activities_wp=payload.enteric_activities_wp,
            burning_activities_bsl=payload.burning_activities_bsl,
            burning_activities_wp=payload.burning_activities_wp,
            methanogenesis_bsl=payload.methanogenesis_bsl,
            methanogenesis_wp=payload.methanogenesis_wp,
            woody_pool_data=payload.woody_pool_data,
            leakage_data=payload.leakage_data,
            npr_rating_pct=payload.npr_rating_pct,
            risk_assessment_id=payload.risk_assessment_id,
            annual_vintages_input=payload.annual_vintages_input,
            notes=payload.notes,
        )
        await db.commit()
        return result
    except (ValueError, NetGHGCalculationError) as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/net-ghg/results",
    response_model=List[AgricultureNetGHGResultResponse],
)
async def list_net_ghg_results(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """Lists all Net GHG quantification results for a project."""
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)
    return await AgricultureService.list_net_ghg_results(db, project_id, org_id)


@router.get(
    "/projects/{project_id}/net-ghg/results/{result_id}",
    response_model=AgricultureNetGHGResultResponse,
)
async def get_net_ghg_result(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a single Net GHG quantification result."""
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)
    return await AgricultureService.get_net_ghg_result(db, project_id, result_id, org_id)


@router.get(
    "/projects/{project_id}/net-ghg/results/{result_id}/components",
    response_model=Dict[str, Any],
)
async def get_net_ghg_result_components(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    current_user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full component audit lineage for a Net GHG quantification result."""
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    org_id = await _resolve_org_id(db, project_id, current_user)
    res = await AgricultureService.get_net_ghg_result(db, project_id, result_id, org_id)
    return {
        "result_id": str(res.id),
        "result_code": res.result_code,
        "methodology_version": res.methodology_version,
        "corrections_clarifications_version": res.corrections_clarifications_version,
        "calculation_engine_version": res.calculation_engine_version,
        "ruleset_version": res.ruleset_version,
        "verification_period_start": res.verification_period_start.isoformat(),
        "verification_period_end": res.verification_period_end.isoformat(),
        "elapsed_years": str(res.elapsed_years),
        "applicability_matrix": res.applicability_matrix,
        "total_baseline_emissions_tco2e": str(res.total_baseline_emissions_tco2e),
        "total_project_emissions_tco2e": str(res.total_project_emissions_tco2e),
        "total_emission_reductions_from_sources_tco2e": str(res.total_emission_reductions_from_sources_tco2e),
        "eq44_baseline_total_carbon_stock_change_tco2e": str(res.eq44_baseline_total_carbon_stock_change_tco2e),
        "eq45_project_total_carbon_stock_change_tco2e": str(res.eq45_project_total_carbon_stock_change_tco2e),
        "eq44_eq45_status": res.eq44_eq45_status,
        "gross_reductions_er_tco2e": str(res.gross_reductions_er_tco2e),
        "gross_removals_cr_tco2e": str(res.gross_removals_cr_tco2e),
        "total_leakage_tco2e": str(res.total_leakage_tco2e),
        "leakage_allocation_er_lker_tco2e": str(res.leakage_allocation_er_lker_tco2e),
        "leakage_allocation_cr_lkcr_tco2e": str(res.leakage_allocation_cr_lkcr_tco2e),
        "net_reductions_ernet_tco2e": str(res.net_reductions_ernet_tco2e),
        "net_removals_crnet_tco2e": str(res.net_removals_crnet_tco2e),
        "total_net_ghg_errnet_tco2e": str(res.total_net_ghg_errnet_tco2e),
        "npr_rating_pct": str(res.npr_rating_pct) if res.npr_rating_pct is not None else None,
        "risk_assessment_id": res.risk_assessment_id,
        "buffer_deduction_reductions_tco2e": str(res.buffer_deduction_reductions_tco2e) if res.buffer_deduction_reductions_tco2e is not None else None,
        "buffer_deduction_removals_tco2e": str(res.buffer_deduction_removals_tco2e) if res.buffer_deduction_removals_tco2e is not None else None,
        "total_buffer_deduction_tco2e": str(res.total_buffer_deduction_tco2e) if res.total_buffer_deduction_tco2e is not None else None,
        "internal_vcu_eligible_reductions_tco2e": str(res.internal_vcu_eligible_reductions_tco2e) if res.internal_vcu_eligible_reductions_tco2e is not None else None,
        "internal_vcu_eligible_removals_tco2e": str(res.internal_vcu_eligible_removals_tco2e) if res.internal_vcu_eligible_removals_tco2e is not None else None,
        "internal_vcu_eligible_total_tco2e": str(res.internal_vcu_eligible_total_tco2e) if res.internal_vcu_eligible_total_tco2e is not None else None,
        "vcu_readiness_status": res.vcu_readiness_status,
        "internal_mrv_status": res.internal_mrv_status,
        "vvb_status": res.vvb_status,
        "registry_status": res.registry_status,
        "ledger_status": res.ledger_status,
        "result_status": res.result_status,
        "calculation_hash": res.calculation_hash,
        "input_snapshot_hash": res.input_snapshot_hash,
        "component_breakdown": res.component_breakdown,
        "vintages": [
            {
                "vintage_year": v.vintage_year,
                "total_baseline_emissions_tco2e": str(v.total_baseline_emissions_tco2e),
                "total_project_emissions_tco2e": str(v.total_project_emissions_tco2e),
                "total_emission_reductions_from_sources_tco2e": str(v.total_emission_reductions_from_sources_tco2e),
                "eq44_baseline_total_carbon_stock_change_tco2e": str(v.eq44_baseline_total_carbon_stock_change_tco2e),
                "eq45_project_total_carbon_stock_change_tco2e": str(v.eq45_project_total_carbon_stock_change_tco2e),
                "gross_reductions_er_tco2e": str(v.gross_reductions_er_tco2e),
                "gross_removals_cr_tco2e": str(v.gross_removals_cr_tco2e),
                "total_leakage_tco2e": str(v.total_leakage_tco2e),
                "leakage_allocation_er_lker_tco2e": str(v.leakage_allocation_er_lker_tco2e),
                "leakage_allocation_cr_lkcr_tco2e": str(v.leakage_allocation_cr_lkcr_tco2e),
                "net_reductions_ernet_tco2e": str(v.net_reductions_ernet_tco2e),
                "net_removals_crnet_tco2e": str(v.net_removals_crnet_tco2e),
                "total_net_ghg_errnet_tco2e": str(v.total_net_ghg_errnet_tco2e),
                "buffer_deduction_reductions_tco2e": str(v.buffer_deduction_reductions_tco2e) if v.buffer_deduction_reductions_tco2e is not None else None,
                "buffer_deduction_removals_tco2e": str(v.buffer_deduction_removals_tco2e) if v.buffer_deduction_removals_tco2e is not None else None,
                "total_buffer_deduction_tco2e": str(v.total_buffer_deduction_tco2e) if v.total_buffer_deduction_tco2e is not None else None,
                "internal_vcu_eligible_reductions_tco2e": str(v.internal_vcu_eligible_reductions_tco2e) if v.internal_vcu_eligible_reductions_tco2e is not None else None,
                "internal_vcu_eligible_removals_tco2e": str(v.internal_vcu_eligible_removals_tco2e) if v.internal_vcu_eligible_removals_tco2e is not None else None,
                "internal_vcu_eligible_total_tco2e": str(v.internal_vcu_eligible_total_tco2e) if v.internal_vcu_eligible_total_tco2e is not None else None,
                "vintage_details": v.vintage_details,
            }
            for v in res.vintages
        ],
    }
