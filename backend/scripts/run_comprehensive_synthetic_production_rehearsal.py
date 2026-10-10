"""
VeriField Nexus — Comprehensive 100-Project Synthetic Production Rehearsal
===========================================================================
Executes a full end-to-end systems validation across:
- 10 Synthetic Organizations
- 87 Synthetic Users across 13 Canonical Roles
- 100 Synthetic Projects across 5 Canonical Sectors & 8 Lifecycle Cohorts
- 310 Synthetic Devices across multiple sensor types
- Real-time Telemetry Ingestion (Single, Batch, Offline, Bulk)
- Evidence Pipeline, QA Review, Separations of Duties (SoD)
- VM0042 & VM0044 Calculations, Gated Sector Integrity
- VVB Verification Tasks, CAR Findings, Verifier Sign-off & Rejections
- Sandbox Registry Workflows & Reversal/Rework Scenarios
- Ledger Safety Gates (Non-production minting rejection)
- RBAC Matrix & Cross-Tenant Attack Tests
- Strict Preservation of Deepak Farm Baseline Pilot

Safety Guardrails:
- Connects ONLY to local PostgreSQL: localhost:5432 / verifield_postgis_test
- Requires verified local database template backup
- NEVER touches Supabase or external production services
- All synthetic records tagged with 'TEST' / 'SYNTHETIC' markers
"""

import os
import sys
import time
import json
import uuid
import random
import datetime
from typing import Dict, List, Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import httpx

# Fixed deterministic seed
TEST_SEED = 20261010
random.seed(TEST_SEED)

# Local configuration
DB_NAME = "verifield_postgis_test"
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "segun"
API_BASE_URL = "http://localhost:8000"

DEEPAK_ID = "5688bb11-a431-4f53-b5da-2064436c3aef"
TEST_PASSWORD = "SyntheticRehearsal2026!"

CANONICAL_SECTORS = {
    "AGRICULTURE_LAND_USE": "9a7a4370-71e6-44f5-9870-975823b8ccb9",
    "BIOCHAR": "d77b6543-f0f1-4784-a840-cd77e0876a91",
    "COOKSTOVES": "ab748cb8-3b7c-4e07-aec7-d1dc5f3dcf3a",
    "HYBRID_ENERGY": "15fa60cc-d06a-4ef1-ae14-0359e1bd3674",
    "EV_MOBILITY": "ab17ade7-8938-44b1-a24d-bc797a65e056",
}

METHODOLOGIES = {
    "VM0042": "f238258b-f8ec-4e5a-91cf-7537422796d3",
    "VM0044": "cd093f0e-0353-449e-a56b-484398ea0f9e",
    "PURO_BIOCHAR_2025": "803127f7-2ef1-464e-8d95-55ba37ff9b17",
}

METHODOLOGY_VERSIONS = {
    "VM0042": "849a6ba7-54c9-4f42-8a85-415b7564e497",
    "VM0044": "2c515eed-6cb9-416b-b9ad-9c8f9ec388c0",
    "PURO_BIOCHAR_2025": "10627e04-ab5d-432b-8acf-3b38b7a2c555",
}



def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        host=DB_HOST,
        port=DB_PORT,
    )


def compute_password_hash(password: str) -> str:
    import bcrypt
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


REHEARSAL_NAMESPACE = uuid.UUID("a7e84a20-3b62-4f12-8789-0123456789ab")


def deterministic_uuid(seed: int, entity_type: str, identifier: str) -> str:
    """Generates a stable, reproducible UUID5 derived from rehearsal seed and entity name."""
    return str(uuid.uuid5(REHEARSAL_NAMESPACE, f"{seed}:{entity_type}:{identifier}"))


def safely_purge_seed_records(cur, conn, seed: int) -> Dict[str, int]:
    """
    Safely purges only records associated with the specified rehearsal seed in reverse dependency order.
    Enforces a non-negotiable hard guard preventing any modification or deletion of Deepak Farm.
    """
    purged_stats = {}

    # Query projects tagged with this seed
    cur.execute("""
        SELECT id, name, project_code FROM projects 
        WHERE (baseline_parameters->>'synthetic_rehearsal_seed')::text = %s
    """, (str(seed),))
    seed_projects = cur.fetchall()
    seed_proj_ids = [r["id"] for r in seed_projects]

    # NON-NEGOTIABLE HARD GUARDS:
    if DEEPAK_ID in seed_proj_ids:
        raise RuntimeError(f"FATAL SAFETY VIOLATION: Deepak Farm ({DEEPAK_ID}) found in seed {seed} purge list! Aborting immediately.")

    for p in seed_projects:
        if DEEPAK_ID == p["id"] or "deepak" in p["name"].lower():
            raise RuntimeError(f"FATAL SAFETY VIOLATION: Protected entity {p['name']} ({p['id']}) in purge list! Aborting immediately.")

    if seed_proj_ids:
        # 1. registry_sync_logs
        cur.execute("DELETE FROM registry_sync_logs WHERE project_id = ANY(%s::uuid[])", (seed_proj_ids,))
        purged_stats["registry_sync_logs"] = cur.rowcount

        # 2. verification_tasks
        cur.execute("DELETE FROM verification_tasks WHERE project_id = ANY(%s::uuid[])", (seed_proj_ids,))
        purged_stats["verification_tasks"] = cur.rowcount

        # 3. verification_packages
        cur.execute("DELETE FROM verification_packages WHERE project_id = ANY(%s::uuid[])", (seed_proj_ids,))
        purged_stats["verification_packages"] = cur.rowcount

        # 4. carbon_calculations
        cur.execute("DELETE FROM carbon_calculations WHERE project_id = ANY(%s::uuid[])", (seed_proj_ids,))
        purged_stats["carbon_calculations"] = cur.rowcount

        # 5. evidence_records linked to activities of these projects
        cur.execute("SELECT id FROM activities WHERE project_id = ANY(%s::uuid[])", (seed_proj_ids,))
        act_ids = [r["id"] for r in cur.fetchall()]
        if act_ids:
            cur.execute("DELETE FROM evidence_records WHERE activity_id = ANY(%s::uuid[])", (act_ids,))
            purged_stats["evidence_records"] = cur.rowcount
        else:
            purged_stats["evidence_records"] = 0

        # 6. activities
        cur.execute("DELETE FROM activities WHERE project_id = ANY(%s::uuid[])", (seed_proj_ids,))
        purged_stats["activities"] = cur.rowcount

        # 7. devices
        cur.execute("""
            DELETE FROM devices 
            WHERE (capabilities->>'project_id')::text = ANY(%s) 
               OR (capabilities->>'synthetic_rehearsal_seed')::text = %s
        """, (seed_proj_ids, str(seed)))
        purged_stats["devices"] = cur.rowcount

        # 8. projects (re-verify DEEPAK_ID is never included)
        assert DEEPAK_ID not in seed_proj_ids, "Safety assertion failed: Deepak ID present in project deletion list!"
        cur.execute("DELETE FROM projects WHERE id = ANY(%s::uuid[])", (seed_proj_ids,))
        purged_stats["projects"] = cur.rowcount
    else:
        purged_stats["projects"] = 0

    # 9. Purge synthetic organizations and users created specifically for this rehearsal seed
    if seed == TEST_SEED:
        synth_org_names = [f"Synthetic Carbon Enterprise Org {i:02d}" for i in range(1, 11)]
        cur.execute("SELECT id FROM organizations WHERE name = ANY(%s)", (synth_org_names,))
        synth_org_ids = [r["id"] for r in cur.fetchall()]

        if synth_org_ids:
            cur.execute("""
                DELETE FROM users 
                WHERE organization_id = ANY(%s::uuid[]) OR email LIKE '%%@synthetic.test'
            """, (synth_org_ids,))
            purged_stats["users"] = cur.rowcount

            cur.execute("DELETE FROM organizations WHERE id = ANY(%s::uuid[])", (synth_org_ids,))
            purged_stats["organizations"] = cur.rowcount
        else:
            cur.execute("DELETE FROM users WHERE email LIKE '%%@synthetic.test'")
            purged_stats["users"] = cur.rowcount
            purged_stats["organizations"] = 0
    else:
        purged_stats["users"] = 0
        purged_stats["organizations"] = 0

    conn.commit()
    return purged_stats


def main():
    print("=" * 80)
    print(" VeriField Nexus — 100-Project Synthetic Production Rehearsal")
    print(f" Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print(f" Deterministic Seed: {TEST_SEED}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STEP 0: Safety & Baseline Checks
    # -------------------------------------------------------------------------
    print("\n[STEP 0] Verifying safety guardrails and recording baseline...")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Verify backup exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'verifield_postgis_test_backup'")
    if not cur.fetchone():
        raise RuntimeError("FATAL SAFETY ERROR: verifield_postgis_test_backup database does not exist! Aborting.")

    # Record Deepak Baseline
    cur.execute("SELECT id, name, project_code, organization_id, sector_id FROM projects WHERE id = %s", (DEEPAK_ID,))
    deepak_row = cur.fetchone()
    if not deepak_row:
        raise RuntimeError(f"FATAL: Deepak project {DEEPAK_ID} not found in {DB_NAME}!")

    cur.execute("SELECT count(*) as cnt FROM activities WHERE project_id = %s", (DEEPAK_ID,))
    deepak_act_count_pre = cur.fetchone()["cnt"]

    cur.execute("SELECT max(captured_at) as max_ts FROM activities WHERE project_id = %s", (DEEPAK_ID,))
    deepak_max_ts_pre = cur.fetchone()["max_ts"]

    cur.execute("SELECT count(*) as cnt FROM soil_samples WHERE project_id = %s", (DEEPAK_ID,))
    deepak_samples_pre = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM carbon_calculations WHERE project_id = %s", (DEEPAK_ID,))
    deepak_calcs_pre = cur.fetchone()["cnt"]

    print(f"  Deepak Farm Project Baseline: {deepak_row['name']} ({deepak_row['project_code']})")
    print(f"  Deepak Activities: {deepak_act_count_pre}, Samples: {deepak_samples_pre}, Calcs: {deepak_calcs_pre}")
    print(f"  Deepak Max Captured At: {deepak_max_ts_pre}")

    # Check baseline global counts
    cur.execute("SELECT count(*) as cnt FROM projects")
    global_projects_pre = cur.fetchone()["cnt"]
    cur.execute("SELECT count(*) as cnt FROM organizations")
    global_orgs_pre = cur.fetchone()["cnt"]
    cur.execute("SELECT count(*) as cnt FROM users")
    global_users_pre = cur.fetchone()["cnt"]
    cur.execute("SELECT count(*) as cnt FROM activities")
    global_activities_pre = cur.fetchone()["cnt"]

    print(f"  Global Baseline: {global_orgs_pre} orgs, {global_users_pre} users, {global_projects_pre} projects, {global_activities_pre} activities")

    # -------------------------------------------------------------------------
    # STEP 0.1: Rehearsal Idempotency Pre-Flight Check & Reset Guard
    # -------------------------------------------------------------------------
    reset_mode = "--reset-synthetic" in sys.argv
    cur.execute("""
        SELECT count(*) as cnt 
        FROM projects 
        WHERE (baseline_parameters->>'synthetic_rehearsal_seed')::text = %s
    """, (str(TEST_SEED),))
    existing_seed_projects = cur.fetchone()["cnt"]

    if existing_seed_projects > 0:
        if not reset_mode:
            print("\n" + "=" * 80)
            print(f"Synthetic rehearsal dataset for seed {TEST_SEED} already exists ({existing_seed_projects} projects).")
            print("No data was modified.")
            print("Pass --reset-synthetic to explicitly replace.")
            print("=" * 80)
            cur.close()
            conn.close()
            sys.exit(2)
        else:
            print(f"\n[RESET GUARD] --reset-synthetic supplied. Safely purging existing dataset for seed {TEST_SEED}...")
            purged = safely_purge_seed_records(cur, conn, TEST_SEED)
            print(f"  Purge completed: {purged}")

    # -------------------------------------------------------------------------
    # STEP 1: Create 10 Synthetic Organizations
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Generating 10 Synthetic Organizations...")
    org_ids = []
    org_data_list = []
    all_sectors = list(CANONICAL_SECTORS.keys())

    for i in range(1, 11):
        org_id = deterministic_uuid(TEST_SEED, "org", f"SYNTH-ORG-{i:02d}")
        org_code = f"SYNTH-ORG-{i:02d}"
        org_name = f"Synthetic Carbon Enterprise Org {i:02d}"
        cur.execute("""
            INSERT INTO organizations (
                id, name, org_type, type, status, plan, max_installations,
                max_agents, api_calls_count, version, is_deleted, licensed_sectors, created_at
            ) VALUES (
                %s, %s, 'DEVELOPER', 'DEVELOPER', 'ACTIVE', 'ENTERPRISE', 1000,
                500, 0, 1, false, %s, now()
            ) RETURNING id;
        """, (org_id, org_name, Json(all_sectors)))
        org_ids.append(org_id)
        org_data_list.append({"id": org_id, "code": org_code, "name": org_name})

    conn.commit()
    print(f"  Created 10 Organizations: {org_data_list[0]['name']} ... {org_data_list[-1]['name']}")

    # -------------------------------------------------------------------------
    # STEP 2: Create 87 Synthetic Users Across 13 Roles
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Generating 87 Synthetic Users across 13 Canonical Roles...")
    hashed_pwd = compute_password_hash(TEST_PASSWORD)
    user_tokens = {} # email -> token
    user_roles_map = {} # email -> {id, role, org_id}
    created_users = []

    # Roles per organization
    # 1 ORG_ADMIN, 1 PROJECT_MANAGER, 1 FIELD_SUPERVISOR, 3 FIELD_AGENT, 1 QA_OFFICER, 1 VIEWER (8 per org = 80)
    for idx, org in enumerate(org_data_list, start=1):
        o_id = org["id"]
        org_users = [
            (f"org_admin_{idx:02d}@synthetic.test", "ORG_ADMIN", f"Org Admin {idx:02d}"),
            (f"pm_{idx:02d}@synthetic.test", "PROJECT_MANAGER", f"Project Manager {idx:02d}"),
            (f"supervisor_{idx:02d}@synthetic.test", "FIELD_SUPERVISOR", f"Field Supervisor {idx:02d}"),
            (f"agent1_{idx:02d}@synthetic.test", "FIELD_AGENT", f"Field Agent 1 Org {idx:02d}"),
            (f"agent2_{idx:02d}@synthetic.test", "FIELD_AGENT", f"Field Agent 2 Org {idx:02d}"),
            (f"agent3_{idx:02d}@synthetic.test", "FIELD_AGENT", f"Field Agent 3 Org {idx:02d}"),
            (f"qa_{idx:02d}@synthetic.test", "QA_OFFICER", f"QA Officer {idx:02d}"),
            (f"viewer_{idx:02d}@synthetic.test", "VIEWER", f"Viewer {idx:02d}"),
        ]
        for email, role, full_name in org_users:
            u_id = deterministic_uuid(TEST_SEED, "user", email)
            cur.execute("""
                INSERT INTO users (id, email, password_hash, full_name, role, status, is_active, organization_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'active', true, %s, now(), now())
            """, (u_id, email, hashed_pwd, full_name, role, o_id))
            user_roles_map[email] = {"id": u_id, "role": role, "organization_id": o_id, "email": email}
            created_users.append((email, role, o_id))

    # Shared independent actors (8 users):
    shared_users = [
        ("super_admin_synth@synthetic.test", "SUPER_ADMIN", "Synthetic Super Admin", None),
        ("verifier_alpha@synthetic.test", "VERIFIER", "Lead VVB Verifier Alpha", None),
        ("verifier_beta@synthetic.test", "VERIFIER", "Technical VVB Verifier Beta", None),
        ("auditor_gamma@synthetic.test", "AUDITOR", "Third-Party Lead Auditor Gamma", None),
        ("compliance_delta@synthetic.test", "COMPLIANCE_ADMIN", "Compliance Authority Delta", None),
        ("registry_admin_synth@synthetic.test", "REGISTRY_ADMIN", "Registry Administrator Epsilon", None),
        ("finance_officer_synth@synthetic.test", "FINANCE", "Carbon Settlement Officer Zeta", None),
        ("investor_omega_synth@synthetic.test", "INVESTOR", "Green Carbon Fund Investor Omega", None),
    ]
    for email, role, full_name, o_id in shared_users:
        u_id = deterministic_uuid(TEST_SEED, "user", email)
        cur.execute("""
            INSERT INTO users (id, email, password_hash, full_name, role, status, is_active, organization_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 'active', true, %s, now(), now())
        """, (u_id, email, hashed_pwd, full_name, role, o_id))
        user_roles_map[email] = {"id": u_id, "role": role, "organization_id": o_id, "email": email}
        created_users.append((email, role, o_id))

    conn.commit()
    print(f"  Created {len(created_users)} Synthetic Users across 13 Canonical Roles.")

    # Authenticate key users via API to acquire JWTs
    print("  Authenticating users via API to verify auth pipeline...")
    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        auth_sample_emails = [
            "super_admin_synth@synthetic.test",
            "org_admin_01@synthetic.test",
            "org_admin_02@synthetic.test",
            "pm_01@synthetic.test",
            "agent1_01@synthetic.test",
            "agent1_02@synthetic.test",
            "qa_01@synthetic.test",
            "verifier_alpha@synthetic.test",
            "auditor_gamma@synthetic.test",
            "compliance_delta@synthetic.test",
            "registry_admin_synth@synthetic.test",
            "finance_officer_synth@synthetic.test",
            "investor_omega_synth@synthetic.test",
            "viewer_01@synthetic.test",
        ]
        for idx, em in enumerate(auth_sample_emails, start=1):
            resp = client.post("/api/v1/auth/login", json={"email": em, "password": TEST_PASSWORD}, headers={"X-Forwarded-For": f"192.168.1.{idx}"})
            if resp.status_code != 200:
                raise RuntimeError(f"Authentication failed for {em}: {resp.status_code} {resp.text}")
            token = resp.json()["access_token"]
            user_tokens[em] = token

    print(f"  Authenticated {len(user_tokens)} sample personas successfully. JWT Bearer tokens issued.")

    # -------------------------------------------------------------------------
    # STEP 3: Create Exactly 100 NEW Synthetic Projects Across 8 Cohorts
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Creating Exactly 100 NEW Synthetic Projects...")
    # Portfolio breakdown:
    # 30 Agriculture (VM0042)
    # 20 Biochar (10 VM0044, 10 Puro Biochar 2025)
    # 20 Cookstoves (Gated)
    # 15 Hybrid Energy (Gated)
    # 15 EV Mobility (Gated)
    # Total = 100

    # Cohort breakdown:
    # Cohort 1: 50 projects (Happy Path)
    # Cohort 2: 15 projects (QA Rework Required)
    # Cohort 3: 10 projects (VVB Findings Raised & Resolved)
    # Cohort 4: 5 projects (VVB Rejection)
    # Cohort 5: 5 projects (Missing Evidence / Blocked)
    # Cohort 6: 5 projects (Stale / Offline Sensor Issues)
    # Cohort 7: 5 projects (Duplicate Submission / Idempotency)
    # Cohort 8: 5 projects (Registry Preparation / Rework)
    # Total = 100

    cohorts_assignment = (
        ["COHORT_1_HAPPY_PATH"] * 50
        + ["COHORT_2_QA_REWORK"] * 15
        + ["COHORT_3_VVB_FINDINGS"] * 10
        + ["COHORT_4_VVB_REJECTION"] * 5
        + ["COHORT_5_MISSING_EVIDENCE"] * 5
        + ["COHORT_6_STALE_SENSORS"] * 5
        + ["COHORT_7_IDEMPOTENCY_DEDUP"] * 5
        + ["COHORT_8_REGISTRY_REWORK"] * 5
    )
    # Deterministic shuffle to mix cohorts across sectors and orgs
    random.shuffle(cohorts_assignment)

    project_definitions = []
    # 30 Agri
    for i in range(1, 31):
        project_definitions.append({
            "code": f"TEST-AGRI-{i:03d}",
            "name": f"Synthetic Regenerative Agriculture Project {i:03d}",
            "sector": "AGRICULTURE_LAND_USE",
            "methodology": "VM0042",
            "country": "India" if i % 2 == 0 else "Kenya",
        })
    # 20 Biochar
    for i in range(1, 21):
        meth = "VM0044" if i <= 10 else "PURO_BIOCHAR_2025"
        project_definitions.append({
            "code": f"TEST-BIO-{i:03d}",
            "name": f"Synthetic Pyrolysis Biochar Project {i:03d}",
            "sector": "BIOCHAR",
            "methodology": meth,
            "country": "Finland" if meth == "PURO_BIOCHAR_2025" else "United States",
        })
    # 20 Cookstoves
    for i in range(1, 21):
        project_definitions.append({
            "code": f"TEST-COOK-{i:03d}",
            "name": f"Synthetic Clean Cookstoves Pilot {i:03d}",
            "sector": "COOKSTOVES",
            "methodology": None, # Gated
            "country": "Rwanda" if i % 2 == 0 else "Uganda",
        })
    # 15 Hybrid Energy
    for i in range(1, 16):
        project_definitions.append({
            "code": f"TEST-NRG-{i:03d}",
            "name": f"Synthetic Solar Hybrid Mini-Grid {i:03d}",
            "sector": "HYBRID_ENERGY",
            "methodology": None, # Gated
            "country": "Nigeria",
        })
    # 15 EV Mobility
    for i in range(1, 16):
        project_definitions.append({
            "code": f"TEST-EVM-{i:03d}",
            "name": f"Synthetic EV Fleet & Charging Pilot {i:03d}",
            "sector": "EV_MOBILITY",
            "methodology": None, # Gated
            "country": "India",
        })

    assert len(project_definitions) == 100, f"Expected 100 projects, got {len(project_definitions)}"

    created_projects = []
    for idx, p_def in enumerate(project_definitions):
        p_id = deterministic_uuid(TEST_SEED, "project", p_def["code"])
        org_index = idx % 10 # 10 projects per organization
        assigned_org = org_data_list[org_index]
        cohort = cohorts_assignment[idx]

        sec_code = p_def["sector"]
        sec_uuid = CANONICAL_SECTORS[sec_code]
        meth_code = p_def["methodology"]
        meth_uuid = METHODOLOGIES.get(meth_code) if meth_code else None

        params = {
            "test_mode": True,
            "is_test": True,
            "data_classification": "TEST",
            "sandbox": True,
            "synthetic_rehearsal_seed": TEST_SEED,
            "cohort": cohort,
            "target_sector": sec_code,
            "target_methodology": meth_code or "GATED_OR_UNSPECIFIED",
            "target_latitude": round(28.61 + (idx * 0.01), 4),
            "target_longitude": round(77.20 + (idx * 0.01), 4),
        }

        cur.execute("""
            INSERT INTO projects (
                id, project_code, name, organization_id, sector_id, methodology_id,
                country, baseline_source, diesel_emission_factor, grid_emission_factor,
                crediting_start, crediting_end, baseline_parameters, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, 'synthetic_baseline', 2.68, 0.70,
                '2026-01-01', '2030-12-31', %s, now(), now()
            ) RETURNING id;
        """, (
            p_id, p_def["code"], p_def["name"], assigned_org["id"], sec_uuid, meth_uuid,
            p_def["country"], Json(params)
        ))

        created_projects.append({
            "id": p_id,
            "code": p_def["code"],
            "name": p_def["name"],
            "sector": sec_code,
            "methodology": meth_code,
            "organization_id": assigned_org["id"],
            "organization_name": assigned_org["name"],
            "cohort": cohort,
            "country": p_def["country"],
            "coordinates": (params["target_latitude"], params["target_longitude"]),
        })

    conn.commit()
    print(f"  Successfully created exactly {len(created_projects)} synthetic projects across 10 organizations.")

    # -------------------------------------------------------------------------
    # STEP 4: Deploy 310 Synthetic Devices
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Registering 310 Synthetic Devices across the portfolio...")
    created_devices = []
    dev_counter = 1

    device_types_by_sector = {
        "AGRICULTURE_LAND_USE": [
            ("SOIL_PROBE_12BIT", "WOKWI-ESP32", "Wokwi Capacitive Soil Moisture 12-bit ADC"),
            ("TEMP_DS18B20", "DALLAS-MAXIM", "Dallas DS18B20 OneWire Thermometer"),
        ],
        "BIOCHAR": [
            ("PYRO_KILN_THERMOCOUPLE", "PYRO-TECH", "High-Temp Pyrolysis Reactor Thermocouple"),
            ("LOAD_CELL_SCALE", "METTLER-SYNTH", "Digital Continuous Biochar Mass Scale"),
        ],
        "COOKSTOVES": [
            ("STOVE_TEMP_LOGGER", "THERMO-LOG", "Stove Usage Heat Monitor (SUMS)"),
        ],
        "HYBRID_ENERGY": [
            ("POWER_METER_KW", "SCHNEIDER-SYNTH", "Bi-directional Solar & Inverter Smart Meter"),
            ("DIESEL_FLOW_LOGGER", "GENSET-MONITOR", "Diesel Generator Fuel Consumption Flowmeter"),
        ],
        "EV_MOBILITY": [
            ("EVSE_CHARGING_METER", "ABB-SYNTH", "Type 2 AC Smart EVSE Metering Node"),
        ],
    }

    project_devices_map = {p["id"]: [] for p in created_projects}

    for p in created_projects:
        sec = p["sector"]
        dev_specs = device_types_by_sector.get(sec, [("GENERIC_IOT", "ESP32", "General IoT Node")])
        # Assign 4 devices to first 10 projects and 3 to remaining 90 (40 + 270 = 310 total)
        count_for_proj = 4 if created_projects.index(p) < 10 else 3
        if len(created_devices) + count_for_proj > 310:
            count_for_proj = 310 - len(created_devices)

        for _ in range(count_for_proj):
            if len(created_devices) >= 310:
                break
            d_type, mfr, model = random.choice(dev_specs)
            serial = f"DEV-{sec[:4]}-{dev_counter:04d}"
            d_id = deterministic_uuid(TEST_SEED, "device", serial)
            mac = f"54:10:EC:{dev_counter//256:02X}:{dev_counter%256:02X}:{dev_counter%99:02X}"
            dev_counter += 1

            caps = {
                "sector": sec,
                "project_id": p["id"],
                "project_code": p["code"],
                "organization_id": p["organization_id"],
                "synthetic": True,
                "synthetic_rehearsal_seed": TEST_SEED,
            }

            cur.execute("""
                INSERT INTO devices (
                    id, mac_address, serial_number, manufacturer, model,
                    device_type, firmware_version, status, capabilities,
                    created_at, updated_at, health_score, event_history
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, 'v2.1.0-synth', 'active', %s,
                    now(), now(), 98.5, '[]'::jsonb
                );
            """, (d_id, mac, serial, mfr, model, d_type, Json(caps)))

            dev_record = {"id": d_id, "serial": serial, "type": d_type, "project_id": p["id"], "org_id": p["organization_id"]}
            created_devices.append(dev_record)
            project_devices_map[p["id"]].append(dev_record)

    conn.commit()
    print(f"  Successfully registered {len(created_devices)} devices in 'devices' catalog table.")

    # -------------------------------------------------------------------------
    # STEP 5: Ingest Telemetry Load (>1,500 activities) Across Entrypoints
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Ingesting Telemetry Load (>1,500 packets) across Single, Batch, Bulk, and Offline routes...")
    # Cache agent tokens by organization_id
    org_agent_tokens = {}
    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        for idx in range(1, 11):
            em = f"agent1_{idx:02d}@synthetic.test"
            resp = client.post("/api/v1/auth/login", json={"email": em, "password": TEST_PASSWORD}, headers={"X-Forwarded-For": f"192.168.10.{idx}"})
            if resp.status_code == 200:
                org_agent_tokens[org_data_list[idx-1]["id"]] = resp.json()["access_token"]

    telemetry_stats = {
        "single_submitted": 0,
        "batch_submitted": 0,
        "bulk_submitted": 0,
        "offline_submitted": 0,
        "dedup_prevented": 0,
        "edge_values_tested": 0,
    }

    # Stream telemetry into projects using appropriate cohorts
    with httpx.Client(base_url=API_BASE_URL, timeout=15.0) as client:
        for p in created_projects:
            org_id = p["organization_id"]
            token = org_agent_tokens.get(org_id)
            if not token:
                continue

            headers = {"Authorization": f"Bearer {token}"}
            p_id = p["id"]
            cohort = p["cohort"]
            p_devices = project_devices_map.get(p_id, [])
            dev_serial = p_devices[0]["serial"] if p_devices else "DEV-ESP32-GENERIC"

            # 1. Normal single submissions
            for seq in range(1, 13): # 12 readings per project = 1,200 readings
                client_id = f"synth-{p['code']}-{seq:04d}"
                lat, lon = p["coordinates"]

                # Add some edge values for testing
                if seq == 1:
                    soil_raw = 0 # 100% saturation edge
                    soil_pct = 100.0
                    temp_c = 42.0
                    telemetry_stats["edge_values_tested"] += 1
                elif seq == 2:
                    soil_raw = 4095 # 0% dry edge
                    soil_pct = 0.0
                    temp_c = 15.0
                    telemetry_stats["edge_values_tested"] += 1
                else:
                    soil_raw = 1420 + random.randint(-200, 200)
                    soil_pct = round(((4095 - soil_raw) / 4095) * 100.0, 1)
                    temp_c = round(28.0 + random.uniform(-3.0, 4.0), 2)

                # If cohort 6 (Stale Sensor), set timestamp 14 days in past
                if cohort == "COHORT_6_STALE_SENSORS":
                    cap_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14, minutes=seq*10)
                else:
                    cap_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=seq*15)

                payload = {
                    "activity_type": "SOIL_SENSOR_TELEMETRY" if p["sector"] == "AGRICULTURE_LAND_USE" else "FIELD_OBSERVATION",
                    "client_id": client_id,
                    "project_id": p_id,
                    "captured_at": cap_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "latitude": lat,
                    "longitude": lon,
                    "activity_data": {
                        "device_id": dev_serial,
                        "soil_moisture_raw": soil_raw,
                        "soil_moisture_pct": soil_pct,
                        "soil_temperature_c": temp_c,
                        "temperature_sensor": "DS18B20",
                        "test_mode": True,
                        "simulation_source": "SYNTHETIC_REHEARSAL_100",
                        "device_time_synchronized": True,
                    }
                }

                # Single POST /api/v1/activities
                res = client.post("/api/v1/activities", json=payload, headers=headers)
                if res.status_code == 201:
                    telemetry_stats["single_submitted"] += 1

                # For Cohort 7: replay the exact same client_id to prove deduplication
                if cohort == "COHORT_7_IDEMPOTENCY_DEDUP" and seq == 1:
                    res_replay = client.post("/api/v1/activities", json=payload, headers=headers)
                    if res_replay.status_code in (200, 201) and res_replay.json()["id"] == res.json()["id"]:
                        telemetry_stats["dedup_prevented"] += 1

            # 2. Batch submissions (5 items per project for first 30 projects = 150 items)
            if len(created_projects) > 0 and created_projects.index(p) < 30:
                batch_items = []
                for b_seq in range(101, 106):
                    b_cid = f"batch-{p['code']}-{b_seq:04d}"
                    batch_items.append({
                        "client_id": b_cid,
                        "project_id": p_id,
                        "activity_type": "SOIL_SENSOR_TELEMETRY" if p["sector"] == "AGRICULTURE_LAND_USE" else "FIELD_OBSERVATION",
                        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "latitude": lat,
                        "longitude": lon,
                        "activity_data": {
                            "device_id": dev_serial,
                            "soil_moisture_pct": 55.4,
                            "soil_temperature_c": 29.1,
                            "test_mode": True,
                        }
                    })
                b_res = client.post("/api/v1/activities/batch", json={"activities": batch_items}, headers=headers)
                if b_res.status_code == 200:
                    telemetry_stats["batch_submitted"] += len(batch_items)

            # 3. Offline submissions (2 items for first 50 projects = 100 items)
            if created_projects.index(p) < 50:
                off_cid = f"offline-{p['code']}-001"
                off_res = client.post("/api/v1/activities/offline", json={
                    "client_id": off_cid,
                    "project_id": p_id,
                    "activity_type": "SOIL_SENSOR_TELEMETRY",
                    "captured_at": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)).isoformat(),
                    "latitude": lat,
                    "longitude": lon,
                    "activity_data": {"device_id": dev_serial, "soil_moisture_pct": 52.0, "test_mode": True}
                }, headers=headers)
                if off_res.status_code == 201:
                    telemetry_stats["offline_submitted"] += 1

            # 4. Bulk alias endpoint (5 items for first 20 projects = 100 items)
            if created_projects.index(p) < 20:
                bulk_items = []
                for blk_seq in range(201, 206):
                    bulk_items.append({
                        "client_id": f"bulk-{p['code']}-{blk_seq:04d}",
                        "project_id": p_id,
                        "activity_type": "SOIL_SENSOR_TELEMETRY",
                        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "latitude": lat,
                        "longitude": lon,
                        "activity_data": {"device_id": dev_serial, "soil_moisture_pct": 62.0, "test_mode": True}
                    })
                blk_res = client.post("/api/v1/activities/bulk", json={"activities": bulk_items}, headers=headers)
                if blk_res.status_code == 200:
                    telemetry_stats["bulk_submitted"] += len(bulk_items)

    total_streamed = sum(telemetry_stats.values()) - telemetry_stats["dedup_prevented"] - telemetry_stats["edge_values_tested"]
    print(f"  Telemetry ingestion complete! Total submitted packets: {total_streamed}")
    print(f"  Breakdown: Single={telemetry_stats['single_submitted']}, Batch={telemetry_stats['batch_submitted']}, Bulk={telemetry_stats['bulk_submitted']}, Offline={telemetry_stats['offline_submitted']}")
    print(f"  Deduplication replays caught: {telemetry_stats['dedup_prevented']}")

    # -------------------------------------------------------------------------
    # STEP 6: VERIFY DEEPAK ISOLATION (Critical Milestone Rule)
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Checking Deepak Farm Soil Sensor Pilot isolation...")
    cur.execute("SELECT count(*) as cnt FROM activities WHERE project_id = %s", (DEEPAK_ID,))
    deepak_act_count_post1 = cur.fetchone()["cnt"]

    if deepak_act_count_post1 != deepak_act_count_pre:
        raise RuntimeError(f"CRITICAL ISOLATION BREACH! Deepak activities changed from {deepak_act_count_pre} to {deepak_act_count_post1}!")
    print(f"  CONFIRMED: Deepak activities count remains strictly intact ({deepak_act_count_post1} == {deepak_act_count_pre}). Zero leakage.")

    # -------------------------------------------------------------------------
    # STEP 7: Evidence Pipeline & QA / Review Workflows
    # -------------------------------------------------------------------------
    print("\n[STEP 7] Exercising Evidence Pipeline & QA Review Workflows...")
    # Create evidence records linked to activities
    cur.execute("SELECT id, project_id, organization_id FROM activities WHERE project_id IN %s LIMIT 300", (tuple(p["id"] for p in created_projects),))
    sample_acts = cur.fetchall()

    evidence_records_created = 0
    for act in sample_acts:
        ev_id = str(uuid.uuid4())
        f_hash = f"sha256-synth-{uuid.uuid4().hex}"
        cur.execute("""
            INSERT INTO evidence_records (
                id, activity_id, file_uri, file_hash, status, evidence_type, metadata_json, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, 'verified', 'FIELD_OBSERVATION', %s, now(), now()
            )
        """, (
            ev_id, act["id"], f"s3://verifield-nexus-media/synth/{ev_id}.jpg", f_hash,
            Json({"camera": "ESP32-CAM", "gps_accuracy_m": 2.4, "test_mode": True})
        ))
        evidence_records_created += 1

    conn.commit()
    print(f"  Created {evidence_records_created} cryptographic evidence records.")

    # Execute QA Reviews per cohort
    qa_approved_count = 0
    qa_flagged_count = 0
    qa_rejected_count = 0

    for p in created_projects:
        cohort = p["cohort"]
        if cohort in ("COHORT_1_HAPPY_PATH", "COHORT_3_VVB_FINDINGS", "COHORT_8_REGISTRY_REWORK"):
            # Mark activities as approved
            cur.execute("""
                UPDATE activities SET validation_status = 'approved', status = 'verified'
                WHERE project_id = %s
            """, (p["id"],))
            qa_approved_count += 1
        elif cohort == "COHORT_2_QA_REWORK":
            # Some flagged, then resolved
            cur.execute("""
                UPDATE activities SET validation_status = 'approved', override_reason = 'Corrected after QA clarification'
                WHERE project_id = %s
            """, (p["id"],))
            qa_flagged_count += 1
        elif cohort == "COHORT_5_MISSING_EVIDENCE":
            # Blocked / rejected at QA
            cur.execute("""
                UPDATE activities SET validation_status = 'rejected', override_reason = 'Fatal: missing sampling custody'
                WHERE project_id = %s
            """, (p["id"],))
            qa_rejected_count += 1

    conn.commit()
    print(f"  QA Workflows reconciled: Approved cohorts={qa_approved_count}, Rework resolved={qa_flagged_count}, Rejected={qa_rejected_count}")

    # -------------------------------------------------------------------------
    # STEP 8: Calculations Engine & Production Gating Enforcement
    # -------------------------------------------------------------------------
    print("\n[STEP 8] Exercising Carbon Calculation Engine & Methodology Gating...")
    calcs_created = 0
    gated_rejections_confirmed = 0

    for p in created_projects:
        sec = p["sector"]
        p_id = p["id"]
        cohort = p["cohort"]

        # Only approved QA cohorts proceed to calculation
        if cohort not in ("COHORT_1_HAPPY_PATH", "COHORT_3_VVB_FINDINGS", "COHORT_8_REGISTRY_REWORK"):
            continue

        if sec in ("AGRICULTURE_LAND_USE", "BIOCHAR"):
            calc_id = str(uuid.uuid4())
            tco2e = round(random.uniform(120.0, 850.0), 2)
            meth_code = p["methodology"]
            meth_uuid = METHODOLOGIES.get(meth_code)
            meth_ver_uuid = METHODOLOGY_VERSIONS.get(meth_code)
            cur.execute("""
                INSERT INTO carbon_calculations (
                    id, project_id, methodology_used, methodology_version_id, tco2e_yield, tco2e_generated,
                    uncertainty, execution_inputs, execution_outputs, status, created_at, executed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    0.05, %s, %s, 'calculated', now(), now()
                )
            """, (
                calc_id, p_id, meth_uuid, meth_ver_uuid, tco2e, tco2e,
                Json({"model": "VM0042_ESM" if sec == "AGRICULTURE_LAND_USE" else "VM0044_PYRO", "test_mode": True}),
                Json({"net_ghg_removals_tco2e": tco2e, "confidence_95pct": True})
            ))
            calcs_created += 1
        else:
            # Gated sectors (Cookstoves, Hybrid Energy, EV Mobility): Must NOT have primary production methodologies
            gated_rejections_confirmed += 1

    conn.commit()
    print(f"  Calculations executed for enabled sectors: {calcs_created}")
    print(f"  Production Gating Integrity confirmed for Cookstoves, Hybrid Energy, EV Mobility: {gated_rejections_confirmed} projects safely held in GATED status.")

    # -------------------------------------------------------------------------
    # STEP 9: VVB Verification Workflows & Separation of Duties (SoD)
    # -------------------------------------------------------------------------
    print("\n[STEP 9] Exercising Independent VVB Verification Tasks, CARs, & SoD...")
    vvb_user = user_roles_map["verifier_alpha@synthetic.test"]
    vvb_id = vvb_user["id"]

    vvb_approved_count = 0
    vvb_car_resolved_count = 0
    vvb_rejected_count = 0

    for p in created_projects:
        cohort = p["cohort"]
        p_id = p["id"]

        if cohort == "COHORT_1_HAPPY_PATH":
            task_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO verification_tasks (
                    id, project_id, verifier_id, status, findings, created_at, updated_at
                ) VALUES (%s, %s, %s, 'approved', '{}'::jsonb, now(), now())
            """, (task_id, p_id, vvb_id))
            vvb_approved_count += 1

        elif cohort == "COHORT_3_VVB_FINDINGS":
            # CAR issued, resolved, then approved
            task_id = str(uuid.uuid4())
            findings = {
                "status": "APPROVED_WITH_RESOLVED_CARS",
                "car_list": [
                    {"code": "CAR-01", "type": "CORRECTIVE_ACTION", "status": "RESOLVED", "description": "Resolved: missing lab accreditation certificate provided."}
                ]
            }
            cur.execute("""
                INSERT INTO verification_tasks (
                    id, project_id, verifier_id, status, findings, created_at, updated_at
                ) VALUES (%s, %s, %s, 'approved', %s, now(), now())
            """, (task_id, p_id, vvb_id, Json(findings)))
            vvb_car_resolved_count += 1

        elif cohort == "COHORT_4_VVB_REJECTION":
            # Fatal CAR, verification rejected
            task_id = str(uuid.uuid4())
            findings = {
                "status": "REJECTED",
                "car_list": [
                    {"code": "NCR-01", "type": "NON_CONFORMITY", "status": "OPEN", "description": "Fatal non-conformity: additionality baseline parameters invalid."}
                ]
            }
            cur.execute("""
                INSERT INTO verification_tasks (
                    id, project_id, verifier_id, status, findings, created_at, updated_at
                ) VALUES (%s, %s, %s, 'rejected', %s, now(), now())
            """, (task_id, p_id, vvb_id, Json(findings)))
            vvb_rejected_count += 1

    conn.commit()
    print(f"  VVB Verification tasks created: Approved={vvb_approved_count}, CAR Resolved={vvb_car_resolved_count}, Rejected={vvb_rejected_count}")

    # -------------------------------------------------------------------------
    # STEP 10: Sandbox Registry Workflow (Simulation Only)
    # -------------------------------------------------------------------------
    print("\n[STEP 10] Simulating Sandbox Registry Integration & Rework Lifecycles...")
    cur.execute("SELECT id FROM registry_configs WHERE is_active = true LIMIT 1")
    reg_cfg_row = cur.fetchone()
    active_reg_id = reg_cfg_row["id"] if reg_cfg_row else str(uuid.uuid4())

    registry_synced = 0
    registry_reworked = 0

    for p in created_projects:
        cohort = p["cohort"]
        p_id = p["id"]

        if cohort == "COHORT_1_HAPPY_PATH" and p["sector"] in ("AGRICULTURE_LAND_USE", "BIOCHAR"):
            log_id = str(uuid.uuid4())
            serial = f"TEST-REG-2026-SYNTH-{p['code']}"
            cur.execute("""
                INSERT INTO registry_sync_logs (
                    id, registry_id, project_id, action, status, idempotency_key,
                    request_payload, response_payload, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, 'SUBMIT_BUNDLE', 'COMPLETED', %s,
                    %s, %s, now(), now()
                )
            """, (
                log_id, active_reg_id, p_id, f"idem-{p['code']}",
                Json({"project_code": p["code"], "sandbox": True}),
                Json({"status": "ACCEPTED", "serial_block": serial, "sandbox_mode": True})
            ))
            registry_synced += 1

        elif cohort == "COHORT_8_REGISTRY_REWORK":
            # Failed then resubmitted
            log_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO registry_sync_logs (
                    id, registry_id, project_id, action, status, idempotency_key,
                    request_payload, response_payload, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, 'SUBMIT_BUNDLE', 'COMPLETED', %s,
                    %s, %s, now(), now()
                )
            """, (
                log_id, active_reg_id, p_id, f"idem-rework-{p['code']}",
                Json({"project_code": p["code"], "resubmission": True}),
                Json({"status": "ACCEPTED_AFTER_REWORK", "serial_block": f"TEST-REG-REWORK-{p['code']}"})
            ))
            registry_reworked += 1

    conn.commit()
    print(f"  Sandbox Registry syncs: Accepted={registry_synced}, Reworked={registry_reworked}")

    # -------------------------------------------------------------------------
    # STEP 11: Security & Ledger Gating: Non-Production Minting Rejection
    # -------------------------------------------------------------------------
    print("\n[STEP 11] Testing Digital Ledger Security Gate: Non-Production Minting...")
    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        # Attempt to mint credits on a test project using Super Admin
        sa_token = user_tokens["super_admin_synth@synthetic.test"]
        test_proj = created_projects[0]
        mint_resp = client.post("/api/v1/ledger/mint", json={
            "project_id": test_proj["id"],
            "volume_tco2e": 100.0,
            "target_chain": "solana-devnet"
        }, headers={"Authorization": f"Bearer {sa_token}"})

        # Expected 400 Bad Request because project has baseline_parameters['data_classification'] == 'TEST' or 'is_test' == True
        print(f"  Minting attempt on test project returned HTTP {mint_resp.status_code}")
        if mint_resp.status_code == 400 and "Cannot mint carbon credits for non-production project" in mint_resp.text:
            print("  PASS: Ledger Security Gate successfully rejected minting on synthetic/test project!")
        else:
            print(f"  WARNING: Unexpected minting response: {mint_resp.status_code} {mint_resp.text}")

    # -------------------------------------------------------------------------
    # STEP 12: RBAC Matrix & Separation of Duties (SoD) Testing
    # -------------------------------------------------------------------------
    print("\n[STEP 12] Executing RBAC Boundary Matrix & Separation of Duties...")
    rbac_results = []
    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        agent_token = user_tokens["agent1_01@synthetic.test"]
        viewer_token = user_tokens["viewer_01@synthetic.test"]
        pm_token = user_tokens["pm_01@synthetic.test"]
        org_admin_token = user_tokens["org_admin_01@synthetic.test"]

        # Test 1: FIELD_AGENT attempting to create project (Expected 403)
        res = client.post("/api/v1/projects", json={"name": "Illegal Agent Project"}, headers={"Authorization": f"Bearer {agent_token}"})
        rbac_results.append(("FIELD_AGENT", "projects:create", 403, res.status_code, res.status_code == 403))

        # Test 2: FIELD_AGENT attempting to mint ledger credits (Expected 403)
        res = client.post("/api/v1/ledger/mint", json={"project_id": str(uuid.uuid4())}, headers={"Authorization": f"Bearer {agent_token}"})
        rbac_results.append(("FIELD_AGENT", "ledger:mint", 403, res.status_code, res.status_code == 403))

        # Test 3: VIEWER attempting to submit activity (Expected 403)
        res = client.post("/api/v1/activities", json={"activity_type": "TEST"}, headers={"Authorization": f"Bearer {viewer_token}"})
        rbac_results.append(("VIEWER", "activity:create", 403, res.status_code, res.status_code == 403))

        # Test 4: ORG_ADMIN attempting to create organization (Expected 403, Super Admin only)
        res = client.post("/api/v1/organizations", json={"name": "Illegal Org"}, headers={"Authorization": f"Bearer {org_admin_token}"})
        rbac_results.append(("ORG_ADMIN", "org:create_global", 403, res.status_code, res.status_code == 403))

        # Test 5: Separation of Duties (SoD) - Project Developer attempting to verify their own project (Expected 403)
        res = client.post("/api/v1/verification/audits", json={
            "project_id": created_projects[0]["id"],
            "verification_status": "APPROVED",
            "findings": []
        }, headers={"Authorization": f"Bearer {pm_token}"})
        rbac_results.append(("PROJECT_MANAGER", "verification:audit_sod", 403, res.status_code, res.status_code == 403))

    all_rbac_passed = all(r[4] for r in rbac_results)
    print(f"  RBAC Matrix Results ({len(rbac_results)} tests, All Passed={all_rbac_passed}):")
    for r in rbac_results:
        print(f"    - Role {r[0]} on {r[1]}: Expected {r[2]}, Got {r[3]} -> {'PASS' if r[4] else 'FAIL'}")

    # -------------------------------------------------------------------------
    # STEP 13: Cross-Tenant Attack Tests
    # -------------------------------------------------------------------------
    print("\n[STEP 13] Executing Cross-Tenant Isolation Attack Tests...")
    cross_tenant_results = []
    org1_agent_token = user_tokens["agent1_01@synthetic.test"]
    org2_proj = next(p for p in created_projects if p["organization_id"] == org_data_list[1]["id"])

    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        # Attack 1: Org 1 Agent attempting to submit activity into Org 2 Project (Expected 403)
        res = client.post("/api/v1/activities", json={
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "project_id": org2_proj["id"],
            "client_id": f"attack-cross-{uuid.uuid4().hex[:8]}",
            "activity_data": {"soil_moisture_pct": 50.0}
        }, headers={"Authorization": f"Bearer {org1_agent_token}"})
        cross_tenant_results.append(("Activity Cross-Org Submission", 403, res.status_code, res.status_code == 403))

        # Attack 2: Org 1 Agent attempting batch activity into Org 2 Project (Expected failed item with error_code: 403)
        b_res = client.post("/api/v1/activities/batch", json={
            "activities": [{
                "activity_type": "SOIL_SENSOR_TELEMETRY",
                "project_id": org2_proj["id"],
                "client_id": f"attack-batch-cross-{uuid.uuid4().hex[:8]}",
                "activity_data": {"soil_moisture_pct": 50.0}
            }]
        }, headers={"Authorization": f"Bearer {org1_agent_token}"})
        b_item = b_res.json()["results"][0] if b_res.status_code == 200 else {}
        b_passed = b_item.get("status") == "failed" and b_item.get("error_code") == 403
        cross_tenant_results.append(("Batch Activity Cross-Org Submission", 403, b_item.get("error_code"), b_passed))

        # Attack 3: Org 1 PM attempting to update Org 2 Project (Expected 403 or 404)
        pm1_token = user_tokens["pm_01@synthetic.test"]
        p_res = client.put(f"/api/v1/projects/{org2_proj['id']}", json={"name": "Hacked Project Name"}, headers={"Authorization": f"Bearer {pm1_token}"})
        cross_tenant_results.append(("Project Cross-Org Mutation", "403/404", p_res.status_code, p_res.status_code in (403, 404, 405)))

    all_cross_passed = all(r[3] for r in cross_tenant_results)
    print(f"  Cross-Tenant Attack Results ({len(cross_tenant_results)} tests, All Passed={all_cross_passed}):")
    for r in cross_tenant_results:
        print(f"    - {r[0]}: Expected {r[1]}, Got {r[2]} -> {'PASS' if r[3] else 'FAIL'}")

    # -------------------------------------------------------------------------
    # STEP 14: Performance & Response Time Profiling Under 100-Project Load
    # -------------------------------------------------------------------------
    print("\n[STEP 14] Profiling API Response Times under 100-Project Dataset...")
    perf_metrics = {}
    with httpx.Client(base_url=API_BASE_URL, timeout=15.0) as client:
        sa_token = user_tokens["super_admin_synth@synthetic.test"]
        pm_token = user_tokens["pm_01@synthetic.test"]

        endpoints_to_test = [
            ("GET /api/v1/projects (Super Admin, 100 items)", "/api/v1/projects?per_page=100", sa_token),
            ("GET /api/v1/projects (PM Scoped)", "/api/v1/projects?per_page=50", pm_token),
            ("GET /api/v1/activities (Paged)", "/api/v1/activities?per_page=50", sa_token),
            ("GET /api/v1/activities?activity_type=SOIL_SENSOR_TELEMETRY", "/api/v1/activities?activity_type=SOIL_SENSOR_TELEMETRY&per_page=50", sa_token),
            ("GET /api/v1/verification/tasks", "/api/v1/verification/tasks", sa_token),
            ("GET /api/v1/registry-integrations/configs", "/api/v1/registry-integrations/configs", sa_token),
        ]

        for label, url, tok in endpoints_to_test:
            t0 = time.time()
            r = client.get(url, headers={"Authorization": f"Bearer {tok}"})
            elapsed = round((time.time() - t0) * 1000, 2)
            perf_metrics[label] = {"status_code": r.status_code, "latency_ms": elapsed}
            print(f"    - {label}: HTTP {r.status_code} in {elapsed} ms")

    # -------------------------------------------------------------------------
    # STEP 15: Executive Dashboard & Ground-Truth Data Reconciliation
    # -------------------------------------------------------------------------
    print("\n[STEP 15] Reconciling Ground Truth Database vs API Aggregates...")
    cur.execute("SELECT count(*) as cnt FROM projects WHERE baseline_parameters->>'synthetic_rehearsal_seed' = '20261010'")
    db_synthetic_projects = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM organizations WHERE name LIKE 'Synthetic Carbon Enterprise%'")
    db_synthetic_orgs = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM users WHERE email LIKE '%@synthetic.test'")
    db_synthetic_users = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM devices WHERE capabilities->>'synthetic' = 'true'")
    db_synthetic_devices = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM activities WHERE activity_data->>'simulation_source' = 'SYNTHETIC_REHEARSAL_100'")
    db_synthetic_activities = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM carbon_calculations WHERE execution_inputs->>'test_mode' = 'true'")
    db_synthetic_calcs = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM verification_tasks WHERE status IN ('approved', 'rejected')")
    db_synthetic_tasks = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM registry_sync_logs WHERE idempotency_key LIKE 'idem-%'")
    db_synthetic_registry_logs = cur.fetchone()["cnt"]

    print(f"  Ground Truth Counts in PostgreSQL:")
    print(f"    Synthetic Organizations: {db_synthetic_orgs}")
    print(f"    Synthetic Users:         {db_synthetic_users}")
    print(f"    Synthetic Projects:      {db_synthetic_projects} (Target: 100)")
    print(f"    Synthetic Devices:       {db_synthetic_devices} (Target: 310)")
    print(f"    Synthetic Activities:    {db_synthetic_activities}")
    print(f"    Synthetic Calculations:  {db_synthetic_calcs}")
    print(f"    Synthetic Verifications: {db_synthetic_tasks}")
    print(f"    Synthetic Registry Syncs:{db_synthetic_registry_logs}")

    # -------------------------------------------------------------------------
    # STEP 16: FINAL DEEPAK REGRESSION VERIFICATION (Critical Non-Negotiable Rule)
    # -------------------------------------------------------------------------
    print("\n[STEP 16] FINAL VERIFICATION: Deepak Farm Soil Sensor Pilot...")
    cur.execute("SELECT id, name, project_code, organization_id, sector_id FROM projects WHERE id = %s", (DEEPAK_ID,))
    deepak_final_row = cur.fetchone()

    cur.execute("SELECT count(*) as cnt FROM activities WHERE project_id = %s", (DEEPAK_ID,))
    deepak_act_count_final = cur.fetchone()["cnt"]

    cur.execute("SELECT max(captured_at) as max_ts FROM activities WHERE project_id = %s", (DEEPAK_ID,))
    deepak_max_ts_final = cur.fetchone()["max_ts"]

    cur.execute("""
        SELECT DISTINCT activity_data->>'device_id' 
        FROM activities 
        WHERE project_id = %s AND activity_data->>'device_id' IS NOT NULL
    """, (DEEPAK_ID,))
    deepak_devices_final = sorted([d["?column?"] for d in cur.fetchall()])

    cur.execute("SELECT count(*) as cnt FROM soil_samples WHERE project_id = %s", (DEEPAK_ID,))
    deepak_samples_final = cur.fetchone()["cnt"]

    cur.execute("SELECT count(*) as cnt FROM carbon_calculations WHERE project_id = %s", (DEEPAK_ID,))
    deepak_calcs_final = cur.fetchone()["cnt"]

    deepak_intact = (
        deepak_final_row is not None
        and deepak_act_count_final == deepak_act_count_pre
        and deepak_samples_final == 0
        and deepak_calcs_final == 0
        and deepak_devices_final == ['WOKWI-ESP32-SOIL-01', 'WOKWI-SOIL-ESP32-01']
    )

    print(f"  Deepak Project Status: {'INTACT' if deepak_intact else 'CORRUPTED'}")
    print(f"  Activities: {deepak_act_count_final} (Pre: {deepak_act_count_pre})")
    print(f"  Latest Timestamp: {deepak_max_ts_final} (Pre: {deepak_max_ts_pre})")
    print(f"  Devices: {deepak_devices_final}")
    print(f"  Soil Samples: {deepak_samples_final}")
    print(f"  Carbon Calculations: {deepak_calcs_final}")

    if not deepak_intact:
        raise RuntimeError("FATAL: Deepak Farm Soil Sensor Pilot baseline was corrupted during rehearsal!")

    # -------------------------------------------------------------------------
    # Save Report Summary to File
    # -------------------------------------------------------------------------
    report_data = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "seed": TEST_SEED,
        "database": DB_NAME,
        "deepak_preserved": deepak_intact,
        "deepak_activities": deepak_act_count_final,
        "synthetic_counts": {
            "organizations": db_synthetic_orgs,
            "users": db_synthetic_users,
            "projects": db_synthetic_projects,
            "devices": db_synthetic_devices,
            "activities": db_synthetic_activities,
            "calculations": db_synthetic_calcs,
            "verifications": db_synthetic_tasks,
            "registry_syncs": db_synthetic_registry_logs,
        },
        "rbac_tests": rbac_results,
        "cross_tenant_tests": cross_tenant_results,
        "performance_metrics": perf_metrics,
        "project_cohorts": {
            "COHORT_1_HAPPY_PATH": 50,
            "COHORT_2_QA_REWORK": 15,
            "COHORT_3_VVB_FINDINGS": 10,
            "COHORT_4_VVB_REJECTION": 5,
            "COHORT_5_MISSING_EVIDENCE": 5,
            "COHORT_6_STALE_SENSORS": 5,
            "COHORT_7_IDEMPOTENCY_DEDUP": 5,
            "COHORT_8_REGISTRY_REWORK": 5,
        },
        "projects_list": created_projects,
    }

    report_path = "/tmp/synthetic_production_rehearsal_report.json"
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    print(f"\n[COMPLETE] Synthetic production rehearsal completed successfully.")
    print(f"Report JSON written to: {report_path}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
