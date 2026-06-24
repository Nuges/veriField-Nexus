"""
=============================================================================
VeriField Nexus — CSI Plausibility & Validation Engine
=============================================================================
Provides deterministic data quality and compliance checking for biochar
C-sink activities, ensuring alignment with Carbon Standards International
standards before ledger registration.
=============================================================================
"""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.carbon_sink import KilnProfile, BiomassProfile


async def validate_csi_plausibility(
    activity_data: dict, 
    latitude: float, 
    longitude: float, 
    db: AsyncSession
) -> dict:
    """
    Validates biochar application activity data against CSI criteria:
    1. H/C ratio < 0.7 (measure of biochar stability)
    2. Carbon content between 50.0% and 98.0%
    3. GPS accuracy & precision (minimum of 5 decimal places)
    4. Reported yield vs physical capacity limits of the kiln (with a 20% buffer)
    5. Application matrix verification against positive lists
    
    Returns:
        dict: {"status": "success"/"failed", "errors": [list of error messages]}
    """
    errors = []

    # 1. Enforce H/C ratio constraint
    hc_ratio = activity_data.get("lab_hc_ratio")
    if hc_ratio is not None:
        try:
            hc_val = float(hc_ratio)
            if hc_val >= 0.7:
                errors.append(f"H/C ratio ({hc_val}) exceeds the CSI maximum limit of 0.7.")
        except (ValueError, TypeError):
            errors.append("Invalid H/C ratio format.")
    else:
        errors.append("H/C ratio is required.")

    # 2. Check carbon content bounds
    carbon_pct = activity_data.get("lab_carbon_content_pct")
    if carbon_pct is not None:
        try:
            c_val = float(carbon_pct)
            if not (50.0 <= c_val <= 98.0):
                errors.append(f"Carbon content ({c_val}%) lies outside the permissible CSI range (50%-98%).")
        except (ValueError, TypeError):
            errors.append("Invalid carbon content format.")
    else:
        errors.append("Carbon content is required.")

    # 3. GPS Decimal Precision validation
    for coord, val in [("latitude", latitude), ("longitude", longitude)]:
        if val is not None:
            # Check string representation for decimal precision
            val_str = f"{val:.15f}".rstrip('0')
            decimal_part = val_str.split('.')[-1] if '.' in val_str else ''
            
            raw_str = str(val)
            raw_decimal = raw_str.split('.')[-1] if '.' in raw_str else ''
            
            if len(decimal_part) < 5 and len(raw_decimal) < 5:
                errors.append(f"GPS {coord} must have at least 5 decimal places for audit accuracy.")
        else:
            errors.append(f"GPS {coord} is required.")

    # 4. Production vs. Capacity check
    kiln_id_str = activity_data.get("kiln_id")
    batch_weight = activity_data.get("batch_weight_kg")
    if kiln_id_str and batch_weight is not None:
        try:
            kiln_uuid = uuid.UUID(str(kiln_id_str))
            result = await db.execute(select(KilnProfile).where(KilnProfile.id == kiln_uuid))
            kiln = result.scalar_one_or_none()
            if kiln:
                # Query biomass profile to retrieve bulk density
                biomass_id_str = activity_data.get("biomass_id")
                bulk_density = 0.25 # Default 250 kg/m3 bulk density
                
                if biomass_id_str:
                    biom_uuid = uuid.UUID(str(biomass_id_str))
                    biom_res = await db.execute(select(BiomassProfile).where(BiomassProfile.id == biom_uuid))
                    biomass = biom_res.scalar_one_or_none()
                    if biomass:
                        bulk_density = biomass.bulk_density_g_cm3
                
                # Max raw biomass hold capacity (m3 * bulk density * 1000 = kg)
                max_hold_capacity = kiln.capacity_m3 * bulk_density * 1000
                weight_val = float(batch_weight)
                
                # Check if reported yield exceeds 120% of kiln physical volume capacity
                if weight_val > (max_hold_capacity * 1.2):
                    errors.append(
                        f"Reported yield ({weight_val} kg) exceeds physical capacity limit of the kiln "
                        f"({max_hold_capacity:.1f} kg)."
                    )
            else:
                errors.append(f"Referenced kiln profile '{kiln_id_str}' does not exist.")
        except ValueError:
            errors.append("Invalid Kiln UUID or weight format.")
    else:
        errors.append("Both kiln_id and batch_weight_kg are required for capacity checking.")

    # 5. Positive matrix list check
    matrix = activity_data.get("application_matrix")
    allowed_matrices = ["soil_amendment", "compost_additive", "concrete_admixture", "animal_feed", "biomaterial"]
    if matrix:
        if matrix not in allowed_matrices:
            errors.append(f"Application matrix '{matrix}' is not on the CSI positive list of permissible matrices.")
    else:
        errors.append("Application matrix is required.")

    status = "failed" if errors else "success"
    return {"status": status, "errors": errors}
