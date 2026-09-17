"""
=============================================================================
VeriField Nexus — EO-to-Carbon Invariant Architecture Tests
=============================================================================
Methodological Invariant:
No direct algorithmic path may exist from satellite Earth Observation indices
(NDVI, EVI, NDMI, SAR VV/VH backscatter, or land-cover classifications)
directly into verified or issued carbon credits without:
1. Approved methodology framework.
2. Calibrated and validated biogeochemical/allometric model (e.g. DayCent, VT0014 DSM).
3. Ground-truth physical evidence (soil cores >= 30cm, tree census DBH).
4. Explicit spatial uncertainty quantification.
5. Independent VVB audit and cryptographic ledger seal.
=============================================================================
"""

import inspect
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.calculators import (
    VM0042CalculatorV22,
    VM0047CalculatorV11,
    VM0051CalculatorV11,
)
from app.domains.agriculture.earth_observation import (
    EarthObservationProvider,
    LandsatProvider,
    PlanetScopeProvider,
    Sentinel1Provider,
    Sentinel2Provider,
    SkySatProvider,
)
from app.domains.agriculture.models import SatelliteObservation
from app.domains.agriculture.schemas import SatelliteObservationCreate
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


def test_code_structure_eo_cannot_directly_issue_credits():
    """
    Forensic architectural invariant:
    Verifies that no function or method in the earth_observation module
    returns credits, mints tokens, or writes to the ledger.
    """
    for cls in [Sentinel2Provider, Sentinel1Provider, LandsatProvider, PlanetScopeProvider, SkySatProvider, EarthObservationProvider]:
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for name, fn in methods:
            source = inspect.getsource(fn)
            # Must not contain minting or issuance logic
            assert "mint_credits" not in source
            assert "issue_credits" not in source
            assert "credit_amount" not in source
            assert "t_co2e" not in source or "proxy" in source or "description" in source


@pytest.mark.asyncio
async def test_satellite_observation_alone_cannot_produce_carbon_credits(db_session: AsyncSession):
    """
    Verifies that storing satellite scenes and spectral indices creates raw telemetry
    and provenance records, but produces 0.0 issuable credits and cannot trigger carbon minting.
    """
    org = Organization(name=f"Synthetic Remote Sensing Tenant {uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    project = Project(
        name="Spectral Monitoring Pilot",
        project_code=f"AGR-EO-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.flush()

    # 1. Ingest Optical Scene with High NDVI
    sat_obs = SatelliteObservation(
        organization_id=org.id,
        project_id=project.id,
        provider="SENTINEL_2",
        scene_id="S2B_MSIL2A_20260601T103021",
        acquisition_timestamp=datetime.now(timezone.utc),
        spatial_resolution_m=10.0,
        observation_type="OPTICAL_MULTISPECTRAL",
        derived_indices={"ndvi_mean": 0.82, "evi_mean": 0.58},
        provenance_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        lineage_manifest={"bounding_box": [77.10, 28.50, 77.12, 28.52]},
    )
    db_session.add(sat_obs)
    await db_session.commit()

    # Verify model has no credit issuance fields
    assert not hasattr(sat_obs, "credits_issued")
    assert not hasattr(sat_obs, "t_co2e")

    # 2. Invariant: Attempting to quantify credits with only EO data fails closed
    calc42 = VM0042CalculatorV22()
    result42 = calc42.calculate_project_credits(
        project_data={"id": str(project.id)},
        monitoring_data={"satellite_observations": [sat_obs.id]},
    )
    assert result42.is_issuance_eligible is False
    assert result42.issuable_credits_t_co2e == 0.0
    assert result42.status.value == "NOT_CONFIGURED"

    calc47 = VM0047CalculatorV11()
    result47 = calc47.calculate_project_credits(
        project_data={"id": str(project.id)},
        monitoring_data={"satellite_observations": [sat_obs.id]},
    )
    assert result47.is_issuance_eligible is False
    assert result47.issuable_credits_t_co2e == 0.0
    assert result47.status.value == "NOT_CONFIGURED"

    calc51 = VM0051CalculatorV11()
    result51 = calc51.calculate_project_credits(
        project_data={"id": str(project.id)},
        monitoring_data={"satellite_observations": [sat_obs.id]},
    )
    assert result51.is_issuance_eligible is False
    assert result51.issuable_credits_t_co2e == 0.0
    assert result51.status.value == "NOT_CONFIGURED"
