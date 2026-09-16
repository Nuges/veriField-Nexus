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
async def test_biochar_value_chain_full_lifecycle(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    # 1. Setup Synthetic Org, User, and Project
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name=f"Synthetic Biochar Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
    db_session.add(org)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"biochar_operator_{uuid.uuid4().hex[:6]}@synthetic-nexus.org",
        full_name="Synthetic Biochar Proponent",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name="Synthetic Biochar Pyrolysis Facility Alpha",
        project_code=f"SYN-BIO-{uuid.uuid4().hex[:4].upper()}",
        organization_id=org_id,
        country="Kenya",
    )
    db_session.add(project)
    await db_session.commit()

    token = _create_token(user_id, user.email, user.role, org_id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 2. Register Feedstock Source
        src_payload = {
            "project_id": str(project_id),
            "source_code": f"SRC-{uuid.uuid4().hex[:6].upper()}",
            "source_name": "Synthetic Agricultural Residue Supply",
            "source_type": "AGRICULTURAL_RESIDUE",
            "biomass_type": "COFFEE_HUSK",
            "origin_location": "Central Highlands Processing Station",
            "supplier_name": "Synthetic Cooperative Hub",
            "waste_status": "CONFIRMED_WASTE_BIOMASS",
            "baseline_fate": "OPEN_BURNING",
            "sustainability_status": "LOW_RISK",
        }
        res_src = await client.post("/api/v1/biochar/sources", json=src_payload, headers=headers)
        assert res_src.status_code == 201, res_src.text
        source_data = res_src.json()
        source_id = source_data["id"]
        assert source_data["waste_status"] == "CONFIRMED_WASTE_BIOMASS"

        # 3. Create Feedstock Lot with Dry Mass derivation
        lot_payload = {
            "project_id": str(project_id),
            "source_id": source_id,
            "lot_number": f"LOT-{uuid.uuid4().hex[:6].upper()}",
            "feedstock_type": "COFFEE_HUSK",
            "mass_received_tonnes": 50.0,
            "moisture_content_pct": 15.0,
            "storage_location": "Covered Silo 2",
        }
        res_lot = await client.post("/api/v1/biochar/lots", json=lot_payload, headers=headers)
        assert res_lot.status_code == 201, res_lot.text
        lot_data = res_lot.json()
        lot_id = lot_data["id"]
        # Expected dry mass: 50.0 * (1 - 0.15) = 42.5 t
        assert abs(lot_data["dry_mass_tonnes"] - 42.5) < 0.01
        assert lot_data["allocated_mass_tonnes"] == 0.0

        # 4. Register Production Facility & Reactor
        fac_payload = {
            "project_id": str(project_id),
            "facility_code": f"FAC-{uuid.uuid4().hex[:6].upper()}",
            "facility_name": "Synthetic Pyrolysis Unit 1",
            "location": "Industrial Processing Zone",
            "facility_status": "NEW_OPERATIONAL",
            "technology_type": "SLOW_PYROLYSIS",
            "production_capacity_tpy": 2500.0,
        }
        res_fac = await client.post("/api/v1/biochar/facilities", json=fac_payload, headers=headers)
        assert res_fac.status_code == 201, res_fac.text
        fac_id = res_fac.json()["id"]

        reac_payload = {
            "reactor_code": "REACTOR-01",
            "manufacturer": "Continuous Retort Systems Ltd",
            "model": "Pyros-500",
            "technology_type": "SLOW_PYROLYSIS",
            "operating_temp_min_c": 500.0,
            "operating_temp_max_c": 650.0,
            "residence_time_min_minutes": 30.0,
            "residence_time_max_minutes": 45.0,
        }
        res_reac = await client.post(f"/api/v1/biochar/facilities/{fac_id}/reactors", json=reac_payload, headers=headers)
        assert res_reac.status_code == 201, res_reac.text
        reac_id = res_reac.json()["id"]

        # 5. Create Production Run
        run_payload = {
            "project_id": str(project_id),
            "facility_id": fac_id,
            "reactor_id": reac_id,
            "run_number": f"RUN-{uuid.uuid4().hex[:6].upper()}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "avg_pyrolysis_temp_celsius": 580.0,
            "residence_time_minutes": 35.0,
            "electricity_kwh": 120.0,
            "fuel_liters": 15.0,
            "output_biochar_mass_tonnes": 10.0,
        }
        res_run = await client.post("/api/v1/biochar/runs", json=run_payload, headers=headers)
        assert res_run.status_code == 201, res_run.text
        run_id = res_run.json()["id"]

        # 6. Test Atomic Feedstock Lot Allocation & Cap Enforcement
        # Allocating 30 tonnes out of 50 tonnes -> SUCCEEDS
        alloc_payload = {
            "lot_id": lot_id,
            "production_run_id": run_id,
            "allocated_wet_mass_tonnes": 30.0,
        }
        res_alloc = await client.post("/api/v1/biochar/allocations", json=alloc_payload, headers=headers)
        assert res_alloc.status_code == 201, res_alloc.text

        # Allocating 25 tonnes when only 20 tonnes remain -> MUST FAIL with 400 Bad Request
        over_alloc_payload = {
            "lot_id": lot_id,
            "production_run_id": run_id,
            "allocated_wet_mass_tonnes": 25.0,
        }
        res_over = await client.post("/api/v1/biochar/allocations", json=over_alloc_payload, headers=headers)
        assert res_over.status_code == 400, res_over.text
        assert "Mass balance violation" in res_over.json()["detail"]

        # 7. Create Biochar Output Batch
        batch_payload = {
            "project_id": str(project_id),
            "batch_number": f"BATCH-{uuid.uuid4().hex[:6].upper()}",
            "facility_name": "Synthetic Pyrolysis Unit 1",
            "kiln_id": "REACTOR-01",
            "production_run_id": run_id,
            "feedstock_type": "COFFEE_HUSK",
            "feedstock_weight_tonnes": 30.0,
            "moisture_content_pct": 10.0,
            "pyrolysis_temp_celsius": 580.0,
            "residence_time_minutes": 35.0,
            "biochar_yield_tonnes": 10.0,
            "fixed_carbon_pct": 80.0,
            "ash_content_pct": 6.0,
            "molar_h_c_ratio": 0.35,
            "carbon_claim_registry": "VERRA",
            "carbon_claim_methodology": "VM0044",
        }
        res_batch = await client.post("/api/v1/biochar/batches", json=batch_payload, headers=headers)
        assert res_batch.status_code == 201, res_batch.text
        batch_data = res_batch.json()
        batch_id = batch_data["id"]
        assert batch_data["quality_grade"] == "GRADE_A"
        assert batch_data["status"] == "PRODUCED"

        # 8. Record Laboratory Analysis
        lab_payload = {
            "batch_id": batch_id,
            "sample_id": "SMP-2026-001",
            "sampling_date": datetime.now(timezone.utc).isoformat(),
            "laboratory_name": "Eurofins Carbon Analytics GmbH",
            "accreditation_standard": "ISO_17025",
            "test_method": "DIN_51732",
            "molar_h_c_ratio": 0.35,
            "organic_carbon_pct": 78.5,
            "fixed_carbon_pct": 80.0,
            "moisture_pct": 4.0,
            "ash_pct": 6.0,
            "heavy_metals_pass": True,
        }
        res_lab = await client.post(f"/api/v1/biochar/batches/{batch_id}/lab-analyses", json=lab_payload, headers=headers)
        assert res_lab.status_code == 201, res_lab.text
        assert res_lab.json()["qa_status"] == "VERIFIED"

        # 9. Record Transport & Storage Events
        trans_payload = {
            "project_id": str(project_id),
            "material_type": "BIOCHAR_BATCH",
            "reference_id": batch_id,
            "origin_address": "Industrial Processing Zone Plant 1",
            "destination_address": "Regional Warehouse Depot B",
            "mass_transported_tonnes": 10.0,
            "distance_km": 42.5,
            "transport_mode": "ROAD_DIESEL_TRUCK",
            "carrier_name": "Synthetic Express Freight",
            "departure_date": datetime.now(timezone.utc).isoformat(),
            "delivery_date": datetime.now(timezone.utc).isoformat(),
            "proof_of_delivery_ref": "POD-2026-99881",
        }
        res_trans = await client.post("/api/v1/biochar/transports", json=trans_payload, headers=headers)
        assert res_trans.status_code == 201, res_trans.text

        stor_payload = {
            "batch_id": batch_id,
            "storage_facility_name": "Regional Warehouse Depot B",
            "storage_location": "Bay 4, Dry Covered Pallets",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "quantity_stored_tonnes": 10.0,
            "loss_or_damage_tonnes": 0.1,
            "storage_conditions": "COVERED_DRY_VENTILATED",
        }
        res_stor = await client.post("/api/v1/biochar/storage-events", json=stor_payload, headers=headers)
        assert res_stor.status_code == 201, res_stor.text

        # 10. Record End-Use: Non-Soil Durable Application (3.0 tonnes)
        eu_payload = {
            "project_id": str(project_id),
            "batch_id": batch_id,
            "end_use_type": "NON_SOIL_APPLICATION",
            "applied_quantity_tonnes": 3.0,
            "event_date": datetime.now(timezone.utc).isoformat(),
            "product_category": "CONCRETE_READYMIX",
            "recipient_organization": "Synthetic Infrastructure Materials Ltd",
            "durability_classification": "DURABLE_BUILDING_MATERIAL",
        }
        res_eu = await client.post("/api/v1/biochar/end-uses", json=eu_payload, headers=headers)
        assert res_eu.status_code == 201, res_eu.text
        assert res_eu.json()["verification_status"] in ("VERIFIED", "PENDING_VERIFICATION")

        # Verify summary reflects recorded batch
        res_sum = await client.get(f"/api/v1/biochar/summary?project_id={project_id}", headers=headers)
        assert res_sum.status_code == 200, res_sum.text
        sum_data = res_sum.json()
        assert sum_data["total_batches"] >= 1
        assert sum_data["total_biochar_produced_tonnes"] >= 10.0
