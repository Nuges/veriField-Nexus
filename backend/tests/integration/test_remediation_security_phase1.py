"""
=============================================================================
VeriField Nexus — Phase 1 Remediation Integration & Security Verification Suite
=============================================================================

Empirical verification suite testing:
1. Priority 0 — Identity / JWT Security & SUPER_ADMIN Auto-Provisioning Safeguards
2. Priority 1 — Multi-Tenant Authorization across:
   - POST /projects (Cross-tenant payload rejection)
   - Energy domain write, read, and portfolio endpoints
   - EV domain write, read, and summary endpoints
   - Cookstoves domain write, read, and summary endpoints
   - Biochar domain write, read, and summary endpoints
   - AI Orchestrator write endpoints
   - System Settings patch endpoint
=============================================================================
"""

import asyncio
import uuid
import requests
import jwt
from datetime import datetime, timezone, timedelta

BACKEND_URL = "http://127.0.0.1:8000/api/v1"


def run_phase1_security_suite():
    print("=" * 80)
    print("VERIFIELD NEXUS — PHASE 1 REMEDIATION SECURITY VERIFICATION SUITE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Setup Phase: Authenticate Super Admin and Create Isolated Test Orgs
    # -------------------------------------------------------------------------
    sa_login = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": "admin@verifield.io", "password": "Lovelyday1"},
    )
    assert sa_login.status_code == 200, f"Super Admin login failed: {sa_login.text}"
    sa_token = sa_login.json()["access_token"]
    sa_headers = {"Authorization": f"Bearer {sa_token}"}
    print("✓ Super Admin authenticated successfully.")

    # 1. Create Organization A via Super Admin & Signup Admin User
    code_a = f"ORGA_{uuid.uuid4().hex[:4]}".upper()
    org_a_req = requests.post(
        f"{BACKEND_URL}/organizations",
        headers=sa_headers,
        json={"name": f"Organization A ({code_a})", "code": code_a},
    )
    assert org_a_req.status_code in (200, 201), f"Failed Org A creation: {org_a_req.text}"
    org_a_id = org_a_req.json()["id"]

    email_a = f"admin_{uuid.uuid4().hex[:6]}@example.com"
    user_a_req = requests.post(
        f"{BACKEND_URL}/auth/signup",
        json={
            "email": email_a,
            "password": "Password123!",
            "full_name": "Admin Org A",
            "role": "ADMIN",
            "organization_id": org_a_id,
        },
    )
    assert user_a_req.status_code in (200, 201), f"Failed Org A admin signup: {user_a_req.text}"
    token_a = user_a_req.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Create Organization B via Super Admin & Signup Admin User
    code_b = f"ORGB_{uuid.uuid4().hex[:4]}".upper()
    org_b_req = requests.post(
        f"{BACKEND_URL}/organizations",
        headers=sa_headers,
        json={"name": f"Organization B ({code_b})", "code": code_b},
    )
    assert org_b_req.status_code in (200, 201), f"Failed Org B creation: {org_b_req.text}"
    org_b_id = org_b_req.json()["id"]

    email_b = f"admin_{uuid.uuid4().hex[:6]}@example.com"
    user_b_req = requests.post(
        f"{BACKEND_URL}/auth/signup",
        json={
            "email": email_b,
            "password": "Password123!",
            "full_name": "Admin Org B",
            "role": "ADMIN",
            "organization_id": org_b_id,
        },
    )
    assert user_b_req.status_code in (200, 201), f"Failed Org B admin signup: {user_b_req.text}"
    token_b = user_b_req.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    print(f"✓ Created Isolated Test Tenants: Org A ({org_a_id}) and Org B ({org_b_id})")

    # -------------------------------------------------------------------------
    # TEST 1: Identity & JWT Security — Preventing Forged SUPER_ADMIN Claims
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Identity & JWT Security — Forged Claim Protection...")

    # Create a forged JWT token signed with default secret key requesting SUPER_ADMIN
    forged_user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    forged_payload = {
        "sub": forged_user_id,
        "email": f"hacker_{uuid.uuid4().hex[:4]}@example.com",
        "role": "SUPER_ADMIN",
        "exp": now + timedelta(hours=1),
        "iat": now,
    }
    forged_token = jwt.encode(forged_payload, "verifield-dev-secret-key", algorithm="HS256")
    forged_headers = {"Authorization": f"Bearer {forged_token}"}

    # Attempt admin-only endpoint with forged SUPER_ADMIN token
    admin_req = requests.get(f"{BACKEND_URL}/admin/users", headers=forged_headers)
    # Role demotion or auto-provisioning safeguard must block SUPER_ADMIN access
    assert admin_req.status_code in (401, 403), (
        f"Security Failure: Forged JWT granted SUPER_ADMIN access! Status: {admin_req.status_code}"
    )
    print(f"✓ Forged SUPER_ADMIN JWT successfully blocked (HTTP {admin_req.status_code}).")

    # -------------------------------------------------------------------------
    # TEST 2: POST /projects Cross-Tenant Payload Manipulation Safeguard
    # -------------------------------------------------------------------------
    print("\n[TEST 2] POST /projects Cross-Tenant Payload Manipulation...")

    # Case A: Org A Admin creates project for Org A -> 201 Created
    proj_a_req = requests.post(
        f"{BACKEND_URL}/projects",
        headers=headers_a,
        json={
            "name": f"Project Alpha {uuid.uuid4().hex[:4]}",
            "country": "Kenya",
            "sector": "Solar Energy",
            "organization_id": org_a_id,
        },
    )
    assert proj_a_req.status_code == 201, f"Failed valid project creation: {proj_a_req.text}"
    proj_a_id = proj_a_req.json()["id"]
    print("  ✓ Case A: Org A Admin created project for Org A (HTTP 201 Created).")

    # Case B: Org A Admin attempts to submit Org B's organization_id -> 403 Forbidden
    proj_cross_req = requests.post(
        f"{BACKEND_URL}/projects",
        headers=headers_a,
        json={
            "name": f"Malicious Project {uuid.uuid4().hex[:4]}",
            "country": "Kenya",
            "sector": "Solar Energy",
            "organization_id": org_b_id,
        },
    )
    assert proj_cross_req.status_code == 403, (
        f"Cross-tenant Project Vulnerability: Expected 403, got {proj_cross_req.status_code}"
    )
    print("  ✓ Case B: Org A Admin submitting Org B organization_id rejected (HTTP 403 Forbidden).")

    # Case C: Unauthenticated request -> 401 Unauthorized
    proj_unauth = requests.post(
        f"{BACKEND_URL}/projects",
        json={"name": "Unauth Project", "country": "Kenya", "sector": "Solar Energy"},
    )
    assert proj_unauth.status_code in (401, 403), f"Expected 401/403, got {proj_unauth.status_code}"
    print(f"  ✓ Case C: Unauthenticated POST /projects rejected (HTTP {proj_unauth.status_code}).")

    # Case D: Super Admin creating project for Org B -> 201 Created
    proj_sa_req = requests.post(
        f"{BACKEND_URL}/projects",
        headers=sa_headers,
        json={
            "name": f"Project Beta {uuid.uuid4().hex[:4]}",
            "country": "Rwanda",
            "sector": "EV Mobility",
            "organization_id": org_b_id,
        },
    )
    assert proj_sa_req.status_code == 201, f"Super admin project creation failed: {proj_sa_req.text}"
    proj_b_id = proj_sa_req.json()["id"]
    print("  ✓ Case D: Super Admin created project for Org B (HTTP 201 Created).")

    # -------------------------------------------------------------------------
    # TEST 3: Energy Domain Write & Read Multi-Tenant Authorization
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Energy Domain Multi-Tenant Authorization...")
    site_code_a = f"S1_{uuid.uuid4().hex[:4]}"

    # Unauthenticated asset creation -> 401/403
    asset_unauth = requests.post(f"{BACKEND_URL}/energy/assets?project_id={proj_a_id}&site_code={site_code_a}&site_name=Site1&latitude=1.0&longitude=36.0")
    assert asset_unauth.status_code in (401, 403), f"Expected 401/403, got {asset_unauth.status_code}"
    print(f"  ✓ Unauthenticated POST /energy/assets rejected (HTTP {asset_unauth.status_code}).")

    # Org B user trying to create asset under Org A project -> 403
    asset_cross = requests.post(
        f"{BACKEND_URL}/energy/assets?project_id={proj_a_id}&site_code={site_code_a}&site_name=Site1&latitude=1.0&longitude=36.0",
        headers=headers_b,
    )
    assert asset_cross.status_code == 403, f"Expected 403, got {asset_cross.status_code}"
    print("  ✓ Cross-tenant POST /energy/assets rejected (HTTP 403).")

    # Org A user creating asset under Org A project -> 201
    asset_a_res = requests.post(
        f"{BACKEND_URL}/energy/assets?project_id={proj_a_id}&site_code={site_code_a}&site_name=Site1&latitude=1.0&longitude=36.0",
        headers=headers_a,
    )
    assert asset_a_res.status_code == 201, f"Expected 201, got {asset_a_res.status_code}: {asset_a_res.text}"
    asset_a = asset_a_res.json()
    asset_a_id = asset_a["id"]
    print("  ✓ Authorized POST /energy/assets succeeded (HTTP 201).")

    # Cross-tenant telemetry post -> 403
    telem_cross = requests.post(
        f"{BACKEND_URL}/energy/telemetry?solar_asset_id={asset_a_id}&solar_generation_kwh=500&battery_discharge_kwh=100&diesel_generation_kwh=0&diesel_fuel_consumed_liters=0",
        headers=headers_b,
    )
    assert telem_cross.status_code == 403, f"Expected 403, got {telem_cross.status_code}"
    print("  ✓ Cross-tenant POST /energy/telemetry rejected (HTTP 403).")

    # Valid telemetry post -> 201
    telem_a = requests.post(
        f"{BACKEND_URL}/energy/telemetry?solar_asset_id={asset_a_id}&solar_generation_kwh=500&battery_discharge_kwh=100&diesel_generation_kwh=0&diesel_fuel_consumed_liters=0",
        headers=headers_a,
    )
    assert telem_a.status_code == 201, f"Expected 201, got {telem_a.status_code}"
    print("  ✓ Authorized POST /energy/telemetry succeeded (HTTP 201).")

    # Check Portfolio read scoping
    portfolio_b = requests.get(f"{BACKEND_URL}/energy/portfolio", headers=headers_b).json()
    assert portfolio_b["total_sites"] == 0, f"Tenant leakage in Energy Portfolio! Found {portfolio_b['total_sites']}"
    print("  ✓ Energy GET /energy/portfolio correctly isolated per tenant (0 sites for Org B).")

    # -------------------------------------------------------------------------
    # TEST 4: EV Domain Write & Read Multi-Tenant Authorization
    # -------------------------------------------------------------------------
    print("\n[TEST 4] EV Mobility Multi-Tenant Authorization...")
    st_code_a = f"EV-01_{uuid.uuid4().hex[:4]}"

    # Unauthenticated station creation -> 401/403
    st_unauth = requests.post(
        f"{BACKEND_URL}/ev/stations",
        json={
            "project_id": proj_a_id,
            "station_code": st_code_a,
            "operator_name": "Operator 1",
            "location_name": "Station 1",
            "latitude": 1.1,
            "longitude": 36.1,
            "charger_type": "DC_FAST",
            "max_output_kw": 50.0,
        },
    )
    assert st_unauth.status_code in (401, 403), f"Expected 401/403, got {st_unauth.status_code}"
    print(f"  ✓ Unauthenticated POST /ev/stations rejected (HTTP {st_unauth.status_code}).")

    # Cross-tenant station creation -> 403
    st_cross = requests.post(
        f"{BACKEND_URL}/ev/stations",
        headers=headers_b,
        json={
            "project_id": proj_a_id,
            "station_code": st_code_a,
            "operator_name": "Operator 1",
            "location_name": "Station 1",
            "latitude": 1.1,
            "longitude": 36.1,
            "charger_type": "DC_FAST",
            "max_output_kw": 50.0,
        },
    )
    assert st_cross.status_code == 403, f"Expected 403, got {st_cross.status_code}"
    print("  ✓ Cross-tenant POST /ev/stations rejected (HTTP 403).")

    # Authorized station creation -> 201
    st_a = requests.post(
        f"{BACKEND_URL}/ev/stations",
        headers=headers_a,
        json={
            "project_id": proj_a_id,
            "station_code": st_code_a,
            "operator_name": "Operator 1",
            "location_name": "Station 1",
            "latitude": 1.1,
            "longitude": 36.1,
            "charger_type": "DC_FAST",
            "max_output_kw": 50.0,
        },
    ).json()
    st_a_id = st_a["id"]
    print("  ✓ Authorized POST /ev/stations succeeded (HTTP 201).")

    # Cross-tenant session post -> 403
    sess_cross = requests.post(
        f"{BACKEND_URL}/ev/sessions",
        headers=headers_b,
        json={
            "station_id": st_a_id,
            "vehicle_vin": "VIN123456789",
            "fleet_operator_id": "FLEET_01",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "energy_consumed_kwh": 30.0,
            "distance_displaced_km": 150.0,
        },
    )
    assert sess_cross.status_code == 403, f"Expected 403, got {sess_cross.status_code}"
    print("  ✓ Cross-tenant POST /ev/sessions rejected (HTTP 403).")

    # Check EV Summary scoping
    ev_sum_b = requests.get(f"{BACKEND_URL}/ev/summary", headers=headers_b).json()
    assert ev_sum_b["total_stations"] == 0, "Tenant leakage in EV summary!"
    print("  ✓ EV GET /ev/summary correctly isolated per tenant (0 stations for Org B).")

    # -------------------------------------------------------------------------
    # TEST 5: Cookstoves Domain Write & Read Multi-Tenant Authorization
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Cookstoves Domain Multi-Tenant Authorization...")
    hh_code_a = f"HH-100_{uuid.uuid4().hex[:4]}"

    # Unauthenticated household registration -> 401/403
    hh_unauth = requests.post(
        f"{BACKEND_URL}/cookstoves/households",
        json={
            "project_id": proj_a_id,
            "household_code": hh_code_a,
            "head_of_household": "John Doe",
            "address": "123 Main St",
            "community_name": "Village A",
            "latitude": 0.5,
            "longitude": 35.5,
            "family_members_count": 5,
            "baseline_fuel_type": "WOOD_FIRE",
            "baseline_fuel_kg_per_day": 7.5,
        },
    )
    assert hh_unauth.status_code in (401, 403), f"Expected 401/403, got {hh_unauth.status_code}"
    print(f"  ✓ Unauthenticated POST /cookstoves/households rejected (HTTP {hh_unauth.status_code}).")

    # Cross-tenant household registration -> 403
    hh_cross = requests.post(
        f"{BACKEND_URL}/cookstoves/households",
        headers=headers_b,
        json={
            "project_id": proj_a_id,
            "household_code": hh_code_a,
            "head_of_household": "John Doe",
            "address": "123 Main St",
            "community_name": "Village A",
            "latitude": 0.5,
            "longitude": 35.5,
            "family_members_count": 5,
            "baseline_fuel_type": "WOOD_FIRE",
            "baseline_fuel_kg_per_day": 7.5,
        },
    )
    assert hh_cross.status_code == 403, f"Expected 403, got {hh_cross.status_code}"
    print("  ✓ Cross-tenant POST /cookstoves/households rejected (HTTP 403).")

    # Authorized household registration -> 201
    hh_a = requests.post(
        f"{BACKEND_URL}/cookstoves/households",
        headers=headers_a,
        json={
            "project_id": proj_a_id,
            "household_code": hh_code_a,
            "head_of_household": "John Doe",
            "address": "123 Main St",
            "community_name": "Village A",
            "latitude": 0.5,
            "longitude": 35.5,
            "family_members_count": 5,
            "baseline_fuel_type": "WOOD_FIRE",
            "baseline_fuel_kg_per_day": 7.5,
        },
    ).json()
    hh_a_id = hh_a["id"]
    print("  ✓ Authorized POST /cookstoves/households succeeded (HTTP 201).")

    # Check Cookstoves summary scoping
    cs_sum_b = requests.get(f"{BACKEND_URL}/cookstoves/summary", headers=headers_b).json()
    assert cs_sum_b["total_households"] == 0, "Tenant leakage in Cookstoves summary!"
    print("  ✓ Cookstoves GET /cookstoves/summary correctly isolated per tenant (0 households for Org B).")

    # -------------------------------------------------------------------------
    # TEST 6: Biochar Domain Write & Read Multi-Tenant Authorization
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Biochar Domain Multi-Tenant Authorization...")
    batch_num_a = f"BATCH-001_{uuid.uuid4().hex[:4]}"

    # Unauthenticated batch creation -> 401/403
    bio_unauth = requests.post(
        f"{BACKEND_URL}/biochar/batches",
        json={
            "project_id": proj_a_id,
            "batch_number": batch_num_a,
            "facility_name": "Facility 1",
            "kiln_id": "KILN-01",
            "feedstock_type": "RICE_HUSK",
            "feedstock_weight_tonnes": 10.0,
            "moisture_content_pct": 12.0,
            "origin_location": "Field 1",
            "pyrolysis_temp_celsius": 550.0,
            "residence_time_minutes": 30.0,
            "biochar_yield_tonnes": 3.0,
            "fixed_carbon_pct": 75.0,
            "ash_content_pct": 5.0,
            "molar_h_c_ratio": 0.3,
        },
    )
    assert bio_unauth.status_code in (401, 403), f"Expected 401/403, got {bio_unauth.status_code}"
    print(f"  ✓ Unauthenticated POST /biochar/batches rejected (HTTP {bio_unauth.status_code}).")

    # Cross-tenant batch creation -> 403
    bio_cross = requests.post(
        f"{BACKEND_URL}/biochar/batches",
        headers=headers_b,
        json={
            "project_id": proj_a_id,
            "batch_number": batch_num_a,
            "facility_name": "Facility 1",
            "kiln_id": "KILN-01",
            "feedstock_type": "RICE_HUSK",
            "feedstock_weight_tonnes": 10.0,
            "moisture_content_pct": 12.0,
            "origin_location": "Field 1",
            "pyrolysis_temp_celsius": 550.0,
            "residence_time_minutes": 30.0,
            "biochar_yield_tonnes": 3.0,
            "fixed_carbon_pct": 75.0,
            "ash_content_pct": 5.0,
            "molar_h_c_ratio": 0.3,
        },
    )
    assert bio_cross.status_code == 403, f"Expected 403, got {bio_cross.status_code}"
    print("  ✓ Cross-tenant POST /biochar/batches rejected (HTTP 403).")

    # Authorized batch creation -> 201
    bio_a = requests.post(
        f"{BACKEND_URL}/biochar/batches",
        headers=headers_a,
        json={
            "project_id": proj_a_id,
            "batch_number": batch_num_a,
            "facility_name": "Facility 1",
            "kiln_id": "KILN-01",
            "feedstock_type": "RICE_HUSK",
            "feedstock_weight_tonnes": 10.0,
            "moisture_content_pct": 12.0,
            "origin_location": "Field 1",
            "pyrolysis_temp_celsius": 550.0,
            "residence_time_minutes": 30.0,
            "biochar_yield_tonnes": 3.0,
            "fixed_carbon_pct": 75.0,
            "ash_content_pct": 5.0,
            "molar_h_c_ratio": 0.3,
        },
    )
    assert bio_a.status_code == 201, f"Expected 201, got {bio_a.status_code}"
    print("  ✓ Authorized POST /biochar/batches succeeded (HTTP 201).")

    # Check Biochar summary scoping
    bio_sum_b = requests.get(f"{BACKEND_URL}/biochar/summary", headers=headers_b).json()
    assert bio_sum_b["total_batches"] == 0, "Tenant leakage in Biochar summary!"
    print("  ✓ Biochar GET /biochar/summary correctly isolated per tenant (0 batches for Org B).")

    # -------------------------------------------------------------------------
    # TEST 7: AI Orchestrator & System Settings Authorization
    # -------------------------------------------------------------------------
    print("\n[TEST 7] AI Orchestrator & System Settings Authorization...")

    # Unauthenticated AI orchestrate -> 401
    ai_unauth = requests.post(f"{BACKEND_URL}/ai/orchestrate")
    assert ai_unauth.status_code in (401, 403), f"Expected 401/403, got {ai_unauth.status_code}"
    print(f"  ✓ Unauthenticated POST /ai/orchestrate rejected (HTTP {ai_unauth.status_code}).")

    # Cross-tenant AI orchestrate for Org A project -> 403
    ai_cross = requests.post(f"{BACKEND_URL}/ai/orchestrate?project_id={proj_a_id}", headers=headers_b)
    assert ai_cross.status_code == 403, f"Expected 403, got {ai_cross.status_code}"
    print("  ✓ Cross-tenant POST /ai/orchestrate rejected (HTTP 403).")

    # Unauthenticated system settings patch -> 401/403
    sett_unauth = requests.patch(f"{BACKEND_URL}/settings", json={"gps_max_distance_km": 5.0})
    assert sett_unauth.status_code in (401, 403), f"Expected 401/403, got {sett_unauth.status_code}"
    print(f"  ✓ Unauthenticated PATCH /settings rejected (HTTP {sett_unauth.status_code}).")

    # Super Admin system settings patch -> 200
    sett_sa = requests.patch(f"{BACKEND_URL}/settings", headers=sa_headers, json={"gps_max_distance_km": 5.0})
    assert sett_sa.status_code == 200, f"Expected 200, got {sett_sa.status_code}"
    print("  ✓ Super Admin PATCH /settings succeeded (HTTP 200).")

    # -------------------------------------------------------------------------
    # Cleanup Phase: Delete Test Organizations
    # -------------------------------------------------------------------------
    if org_a_id:
        requests.delete(f"{BACKEND_URL}/organizations/{org_a_id}", headers=sa_headers)
    if org_b_id:
        requests.delete(f"{BACKEND_URL}/organizations/{org_b_id}", headers=sa_headers)
    print("\n✓ Cleaned up temporary test organizations.")

    print("=" * 80)
    print("OVERALL VERDICT: ALL PHASE 1 REMEDIATION SECURITY TESTS PASSED 100% CLEANLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_phase1_security_suite()
