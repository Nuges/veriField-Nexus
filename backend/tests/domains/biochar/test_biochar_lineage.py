import uuid
from datetime import date, datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.agriculture.models import LandUnit
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
async def test_biochar_chain_of_custody_and_lineage(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Lineage Provenance Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"lineage_auditor_{uuid.uuid4().hex[:6]}@synthetic-nexus.org",
        full_name="Synthetic Lineage Auditor",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name="Synthetic Lineage Tracing Project",
        project_code=f"PROJ-LIN-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        country="Colombia",
    )
    db_session.add(project)

    # LandUnit for feedstock source
    source_land_unit_id = uuid.uuid4()
    dummy_geo = {"type": "Polygon", "coordinates": [[[77.1, 28.5], [77.2, 28.5], [77.2, 28.6], [77.1, 28.6], [77.1, 28.5]]]}
    land_unit = LandUnit(
        id=source_land_unit_id,
        organization_id=org_id,
        project_id=project_id,
        name="Synthetic Agroforestry Farm Boundary",
        unit_type="PARCEL",
        area_ha=60.0,
        boundary_geojson=dummy_geo,
        is_active=True,
    )
    db_session.add(land_unit)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Feedstock Source with LandUnit Link
        src_payload = {
            "project_id": str(project_id),
            "source_code": f"SRC-LIN-{uuid.uuid4().hex[:6].upper()}",
            "source_name": "Pruned Coffee Agroforestry Biomass",
            "source_type": "AGRICULTURAL_RESIDUE",
            "biomass_type": "PRUNINGS",
            "origin_location": "Andean Highland Agroforestry Zone",
            "source_land_unit_id": str(source_land_unit_id),
            "waste_status": "CONFIRMED_WASTE_BIOMASS",
            "baseline_fate": "DECAY",
        }
        res_src = await client.post("/api/v1/biochar/sources", json=src_payload, headers=headers)
        assert res_src.status_code == 201, res_src.text
        source_id = res_src.json()["id"]

        # 2. Feedstock Lot with cryptographic evidence hash
        lot_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        lot_payload = {
            "project_id": str(project_id),
            "source_id": source_id,
            "lot_number": f"LOT-LIN-{uuid.uuid4().hex[:6].upper()}",
            "feedstock_type": "PRUNINGS",
            "mass_received_tonnes": 40.0,
            "moisture_content_pct": 12.0,
            "evidence_hash": lot_hash,
        }
        res_lot = await client.post("/api/v1/biochar/lots", json=lot_payload, headers=headers)
        assert res_lot.status_code == 201, res_lot.text
        lot_id = res_lot.json()["id"]

        # 3. Facility and Reactor
        fac_payload = {
            "project_id": str(project_id),
            "facility_code": f"FAC-LIN-{uuid.uuid4().hex[:6].upper()}",
            "facility_name": "Synthetic Andean Pyrolysis Facility",
            "location": "Highland Agro-Industrial Corridor",
            "facility_status": "NEW_OPERATIONAL",
            "technology_type": "SLOW_PYROLYSIS",
        }
        res_fac = await client.post("/api/v1/biochar/facilities", json=fac_payload, headers=headers)
        assert res_fac.status_code == 201, res_fac.text
        fac_id = res_fac.json()["id"]

        reac_payload = {
            "reactor_code": "REACTOR-LIN-01",
            "technology_type": "SLOW_PYROLYSIS",
            "operating_temp_min_c": 520.0,
            "operating_temp_max_c": 680.0,
            "residence_time_min_minutes": 25.0,
            "residence_time_max_minutes": 40.0,
        }
        res_reac = await client.post(f"/api/v1/biochar/facilities/{fac_id}/reactors", json=reac_payload, headers=headers)
        assert res_reac.status_code == 201, res_reac.text
        reac_id = res_reac.json()["id"]

        # 4. Production Run and Lot Allocation
        run_payload = {
            "project_id": str(project_id),
            "facility_id": fac_id,
            "reactor_id": reac_id,
            "run_number": f"RUN-LIN-{uuid.uuid4().hex[:6].upper()}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "avg_pyrolysis_temp_celsius": 600.0,
            "residence_time_minutes": 30.0,
            "output_biochar_mass_tonnes": 12.0,
        }
        res_run = await client.post("/api/v1/biochar/runs", json=run_payload, headers=headers)
        assert res_run.status_code == 201, res_run.text
        run_id = res_run.json()["id"]

        alloc_payload = {
            "lot_id": lot_id,
            "production_run_id": run_id,
            "allocated_wet_mass_tonnes": 40.0,
        }
        res_alloc = await client.post("/api/v1/biochar/allocations", json=alloc_payload, headers=headers)
        assert res_alloc.status_code == 201, res_alloc.text

        # 5. Output Batch
        batch_payload = {
            "project_id": str(project_id),
            "batch_number": f"BATCH-LIN-{uuid.uuid4().hex[:6].upper()}",
            "facility_name": "Synthetic Andean Pyrolysis Facility",
            "kiln_id": "REACTOR-LIN-01",
            "production_run_id": run_id,
            "feedstock_type": "PRUNINGS",
            "feedstock_weight_tonnes": 40.0,
            "moisture_content_pct": 12.0,
            "pyrolysis_temp_celsius": 600.0,
            "residence_time_minutes": 30.0,
            "biochar_yield_tonnes": 12.0,
            "fixed_carbon_pct": 83.0,
            "ash_content_pct": 4.5,
            "molar_h_c_ratio": 0.31,
            "carbon_claim_registry": "VERRA",
            "carbon_claim_methodology": "VM0044",
        }
        res_batch = await client.post("/api/v1/biochar/batches", json=batch_payload, headers=headers)
        assert res_batch.status_code == 201, res_batch.text
        batch_id = res_batch.json()["id"]

        # 6. Lab Analysis with Report Hash
        lab_hash = "f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2"
        lab_payload = {
            "batch_id": batch_id,
            "sample_id": "SMP-LIN-999",
            "sampling_date": datetime.now(timezone.utc).isoformat(),
            "laboratory_name": "BSI Certified Testing Services",
            "molar_h_c_ratio": 0.31,
            "organic_carbon_pct": 81.0,
            "fixed_carbon_pct": 83.0,
            "moisture_pct": 3.5,
            "ash_pct": 4.5,
            "lab_report_hash": lab_hash,
        }
        res_lab = await client.post(f"/api/v1/biochar/batches/{batch_id}/lab-analyses", json=lab_payload, headers=headers)
        assert res_lab.status_code == 201, res_lab.text

        # 7. Transport and Delivery with POD Hash
        pod_hash = "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b"
        trans_payload = {
            "project_id": str(project_id),
            "material_type": "BIOCHAR_BATCH",
            "reference_id": batch_id,
            "origin_address": "Highland Pyrolysis Site",
            "destination_address": "Agro-Distribution Hub Bogotá",
            "mass_transported_tonnes": 12.0,
            "distance_km": 110.0,
            "pod_document_hash": pod_hash,
            "departure_date": datetime.now(timezone.utc).isoformat(),
            "delivery_date": datetime.now(timezone.utc).isoformat(),
        }
        res_trans = await client.post("/api/v1/biochar/transports", json=trans_payload, headers=headers)
        assert res_trans.status_code == 201, res_trans.text

        # 8. Terminal End-Use (Durable Product)
        eu_payload = {
            "project_id": str(project_id),
            "batch_id": batch_id,
            "end_use_type": "NON_SOIL_APPLICATION",
            "applied_quantity_tonnes": 12.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "product_category": "CONCRETE_READYMIX",
            "recipient_organization": "Synthetic Infrastructure Materials",
        }
        res_eu = await client.post("/api/v1/biochar/end-uses", json=eu_payload, headers=headers)
        assert res_eu.status_code == 201, res_eu.text

        # 9. Query Full Chain of Custody & Lineage
        res_lin = await client.get(f"/api/v1/biochar/batches/{batch_id}/lineage", headers=headers)
        assert res_lin.status_code == 200, res_lin.text
        lin_data = res_lin.json()

        assert lin_data["traceability_complete"] is True
        node_types = {n["node_type"] for n in lin_data["nodes"]}
        assert "SOURCE" in node_types
        assert "LOT" in node_types
        assert "FACILITY" in node_types
        assert "REACTOR" in node_types
        assert "RUN" in node_types
        assert "BATCH" in node_types
        assert "LAB" in node_types
        assert "TRANSPORT" in node_types
        assert "END_USE" in node_types

        # Verify evidence hashes preserved
        hashes = set(lin_data["evidence_hashes"])
        assert lot_hash in hashes
        assert lab_hash in hashes
        assert pod_hash in hashes
