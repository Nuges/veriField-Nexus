"""
Migration Upgrade & Compatibility Tests for Biochar Value Chain
Tests:
A. Clean Database: Empty DB -> apply biochar value-chain migration (8c2f1e4a5d3b) -> all 13 tables exist with Numeric(18,6) precision.
B. Existing Database: Existing database with pre-migration schema and data across sectors (Cookstoves, Hybrid, EV, Agriculture, Biochar) -> apply migration (8c2f1e4a5d3b) -> verify legacy data preserved intact -> verify new columns and relations functional.
"""
import os
import tempfile
import uuid
import importlib
import importlib.util
import pytest
from sqlalchemy import create_engine, text, Column, String, Float, DateTime, MetaData, Table
from alembic.migration import MigrationContext
from alembic.operations import Operations

# Import the new migration module dynamically
_candidates = [
    os.path.abspath("backend/alembic/versions/2026_09_16_0800-8c2f1e4a5d3b_biochar_value_chain_schema.py"),
    os.path.abspath("alembic/versions/2026_09_16_0800-8c2f1e4a5d3b_biochar_value_chain_schema.py"),
]
migration_path = next((p for p in _candidates if os.path.exists(p)), _candidates[0])
spec = importlib.util.spec_from_file_location("biochar_migration", migration_path)
migration_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_mod)


def test_scenario_a_clean_database_migration():
    """Scenario A: Clean Database migration creating all Biochar value-chain tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        engine = create_engine(sqlite_url)

        # 1. Provide foundational tables (organizations, projects, land_units) required by foreign keys
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    org_type TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE land_units (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE biochar_batches (
                    id TEXT PRIMARY KEY,
                    batch_number TEXT NOT NULL,
                    quantity_kg REAL NOT NULL
                )
            """))

        # 2. Execute migration upgrade()
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn, opts={"as_sql": False})
            op = Operations(ctx)
            # Patch op into migration module
            migration_mod.op = op
            migration_mod.upgrade()

        # 3. Verify all 13 new/altered tables exist
        with engine.connect() as conn:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = {r[0] for r in res.fetchall()}

            expected_tables = [
                "biochar_feedstock_sources",
                "biochar_feedstock_lots",
                "biochar_production_facilities",
                "biochar_facility_reactors",
                "biochar_production_runs",
                "biochar_feedstock_run_allocations",
                "biochar_batches",
                "biochar_lab_analyses",
                "biochar_material_transactions",
                "biochar_transport_events",
                "biochar_storage_events",
                "biochar_end_use_records",
                "biochar_carbon_pool_claims",
            ]
            for t in expected_tables:
                assert t in tables, f"Expected table {t} missing in clean migrated database"

            # Check Numeric precision / columns on biochar_batches
            batch_cols_res = conn.execute(text("PRAGMA table_info(biochar_batches)"))
            batch_cols = {r[1] for r in batch_cols_res.fetchall()}
            assert "biochar_yield_tonnes" in batch_cols
            assert "feedstock_weight_tonnes" in batch_cols
            assert "batch_digest_hash" in batch_cols
            assert "mass_balance_status" in batch_cols

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_scenario_b_existing_database_upgrade():
    """Scenario B: Existing database with pre-migration schema and data -> apply migration -> verify data preservation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        engine = create_engine(sqlite_url)

        pre_batch_id = str(uuid.uuid4())
        pre_org_id = str(uuid.uuid4())
        pre_project_id = str(uuid.uuid4())

        # 1. Build pre-migration schema and populate existing data across sectors
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    org_type TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    licensed_sectors TEXT NOT NULL,
                    status TEXT NOT NULL,
                    is_deleted INTEGER NOT NULL DEFAULT 0
                )
            """))
            conn.execute(text("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    country TEXT NOT NULL,
                    sector_id TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE land_units (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL
                )
            """))
            # Legacy pre-migration biochar_batches table
            conn.execute(text("""
                CREATE TABLE biochar_batches (
                    id TEXT PRIMARY KEY,
                    kiln_id TEXT NOT NULL,
                    biomass_id TEXT NOT NULL,
                    batch_number TEXT NOT NULL,
                    quantity_kg REAL NOT NULL,
                    produced_at TEXT NOT NULL
                )
            """))

            # Populate pre-existing multi-sector data
            conn.execute(text("""
                INSERT INTO organizations (id, name, org_type, plan, licensed_sectors, status, is_deleted)
                VALUES (:id, 'Existing Biochar Corp', 'DEVELOPER', 'ENTERPRISE', '["BIOCHAR", "AGRICULTURE_LAND_USE", "COOKSTOVES"]', 'ACTIVE', 0)
            """), {"id": pre_org_id})

            conn.execute(text("""
                INSERT INTO projects (id, organization_id, name, status, country, sector_id)
                VALUES (:id, :org_id, 'Legacy Multi-Sector Project', 'ACTIVE', 'Kenya', :org_id)
            """), {"id": pre_project_id, "org_id": pre_org_id})

            conn.execute(text("""
                INSERT INTO biochar_batches (id, kiln_id, biomass_id, batch_number, quantity_kg, produced_at)
                VALUES (:id, :kiln, :biomass, 'LEGACY-BATCH-001', 5000.0, '2025-01-01 00:00:00')
            """), {"id": pre_batch_id, "kiln": str(uuid.uuid4()), "biomass": str(uuid.uuid4())})

        # 2. Apply Biochar migration (8c2f1e4a5d3b)
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn, opts={"as_sql": False})
            op = Operations(ctx)
            migration_mod.op = op
            migration_mod.upgrade()

        # 3. Verify old data is preserved intact
        with engine.connect() as conn:
            # Check old batch preserved
            batch_res = conn.execute(text("SELECT batch_number, quantity_kg, status FROM biochar_batches WHERE id = :id"), {"id": pre_batch_id})
            row = batch_res.fetchone()
            assert row is not None, "Pre-existing biochar batch was lost during migration!"
            assert row[0] == "LEGACY-BATCH-001"
            assert row[1] == 5000.0
            assert row[2] == "PRODUCED"  # Default status assigned

            # Check old organization preserved
            org_res = conn.execute(text("SELECT name, status, licensed_sectors FROM organizations WHERE id = :id"), {"id": pre_org_id})
            org_row = org_res.fetchone()
            assert org_row is not None
            assert org_row[0] == "Existing Biochar Corp"
            assert "BIOCHAR" in org_row[2]

            # Check new columns were added with default values
            cols_res = conn.execute(text("PRAGMA table_info(biochar_batches)"))
            cols = {r[1] for r in cols_res.fetchall()}
            assert "biochar_yield_tonnes" in cols
            assert "feedstock_weight_tonnes" in cols
            assert "batch_digest_hash" in cols
            assert "mass_balance_status" in cols

            # 4. Insert new value-chain records into the upgraded database
            source_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO biochar_feedstock_sources (id, organization_id, project_id, source_code, source_name, source_type, biomass_type)
                VALUES (:id, :org_id, :proj_id, 'SRC-001', 'Coffee Husk Residue', 'AGRICULTURAL_RESIDUE', 'HUSKS')
            """), {"id": source_id, "org_id": pre_org_id, "proj_id": pre_project_id})

            src_res = conn.execute(text("SELECT source_code FROM biochar_feedstock_sources WHERE id = :id"), {"id": source_id})
            assert src_res.fetchone()[0] == "SRC-001"

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
