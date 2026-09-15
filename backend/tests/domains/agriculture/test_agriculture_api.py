"""
=============================================================================
VeriField Nexus — Agriculture & Land Use REST API Integration Tests
=============================================================================
Tests:
1. POST /api/v1/agriculture/land-units (with GeoJSON topology and geodesic area)
2. GET /api/v1/agriculture/land-units
3. POST /api/v1/agriculture/soil-samples (with VM0042 depth classification)
4. POST /api/v1/agriculture/tree-observations/batch (with allometric biomass)
5. POST /api/v1/agriculture/satellite-observations (with provenance hash)
6. POST /api/v1/agriculture/model-runs/vt0014 (with spatial uncertainty)
7. POST /api/v1/agriculture/verification-dossier/{project_id} (sealed manifest)
8. GET /api/v1/agriculture/summary/{project_id}
=============================================================================
"""

import uuid
from datetime import date, datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


def _create_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id) if org_id else None,
        "iat": now,
        "exp": now + timedelta(hours=2),
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_agriculture_api_end_to_end_flow(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    # 1. Setup Org, User, and Project
    unique_suffix = uuid.uuid4().hex[:6]
    org = Organization(name=f"Integrated Agriculture Holdings {unique_suffix}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        email=f"agri.officer.{unique_suffix}@example.com",
        full_name="Agronomy Verification Officer",
        role="ADMIN",
        organization_id=org.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(
        name=f"Agro-Ecosystem Demonstration {unique_suffix}",
        project_code=f"AGR-API-{unique_suffix}",
        organization_id=org.id,
        baseline_parameters={
            "locked_methodology_version": {
                "methodology_code": "VM0042",
                "version": "2.2",
                "status": "LOCKED",
            }
        },
    )
    db_session.add(project)
    await db_session.commit()

    token = _create_token(user.id, user.email, user.role, org.id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Create Land Unit
        lu_resp = await client.post(
            "/api/v1/agriculture/land-units",
            headers=headers,
            json={
                "project_id": str(project.id),
                "name": "North Field 1",
                "code": "NF-1",
                "unit_type": "FIELD",
                "boundary_source": "GNSS_SURVEY",
                "boundary_geojson": {
                    "type": "Polygon",
                    "coordinates": [
                        [[77.10, 28.50], [77.12, 28.50], [77.12, 28.52], [77.10, 28.52], [77.10, 28.50]]
                    ],
                },
            },
        )
        assert lu_resp.status_code == 201, lu_resp.text
        unit_data = lu_resp.json()
        unit_id = unit_data["id"]
        assert unit_data["area_ha"] > 0
        assert unit_data["centroid_lat"] is not None

        # 3. List Land Units
        list_lu = await client.get(f"/api/v1/agriculture/land-units?project_id={project.id}", headers=headers)
        assert list_lu.status_code == 200
        assert len(list_lu.json()) == 1

        # 4. Create 3 Soil Samples
        for i in range(3):
            s_resp = await client.post(
                "/api/v1/agriculture/soil-samples",
                headers=headers,
                json={
                    "project_id": str(project.id),
                    "land_unit_id": unit_id,
                    "sample_code": f"SOIL-API-0{i+1}",
                    "sampling_date": "2026-06-01",
                    "latitude": 28.51 + i * 0.002,
                    "longitude": 77.11 + i * 0.002,
                    "depth_upper_cm": 0.0,
                    "depth_lower_cm": 30.0,
                    "bulk_density_g_cm3": 1.32,
                    "soc_stock_pct": 1.45,
                    "lab_method": "DRY_COMBUSTION",
                },
            )
            assert s_resp.status_code == 201, s_resp.text
            assert s_resp.json()["compliance_classification"] == "EX_POST_QUANTIFICATION_ELIGIBLE"

        # 5. Batch Create Tree Observations
        trees_resp = await client.post(
            "/api/v1/agriculture/tree-observations/batch",
            headers=headers,
            json={
                "project_id": str(project.id),
                "land_unit_id": unit_id,
                "observations": [
                    {
                        "sampling_approach": "AREA_BASED",
                        "tag_number": "TR-01",
                        "species_scientific": "Azadirachta indica",
                        "dbh_cm": 22.0,
                        "height_m": 9.5,
                        "measurement_date": "2026-06-01",
                    }
                ],
            },
        )
        assert trees_resp.status_code == 201, trees_resp.text
        assert len(trees_resp.json()) == 1
        assert trees_resp.json()[0]["derived_carbon_stock_t_co2e"] > 0

        # 6. Ingest Satellite Observation
        sat_resp = await client.post(
            "/api/v1/agriculture/satellite-observations",
            headers=headers,
            json={
                "project_id": str(project.id),
                "land_unit_id": unit_id,
                "provider": "SENTINEL_2",
                "scene_id": "S2B_TEST_SCENE",
                "acquisition_timestamp": datetime.now(timezone.utc).isoformat(),
                "spatial_resolution_m": 10.0,
                "observation_type": "OPTICAL_MULTISPECTRAL",
                "bounding_box": [77.10, 28.50, 77.12, 28.52],
                "derived_indices": {"ndvi_mean": 0.68, "evi_mean": 0.45},
            },
        )
        assert sat_resp.status_code == 201, sat_resp.text
        assert len(sat_resp.json()["provenance_hash"]) == 64

        # 7. Run VT0014 Soil Mapping
        model_resp = await client.post(
            "/api/v1/agriculture/model-runs/vt0014",
            headers=headers,
            json={
                "project_id": str(project.id),
                "covariate_features": ["ndvi", "elevation"],
            },
        )
        assert model_resp.status_code == 201, model_resp.text
        model_data = model_resp.json()
        assert model_data["status"] == "COMPLETED"
        assert model_data["uncertainty_metrics"]["is_uncertainty_quantified"] is True

        # 8. Generate Verification Dossier
        dossier_resp = await client.post(
            f"/api/v1/agriculture/verification-dossier/{project.id}",
            headers=headers,
        )
        assert dossier_resp.status_code == 200, dossier_resp.text
        dossier = dossier_resp.json()
        assert dossier["sector_code"] == "AGRICULTURE_LAND_USE"
        assert dossier["ledger_seal_status"] == "SEALED_CRYPTOGRAPHICALLY"
        assert len(dossier["manifest_sha256"]) == 64

        # 9. Get Project Summary
        summary_resp = await client.get(
            f"/api/v1/agriculture/summary/{project.id}",
            headers=headers,
        )
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert summary["land_units_count"] == 1
        assert summary["soil_samples"]["total_count"] == 3
        assert summary["soil_samples"]["ex_post_eligible_count"] == 3
        assert summary["tree_inventory"]["total_count"] == 1
        assert summary["model_runs_count"] == 1
