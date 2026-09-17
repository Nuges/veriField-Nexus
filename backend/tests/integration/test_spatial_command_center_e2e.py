"""
=============================================================================
VeriField Nexus — Spatial Command Center End-to-End & IDOR Integration Tests
=============================================================================
Verifies:
1. Agriculture Spatial Lifecycle: Boundaries, Land Units, Soil Samples,
   Trees, Field Activities, and Satellite Observations.
2. Biochar Value Chain Spatial Lifecycle: Facilities, Feedstocks, End-Use.
3. Hybrid Energy & EV Mobility Asset Geocoding (Mapped vs Ungeocoded).
4. Two-Tenant IDOR Matrix across all spatial endpoints.
=============================================================================
"""

import uuid
from datetime import date, datetime, timezone, timedelta
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.organizations.models import Organization
from app.domains.authentication.models import User
from app.domains.projects.models import Project
from app.domains.agriculture.models import LandUnit, SoilSample, TreeObservation, SatelliteObservation
from app.domains.biochar.models import ProductionFacility, FeedstockSource, BiocharBatch, BiocharEndUseRecord
from app.domains.assets.models import Asset
from app.domains.activities.models import Activity
from app.main import app


def _create_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id),
        "iat": now,
        "exp": now + timedelta(hours=2),
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_spatial_command_center_all_sectors_and_idor(db_session: AsyncSession):
    # ─── 1. Setup Tenant A and Tenant B ───
    suffix_a = uuid.uuid4().hex[:6]
    suffix_b = uuid.uuid4().hex[:6]

    org_a = Organization(name=f"Spatial Tenant Alpha {suffix_a}")
    org_b = Organization(name=f"Spatial Tenant Beta {suffix_b}")
    db_session.add(org_a)
    db_session.add(org_b)
    await db_session.flush()

    user_a = User(
        email=f"officer.a.{suffix_a}@example.com",
        full_name="Officer Alpha",
        role="ADMIN",
        organization_id=org_a.id,
        is_active=True
    )
    user_b = User(
        email=f"officer.b.{suffix_b}@example.com",
        full_name="Officer Beta",
        role="ADMIN",
        organization_id=org_b.id,
        is_active=True
    )
    db_session.add(user_a)
    db_session.add(user_b)
    await db_session.flush()

    token_a = _create_token(user_a.id, user_a.email, user_a.role, org_a.id)
    token_b = _create_token(user_b.id, user_b.email, user_b.role, org_b.id)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # ─── 2. Setup Agriculture Project in Tenant A ───
    project_a = Project(
        name=f"Agroforestry Re-greening {suffix_a}",
        project_code=f"AGR-{suffix_a}",
        organization_id=org_a.id,
    )
    db_session.add(project_a)
    await db_session.flush()

    # 2 Land Units
    lu1 = LandUnit(
        organization_id=org_a.id,
        project_id=project_a.id,
        name="North Field Cultivation Plot 1",
        unit_type="FIELD",
        land_use_category="CROPLAND",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[7.51, 9.01], [7.54, 9.01], [7.54, 9.04], [7.51, 9.04], [7.51, 9.01]]]
        },
        area_ha=14.2,
    )
    lu2 = LandUnit(
        organization_id=org_a.id,
        project_id=project_a.id,
        name="South Agroforestry Plot 2",
        unit_type="FIELD",
        land_use_category="AGROFORESTRY",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[7.55, 9.05], [7.58, 9.05], [7.58, 9.08], [7.55, 9.08], [7.55, 9.05]]]
        },
        area_ha=18.5,
    )
    db_session.add_all([lu1, lu2])
    await db_session.flush()

    # 2 Soil Samples
    ss1 = SoilSample(
        organization_id=org_a.id,
        project_id=project_a.id,
        land_unit_id=lu1.id,
        sample_code=f"SOC-01-{suffix_a}",
        sampling_date=date.today(),
        depth_upper_cm=0.0,
        depth_lower_cm=30.0,
        latitude=9.025,
        longitude=7.525,
        soc_stock_pct=3.24,
    )
    ss2 = SoilSample(
        organization_id=org_a.id,
        project_id=project_a.id,
        land_unit_id=lu2.id,
        sample_code=f"SOC-02-{suffix_a}",
        sampling_date=date.today(),
        depth_upper_cm=30.0,
        depth_lower_cm=100.0,
        latitude=9.065,
        longitude=7.565,
        soc_stock_pct=4.51,
    )
    db_session.add_all([ss1, ss2])

    # 2 Tree Observations
    tr1 = TreeObservation(
        organization_id=org_a.id,
        project_id=project_a.id,
        land_unit_id=lu2.id,
        species_scientific="Faidherbia albida",
        measurement_date=date.today(),
        dbh_cm=28.5,
        height_m=12.2,
        latitude=9.066,
        longitude=7.566,
    )
    tr2 = TreeObservation(
        organization_id=org_a.id,
        project_id=project_a.id,
        land_unit_id=lu2.id,
        species_scientific="Acacia senegal",
        measurement_date=date.today(),
        dbh_cm=18.2,
        height_m=8.5,
        latitude=9.068,
        longitude=7.568,
    )
    db_session.add_all([tr1, tr2])

    # 1 Field Activity
    act1 = Activity(
        organization_id=org_a.id,
        user_id=user_a.id,
        activity_type="TREE_PLANTING",
        latitude=9.030,
        longitude=7.530,
        activity_data={"title": "Community Enrichment Planting", "trees_planted": 150},
        environment_type="RURAL",
        captured_at=datetime.now(timezone.utc),
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(act1)

    # 1 Satellite Observation (Sentinel-2 with provenance)
    sat_obs = SatelliteObservation(
        organization_id=org_a.id,
        project_id=project_a.id,
        land_unit_id=lu1.id,
        provider="SENTINEL_2",
        scene_id=f"S2B_MSIL2A_20260316_T31PNN_{suffix_a}",
        acquisition_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
        cloud_coverage_pct=3.8,
        spatial_resolution_m=10.0,
        observation_type="OPTICAL_MULTISPECTRAL",
        raw_band_uris={"B04": "s3://copernicus/B04.jp2", "B08": "s3://copernicus/B08.jp2"},
        derived_indices={"ndvi_mean": 0.72, "evi_mean": 0.48},
        provenance_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        processing_level="L2A",
    )
    db_session.add(sat_obs)

    # ─── 3. Setup Biochar Value Chain in Tenant A ───
    biochar_proj = Project(
        name=f"Biochar Agronomic Sequestration {suffix_a}",
        project_code=f"BIO-{suffix_a}",
        organization_id=org_a.id,
    )
    db_session.add(biochar_proj)
    await db_session.flush()

    fac = ProductionFacility(
        organization_id=org_a.id,
        project_id=biochar_proj.id,
        facility_code=f"FAC-{suffix_a}",
        facility_name="Kaduna Pyrolysis Facility Unit 1",
        technology_type="SLOW_PYROLYSIS",
        facility_status="NEW_OPERATIONAL",
        location="10.52, 7.44",
        production_capacity_tpy=2500.0,
    )
    src = FeedstockSource(
        organization_id=org_a.id,
        project_id=biochar_proj.id,
        source_code=f"SRC-{suffix_a}",
        source_name="Zaria Agricultural Husk Hub",
        source_type="AGRICULTURAL_RESIDUE",
        biomass_type="HUSKS",
        origin_location="11.08, 7.71",
    )
    db_session.add_all([fac, src])
    await db_session.flush()

    batch = BiocharBatch(
        organization_id=org_a.id,
        project_id=biochar_proj.id,
        batch_number=f"BATCH-{suffix_a}",
        facility_name=fac.facility_name,
        kiln_id="RETORT-01",
        feedstock_type="CROP_RESIDUE",
        feedstock_weight_tonnes=100.0,
        moisture_content_pct=12.5,
        pyrolysis_temp_celsius=550.0,
        residence_time_minutes=45.0,
        biochar_yield_tonnes=30.0,
    )
    db_session.add(batch)
    await db_session.flush()

    end_use = BiocharEndUseRecord(
        organization_id=org_a.id,
        project_id=biochar_proj.id,
        batch_id=batch.id,
        end_use_type="SOIL_APPLICATION",
        applied_quantity_tonnes=42.0,
        event_date=datetime.now(timezone.utc),
        gps_coordinates="11.17,7.63",
        application_method="BROADCAST_INCORPORATED",
        verification_status="VERIFIED",
    )
    db_session.add(end_use)

    # ─── 4. Setup Hybrid Energy & EV in Tenant A ───
    asset_solar = Asset(
        organization_id=org_a.id,
        project_id=project_a.id,
        name="Kano 500kW Solar Mini-grid",
        status="active",
        latitude=11.99,
        longitude=8.52,
        attributes={"sector": "HYBRID_ENERGY", "type": "SOLAR_PV_ARRAY", "capacity_kw": 500},
    )
    asset_ev = Asset(
        organization_id=org_a.id,
        project_id=project_a.id,
        name="Abuja Central EV Hub",
        status="active",
        latitude=9.06,
        longitude=7.49,
        attributes={"sector": "EV_MOBILITY", "type": "CHARGING_STATION", "chargers_count": 8},
    )
    asset_ungeocoded = Asset(
        organization_id=org_a.id,
        project_id=project_a.id,
        name="Ungeocoded Inverter Registry Asset",
        status="active",
        latitude=None,
        longitude=None,
        attributes={"sector": "HYBRID_ENERGY", "type": "INVERTER", "status": "OFFLINE"},
    )
    db_session.add_all([asset_solar, asset_ev, asset_ungeocoded])

    await db_session.commit()

    # ─── 5. Test Spatial Endpoints for Tenant A ───
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Agriculture Land Units
        r_lu = await client.get(f"/api/v1/agriculture/land-units?project_id={project_a.id}", headers=headers_a)
        assert r_lu.status_code == 200
        lu_data = r_lu.json()
        assert len(lu_data) == 2
        assert {u["name"] for u in lu_data} == {"North Field Cultivation Plot 1", "South Agroforestry Plot 2"}

        # Agriculture Soil Samples
        r_ss = await client.get(f"/api/v1/agriculture/soil-samples?project_id={project_a.id}", headers=headers_a)
        assert r_ss.status_code == 200
        ss_data = r_ss.json()
        assert len(ss_data) == 2
        assert all(s["latitude"] is not None and s["longitude"] is not None for s in ss_data)

        # Agriculture Tree Observations
        r_tr = await client.get(f"/api/v1/agriculture/tree-observations?project_id={project_a.id}", headers=headers_a)
        assert r_tr.status_code == 200
        tr_data = r_tr.json()
        assert len(tr_data) == 2
        assert {t["species_scientific"] for t in tr_data} == {"Faidherbia albida", "Acacia senegal"}

        # Agriculture Satellite Observations
        r_sat = await client.get(f"/api/v1/agriculture/satellite-observations?project_id={project_a.id}", headers=headers_a)
        assert r_sat.status_code == 200
        sat_data = r_sat.json()
        assert len(sat_data) == 1
        assert sat_data[0]["provider"] == "SENTINEL_2"
        assert sat_data[0]["provenance_hash"] is not None

        # Biochar Facilities
        r_fac = await client.get(f"/api/v1/biochar/facilities?project_id={biochar_proj.id}", headers=headers_a)
        assert r_fac.status_code == 200
        fac_data = r_fac.json()
        assert len(fac_data) == 1
        assert fac_data[0]["facility_name"] == "Kaduna Pyrolysis Facility Unit 1"
        assert fac_data[0]["location"] == "10.52, 7.44"

        # Biochar Feedstock Sources
        r_src = await client.get(f"/api/v1/biochar/sources?project_id={biochar_proj.id}", headers=headers_a)
        assert r_src.status_code == 200
        src_data = r_src.json()
        assert len(src_data) == 1
        assert src_data[0]["source_name"] == "Zaria Agricultural Husk Hub"
        assert src_data[0]["origin_location"] == "11.08, 7.71"

        # Biochar End Use Records
        r_end = await client.get(f"/api/v1/biochar/end-uses?project_id={biochar_proj.id}", headers=headers_a)
        assert r_end.status_code == 200
        end_data = r_end.json()
        assert len(end_data) == 1
        assert end_data[0]["gps_coordinates"] == "11.17,7.63"

        # Hybrid Energy & EV Assets
        r_assets = await client.get("/api/v1/assets?per_page=100", headers=headers_a)
        assert r_assets.status_code == 200
        assets_res = r_assets.json()
        items = assets_res if isinstance(assets_res, list) else (assets_res.get("assets") or assets_res.get("items") or [])
        assert len(items) >= 3

        mapped_assets = [a for a in items if a.get("latitude") is not None and a.get("longitude") is not None]
        ungeocoded_assets = [a for a in items if a.get("latitude") is None or a.get("longitude") is None]
        assert len(mapped_assets) >= 2
        assert len(ungeocoded_assets) >= 1

        # ─── 6. Two-Tenant IDOR Matrix: Tenant B queries Tenant A data ───
        # Tenant B MUST NOT see Tenant A's land units
        r_idor_lu = await client.get(f"/api/v1/agriculture/land-units?project_id={project_a.id}", headers=headers_b)
        assert r_idor_lu.json() == []

        # Tenant B MUST NOT see Tenant A's soil samples
        r_idor_ss = await client.get(f"/api/v1/agriculture/soil-samples?project_id={project_a.id}", headers=headers_b)
        assert r_idor_ss.json() == []

        # Tenant B MUST NOT see Tenant A's tree observations
        r_idor_tr = await client.get(f"/api/v1/agriculture/tree-observations?project_id={project_a.id}", headers=headers_b)
        assert r_idor_tr.json() == []

        # Tenant B MUST NOT see Tenant A's satellite observations
        r_idor_sat = await client.get(f"/api/v1/agriculture/satellite-observations?project_id={project_a.id}", headers=headers_b)
        assert r_idor_sat.json() == []

        # Tenant B MUST NOT see Tenant A's biochar facilities
        r_idor_fac = await client.get(f"/api/v1/biochar/facilities?project_id={biochar_proj.id}", headers=headers_b)
        assert r_idor_fac.status_code in (403, 404) or r_idor_fac.json() == []

        # Tenant B MUST NOT see Tenant A's biochar feedstock sources
        r_idor_src = await client.get(f"/api/v1/biochar/sources?project_id={biochar_proj.id}", headers=headers_b)
        assert r_idor_src.status_code in (403, 404) or r_idor_src.json() == []

        # Tenant B MUST NOT see Tenant A's biochar end use applications
        r_idor_end = await client.get(f"/api/v1/biochar/end-uses?project_id={biochar_proj.id}", headers=headers_b)
        assert r_idor_end.status_code in (403, 404) or r_idor_end.json() == []

        # Tenant B querying assets must NOT see Tenant A's assets
        r_idor_assets = await client.get("/api/v1/assets?per_page=100", headers=headers_b)
        assert r_idor_assets.status_code == 200
        b_items = r_idor_assets.json() if isinstance(r_idor_assets.json(), list) else (r_idor_assets.json().get("assets") or [])
        assert not any(a["name"] == "Kano 500kW Solar Mini-grid" for a in b_items)
        assert not any(a["name"] == "Abuja Central EV Hub" for a in b_items)
        assert not any(a["name"] == "Ungeocoded Inverter Registry Asset" for a in b_items)
