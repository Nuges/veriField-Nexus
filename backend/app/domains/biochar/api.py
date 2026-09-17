import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.abac import ABACEngine
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharInventory,
    BiocharLabAnalysis,
    BiocharMaterialTransaction,
    BiocharStorageEvent,
    BiocharTransportEvent,
    BiocharProductFormulation,
    BiocharProductBatch,
    BiocharIngredientAllocation,
    BiocharProductNonBiocharIngredient,
    FacilityReactor,
    FeedstockLot,
    FeedstockRunAllocation,
    FeedstockSource,
    ProductionFacility,
    ProductionRun,
)
from app.domains.biochar.schemas import (
    BiocharBatchCreate,
    BiocharBatchResponse,
    BiocharEligibilityResponse,
    BiocharEndUseRecordCreate,
    BiocharEndUseRecordResponse,
    BiocharLabAnalysisCreate,
    BiocharLabAnalysisResponse,
    BiocharMaterialTransactionResponse,
    BiocharProductBatchCreate,
    BiocharProductBatchResponse,
    BiocharProductFormulationCreate,
    BiocharProductFormulationResponse,
    BiocharStorageEventCreate,
    BiocharStorageEventResponse,
    BiocharSummaryResponse,
    BiocharTransportEventCreate,
    BiocharTransportEventResponse,
    ChainOfCustodyResponse,
    FacilityReactorCreate,
    FacilityReactorResponse,
    FeedstockAllocationRequest,
    FeedstockAllocationResponse,
    FeedstockLotCreate,
    FeedstockLotResponse,
    FeedstockSourceCreate,
    FeedstockSourceResponse,
    MassBalanceReconciliationResponse,
    MethodologyConflictResponse,
    MultiBiomassBlendBreakdownResponse,
    MultiBiomassBlendComponent,
    ProductionFacilityCreate,
    ProductionFacilityResponse,
    ProductionRunCreate,
    ProductionRunResponse,
)
from app.domains.biochar.service import BiocharQuantificationEngine
from app.domains.biochar.services.conflict_resolver import BiocharMethodologyConflictResolver
from app.domains.biochar.services.eligibility import BiocharEligibilityEngine
from app.domains.biochar.services.lineage import BiocharLineageService
from app.domains.biochar.services.mass_balance import BiocharMassBalanceEngine
from app.domains.projects.models import Project

router = APIRouter()


# ---------------------------------------------------------------------------
# Feedstock Sources
# ---------------------------------------------------------------------------

@router.post("/sources", response_model=FeedstockSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_feedstock_source(
    data: FeedstockSourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(data.project_id)

    org_id = current_user.organization_id
    if not org_id and data.project_id:
        stmt_p = select(Project).where(Project.id == data.project_id)
        res_p = await db.execute(stmt_p)
        p = res_p.scalar_one_or_none()
        if p:
            org_id = p.organization_id

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot determine organization for feedstock source.",
        )

    source = FeedstockSource(
        organization_id=org_id,
        project_id=data.project_id,
        source_code=data.source_code,
        source_name=data.source_name,
        source_type=data.source_type,
        biomass_type=data.biomass_type,
        origin_location=data.origin_location,
        source_land_unit_id=data.source_land_unit_id,
        supplier_name=data.supplier_name,
        waste_status=data.waste_status,
        baseline_fate=data.baseline_fate,
        sustainability_status=data.sustainability_status,
        metadata_json=data.metadata_json,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("/sources", response_model=List[FeedstockSourceResponse])
async def list_feedstock_sources(
    project_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(FeedstockSource)
    if project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(project_id)
        stmt = stmt.where(FeedstockSource.project_id == project_id)
    elif current_user.role != "SUPER_ADMIN":
        if not current_user.organization_id:
            return []
        stmt = stmt.where(FeedstockSource.organization_id == current_user.organization_id)

    stmt = stmt.order_by(FeedstockSource.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# Feedstock Lots & Allocations
# ---------------------------------------------------------------------------

@router.post("/lots", response_model=FeedstockLotResponse, status_code=status.HTTP_201_CREATED)
async def create_feedstock_lot(
    data: FeedstockLotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_src = select(FeedstockSource).where(FeedstockSource.id == data.source_id)
    res_src = await db.execute(stmt_src)
    source = res_src.scalar_one_or_none()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedstock Source {data.source_id} not found.",
        )

    if current_user.role != "SUPER_ADMIN" and current_user.organization_id:
        if source.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to feedstock source across tenant boundary.",
            )

    dry_mass = round(data.mass_received_tonnes * (1.0 - (data.moisture_content_pct / 100.0)), 4)
    lot = FeedstockLot(
        organization_id=source.organization_id,
        project_id=data.project_id or source.project_id,
        source_id=data.source_id,
        lot_number=data.lot_number,
        feedstock_type=data.feedstock_type,
        mass_received_tonnes=data.mass_received_tonnes,
        moisture_content_pct=data.moisture_content_pct,
        dry_mass_tonnes=dry_mass,
        allocated_mass_tonnes=0.0,
        receipt_date=data.receipt_date or datetime.now(timezone.utc),
        storage_location=data.storage_location,
        chain_of_custody_ref=data.chain_of_custody_ref,
        evidence_hash=data.evidence_hash,
        metadata_json=data.metadata_json,
    )
    db.add(lot)
    await db.commit()
    await db.refresh(lot)

    resp = FeedstockLotResponse.model_validate(lot)
    resp.available_mass_tonnes = float(lot.mass_received_tonnes)
    return resp


@router.get("/lots", response_model=List[FeedstockLotResponse])
async def list_feedstock_lots(
    source_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(FeedstockLot)
    if source_id:
        stmt = stmt.where(FeedstockLot.source_id == source_id)
    if project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(project_id)
        stmt = stmt.where(FeedstockLot.project_id == project_id)
    elif current_user.role != "SUPER_ADMIN":
        if not current_user.organization_id:
            return []
        stmt = stmt.where(FeedstockLot.organization_id == current_user.organization_id)

    stmt = stmt.order_by(FeedstockLot.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    lots = res.scalars().all()
    results = []
    for l in lots:
        r = FeedstockLotResponse.model_validate(l)
        from decimal import Decimal
        avail = float(Decimal(str(l.mass_received_tonnes)) - Decimal(str(l.allocated_mass_tonnes or 0.0)))
        r.available_mass_tonnes = round(avail, 4)
        results.append(r)
    return results


@router.post("/allocations", response_model=FeedstockAllocationResponse, status_code=status.HTTP_201_CREATED)
async def allocate_feedstock(
    data: FeedstockAllocationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alloc = await BiocharMassBalanceEngine.allocate_feedstock_lot(
        db=db,
        lot_id=data.lot_id,
        production_run_id=data.production_run_id,
        allocated_wet_mass_tonnes=data.allocated_wet_mass_tonnes,
    )
    return alloc


# ---------------------------------------------------------------------------
# Production Facilities & Reactors
# ---------------------------------------------------------------------------

@router.post("/facilities", response_model=ProductionFacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
    data: ProductionFacilityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(data.project_id)

    org_id = current_user.organization_id
    if not org_id and data.project_id:
        stmt_p = select(Project).where(Project.id == data.project_id)
        res_p = await db.execute(stmt_p)
        p = res_p.scalar_one_or_none()
        if p:
            org_id = p.organization_id

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot determine organization for production facility.",
        )

    facility = ProductionFacility(
        organization_id=org_id,
        project_id=data.project_id,
        facility_code=data.facility_code,
        facility_name=data.facility_name,
        location=data.location,
        commissioning_date=data.commissioning_date,
        first_biochar_production_date=data.first_biochar_production_date,
        project_start_date=data.project_start_date,
        facility_status=data.facility_status,
        operator_name=data.operator_name,
        technology_type=data.technology_type,
        production_capacity_tpy=data.production_capacity_tpy,
        permits_json=data.permits_json,
        emissions_controls_json=data.emissions_controls_json,
        energy_recovery_json=data.energy_recovery_json,
        metadata_json=data.metadata_json,
    )
    db.add(facility)
    await db.commit()
    await db.refresh(facility)
    return facility


@router.get("/facilities", response_model=List[ProductionFacilityResponse])
async def list_facilities(
    project_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProductionFacility)
    if project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(project_id)
        stmt = stmt.where(ProductionFacility.project_id == project_id)
    elif current_user.role != "SUPER_ADMIN":
        if not current_user.organization_id:
            return []
        stmt = stmt.where(ProductionFacility.organization_id == current_user.organization_id)

    stmt = stmt.order_by(ProductionFacility.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/facilities/{facility_id}/reactors", response_model=FacilityReactorResponse, status_code=status.HTTP_201_CREATED)
async def create_reactor(
    facility_id: UUID,
    data: FacilityReactorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_fac = select(ProductionFacility).where(ProductionFacility.id == facility_id)
    res_fac = await db.execute(stmt_fac)
    fac = res_fac.scalar_one_or_none()
    if not fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production Facility {facility_id} not found.",
        )

    reactor = FacilityReactor(
        facility_id=facility_id,
        reactor_code=data.reactor_code,
        manufacturer=data.manufacturer,
        model=data.model,
        technology_type=data.technology_type,
        design_capacity_kg_h=data.design_capacity_kg_h,
        operating_temp_min_c=data.operating_temp_min_c,
        operating_temp_max_c=data.operating_temp_max_c,
        residence_time_min_minutes=data.residence_time_min_minutes,
        residence_time_max_minutes=data.residence_time_max_minutes,
        metadata_json=data.metadata_json,
    )
    db.add(reactor)
    await db.commit()
    await db.refresh(reactor)
    return reactor


@router.get("/facilities/{facility_id}/reactors", response_model=List[FacilityReactorResponse])
async def list_reactors(
    facility_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(FacilityReactor).where(FacilityReactor.facility_id == facility_id).order_by(FacilityReactor.created_at.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# Production Runs
# ---------------------------------------------------------------------------

@router.post("/runs", response_model=ProductionRunResponse, status_code=status.HTTP_201_CREATED)
async def create_production_run(
    data: ProductionRunCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_fac = select(ProductionFacility).where(ProductionFacility.id == data.facility_id)
    res_fac = await db.execute(stmt_fac)
    fac = res_fac.scalar_one_or_none()
    if not fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production Facility {data.facility_id} not found.",
        )

    run = ProductionRun(
        organization_id=fac.organization_id,
        project_id=data.project_id or fac.project_id,
        facility_id=data.facility_id,
        reactor_id=data.reactor_id,
        run_number=data.run_number,
        start_time=data.start_time,
        end_time=data.end_time,
        avg_pyrolysis_temp_celsius=data.avg_pyrolysis_temp_celsius,
        max_pyrolysis_temp_celsius=data.max_pyrolysis_temp_celsius,
        residence_time_minutes=data.residence_time_minutes,
        electricity_kwh=data.electricity_kwh,
        fuel_liters=data.fuel_liters,
        heat_recovered_mj=data.heat_recovered_mj,
        output_biochar_mass_tonnes=data.output_biochar_mass_tonnes,
        co_products_json=data.co_products_json,
        operator_id=data.operator_id or current_user.id,
        metadata_json=data.metadata_json,
        qa_status="LOGGED",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/runs", response_model=List[ProductionRunResponse])
async def list_production_runs(
    facility_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProductionRun)
    if facility_id:
        stmt = stmt.where(ProductionRun.facility_id == facility_id)
    if project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(project_id)
        stmt = stmt.where(ProductionRun.project_id == project_id)
    elif current_user.role != "SUPER_ADMIN":
        if not current_user.organization_id:
            return []
        stmt = stmt.where(ProductionRun.organization_id == current_user.organization_id)

    stmt = stmt.order_by(ProductionRun.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# Biochar Batches
# ---------------------------------------------------------------------------

@router.post("/batches", response_model=BiocharBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_biochar_batch(
    data: BiocharBatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(data.project_id)

    net_co2e, perm_factor, grade, has_anomaly, anomaly_reason = BiocharQuantificationEngine.calculate_removal_and_grade(data)

    dry_mass = data.dry_mass_tonnes
    if not dry_mass:
        dry_mass = round(data.biochar_yield_tonnes * (1.0 - (data.moisture_content_pct / 100.0)), 4)

    # Compute deterministic SHA256 digest hash
    digest_src = f"{data.batch_number}:{data.facility_name}:{data.biochar_yield_tonnes}:{data.molar_h_c_ratio}:{data.fixed_carbon_pct}"
    digest_hash = hashlib.sha256(digest_src.encode('utf-8')).hexdigest()

    batch = BiocharBatch(
        organization_id=current_user.organization_id,
        project_id=data.project_id,
        created_at=datetime.now(timezone.utc),
        batch_number=data.batch_number,
        facility_name=data.facility_name,
        kiln_id=data.kiln_id,
        production_run_id=data.production_run_id,
        feedstock_type=data.feedstock_type,
        feedstock_weight_tonnes=data.feedstock_weight_tonnes,
        moisture_content_pct=data.moisture_content_pct,
        origin_location=data.origin_location,
        pyrolysis_temp_celsius=data.pyrolysis_temp_celsius,
        residence_time_minutes=data.residence_time_minutes,
        biochar_yield_tonnes=data.biochar_yield_tonnes,
        dry_mass_tonnes=dry_mass,
        fixed_carbon_pct=data.fixed_carbon_pct,
        ash_content_pct=data.ash_content_pct,
        molar_h_c_ratio=data.molar_h_c_ratio,
        carbon_permanence_factor=perm_factor,
        net_co2e_removed_tonnes=net_co2e,
        quality_grade=grade,
        lab_report_number=data.lab_report_number,
        lab_document_url=data.lab_document_url,
        has_anomaly=has_anomaly,
        anomaly_reason=anomaly_reason,
        status="PRODUCED",
        carbon_claim_project_id=data.carbon_claim_project_id or data.project_id,
        carbon_claim_registry=data.carbon_claim_registry,
        carbon_claim_methodology=data.carbon_claim_methodology,
        mass_balance_allocated_tonnes=0.0,
        mass_balance_status="IN_BALANCE",
        batch_digest_hash=digest_hash,
        metadata_json=data.metadata_json,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


@router.get("/batches", response_model=List[BiocharBatchResponse])
async def list_biochar_batches(
    project_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BiocharBatch)
    if project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(project_id)
        stmt = stmt.where(BiocharBatch.project_id == project_id)
    elif current_user.role != "SUPER_ADMIN":
        if not current_user.organization_id:
            return []
        org_projects = select(Project.id).where(Project.organization_id == current_user.organization_id)
        stmt = stmt.where(BiocharBatch.project_id.in_(org_projects))

    stmt = stmt.order_by(BiocharBatch.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/batches/{batch_id}", response_model=BiocharBatchResponse)
async def get_biochar_batch(
    batch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BiocharBatch).where(BiocharBatch.id == batch_id)
    res = await db.execute(stmt)
    batch = res.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biochar Batch not found.")

    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(batch.project_id)
    return batch


# ---------------------------------------------------------------------------
# Lab Analyses
# ---------------------------------------------------------------------------

@router.post("/batches/{batch_id}/lab-analyses", response_model=BiocharLabAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_analysis(
    batch_id: UUID,
    data: BiocharLabAnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_b = select(BiocharBatch).where(BiocharBatch.id == batch_id)
    res_b = await db.execute(stmt_b)
    batch = res_b.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biochar Batch not found.")

    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(batch.project_id)

    lab_hash = data.lab_report_hash
    if not lab_hash:
        raw_sig = f"{data.sample_id}:{data.laboratory_name}:{data.molar_h_c_ratio}:{data.organic_carbon_pct}"
        lab_hash = hashlib.sha256(raw_sig.encode('utf-8')).hexdigest()

    analysis = BiocharLabAnalysis(
        organization_id=batch.organization_id or current_user.organization_id,
        project_id=batch.project_id,
        batch_id=batch_id,
        sample_id=data.sample_id,
        sampling_date=data.sampling_date,
        testing_date=data.testing_date,
        laboratory_name=data.laboratory_name,
        accreditation_standard=data.accreditation_standard,
        test_method=data.test_method,
        molar_h_c_ratio=data.molar_h_c_ratio,
        organic_carbon_pct=data.organic_carbon_pct,
        fixed_carbon_pct=data.fixed_carbon_pct,
        moisture_pct=data.moisture_pct,
        ash_pct=data.ash_pct,
        volatile_matter_pct=data.volatile_matter_pct,
        heavy_metals_pass=data.heavy_metals_pass,
        pah_content_mg_kg=data.pah_content_mg_kg,
        lab_report_hash=lab_hash,
        lab_report_uri=data.lab_report_uri,
        metadata_json=data.metadata_json,
        qa_status="VERIFIED" if data.heavy_metals_pass and data.molar_h_c_ratio <= 0.7 else "FLAGGED",
    )
    db.add(analysis)

    # Update batch lab properties
    batch.lab_sample_id = data.sample_id
    batch.molar_h_c_ratio = data.molar_h_c_ratio
    batch.fixed_carbon_pct = data.fixed_carbon_pct
    batch.ash_content_pct = data.ash_pct
    batch.status = "LAB_TESTED"
    await db.commit()
    await db.refresh(analysis)
    return analysis


@router.get("/batches/{batch_id}/lab-analyses", response_model=List[BiocharLabAnalysisResponse])
async def list_lab_analyses(
    batch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BiocharLabAnalysis).where(BiocharLabAnalysis.batch_id == batch_id).order_by(BiocharLabAnalysis.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# Transport & Storage
# ---------------------------------------------------------------------------

@router.post("/transports", response_model=BiocharTransportEventResponse, status_code=status.HTTP_201_CREATED)
async def create_transport_event(
    data: BiocharTransportEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(data.project_id)

    pod_hash = data.pod_document_hash
    if not pod_hash and data.proof_of_delivery_ref:
        pod_hash = hashlib.sha256(data.proof_of_delivery_ref.encode('utf-8')).hexdigest()

    transport = BiocharTransportEvent(
        organization_id=current_user.organization_id,
        project_id=data.project_id,
        material_type=data.material_type,
        reference_id=data.reference_id,
        origin_address=data.origin_address,
        destination_address=data.destination_address,
        mass_transported_tonnes=data.mass_transported_tonnes,
        distance_km=data.distance_km,
        distance_source=data.distance_source,
        transport_mode=data.transport_mode,
        carrier_name=data.carrier_name,
        departure_date=data.departure_date,
        delivery_date=data.delivery_date,
        proof_of_delivery_ref=data.proof_of_delivery_ref,
        pod_document_hash=pod_hash,
        status="DELIVERED" if data.delivery_date else "IN_TRANSIT",
        metadata_json=data.metadata_json,
    )
    db.add(transport)
    await db.commit()
    await db.refresh(transport)
    return transport


@router.get("/transports", response_model=List[BiocharTransportEventResponse])
async def list_transports(
    reference_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BiocharTransportEvent)
    if reference_id:
        stmt = stmt.where(BiocharTransportEvent.reference_id == reference_id)
    if project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(project_id)
        stmt = stmt.where(BiocharTransportEvent.project_id == project_id)
    elif current_user.role != "SUPER_ADMIN":
        if not current_user.organization_id:
            return []
        stmt = stmt.where(BiocharTransportEvent.organization_id == current_user.organization_id)

    stmt = stmt.order_by(BiocharTransportEvent.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/storage-events", response_model=BiocharStorageEventResponse, status_code=status.HTTP_201_CREATED)
async def create_storage_event(
    data: BiocharStorageEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_b = select(BiocharBatch).where(BiocharBatch.id == data.batch_id)
    res_b = await db.execute(stmt_b)
    batch = res_b.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biochar Batch not found.")

    event = BiocharStorageEvent(
        organization_id=batch.organization_id or current_user.organization_id,
        batch_id=data.batch_id,
        storage_facility_name=data.storage_facility_name,
        storage_location=data.storage_location,
        start_date=data.start_date,
        end_date=data.end_date,
        quantity_stored_tonnes=data.quantity_stored_tonnes,
        loss_or_damage_tonnes=data.loss_or_damage_tonnes,
        storage_conditions=data.storage_conditions,
        notes=data.notes,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/batches/{batch_id}/storage-events", response_model=List[BiocharStorageEventResponse])
async def list_storage_events(
    batch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BiocharStorageEvent).where(BiocharStorageEvent.batch_id == batch_id).order_by(BiocharStorageEvent.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# End-Use Records (Soil & Non-Soil)
# ---------------------------------------------------------------------------

@router.post("/end-uses", response_model=BiocharEndUseRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_end_use_record(
    data: BiocharEndUseRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async with BiocharMassBalanceEngine.get_batch_lock(data.batch_id):
        stmt_b = select(BiocharBatch).where(BiocharBatch.id == data.batch_id)
        res_b = await db.execute(stmt_b)
        batch = res_b.scalar_one_or_none()
        if not batch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biochar Batch not found.")

        # 1. State machine validation: Ensure valid material transaction transition to END_USE
        BiocharMassBalanceEngine.validate_material_transition("DELIVERY", "END_USE")

        # 2. Check methodology & double-counting conflict on soil application
        if data.end_use_type == "SOIL_APPLICATION" and data.source_land_unit_id:
            conflict = await BiocharMethodologyConflictResolver.check_land_unit_conflict(
                db=db,
                land_unit_id=data.source_land_unit_id,
                biochar_methodology=batch.carbon_claim_methodology or "VM0044",
                biochar_project_id=batch.carbon_claim_project_id or batch.project_id,
            )
            if conflict.has_conflict and conflict.accounting_blocked:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=conflict.message,
                )

        # 3. Atomically allocate batch mass with row-level locking (with_for_update)
        batch = await BiocharMassBalanceEngine.allocate_batch_end_use(
            db=db,
            batch_id=data.batch_id,
            quantity_tonnes=data.applied_quantity_tonnes,
        )

        record = BiocharEndUseRecord(
            organization_id=batch.organization_id or current_user.organization_id,
            project_id=data.project_id or batch.project_id,
            batch_id=data.batch_id,
            end_use_type=data.end_use_type,
            applied_quantity_tonnes=data.applied_quantity_tonnes,
            event_date=data.event_date,
            source_land_unit_id=data.source_land_unit_id,
            application_rate_tonnes_per_ha=data.application_rate_tonnes_per_ha,
            area_hectares=data.area_hectares,
            application_method=data.application_method,
            gps_coordinates=data.gps_coordinates,
            wetland_exclusion_screened=data.wetland_exclusion_screened,
            crop_type=data.crop_type,
            product_category=data.product_category,
            recipient_organization=data.recipient_organization,
            durability_classification=data.durability_classification,
            proof_photos_json=data.proof_photos_json,
            verification_status="VERIFIED" if data.proof_photos_json or data.wetland_exclusion_screened else "PENDING_VERIFICATION",
            metadata_json=data.metadata_json,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        # Re-reconcile batch mass balance
        await BiocharMassBalanceEngine.reconcile_batch(db, batch.id)
        return record


@router.get("/end-uses", response_model=List[BiocharEndUseRecordResponse])
async def list_end_uses(
    batch_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BiocharEndUseRecord)
    if batch_id:
        stmt = stmt.where(BiocharEndUseRecord.batch_id == batch_id)
    if project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(project_id)
        stmt = stmt.where(BiocharEndUseRecord.project_id == project_id)
    elif current_user.role != "SUPER_ADMIN":
        if not current_user.organization_id:
            return []
        stmt = stmt.where(BiocharEndUseRecord.organization_id == current_user.organization_id)

    stmt = stmt.order_by(BiocharEndUseRecord.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


# ---------------------------------------------------------------------------
# Mass Balance, Conflicts, Eligibility, Lineage
# ---------------------------------------------------------------------------

@router.get("/batches/{batch_id}/mass-balance", response_model=MassBalanceReconciliationResponse)
async def get_batch_mass_balance(
    batch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_b = select(BiocharBatch).where(BiocharBatch.id == batch_id)
    res_b = await db.execute(stmt_b)
    batch = res_b.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biochar Batch not found.")

    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(batch.project_id)
    return await BiocharMassBalanceEngine.reconcile_batch(db, batch_id)


@router.get("/conflicts/land-units/{land_unit_id}", response_model=MethodologyConflictResponse)
async def check_land_unit_conflict(
    land_unit_id: UUID,
    biochar_methodology: str = Query("VM0044", description="Biochar methodology to evaluate against"),
    biochar_project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BiocharMethodologyConflictResolver.check_land_unit_conflict(
        db=db,
        land_unit_id=land_unit_id,
        biochar_methodology=biochar_methodology,
        biochar_project_id=biochar_project_id,
    )


@router.get("/projects/{project_id}/eligibility", response_model=BiocharEligibilityResponse)
async def evaluate_project_eligibility(
    project_id: UUID,
    target_standard: str = Query("VERRA", description="VERRA, PURO_STANDARD, GOLD_STANDARD, INDIA_CCTS"),
    target_methodology: str = Query("VM0044", description="VM0044, PURO_BIOCHAR_2025, GS_PARC"),
    methodology_version: str = Query("v1.2", description="v1.2, Edition_2025_v2, v2.0"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)
    return await BiocharEligibilityEngine.evaluate_project_eligibility(
        db=db,
        project_id=project_id,
        target_standard=target_standard,
        target_methodology=target_methodology,
        methodology_version=methodology_version,
    )


@router.get("/batches/{batch_id}/lineage", response_model=ChainOfCustodyResponse)
async def get_batch_lineage(
    batch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt_b = select(BiocharBatch).where(BiocharBatch.id == batch_id)
    res_b = await db.execute(stmt_b)
    batch = res_b.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biochar Batch not found.")

    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(batch.project_id)
    return await BiocharLineageService.get_batch_chain_of_custody(db, batch_id)


# ---------------------------------------------------------------------------
# Biochar Summary (Preserved)
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BiocharSummaryResponse)
async def get_biochar_summary(
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(
        func.count(BiocharBatch.id).label("total_batches"),
        func.coalesce(func.sum(BiocharBatch.feedstock_weight_tonnes), 0.0).label("total_feedstock"),
        func.coalesce(func.sum(BiocharBatch.biochar_yield_tonnes), 0.0).label("total_yield"),
        func.coalesce(func.sum(BiocharBatch.net_co2e_removed_tonnes), 0.0).label("total_co2e"),
        func.count(BiocharBatch.id).filter(BiocharBatch.quality_grade == "GRADE_A").label("grade_a_count"),
        func.count(BiocharBatch.id).filter(BiocharBatch.has_anomaly == True).label("anomaly_count"),
    )

    if project_id:
        abac = ABACEngine(db, current_user)
        await abac.enforce_project_access(project_id)
        stmt = stmt.where(BiocharBatch.project_id == project_id)
    elif current_user.role != "SUPER_ADMIN":
        if not current_user.organization_id:
            return {
                "total_batches": 0,
                "total_feedstock_tonnes": 0.0,
                "total_biochar_produced_tonnes": 0.0,
                "total_net_co2e_removed_tonnes": 0.0,
                "grade_a_percentage": 0.0,
                "detected_anomalies_count": 0,
            }
        org_projects = select(Project.id).where(Project.organization_id == current_user.organization_id)
        stmt = stmt.where(BiocharBatch.project_id.in_(org_projects))

    res = await db.execute(stmt)
    row = res.one()

    total_b = row.total_batches or 0
    grade_a_pct = (row.grade_a_count / total_b * 100.0) if total_b > 0 else 0.0

    return {
        "total_batches": total_b,
        "total_feedstock_tonnes": float(row.total_feedstock),
        "total_biochar_produced_tonnes": float(row.total_yield),
        "total_net_co2e_removed_tonnes": float(row.total_co2e),
        "grade_a_percentage": round(grade_a_pct, 1),
        "detected_anomalies_count": row.anomaly_count or 0,
    }


# ---------------------------------------------------------------------------
# Multi-Biomass Feedstock Blend & Product Formulation Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/runs/{run_id}/blend-breakdown",
    response_model=MultiBiomassBlendBreakdownResponse,
)
async def get_run_feedstock_blend_breakdown(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the multi-biomass feedstock blend ingredients breakdown for a production run.
    Calculates wet mass, dry mass, moisture content, blend percentages, baseline fate,
    and sustainability status for each allocated feedstock lot.
    """
    from sqlalchemy.orm import selectinload
    stmt = (
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.allocations)
            .selectinload(FeedstockRunAllocation.lot)
            .selectinload(FeedstockLot.source)
        )
        .where(ProductionRun.id == run_id)
    )
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Production Run {run_id} not found")

    total_wet = float(run.total_feedstock_input_tonnes or 0.0)
    total_dry = float(run.total_feedstock_dry_tonnes or 0.0)

    components = []
    for alloc in run.allocations:
        lot = alloc.lot
        source = lot.source if lot else None
        wet = float(alloc.allocated_wet_mass_tonnes)
        dry = float(alloc.allocated_dry_mass_tonnes)
        wet_pct = (wet / total_wet * 100.0) if total_wet > 0 else 0.0
        dry_pct = (dry / total_dry * 100.0) if total_dry > 0 else 0.0

        components.append(
            MultiBiomassBlendComponent(
                source_id=source.id if source else uuid.uuid4(),
                source_code=source.source_code if source else "UNKNOWN",
                source_name=source.source_name if source else "Unknown Source",
                source_type=source.source_type if source else "AGRICULTURAL_RESIDUE",
                biomass_type=source.biomass_type if source else "CROP_RESIDUE",
                baseline_fate=source.baseline_fate if source else "OPEN_BURNING",
                sustainability_status=source.sustainability_status if source else "LOW_RISK",
                lot_id=lot.id if lot else alloc.lot_id,
                lot_number=lot.lot_number if lot else "N/A",
                wet_mass_tonnes=round(wet, 4),
                dry_mass_tonnes=round(dry, 4),
                wet_mass_pct=round(wet_pct, 2),
                dry_mass_pct=round(dry_pct, 2),
                moisture_content_pct=float(lot.moisture_content_pct) if lot else 0.0,
            )
        )

    return MultiBiomassBlendBreakdownResponse(
        production_run_id=run.id,
        run_number=run.run_number,
        total_wet_mass_tonnes=round(total_wet, 4),
        total_dry_mass_tonnes=round(total_dry, 4),
        component_count=len(components),
        components=components,
    )


@router.post(
    "/product-formulations",
    response_model=BiocharProductFormulationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_formulation(
    payload: BiocharProductFormulationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a mixed biochar product formulation recipe."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User does not belong to an organization")

    formulation = BiocharProductFormulation(
        organization_id=org_id,
        project_id=payload.project_id,
        product_name=payload.product_name,
        product_code=payload.product_code,
        target_sector=payload.target_sector,
        description=payload.description,
        biochar_target_ratio=payload.biochar_target_ratio,
        is_active=payload.is_active,
    )
    db.add(formulation)
    await db.commit()
    await db.refresh(formulation)
    return formulation


@router.get(
    "/product-formulations",
    response_model=List[BiocharProductFormulationResponse],
)
async def list_product_formulations(
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists biochar product formulations for project or organization."""
    stmt = select(BiocharProductFormulation)
    if project_id:
        stmt = stmt.where(
            (BiocharProductFormulation.project_id == project_id)
            | (BiocharProductFormulation.project_id.is_(None))
        )
    elif current_user.role != "SUPER_ADMIN" and current_user.organization_id:
        stmt = stmt.where(BiocharProductFormulation.organization_id == current_user.organization_id)

    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "/product-batches",
    response_model=BiocharProductBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_batch(
    payload: BiocharProductBatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manufactures a mixed biochar product batch with mass balance verification.
    Allocates pure biochar from batches and enforces anti-overallocation.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User does not belong to an organization")

    product_batch = BiocharProductBatch(
        organization_id=org_id,
        project_id=payload.project_id,
        formulation_id=payload.formulation_id,
        batch_number=payload.batch_number,
        production_date=payload.production_date,
        total_product_mass_tonnes=payload.total_product_mass_tonnes,
        biochar_mass_tonnes=payload.biochar_mass_tonnes,
        non_biochar_mass_tonnes=payload.non_biochar_mass_tonnes,
        packaging_type=payload.packaging_type,
        storage_location=payload.storage_location,
        qa_status="APPROVED",
    )
    db.add(product_batch)
    await db.flush()

    allocations_out = []
    # Atomically allocate biochar from each contributing batch
    for alloc_input in payload.biochar_batch_allocations:
        alloc = await BiocharMassBalanceEngine.allocate_batch_to_product_batch(
            db=db,
            biochar_batch_id=alloc_input.biochar_batch_id,
            product_batch_id=product_batch.id,
            allocated_biochar_mass_tonnes=alloc_input.allocated_biochar_mass_tonnes,
        )
        allocations_out.append({
            "allocation_id": str(alloc.id),
            "biochar_batch_id": str(alloc.biochar_batch_id),
            "allocated_biochar_mass_tonnes": float(alloc.allocated_biochar_mass_tonnes),
        })

    # Record non-biochar ingredients
    non_biochar_out = []
    for non_b in payload.non_biochar_ingredients:
        ing = BiocharProductNonBiocharIngredient(
            product_batch_id=product_batch.id,
            ingredient_name=non_b.ingredient_name,
            ingredient_type=non_b.ingredient_type,
            mass_tonnes=non_b.mass_tonnes,
            mass_pct=non_b.mass_pct,
            cas_number=non_b.cas_number,
            supplier=non_b.supplier,
        )
        db.add(ing)
        non_biochar_out.append({
            "ingredient_name": ing.ingredient_name,
            "ingredient_type": ing.ingredient_type,
            "mass_tonnes": float(ing.mass_tonnes),
            "mass_pct": ing.mass_pct,
            "supplier": ing.supplier,
        })

    await db.commit()
    await db.refresh(product_batch)

    return BiocharProductBatchResponse(
        id=product_batch.id,
        organization_id=product_batch.organization_id,
        project_id=product_batch.project_id,
        formulation_id=product_batch.formulation_id,
        batch_number=product_batch.batch_number,
        production_date=product_batch.production_date,
        total_product_mass_tonnes=float(product_batch.total_product_mass_tonnes),
        biochar_mass_tonnes=float(product_batch.biochar_mass_tonnes),
        non_biochar_mass_tonnes=float(product_batch.non_biochar_mass_tonnes),
        packaging_type=product_batch.packaging_type,
        storage_location=product_batch.storage_location,
        qa_status=product_batch.qa_status,
        created_at=product_batch.created_at,
        allocations=allocations_out,
        non_biochar_ingredients=non_biochar_out,
    )


@router.get(
    "/product-batches",
    response_model=List[BiocharProductBatchResponse],
)
async def list_product_batches(
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists manufactured product batches with ingredient allocations."""
    from sqlalchemy.orm import selectinload
    stmt = (
        select(BiocharProductBatch)
        .options(
            selectinload(BiocharProductBatch.ingredient_allocations),
            selectinload(BiocharProductBatch.non_biochar_ingredients),
        )
        .order_by(BiocharProductBatch.production_date.desc())
    )
    if project_id:
        stmt = stmt.where(
            (BiocharProductBatch.project_id == project_id)
            | (BiocharProductBatch.project_id.is_(None))
        )
    elif current_user.role != "SUPER_ADMIN" and current_user.organization_id:
        stmt = stmt.where(BiocharProductBatch.organization_id == current_user.organization_id)

    res = await db.execute(stmt)
    batches = res.scalars().all()

    resp = []
    for b in batches:
        resp.append(
            BiocharProductBatchResponse(
                id=b.id,
                organization_id=b.organization_id,
                project_id=b.project_id,
                formulation_id=b.formulation_id,
                batch_number=b.batch_number,
                production_date=b.production_date,
                total_product_mass_tonnes=float(b.total_product_mass_tonnes),
                biochar_mass_tonnes=float(b.biochar_mass_tonnes),
                non_biochar_mass_tonnes=float(b.non_biochar_mass_tonnes),
                packaging_type=b.packaging_type,
                storage_location=b.storage_location,
                qa_status=b.qa_status,
                created_at=b.created_at,
                allocations=[
                    {
                        "allocation_id": str(a.id),
                        "biochar_batch_id": str(a.biochar_batch_id),
                        "allocated_biochar_mass_tonnes": float(a.allocated_biochar_mass_tonnes),
                    }
                    for a in b.ingredient_allocations
                ],
                non_biochar_ingredients=[
                    {
                        "ingredient_name": n.ingredient_name,
                        "ingredient_type": n.ingredient_type,
                        "mass_tonnes": float(n.mass_tonnes),
                        "mass_pct": n.mass_pct,
                        "supplier": n.supplier,
                    }
                    for n in b.non_biochar_ingredients
                ],
            )
        )
    return resp


# Include Puro.earth Biochar Edition 2025 V2 Methodology Router
from app.domains.biochar.puro_api import router as puro_router
router.include_router(puro_router)
