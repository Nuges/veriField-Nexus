"""
=============================================================================
VeriField Nexus — CSI Validation Engine Tests
=============================================================================
Validates:
  1. H/C ratio constraint validation (< 0.7).
  2. GPS decimal precision requirement (>= 5 decimal places).
  3. Positive list matrix validation.
  4. Reported yield vs physical kiln capacity checking.
=============================================================================
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.services.csi_validation import validate_csi_plausibility
from app.models.carbon_sink import KilnProfile, BiomassProfile


@pytest.mark.anyio
async def test_hc_ratio_blocking():
    db = AsyncMock()
    
    # Valid base activity data
    valid_data = {
        "lab_hc_ratio": 0.5,
        "lab_carbon_content_pct": 75.0,
        "kiln_id": str(uuid.uuid4()),
        "biomass_id": str(uuid.uuid4()),
        "batch_weight_kg": 100.0,
        "application_matrix": "soil_amendment"
    }
    
    # Mock database to return a kiln and a biomass profile
    kiln = KilnProfile(capacity_m3=2.0)
    biomass = BiomassProfile(bulk_density_g_cm3=0.25)
    
    async def mock_execute(query):
        mock_res = MagicMock()
        if "kiln_profiles" in str(query):
            mock_res.scalar_one_or_none.return_value = kiln
        elif "biomass_profiles" in str(query):
            mock_res.scalar_one_or_none.return_value = biomass
        return mock_res
        
    db.execute.side_effect = mock_execute

    # Case 1: H/C ratio too high
    invalid_data = valid_data.copy()
    invalid_data["lab_hc_ratio"] = 0.75
    res = await validate_csi_plausibility(invalid_data, 6.52441, 3.37921, db)
    assert res["status"] == "failed"
    assert any("exceeds the CSI maximum limit" in e for e in res["errors"])

    # Case 2: H/C ratio valid
    res = await validate_csi_plausibility(valid_data, 6.52441, 3.37921, db)
    assert res["status"] == "success"
    assert len(res["errors"]) == 0


@pytest.mark.anyio
async def test_gps_precision_blocking():
    db = AsyncMock()
    valid_data = {
        "lab_hc_ratio": 0.5,
        "lab_carbon_content_pct": 75.0,
        "kiln_id": str(uuid.uuid4()),
        "biomass_id": str(uuid.uuid4()),
        "batch_weight_kg": 100.0,
        "application_matrix": "soil_amendment"
    }
    
    kiln = KilnProfile(capacity_m3=2.0)
    biomass = BiomassProfile(bulk_density_g_cm3=0.25)
    
    async def mock_execute(query):
        mock_res = MagicMock()
        if "kiln_profiles" in str(query):
            mock_res.scalar_one_or_none.return_value = kiln
        elif "biomass_profiles" in str(query):
            mock_res.scalar_one_or_none.return_value = biomass
        return mock_res
    db.execute.side_effect = mock_execute

    # Case 1: GPS with < 5 decimal places
    res = await validate_csi_plausibility(valid_data, 6.52, 3.379, db)
    assert res["status"] == "failed"
    assert any("must have at least 5 decimal places" in e for e in res["errors"])

    # Case 2: GPS with >= 5 decimal places
    res = await validate_csi_plausibility(valid_data, 6.52441, 3.37921, db)
    assert res["status"] == "success"


@pytest.mark.anyio
async def test_application_matrix_blocking():
    db = AsyncMock()
    valid_data = {
        "lab_hc_ratio": 0.5,
        "lab_carbon_content_pct": 75.0,
        "kiln_id": str(uuid.uuid4()),
        "biomass_id": str(uuid.uuid4()),
        "batch_weight_kg": 100.0,
        "application_matrix": "soil_amendment"
    }
    
    kiln = KilnProfile(capacity_m3=2.0)
    biomass = BiomassProfile(bulk_density_g_cm3=0.25)
    
    async def mock_execute(query):
        mock_res = MagicMock()
        if "kiln_profiles" in str(query):
            mock_res.scalar_one_or_none.return_value = kiln
        elif "biomass_profiles" in str(query):
            mock_res.scalar_one_or_none.return_value = biomass
        return mock_res
    db.execute.side_effect = mock_execute

    # Case 1: Invalid matrix type
    invalid_data = valid_data.copy()
    invalid_data["application_matrix"] = "open_air_combustion"
    res = await validate_csi_plausibility(invalid_data, 6.52441, 3.37921, db)
    assert res["status"] == "failed"
    assert any("not on the CSI positive list" in e for e in res["errors"])

    # Case 2: Valid matrix type
    res = await validate_csi_plausibility(valid_data, 6.52441, 3.37921, db)
    assert res["status"] == "success"


@pytest.mark.anyio
async def test_kiln_capacity_blocking():
    db = AsyncMock()
    
    # Kiln capacity = 1.0 m3, Biomass bulk density = 0.20 g/cm3 (200 kg/m3)
    # Physical capacity limit = 1.0 * 200 = 200 kg.
    # 120% capacity = 240 kg.
    kiln = KilnProfile(capacity_m3=1.0)
    biomass = BiomassProfile(bulk_density_g_cm3=0.20)
    
    async def mock_execute(query):
        mock_res = MagicMock()
        if "kiln_profiles" in str(query):
            mock_res.scalar_one_or_none.return_value = kiln
        elif "biomass_profiles" in str(query):
            mock_res.scalar_one_or_none.return_value = biomass
        return mock_res
    db.execute.side_effect = mock_execute

    valid_data = {
        "lab_hc_ratio": 0.5,
        "lab_carbon_content_pct": 75.0,
        "kiln_id": str(uuid.uuid4()),
        "biomass_id": str(uuid.uuid4()),
        "batch_weight_kg": 200.0, # Within 120% limit
        "application_matrix": "soil_amendment"
    }

    # Case 1: Within limit
    res = await validate_csi_plausibility(valid_data, 6.52441, 3.37921, db)
    assert res["status"] == "success"

    # Case 2: Exceeding 120% of capacity (250 kg)
    invalid_data = valid_data.copy()
    invalid_data["batch_weight_kg"] = 250.0
    res = await validate_csi_plausibility(invalid_data, 6.52441, 3.37921, db)
    assert res["status"] == "failed"
    assert any("exceeds physical capacity limit" in e for e in res["errors"])
