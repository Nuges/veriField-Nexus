"""
VeriField Nexus — Agriculture MRV Existing-Data Upgrade Verification
===================================================================
Tests upgrading an established database containing Phase 1 entities to Phase 2 Head:
1. Initialize fresh DB and migrate to f6a7b8c9d0e1 (Phase 1).
2. Seed Phase 1 records:
   - Organization & User
   - Methodology Catalogue (VM0042 v2.2)
   - Project with locked methodology snapshot
   - LandUnit with PostGIS polygon geometry
   - Stratum & StratumMembership
   - AgricultureManagementRecord
3. Verify pre-upgrade record existence and relationships.
4. Run Alembic upgrade to HEAD (b2c3d4e5f6a8).
5. Verify:
   - All Phase 1 records remain intact.
   - Project methodology lock is intact and unchanged.
   - LandUnit geometry and spatial attributes are intact.
   - Stratum and StratumMembership FK relationships are intact.
   - Management records are intact.
   - Phase 2 tables are created, empty, and ready for operations.
   - Hardening columns are present on Phase 2 tables.
"""

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_NAME = "verifield_existing_upgrade_test"
SYNC_DB_URL = f"postgresql://segun@localhost:5432/{TEST_DB_NAME}"
ASYNC_DB_URL = f"postgresql+asyncpg://segun@localhost:5432/{TEST_DB_NAME}"

POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [[77.10, 28.50], [77.12, 28.50], [77.12, 28.52], [77.10, 28.52], [77.10, 28.50]]
    ],
}


def run_cmd(cmd: str):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {cmd}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout


async def main():
    print("=" * 70)
    print("AGRICULTURE MRV PHASE 2: EXISTING-DATA UPGRADE TEST")
    print("=" * 70)

    # 1. Reset DB
    print("\n[Step 1] Preparing fresh disposable database...")
    subprocess.run(f"dropdb --if-exists {TEST_DB_NAME}", shell=True)
    run_cmd(f"createdb {TEST_DB_NAME}")
    print(f"Created database: {TEST_DB_NAME}")

    # 2. Upgrade to Phase 1 (f6a7b8c9d0e1)
    print("\n[Step 2] Upgrading database to Phase 1 (f6a7b8c9d0e1)...")
    out = run_cmd(f'DATABASE_URL="{SYNC_DB_URL}" venv/bin/alembic upgrade f6a7b8c9d0e1')
    print("Alembic upgrade output:\n" + out.strip())

    # 3. Seed Phase 1 records
    print("\n[Step 3] Seeding Phase 1 records...")
    from app.domains.agriculture.models import (
        AgricultureManagementRecord,
        LandUnit,
        Stratum,
        StratumMembership,
    )
    from app.domains.agriculture.seed import seed_agriculture_methodologies
    from app.domains.agriculture.service import AgricultureService
    from app.domains.authentication.models import User
    from app.domains.methodologies.models.base_registry import (
        Methodology,
        MethodologyFamily,
        MethodologyVersion,
    )
    from app.domains.organizations.models import Organization
    from app.domains.projects.models import Project

    engine = create_async_engine(ASYNC_DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    seeded_ids = {}

    async with async_session() as session:
        # Seed methodology catalogue
        await seed_agriculture_methodologies(session)

        # Create Organization & User
        org = Organization(name=f"Upgrade Test Agro Org {uuid.uuid4().hex[:6]}")
        session.add(org)
        await session.flush()

        user = User(
            email=f"upgrade.user.{uuid.uuid4().hex[:6]}@verifield.test",
            full_name="Upgrade Test Lead",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
        )
        session.add(user)
        await session.flush()

        # Fetch VM0042 v2.2
        fam = (await session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE"))).scalar_one()
        vm = (await session.execute(select(Methodology).where(Methodology.code == "VM0042"))).scalar_one()
        v22 = (await session.execute(select(MethodologyVersion).where(
            MethodologyVersion.methodology_id == vm.id,
            MethodologyVersion.version == "2.2"
        ))).scalar_one()

        # Create Project
        proj = Project(
            name="Sonipat Regenerative Wheat-Rice Project",
            project_code=f"AGR-SONIPAT-{uuid.uuid4().hex[:6]}",
            organization_id=org.id,
            sector_id=fam.id,
            methodology_id=vm.id,
            methodology_version_id=v22.id,
            crediting_start=date(2025, 1, 1),
            crediting_end=date(2045, 12, 31),
            baseline_parameters={},
        )
        session.add(proj)
        await session.flush()

        # Lock methodology
        lock_res = await AgricultureService.lock_project_methodology(
            db=session,
            project_id=proj.id,
            organization_id=org.id,
            user_id=user.id,
            notes="Pre-feasibility audit completed",
        )

        # Create LandUnit with geometry
        lu = LandUnit(
            organization_id=org.id,
            project_id=proj.id,
            unit_type="FIELD",
            name="Sonipat Field Sector Alpha",
            code="FIELD-ALP-01",
            boundary_geojson=POLYGON_GEOJSON,
            boundary_source="DECLARED",
            boundary_crs="EPSG:4326",
            area_ha=433.2,
            is_active=True,
        )
        session.add(lu)
        await session.flush()

        # Update PostGIS geom
        await session.execute(text("""
            UPDATE land_units
            SET geom = ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
            WHERE id = :id
        """), {"geojson": str(POLYGON_GEOJSON).replace("'", '"'), "id": lu.id})

        # Create Stratum
        stratum = Stratum(
            organization_id=org.id,
            project_id=proj.id,
            code="STRAT-CLAY-01",
            name="Indo-Gangetic Alluvial Clay",
            stratum_type="SOIL_TYPE",
            area_ha=433.2,
            is_active=True,
        )
        session.add(stratum)
        await session.flush()

        # Create Stratum Membership
        membership = StratumMembership(
            organization_id=org.id,
            stratum_id=stratum.id,
            land_unit_id=lu.id,
            valid_from=date(2025, 1, 1),
            status="ACTIVE",
        )
        session.add(membership)
        await session.flush()

        # Create Agriculture Management Record (using raw SQL matching Phase 1 schema before corroboration column exists)
        mgmt_id = uuid.uuid4()
        await session.execute(text("""
            INSERT INTO agriculture_management_records (
                id, organization_id, project_id, land_unit_id, record_type, practice_category,
                event_date, data_source, details, entered_by_id, qa_status, created_at, updated_at
            ) VALUES (
                :id, :org_id, :proj_id, :land_unit_id, 'TILLAGE', 'REGENERATIVE',
                '2025-06-01', 'REPORTED', '{"tillage_depth_cm": 5, "equipment": "zero_till_drill"}'::jsonb,
                :user_id, 'ACCEPTED', now(), now()
            )
        """), {
            "id": mgmt_id,
            "org_id": org.id,
            "proj_id": proj.id,
            "land_unit_id": lu.id,
            "user_id": user.id,
        })
        await session.commit()

        seeded_ids["org_id"] = org.id
        seeded_ids["user_id"] = user.id
        seeded_ids["proj_id"] = proj.id
        seeded_ids["lu_id"] = lu.id
        seeded_ids["stratum_id"] = stratum.id
        seeded_ids["membership_id"] = membership.id
        seeded_ids["mgmt_id"] = mgmt_id

    print("Phase 1 records seeded successfully.")
    for k, v in seeded_ids.items():
        print(f"  - {k}: {v}")

    # 4. Verify Phase 1 Counts Before Upgrade
    async with async_session() as session:
        c_lu = (await session.execute(text("SELECT count(*) FROM land_units"))).scalar()
        c_st = (await session.execute(text("SELECT count(*) FROM agriculture_strata"))).scalar()
        c_mem = (await session.execute(text("SELECT count(*) FROM agriculture_stratum_memberships"))).scalar()
        c_mg = (await session.execute(text("SELECT count(*) FROM agriculture_management_records"))).scalar()
        print(f"\n[Pre-Upgrade Baseline Counts]")
        print(f"  land_units: {c_lu}, agriculture_strata: {c_st}, memberships: {c_mem}, management_records: {c_mg}")
        assert c_lu == 1
        assert c_st == 1
        assert c_mem == 1
        assert c_mg == 1

    # 5. Execute Alembic Upgrade to HEAD (b2c3d4e5f6a8)
    print("\n[Step 4] Executing Alembic upgrade to HEAD (b2c3d4e5f6a8)...")
    out = run_cmd(f'DATABASE_URL="{SYNC_DB_URL}" venv/bin/alembic upgrade b2c3d4e5f6a8')
    print("Alembic upgrade output:\n" + out.strip())

    # 6. Verify Post-Upgrade Integrity
    print("\n[Step 5] Verifying Phase 1 record preservation and Phase 2 schema additions...")
    async with async_session() as session:
        # Check Project Foundation
        proj_res = await session.execute(select(Project).where(Project.id == seeded_ids["proj_id"]))
        proj_post = proj_res.scalar_one()
        assert proj_post.name == "Sonipat Regenerative Wheat-Rice Project"
        foundation = await AgricultureService.get_project_foundation(session, proj_post.id, seeded_ids["org_id"])
        assert foundation["methodology_lock_status"] == "LOCKED"
        assert foundation["locked_methodology_snapshot"]["methodology_code"] == "VM0042"
        assert foundation["locked_methodology_snapshot"]["version"] == "2.2"
        print("  ✓ Project foundation and methodology lock snapshot: INTACT")

        # Check LandUnit & Geometry
        lu_res = await session.execute(select(LandUnit).where(LandUnit.id == seeded_ids["lu_id"]))
        lu_post = lu_res.scalar_one()
        assert lu_post.name == "Sonipat Field Sector Alpha"
        assert lu_post.area_ha == 433.2
        geom_wkt = (await session.execute(text("SELECT ST_AsText(geom) FROM land_units WHERE id = :id"), {"id": lu_post.id})).scalar()
        assert "POLYGON" in geom_wkt
        print(f"  ✓ LandUnit & PostGIS geometry: INTACT ({geom_wkt[:35]}...)")

        # Check Stratum & StratumMembership
        stratum_res = await session.execute(select(Stratum).where(Stratum.id == seeded_ids["stratum_id"]))
        stratum_post = stratum_res.scalar_one()
        assert stratum_post.code == "STRAT-CLAY-01"

        mem_join = (await session.execute(text("""
            SELECT m.status, s.code, l.code
            FROM agriculture_stratum_memberships m
            JOIN agriculture_strata s ON s.id = m.stratum_id
            JOIN land_units l ON l.id = m.land_unit_id
            WHERE m.id = :id
        """), {"id": seeded_ids["membership_id"]})).fetchone()
        assert mem_join[0] == "ACTIVE"
        assert mem_join[1] == "STRAT-CLAY-01"
        assert mem_join[2] == "FIELD-ALP-01"
        print(f"  ✓ Stratum & StratumMembership relationships: INTACT ({mem_join[1]} <-> {mem_join[2]})")

        # Check AgricultureManagementRecord
        mgmt_res = await session.execute(select(AgricultureManagementRecord).where(AgricultureManagementRecord.id == seeded_ids["mgmt_id"]))
        mgmt_post = mgmt_res.scalar_one()
        assert mgmt_post.record_type == "TILLAGE"
        assert mgmt_post.qa_status == "ACCEPTED"
        assert mgmt_post.details.get("equipment") == "zero_till_drill"
        assert mgmt_post.corroboration == "NONE"
        print(f"  ✓ AgricultureManagementRecord: INTACT (corroboration={mgmt_post.corroboration})")

        # Check Phase 2 Tables exist and are operational
        p2_tables = [
            "sampling_campaigns",
            "sampling_plan_versions",
            "sampling_points",
            "sample_collection_events",
            "physical_samples",
            "chain_of_custody_events",
            "laboratory_receipts",
            "laboratory_analyses",
            "laboratory_results",
            "sample_qa_reviews"
        ]
        for tbl in p2_tables:
            cnt = (await session.execute(text(f"SELECT count(*) FROM {tbl}"))).scalar()
            assert cnt == 0
            print(f"  ✓ Phase 2 table operational and ready: {tbl} (count = {cnt})")

        # Check Phase 2 Hardening Columns
        cols_lr = (await session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'laboratory_results'
              AND column_name IN ('quantification_limit', 'normalization_version', 'supersedes_id');
        """))).fetchall()
        lr_names = {r[0] for r in cols_lr}
        assert "quantification_limit" in lr_names
        assert "normalization_version" in lr_names
        assert "supersedes_id" in lr_names
        print(f"  ✓ laboratory_results hardening columns present: {', '.join(sorted(lr_names))}")

        cols_spv = (await session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'sampling_plan_versions'
              AND column_name = 'plan_lock_snapshot';
        """))).fetchall()
        assert len(cols_spv) == 1
        print("  ✓ sampling_plan_versions.plan_lock_snapshot present")

        cols_sce = (await session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'sample_collection_events'
              AND column_name = 'server_received_at';
        """))).fetchall()
        assert len(cols_sce) == 1
        print("  ✓ sample_collection_events.server_received_at present")

    await engine.dispose()

    print("\n[Step 6] Cleaning up disposable database...")
    subprocess.run(f"dropdb {TEST_DB_NAME}", shell=True)
    print(f"Dropped database: {TEST_DB_NAME}")

    print("\n" + "=" * 70)
    print("EXISTING DATA UPGRADE TEST: PASS (100% Intact, Zero Data Loss)")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
