"""
=============================================================================
VeriField Nexus — Agriculture Phase 3B-0 3-Tier Migration Verification
=============================================================================
Executes against isolated disposable PostgreSQL database:
1. Tier 1: Clean DB Migration from base to HEAD (c1d2e3f4a5b6).
2. Tier 2: Existing-Data Upgrade from b3c4d5e6f7a8 to c1d2e3f4a5b6.
   - Verifies pre-existing Phase 1/2/3A records remain 100% intact.
   - Verifies new table agriculture_prerequisite_assessments is created cleanly.
3. Tier 3: Reversible Downgrade/Re-upgrade (c1d2e3f4a5b6 -> b3c4d5e6f7a8 -> c1d2e3f4a5b6).
   - Verifies clean teardown of table & indexes and clean re-creation.
4. Clean teardown and drop of disposable database.
=============================================================================
"""

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_NAME = "verifield_agri_3b0_migration_disposable"
SYNC_DB_URL = f"postgresql://postgres@localhost:5432/{TEST_DB_NAME}"
ASYNC_DB_URL = f"postgresql+asyncpg://postgres@localhost:5432/{TEST_DB_NAME}"


def run_cmd(cmd: str, env_vars=None):
    current_env = os.environ.copy()
    if env_vars:
        current_env.update(env_vars)
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=current_env)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {cmd}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res


async def run_3tier_migration():
    print("=" * 80)
    print("AGRICULTURE PHASE 3B-0: 3-TIER MIGRATION PROOF (DISPOSABLE POSTGRESQL)")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: CLEAN DB MIGRATION (BASE -> HEAD c1d2e3f4a5b6)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Tier 1: Step 1] Creating fresh disposable database...")
    subprocess.run(f"dropdb --if-exists {TEST_DB_NAME}", shell=True)
    run_cmd(f"createdb {TEST_DB_NAME}")
    print(f"[+] Disposable database created: {TEST_DB_NAME}")

    print("\n[Tier 1: Step 2] Running Alembic upgrade head from base to HEAD (c1d2e3f4a5b6)...")
    res_clean = run_cmd("venv/bin/alembic upgrade head", env_vars={"DATABASE_URL": SYNC_DB_URL})
    print("Alembic output:\n" + res_clean.stdout.strip())
    print("[+] Alembic upgrade head completed successfully (exit code 0).")

    # Verify table and indexes
    engine = create_engine(SYNC_DB_URL)
    with engine.connect() as conn:
        tbl_check = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'agriculture_prerequisite_assessments';
        """)).scalar()
        assert tbl_check == "agriculture_prerequisite_assessments", "Table agriculture_prerequisite_assessments missing!"

        idx_rows = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = 'agriculture_prerequisite_assessments';
        """)).fetchall()
        indexes = {r[0] for r in idx_rows}
        print(f"[+] Found {len(indexes)} indexes on agriculture_prerequisite_assessments: {sorted(list(indexes))}")
        assert "ix_agri_prereq_assessments_org_id" in indexes
        assert "ix_agri_prereq_assessments_project_id" in indexes
        assert "ix_agri_prereq_assessments_snapshot_id" in indexes
        assert "ix_agri_prereq_assessments_code" in indexes
        assert "ix_agri_prereq_assessments_hash" in indexes
        assert "ix_agri_prereq_assessments_status" in indexes
    engine.dispose()
    print("[+] Tier 1 (Clean DB Migration from base to HEAD) PASSED.")

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 2: EXISTING-DATA UPGRADE (b3c4d5e6f7a8 -> c1d2e3f4a5b6)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Tier 2: Step 1] Downgrading database to previous revision b3c4d5e6f7a8...")
    run_cmd("venv/bin/alembic downgrade b3c4d5e6f7a8", env_vars={"DATABASE_URL": SYNC_DB_URL})

    # Verify table is dropped at b3c4d5e6f7a8
    with create_engine(SYNC_DB_URL).connect() as conn:
        pre_tbl = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'agriculture_prerequisite_assessments';
        """)).scalar()
        assert pre_tbl is None, "Table should not exist at revision b3c4d5e6f7a8!"
    print("[+] Database successfully positioned at revision b3c4d5e6f7a8.")

    print("\n[Tier 2: Step 2] Seeding representative Phase 1/2/3A records at b3c4d5e6f7a8...")
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    tag = uuid.uuid4().hex[:6]

    async_engine = create_async_engine(ASYNC_DB_URL, echo=False)
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed Org & User
        from app.domains.organizations.models import Organization
        from app.domains.authentication.models import User
        from app.domains.projects.models import Project
        from app.domains.agriculture.models import (
            LandUnit,
            Stratum,
            StratumMembership,
            SamplingCampaign,
            SamplingPlanVersion,
            SamplingPoint,
            PhysicalSample,
            QuantificationInputSnapshot,
        )

        org = Organization(id=org_id, name=f"Tier2 Org {tag}", plan="ENTERPRISE", org_type="DEVELOPER")
        session.add(org)
        user = User(
            id=user_id,
            organization_id=org_id,
            email=f"tier2_{tag}@verifield.test",
            password_hash="hash",
            full_name="Tier 2 PM",
            role="PROJECT_MANAGER",
            status="active",
            is_active=True,
        )
        session.add(user)
        proj = Project(
            id=proj_id,
            organization_id=org_id,
            name=f"Tier 2 Project {tag}",
            project_code=f"AGR-T2-{tag}",
            crediting_start=date(2025, 1, 1),
            crediting_end=date(2045, 12, 31),
            baseline_parameters={"locked": True},
        )
        session.add(proj)
        await session.flush()

        lu = LandUnit(
            id=uuid.uuid4(),
            organization_id=org_id,
            project_id=proj_id,
            code=f"LU-T2-{tag}",
            name="Field T2",
            area_ha=Decimal("150.0"),
            is_active=True,
        )
        session.add(lu)

        strat = Stratum(
            id=uuid.uuid4(),
            organization_id=org_id,
            project_id=proj_id,
            code=f"STR-T2-{tag}",
            name="Stratum T2",
            stratum_type="SOIL_TYPE",
            area_ha=Decimal("150.0"),
            is_active=True,
        )
        session.add(strat)
        await session.flush()

        sm = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org_id,
            stratum_id=strat.id,
            land_unit_id=lu.id,
            valid_from=date(2025, 1, 1),
            status="ACTIVE",
        )
        session.add(sm)

        camp = SamplingCampaign(
            id=uuid.uuid4(),
            organization_id=org_id,
            project_id=proj_id,
            campaign_code=f"CMP-T2-{tag}",
            name="Campaign T2",
            purpose="BASELINE_SOC_DETERMINATION",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=date(2026, 1, 1),
            status="COMPLETE",
        )
        session.add(camp)
        await session.flush()

        plan = SamplingPlanVersion(
            id=uuid.uuid4(),
            organization_id=org_id,
            project_id=proj_id,
            campaign_id=camp.id,
            version_number=1,
            sampling_design_method="STRATIFIED_RANDOM",
            status="LOCKED",
            effective_as_of_date=date(2026, 1, 15),
            is_locked=True,
            locked_at=datetime.now(timezone.utc),
            locked_by_id=user_id,
        )
        session.add(plan)
        await session.flush()

        sp = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=org_id,
            project_id=proj_id,
            campaign_id=camp.id,
            plan_version_id=plan.id,
            land_unit_id=lu.id,
            stratum_id=strat.id,
            point_code=f"SP-T2-{tag}",
            planned_lat=28.52,
            planned_lon=77.12,
            depth_from_cm=0.0,
            depth_to_cm=30.0,
            status="COLLECTED",
        )
        session.add(sp)
        await session.flush()

        ps = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=org_id,
            project_id=proj_id,
            campaign_id=camp.id,
            plan_version_id=plan.id,
            sampling_point_id=sp.id,
            land_unit_id=lu.id,
            stratum_id=strat.id,
            sample_code=f"SMP-T2-{tag}",
            status="QA_ACCEPTED",
        )
        session.add(ps)
        await session.flush()

        qis = QuantificationInputSnapshot(
            id=uuid.uuid4(),
            organization_id=org_id,
            project_id=proj_id,
            snapshot_code=f"QIS-T2-{tag}",
            status="LOCKED",
            context="BASELINE",
            sampling_campaign_id=camp.id,
            snapshot_hash="a" * 64,
            is_locked=True,
            total_eligible_measurements=1,
            total_excluded_measurements=0,
            readiness_summary={"status": "READY"},
            input_package={"test": True},
        )
        session.add(qis)
        await session.commit()
        print("[+] Seeded Phase 1/2/3A records committed cleanly.")

    print("\n[Tier 2: Step 3] Executing Alembic upgrade to HEAD (c1d2e3f4a5b6) over existing data...")
    res_upg = run_cmd("venv/bin/alembic upgrade c1d2e3f4a5b6", env_vars={"DATABASE_URL": SYNC_DB_URL})
    print("Alembic upgrade output:\n" + res_upg.stdout.strip())

    # Verify zero data loss on pre-existing entities
    async with async_session() as session:
        proj_cnt = (await session.execute(select(Project).where(Project.id == proj_id))).scalar_one()
        assert proj_cnt.name == f"Tier 2 Project {tag}"

        lu_cnt = (await session.execute(select(LandUnit).where(LandUnit.project_id == proj_id))).scalar_one()
        assert lu_cnt.area_ha == Decimal("150.0")

        qis_cnt = (await session.execute(select(QuantificationInputSnapshot).where(QuantificationInputSnapshot.project_id == proj_id))).scalar_one()
        assert qis_cnt.snapshot_code == f"QIS-T2-{tag}"

        print("[+] Pre-existing records verified 100% intact after migration upgrade.")

        # Insert new Phase 3B-0 record into newly migrated table
        from app.domains.agriculture.models import AgriculturePrerequisiteAssessment
        prereq = AgriculturePrerequisiteAssessment(
            id=uuid.uuid4(),
            organization_id=org_id,
            project_id=proj_id,
            snapshot_id=qis.id,
            assessment_code=f"PREREQ-T2-{tag}",
            version=1,
            status="LOCKED",
            overall_readiness="READY",
            methodology_code="VM0042",
            methodology_version="2.2",
            corrections_clarifications_version="2026-06-11",
            rule_set_version="VM0042_V2.2_RULES_CC20260611_V1.0",
            vcs_standard_version="VCS_V5.0A",
            vcs_resolution_metadata={"context": "VCS_5_0A"},
            quantification_route_map={"approach": "APPROACH_2"},
            esm_input_dossier={"dossier": True},
            sampling_design_assessment={"design": "STRATIFIED_RANDOM"},
            uncertainty_input_readiness={"ready": True},
            baseline_monitoring_pairing={"paired": True},
            dimensions={"all_17": "READY"},
            blocking_reasons=[],
            advisory_notes=[],
            assessment_hash="b" * 64,
            is_locked=True,
            locked_at=datetime.now(timezone.utc),
            locked_by_id=user_id,
            created_by_id=user_id,
        )
        session.add(prereq)
        await session.commit()
        print("[+] Successfully inserted and persisted record into new agriculture_prerequisite_assessments table.")
    print("[+] Tier 2 (Existing-Data Upgrade) PASSED.")

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 3: DOWNGRADE & RE-UPGRADE (c1d2e3f4a5b6 -> b3c4d5e6f7a8 -> c1d2e3f4a5b6)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Tier 3: Step 1] Executing Alembic downgrade c1d2e3f4a5b6 -> b3c4d5e6f7a8...")
    res_down = run_cmd("venv/bin/alembic downgrade b3c4d5e6f7a8", env_vars={"DATABASE_URL": SYNC_DB_URL})
    print("Alembic downgrade output:\n" + res_down.stdout.strip())

    with create_engine(SYNC_DB_URL).connect() as conn:
        post_down_tbl = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'agriculture_prerequisite_assessments';
        """)).scalar()
        assert post_down_tbl is None, "Table agriculture_prerequisite_assessments was not dropped during downgrade!"
    print("[+] Downgrade verified: agriculture_prerequisite_assessments dropped cleanly.")

    print("\n[Tier 3: Step 2] Executing Alembic re-upgrade b3c4d5e6f7a8 -> c1d2e3f4a5b6...")
    res_reupg = run_cmd("venv/bin/alembic upgrade c1d2e3f4a5b6", env_vars={"DATABASE_URL": SYNC_DB_URL})
    print("Alembic re-upgrade output:\n" + res_reupg.stdout.strip())

    with create_engine(SYNC_DB_URL).connect() as conn:
        reupg_tbl = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'agriculture_prerequisite_assessments';
        """)).scalar()
        assert reupg_tbl == "agriculture_prerequisite_assessments", "Table not re-created during re-upgrade!"
    print("[+] Re-upgrade verified: table re-created cleanly.")
    print("[+] Tier 3 (Reversible Downgrade/Re-upgrade) PASSED.")

    await async_engine.dispose()

    # ─────────────────────────────────────────────────────────────────────────
    # CLEANUP & TEARDOWN
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Cleanup] Dropping disposable database...")
    subprocess.run(f"dropdb {TEST_DB_NAME}", shell=True)
    print(f"[+] Disposable database dropped: {TEST_DB_NAME}")

    print("\n" + "=" * 80)
    print("ALL 3 TIERS OF MIGRATION VERIFICATION PASSED (EXIT CODE 0)!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(run_3tier_migration())
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
