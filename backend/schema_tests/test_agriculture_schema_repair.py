"""Controlled repair tests; a fresh disposable CI database is mandatory for DDL.

The fixture contains catalog column definitions only, never production row data.
No historical Alembic upgrade or Base.metadata.create_all prepares the repair.
"""
import importlib.util
import json
import os
import re
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "alembic/versions/2026_10_23_1509-615d2865c464_reconcile_missing_agriculture_schema_.py"
spec = importlib.util.spec_from_file_location("agriculture_repair", MIGRATION)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)

PROJECT_CONSTRAINTS = [
  {
    "name": "fk_projects_jurisdiction_id_jurisdictions",
    "table": "projects",
    "definition": "FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id) ON DELETE SET NULL"
  },
  {
    "name": "fk_projects_methodology_id_methodologies",
    "table": "projects",
    "definition": "FOREIGN KEY (methodology_id) REFERENCES methodologies(id) ON DELETE RESTRICT"
  },
  {
    "name": "fk_projects_methodology_version_id_methodology_versions",
    "table": "projects",
    "definition": "FOREIGN KEY (methodology_version_id) REFERENCES methodology_versions(id) ON DELETE RESTRICT"
  },
  {
    "name": "fk_projects_organization_id_organizations",
    "table": "projects",
    "definition": "FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE"
  },
  {
    "name": "fk_projects_programme_id_climate_programmes",
    "table": "projects",
    "definition": "FOREIGN KEY (programme_id) REFERENCES climate_programmes(id) ON DELETE RESTRICT"
  },
  {
    "name": "projects_sector_id_fkey",
    "table": "projects",
    "definition": "FOREIGN KEY (sector_id) REFERENCES methodology_families(id) ON DELETE RESTRICT"
  }
]


def validated_test_url(raw):
    url = make_url(raw)
    if (url.host not in {"127.0.0.1", "localhost"} or url.port != 5432
            or url.database != "test_db" or url.username != "test_user"
            or url.get_backend_name() != "postgresql" or url.query):
        raise ValueError("Only the explicit disposable CI PostGIS service is allowed")
    return url.set(drivername="postgresql+psycopg2")


@pytest.mark.parametrize("raw", [
    "postgresql://test_user:x@db.example.com:5432/test_db",
    "postgresql://test_user:x@localhost:5432/postgres",
    "postgresql://postgres:x@localhost:5432/test_db",
    "postgresql://test_user:x@localhost:6543/test_db",
    "postgresql://test_user:x@localhost:5432/test_db?host=db.example.com",
])
def test_non_disposable_targets_are_rejected(raw):
    with pytest.raises(ValueError):
        validated_test_url(raw)


def test_downgrade_preserves_records():
    with pytest.raises(RuntimeError, match="Data-preserving"):
        repair.downgrade()


def raw_sql(conn, statement):
    # No parameter interpolation: the frozen PL/pgSQL uses format('%I', ...).
    with conn.connection.driver_connection.cursor() as cursor:
        cursor.execute(statement)


@pytest.fixture
def repaired_db():
    raw = os.environ.get("SCHEMA_REPAIR_TEST_URL")
    if not raw:
        pytest.skip("SCHEMA_REPAIR_TEST_URL required; no default database fallback")
    url = validated_test_url(raw)
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    database = "vf_agri_repair_" + uuid.uuid4().hex[:16]
    with admin.connect() as conn:
        conn.exec_driver_sql(f'CREATE DATABASE "{database}"')
    admin.dispose()
    engine = create_engine(url.set(database=database))
    columns = json.loads((Path(__file__).with_name("live_schema_columns.json")).read_text())
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA extensions")
        conn.exec_driver_sql("CREATE EXTENSION postgis WITH SCHEMA extensions")
        conn.exec_driver_sql("SET search_path=public,extensions")
        for role in ("anon", "authenticated", "service_role"):
            raw_sql(conn, f"""DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}') THEN
                    CREATE ROLE {role} NOLOGIN;
                END IF;
            END $$;""")
        for name in sorted({col["table_name"] for col in columns}):
            definitions = []
            for col in columns:
                if col["table_name"] != name:
                    continue
                definition = f'"{col["column_name"]}" {col["sql_type"]}'
                if col["not_null"]:
                    definition += " NOT NULL"
                if col["default_sql"] is not None:
                    definition += " DEFAULT " + col["default_sql"]
                if col["column_name"] == "id":
                    definition += " PRIMARY KEY"
                definitions.append(definition)
            conn.exec_driver_sql(f'CREATE TABLE public."{name}" ({", ".join(definitions)})')
        for con in PROJECT_CONSTRAINTS:
            conn.exec_driver_sql(f'ALTER TABLE public.projects ADD CONSTRAINT "{con["name"]}" {con["definition"]}')
        # Only a synthetic sentinel, not a copy of operational activity data/partitioning.
        conn.exec_driver_sql("CREATE TABLE activities (id uuid PRIMARY KEY, project_id uuid, data jsonb)")
        conn.exec_driver_sql("CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)")
        conn.exec_driver_sql("INSERT INTO alembic_version VALUES ('3307d715f0e7')")
    from app.domains.organizations.models import Organization
    from app.domains.projects.models import Project
    from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily, MethodologyRegistry
    with Session(engine) as session:
        org = Organization(name="Existing fixture tenant", licensed_sectors=["COOKSTOVE"], licensed_methodologies=["FIXTURE"])
        registry = MethodologyRegistry(code="FIXTURE", name="Fixture registry")
        family = MethodologyFamily(code="COOKSTOVE", name="Fixture sector")
        session.add_all([org, registry, family])
        session.flush()
        method = Methodology(code="FIXTURE", name="Protected fixture methodology", registry_id=registry.id, family_id=family.id)
        session.add(method)
        session.flush()
        project = Project(name="Protected fixture pilot", project_code="FIXTURE-PILOT",
                          organization_id=org.id, methodology_id=method.id,
                          sector_id=family.id, baseline_parameters={"telemetry_pilot": True})
        session.add(project)
        session.flush()
        session.execute(text("INSERT INTO activities VALUES (:id, :project, CAST(:data AS jsonb))"),
                        {"id": uuid.uuid4(), "project": project.id, "data": '{"test_mode":true}'})
        session.commit()
    yield engine
    # No database/table deletion. GitHub destroys its entire disposable service.
    engine.dispose()


def apply(engine):
    with engine.begin() as conn:
        raw_sql(conn, repair.REPAIR_SQL)


def snapshot(engine):
    with engine.connect() as conn:
        return {
            table: conn.execute(text(
                f"SELECT to_jsonb(t)::text FROM public.{table} t ORDER BY id"
            )).scalars().all()
            for table in ("projects", "activities", "organizations", "methodologies")
        }


def test_full_repair_matches_all_model_columns_and_preserves_existing_records(repaired_db):
    from app.db.base import Base
    before = snapshot(repaired_db)
    before_fk = inspect(repaired_db).get_foreign_keys("projects")
    assert not next(c for c in inspect(repaired_db).get_columns("projects") if c["name"] == "methodology_id")["nullable"]
    apply(repaired_db)
    assert snapshot(repaired_db) == before
    assert inspect(repaired_db).get_foreign_keys("projects") == before_fk
    for name in repair.REPAIR_TABLES:
        actual = {c["name"]: c for c in inspect(repaired_db).get_columns(name)}
        expected = Base.metadata.tables[name]
        assert actual.keys() == set(expected.columns.keys()), name
        for column in expected.columns:
            assert actual[column.name]["nullable"] == column.nullable, (name, column.name)
        with repaired_db.connect() as conn:
            conn.execute(select(expected).limit(0))
    with repaired_db.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "3307d715f0e7"
        rls = conn.execute(text(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace"
        )).all()
        assert all(dict(rls)[name] for name in repair.REPAIR_TABLES)
        for role in ("anon", "authenticated", "service_role"):
            for name in repair.REPAIR_TABLES:
                assert not conn.execute(text("SELECT has_table_privilege(:role, :name, 'SELECT,INSERT,UPDATE,DELETE')"),
                                        {"role": role, "name": "public."+name}).scalar_one()


def test_partial_schema_aborts_before_constraint_change(repaired_db):
    with repaired_db.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE land_units (id uuid PRIMARY KEY)")
    with pytest.raises(Exception, match="target table land_units already exists"):
        apply(repaired_db)
    assert set(inspect(repaired_db).get_table_names()) & set(repair.REPAIR_TABLES) == {"land_units"}
    assert not next(c for c in inspect(repaired_db).get_columns("projects") if c["name"] == "methodology_id")["nullable"]


def test_mid_repair_failure_rolls_back_all_ddl(repaired_db):
    broken = repair.REPAIR_SQL.replace(
        "END;\n$agriculture_repair$;", "RAISE EXCEPTION 'Injected failure';\nEND;\n$agriculture_repair$;"
    )
    assert broken != repair.REPAIR_SQL
    before = snapshot(repaired_db)
    with pytest.raises(Exception, match="Injected failure"):
        with repaired_db.begin() as conn:
            raw_sql(conn, broken)
    assert not (set(inspect(repaired_db).get_table_names()) & set(repair.REPAIR_TABLES))
    assert not next(c for c in inspect(repaired_db).get_columns("projects") if c["name"] == "methodology_id")["nullable"]
    assert snapshot(repaired_db) == before


def test_known_historical_gap_is_completed_without_rewriting_existing_tables(repaired_db):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    # Build the known 25-table predecessor in this disposable database without DROP.
    sql = repair.REPAIR_SQL
    start = sql.index('    CREATE TABLE public.')
    end = sql.index('    -- FastAPI uses')
    groups = re.split(r'(?=    CREATE TABLE public\.)', sql[start:end])
    missing = set(repair.HISTORICAL_MISSING_TABLES)
    kept = [g for g in groups if g and re.match(r'    CREATE TABLE public\.(\w+)', g).group(1) not in missing]
    targets = tuple(n for n in repair.REPAIR_TABLES if n not in missing)
    original_array = 'ARRAY[' + ', '.join(repr(n) for n in repair.REPAIR_TABLES) + ']'
    fixture_array = 'ARRAY[' + ', '.join(repr(n) for n in targets) + ']'
    fixture_sql = (sql[:start] + ''.join(kept) + sql[end:]).replace(original_array, fixture_array)
    with repaired_db.begin() as conn:
        raw_sql(conn, fixture_sql)
    before = snapshot(repaired_db)
    with repaired_db.connect() as conn:
        rls_before = dict(conn.execute(text("SELECT relname, relrowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace")).all())
    with repaired_db.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            repair.upgrade()
    assert set(inspect(repaired_db).get_table_names()) >= set(repair.REPAIR_TABLES)
    assert snapshot(repaired_db) == before
    with repaired_db.connect() as conn:
        rls_after = dict(conn.execute(text("SELECT relname, relrowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace")).all())
    assert all(rls_before[n] == rls_after[n] for n in targets)


@pytest.mark.asyncio
async def test_unassigned_foundation_and_land_unit_persist_without_methodology(repaired_db):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.domains.organizations.models import Organization
    from app.domains.projects.models import Project
    from app.domains.methodologies.models.base_registry import MethodologyFamily
    from app.domains.agriculture.models import LandUnit
    from app.domains.agriculture.schemas import LandUnitCreate
    from app.domains.agriculture.service import AgricultureService
    apply(repaired_db)
    engine = create_async_engine(repaired_db.url.set(drivername="postgresql+asyncpg"), connect_args={"server_settings": {"search_path": "public,extensions"}})
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            org = Organization(name="Unassigned agriculture fixture", licensed_sectors=["AGRICULTURE_LAND_USE"], licensed_methodologies=[])
            family = MethodologyFamily(code="AGRICULTURE_LAND_USE", name="Agriculture & Land Use")
            db.add_all([org, family])
            await db.flush()
            project = Project(name="Unassigned fixture", project_code="AGR-FIXTURE", organization_id=org.id,
                              sector_id=family.id, methodology_id=None, baseline_source=None,
                              diesel_emission_factor=None, grid_emission_factor=None, baseline_parameters={})
            db.add(project)
            await db.flush()
            foundation = await AgricultureService.get_project_foundation(db, project.id, org.id)
            assert foundation["methodology_lock_status"] == "NOT_CONFIGURED"
            assert foundation["methodology"] == {}
            unit = await AgricultureService.create_land_unit(db, LandUnitCreate(
                project_id=project.id, name="Fixture field",
                boundary_geojson={"type":"Polygon","coordinates":[[[77.1,28.5],[77.11,28.5],[77.11,28.51],[77.1,28.51],[77.1,28.5]]]},
                boundary_source="DECLARED",
            ), org.id)
            await db.commit()
            assert await db.get(LandUnit, unit.id) is not None
            assert project.methodology_id is None
            assert org.licensed_methodologies == []
            assert unit.area_ha > 0
            foundation = await AgricultureService.get_project_foundation(db, project.id, org.id)
            assert foundation["land_units_count"] == 1
            assert await AgricultureService.get_land_units(db, uuid.uuid4(), project_id=project.id) == []
        # Defense in depth: even an accidental SELECT grant does not bypass new-table RLS.
        with repaired_db.begin() as conn:
            conn.exec_driver_sql("GRANT SELECT ON land_units TO anon")
            conn.exec_driver_sql("SET LOCAL ROLE anon")
            assert conn.execute(text("SELECT count(*) FROM land_units")).scalar_one() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_existing_collection_contract_against_repaired_postgis(repaired_db):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    apply(repaired_db)
    spec = importlib.util.spec_from_file_location("ground_workflow_contract", ROOT / "tests/domains/agriculture/test_agriculture_mrv_phase2.py")
    contracts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contracts)
    engine = create_async_engine(repaired_db.url.set(drivername="postgresql+asyncpg"), connect_args={"server_settings": {"search_path": "public,extensions"}})
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            # These existing contracts explicitly seed/select VM0042 in this synthetic fixture only.
            await contracts.test_field_collection_and_geodesic_deviation(db)
            await db.commit()
    finally:
        await engine.dispose()
