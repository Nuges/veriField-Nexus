"""
=============================================================================
VeriField Nexus — Carbon Sink Module API Routes
=============================================================================
Endpoints for Artisan profiles, Kiln dimensions, Biomass parameters,
pyrolysis Batches, QR bindings, C-Sink aggregation and CSI registry synchronization.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.models.carbon_sink import (
    ArtisanProfile, KilnProfile, BiomassProfile, BiocharBatch, QrRecord, CSinkUnit, CSinkTransaction
)
from app.models.activity import Activity
from app.models.project import Project
from app.services.csi_validation import validate_csi_plausibility
from app.services.csi_service import CSIRegistryService # We will build this next

router = APIRouter(prefix="/csink", tags=["C-Sink Module"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ArtisanCreate(BaseModel):
    name: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    kiln_type: str = Field(..., max_length=100)
    proficiency_passed: bool = Field(False)
    volume_measuring_device_m3: float = Field(0.0, ge=0.0)
    client_id: Optional[str] = Field(None, max_length=36)
    gps: Optional[Dict[str, float]] = None
    evidence_links: Optional[Dict[str, str]] = None


class KilnCreate(BaseModel):
    artisan_id: uuid.UUID
    serial_number: str = Field(..., max_length=100)
    surface_area_m2: float = Field(..., gt=0.0)
    depth_m: float = Field(..., gt=0.0)
    capacity_m3: float = Field(..., gt=0.0)
    methane_emission_factor: float = Field(0.0, ge=0.0)
    client_id: Optional[str] = Field(None, max_length=36)
    gps: Optional[Dict[str, float]] = None
    evidence_links: Optional[Dict[str, str]] = None


class BiomassCreate(BaseModel):
    name: str = Field(..., max_length=255)
    mixing_ratio: str = Field(..., max_length=100)
    carbon_content_pct: float = Field(..., ge=0.0, le=100.0)
    bulk_density_g_cm3: float = Field(..., gt=0.0)
    methane_compensation_scheme: str = Field(..., max_length=100)
    client_id: Optional[str] = Field(None, max_length=36)
    gps: Optional[Dict[str, float]] = None
    evidence_links: Optional[Dict[str, str]] = None


class BatchCreate(BaseModel):
    kiln_id: uuid.UUID
    biomass_id: uuid.UUID
    batch_number: str = Field(..., max_length=100)
    quantity_kg: float = Field(..., gt=0.0)
    produced_at: datetime
    lab_report_url: Optional[str] = Field(None, max_length=500)
    client_id: Optional[str] = Field(None, max_length=36)
    gps: Optional[Dict[str, float]] = None
    evidence_links: Optional[Dict[str, str]] = None


class QrLinkRequest(BaseModel):
    qr_id: str = Field(..., max_length=100)
    batch_id: uuid.UUID


class BundleCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    project_id: uuid.UUID
    activity_ids: List[uuid.UUID]


class ParameterUpdateRequest(BaseModel):
    value: float
    description: Optional[str] = None
    source_reference: Optional[str] = None


# ---------------------------------------------------------------------------
# Artisan Profiles Endpoints
# ---------------------------------------------------------------------------

@router.post("/artisans", response_model=Dict[str, Any], summary="Register an Artisan Profile")
async def create_artisan(payload: ArtisanCreate, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    artisan = ArtisanProfile(**payload.model_dump())
    db.add(artisan)
    await db.commit()
    await db.refresh(artisan)
    return {"id": artisan.id, "name": artisan.name, "kiln_type": artisan.kiln_type}


@router.get("/artisans", response_model=List[Dict[str, Any]], summary="List Artisan Profiles")
async def get_artisans(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    result = await db.execute(select(ArtisanProfile).order_by(ArtisanProfile.name.asc()))
    artisans = result.scalars().all()
    return [
        {
            "id": a.id, "name": a.name, "phone": a.phone, "kiln_type": a.kiln_type,
            "proficiency_passed": a.proficiency_passed, "volume_measuring_device_m3": a.volume_measuring_device_m3
        } for a in artisans
    ]


# ---------------------------------------------------------------------------
# Kiln Profiles Endpoints
# ---------------------------------------------------------------------------

@router.post("/kilns", response_model=Dict[str, Any], summary="Register a Kiln Profile")
async def create_kiln(payload: KilnCreate, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    kiln = KilnProfile(**payload.model_dump())
    db.add(kiln)
    try:
        await db.commit()
        await db.refresh(kiln)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create kiln (serial_number duplicate?): {e}")
    return {"id": kiln.id, "serial_number": kiln.serial_number, "capacity_m3": kiln.capacity_m3}


@router.get("/kilns", response_model=List[Dict[str, Any]], summary="List Kiln Profiles")
async def get_kilns(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    result = await db.execute(select(KilnProfile).order_by(KilnProfile.serial_number.asc()))
    kilns = result.scalars().all()
    return [
        {
            "id": k.id, "artisan_id": k.artisan_id, "serial_number": k.serial_number,
            "surface_area_m2": k.surface_area_m2, "depth_m": k.depth_m, "capacity_m3": k.capacity_m3,
            "methane_emission_factor": k.methane_emission_factor
        } for k in kilns
    ]


# ---------------------------------------------------------------------------
# Biomass Feedstock Profiles Endpoints
# ---------------------------------------------------------------------------

@router.post("/biomass", response_model=Dict[str, Any], summary="Register a Biomass Profile")
async def create_biomass(payload: BiomassCreate, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    biom = BiomassProfile(**payload.model_dump())
    db.add(biom)
    await db.commit()
    await db.refresh(biom)
    return {"id": biom.id, "name": biom.name, "carbon_content_pct": biom.carbon_content_pct}


@router.get("/biomass", response_model=List[Dict[str, Any]], summary="List Biomass Feedstock Profiles")
async def get_biomass(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    result = await db.execute(select(BiomassProfile).order_by(BiomassProfile.name.asc()))
    biomasses = result.scalars().all()
    return [
        {
            "id": b.id, "name": b.name, "mixing_ratio": b.mixing_ratio,
            "carbon_content_pct": b.carbon_content_pct, "bulk_density_g_cm3": b.bulk_density_g_cm3,
            "methane_compensation_scheme": b.methane_compensation_scheme
        } for b in biomasses
    ]


# ---------------------------------------------------------------------------
# Biochar Production Batches Endpoints
# ---------------------------------------------------------------------------

@router.post("/batches", response_model=Dict[str, Any], summary="Log a Biochar Pyrolysis Batch")
async def create_batch(payload: BatchCreate, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    batch = BiocharBatch(**payload.model_dump())
    db.add(batch)
    try:
        await db.commit()
        await db.refresh(batch)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to log batch (batch_number duplicate?): {e}")
    return {"id": batch.id, "batch_number": batch.batch_number, "quantity_kg": batch.quantity_kg}


@router.get("/batches", response_model=List[Dict[str, Any]], summary="List Biochar Pyrolysis Batches")
async def get_batches(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    result = await db.execute(
        select(BiocharBatch)
        .options(selectinload(BiocharBatch.kiln), selectinload(BiocharBatch.biomass))
        .order_by(BiocharBatch.batch_number.asc())
    )
    batches = result.scalars().all()
    return [
        {
            "id": b.id, 
            "batch_number": b.batch_number, 
            "quantity_kg": b.quantity_kg,
            "produced_at": b.produced_at.isoformat() if b.produced_at else None,
            "kiln_serial": b.kiln.serial_number if b.kiln else "Unknown",
            "biomass_name": b.biomass.name if b.biomass else "Unknown"
        } for b in batches
    ]


# ---------------------------------------------------------------------------
# EBC/WBC QR-Link Registration
# ---------------------------------------------------------------------------

@router.post("/qr-link", response_model=Dict[str, Any], summary="Bind QR Code ID to Biochar Batch")
async def link_qr_to_batch(payload: QrLinkRequest, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    # Verify if batch exists
    batch_res = await db.execute(select(BiocharBatch).where(BiocharBatch.id == payload.batch_id))
    if not batch_res.scalar():
        raise HTTPException(status_code=404, detail="Target biochar batch not found.")

    qr_record = QrRecord(
        qr_id=payload.qr_id,
        batch_id=payload.batch_id,
        verification_status="verified"
    )
    db.add(qr_record)
    try:
        await db.commit()
        await db.refresh(qr_record)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"QR ID '{payload.qr_id}' is already registered or invalid: {e}")

    return {"status": "linked", "qr_id": qr_record.qr_id, "batch_id": qr_record.batch_id}


# ---------------------------------------------------------------------------
# C-Sink Bundling Engine & Registry Synchronization
# ---------------------------------------------------------------------------

@router.post("/bundles", response_model=Dict[str, Any], summary="Create C-Sink Unit Bundle")
async def create_bundle(payload: BundleCreateRequest, db: AsyncSession = Depends(get_db), user = Depends(require_admin)):
    # 1. Verify project
    proj_res = await db.execute(select(Project).where(Project.id == payload.project_id))
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 2. Query all activities
    act_res = await db.execute(select(Activity).where(Activity.id.in_(payload.activity_ids)))
    activities = act_res.scalars().all()
    if len(activities) != len(payload.activity_ids):
        raise HTTPException(status_code=400, detail="One or more specified activities do not exist.")

    # 3. Apply Bundling Homogeneity Rules
    if not activities:
        raise HTTPException(status_code=400, detail="Bundle cannot be empty.")

    # Sample baseline from the first activity
    first_act = activities[0]
    if first_act.activity_type != "BIOCHAR_C_SINK":
        raise HTTPException(status_code=400, detail="Only BIOCHAR_C_SINK activities can be bundled into C-Sink Units.")

    c_content = first_act.activity_data.get("lab_carbon_content_pct")
    biomass = first_act.activity_data.get("biomass_id")
    kiln = first_act.activity_data.get("kiln_id")
    matrix = first_act.activity_data.get("application_matrix")

    for act in activities:
        if act.activity_type != "BIOCHAR_C_SINK":
            raise HTTPException(status_code=400, detail="Bundle contains heterogeneous activity types.")
        
        act_data = act.activity_data or {}
        
        # Verify carbon content within +/- 1% range
        act_c = act_data.get("lab_carbon_content_pct")
        if act_c is None or abs(act_c - c_content) > 1.0:
            raise HTTPException(
                status_code=400, 
                detail=f"Heterogeneous Carbon Content: Activity {act.id} has {act_c}%, expected near {c_content}%."
            )
            
        # Verify biomass feedstock
        if act_data.get("biomass_id") != biomass:
            raise HTTPException(status_code=400, detail="Heterogeneous biomass feedstocks detected in bundle.")
            
        # Verify technology
        if act_data.get("kiln_id") != kiln:
            raise HTTPException(status_code=400, detail="Heterogeneous kiln technologies detected in bundle.")
            
        # Verify application matrix
        if act_data.get("application_matrix") != matrix:
            raise HTTPException(status_code=400, detail="Heterogeneous application matrices detected in bundle.")

    # 4. Calculate total carbon offset (tCO2e)
    # Simple biochar C-sink formula:
    # CO2e (t) = weight (kg) * (carbon_content % / 100) * (3.67 multiplier for C to CO2) * (1 - moisture %) * security_margin / 1000
    # Let's read constants from csi_parameters table (defaulting if query fails)
    from sqlalchemy import text
    margin = 0.90
    try:
        margin_res = await db.execute(text("SELECT value FROM csi_parameters WHERE id = 'margin_of_security'"))
        val = margin_res.scalar()
        if val is not None:
            margin = val
    except Exception:
        pass

    total_weight_kg = 0.0
    for act in activities:
        weight = float(act.activity_data.get("batch_weight_kg", 0.0))
        moisture = float(act.activity_data.get("moisture_content_pct", 0.0)) / 100.0
        c_pct = float(act.activity_data.get("lab_carbon_content_pct", 0.0)) / 100.0
        
        # Formula: kg_biochar * C_pct * 3.67 * (1 - moisture) * security_margin / 1000
        co2e = weight * c_pct * 3.67 * (1 - moisture) * margin / 1000.0
        total_weight_kg += weight

    # Calculate aggregate tCO2e
    c_content_val = float(c_content)
    total_co2e = total_weight_kg * (c_content_val / 100.0) * 3.67 * 0.85 * margin / 1000.0 # moisture fallback

    # Rule: Minimum >= 1 tCO2e
    if total_co2e < 1.0:
        raise HTTPException(
            status_code=400, 
            detail=f"Aggregate bundle weight ({total_co2e:.3f} tCO2e) falls below the CSI minimum threshold of 1.0 tCO2e."
        )

    # 5. Save the C-Sink Unit
    bundle = CSinkUnit(
        name=payload.name,
        total_co2e_t=total_co2e,
        carbon_content_pct=c_content_val,
        biomass_type=str(biomass),
        pyrolysis_technology=str(kiln),
        matrix_category=str(matrix),
        project_id=payload.project_id,
        gps={"latitude": first_act.latitude, "longitude": first_act.longitude}
    )
    db.add(bundle)
    await db.commit()
    await db.refresh(bundle)

    # Link the activities to this C-Sink Unit
    for act in activities:
        act.c_sink_unit_id = bundle.id
    await db.commit()

    return {
        "bundle_id": bundle.id, 
        "name": bundle.name, 
        "total_co2e_t": round(bundle.total_co2e_t, 4), 
        "payload_size": len(activities)
    }


@router.post("/sync-registry/{bundle_id}", summary="Submit Bundle transactions to CSI Registry")
async def sync_bundle_to_registry(bundle_id: uuid.UUID, db: AsyncSession = Depends(get_db), user = Depends(require_admin)):
    # 1. Fetch bundle
    bundle_res = await db.execute(
        select(CSinkUnit)
        .options(selectinload(CSinkUnit.transactions))
        .where(CSinkUnit.id == bundle_id)
    )
    bundle = bundle_res.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found.")

    # 2. Check if already synced successfully
    already_success = any(tx.status == "SUCCESS" and tx.transaction_type == "SINK" for tx in bundle.transactions)
    if already_success:
        return {"status": "already_synced", "message": "This bundle is already fully synchronized with the CSI Registry."}

    # 3. Call the sync client service
    service = CSIRegistryService(db)
    result = await service.sync_bundle(bundle)
    
    if result["status"] == "failed":
        raise HTTPException(status_code=502, detail=result)
        
    return result


# ---------------------------------------------------------------------------
# Carbon Ledger (C-Sink Entries)
# ---------------------------------------------------------------------------

@router.get("/ledger", response_model=Dict[str, Any], summary="Get Carbon C-Sink Ledger")
async def get_csi_ledger(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    # Fetch all verified biochar application activities
    query = (
        select(Activity)
        .where(Activity.activity_type == "BIOCHAR_C_SINK")
        .where(Activity.status == "verified")
        .order_by(Activity.created_at.desc())
    )
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # Calculate carbon credits dynamically for ledger view
    ledger_data = []
    margin = 0.90
    try:
        margin_res = await db.execute(text("SELECT value FROM csi_parameters WHERE id = 'margin_of_security'"))
        val = margin_res.scalar()
        if val is not None:
            margin = val
    except Exception:
        pass

    for act in activities:
        act_data = act.activity_data or {}
        weight = float(act_data.get("batch_weight_kg", 0.0))
        moisture = float(act_data.get("moisture_content_pct", 0.0)) / 100.0
        c_pct = float(act_data.get("lab_carbon_content_pct", 0.0)) / 100.0
        
        # Formula: kg_biochar * C_pct * 3.67 * (1 - moisture) * security_margin / 1000
        co2e = weight * c_pct * 3.67 * (1 - moisture) * margin / 1000.0
        
        # Check sync status if bundled
        sync_status = "unbundled"
        registry_tx_id = None
        bundle_name = None
        if act.c_sink_unit_id:
            tx_res = await db.execute(
                select(CSinkTransaction)
                .where(CSinkTransaction.c_sink_unit_id == act.c_sink_unit_id)
                .where(CSinkTransaction.transaction_type == "SINK")
            )
            sink_tx = tx_res.scalars().first()
            if sink_tx:
                sync_status = sink_tx.status
                registry_tx_id = sink_tx.registry_tx_id
            else:
                sync_status = "bundled"

            unit_res = await db.execute(
                select(CSinkUnit).where(CSinkUnit.id == act.c_sink_unit_id)
            )
            unit = unit_res.scalar_one_or_none()
            if unit:
                bundle_name = unit.name
        
        ledger_data.append({
            "id": act.id,
            "activity_type": act.activity_type,
            "tco2e_generated": round(co2e, 4),
            "methodology_used": "CSI Global Artisan C-Sink Standard v2.1",
            "status": "verified",
            "captured_at": act.captured_at.isoformat() if act.captured_at else None,
            "client_id": act.client_id,
            "bundle_id": act.c_sink_unit_id,
            "bundle_name": bundle_name,
            "application_matrix": act_data.get("application_matrix"),
            "qr_id": act_data.get("qr_id"),
            "sync_status": sync_status,
            "registry_tx_id": registry_tx_id,
        })

    return {
        "data": ledger_data,
        "total_records": len(ledger_data)
    }


# ---------------------------------------------------------------------------
# CSI Emission Factors & Parameters Ledger
# ---------------------------------------------------------------------------

@router.get("/parameters", response_model=List[Dict[str, Any]], summary="Get CSI Versioned Parameters")
async def get_csi_parameters(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    result = await db.execute(text("SELECT id, value, description, source_reference, updated_at FROM csi_parameters ORDER BY id ASC"))
    rows = result.fetchall()
    return [
        {
            "id": r[0], "value": r[1], "description": r[2], 
            "source_reference": r[3], "updated_at": r[4].isoformat() if r[4] else None
        } for r in rows
    ]


@router.post("/parameters/{param_id}", response_model=Dict[str, Any], summary="Update CSI Parameter (Admin Only)")
async def update_csi_parameter(param_id: str, payload: ParameterUpdateRequest, db: AsyncSession = Depends(get_db), user = Depends(require_admin)):
    # Verify if exists
    exists_res = await db.execute(text("SELECT 1 FROM csi_parameters WHERE id = :id"), {"id": param_id})
    if not exists_res.scalar():
        raise HTTPException(status_code=404, detail=f"Parameter '{param_id}' not found.")

    # Prepare update query
    query = "UPDATE csi_parameters SET value = :value, updated_at = now()"
    params = {"value": payload.value, "id": param_id}
    
    if payload.description is not None:
        query += ", description = :description"
        params["description"] = payload.description
    if payload.source_reference is not None:
        query += ", source_reference = :source_reference"
        params["source_reference"] = payload.source_reference
        
    query += " WHERE id = :id"
    
    await db.execute(text(query), params)
    await db.commit()
    return {"status": "updated", "id": param_id, "value": payload.value}
