from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

from app.core.config import settings
from app.db.base import Base
import importlib
import pkgutil
from app import domains

for _, name, _ in pkgutil.walk_packages(domains.__path__, domains.__name__ + '.'):
    if name.endswith('.models') or name.endswith('.puro_models'):
        try:
            importlib.import_module(name)
        except ImportError:
            pass

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    cmd_url = config.get_main_option("sqlalchemy.url")
    if cmd_url:
        return cmd_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    # Replace +asyncpg and +aiosqlite with standard drivers for sync migrations
    url = str(settings.database_url).replace("+asyncpg", "").replace("+aiosqlite", "").split("?")[0]
    # Force use of port 5432 (Session pooler / direct DB) instead of 6543 (Transaction pooler) which hangs on migrations
    url = url.replace(":6543/", ":5432/")
    return url

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name and "activities_y" in name:
        return False
    if type_ == "index" and name and "activities_y" in name:
        return False
    return True

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    from sqlalchemy import event
    @event.listens_for(connectable, "before_cursor_execute", retval=True)
    def clean_statement_syntax(conn, cursor, statement, parameters, context, executemany):
        if "ALTER TABLE carbon_calculations" in statement and "ADD COLUMN" in statement:
            id_type = "TEXT" if connectable.dialect.name == "sqlite" else "UUID"
            cursor.execute(f"CREATE TABLE IF NOT EXISTS carbon_calculations (id {id_type} PRIMARY KEY, project_id {id_type}, activity_id {id_type})")

        if "REFERENCES activities (id)" in statement:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_activities_id ON activities (id)")

        if "REFERENCES land_units (id)" in statement:
            id_type = "TEXT" if connectable.dialect.name == "sqlite" else "UUID"
            cursor.execute(f"CREATE TABLE IF NOT EXISTS land_units (id {id_type} PRIMARY KEY, organization_id {id_type}, name VARCHAR(255))")

        if connectable.dialect.name == "sqlite":
            import re
            if "ALTER COLUMN" in statement:
                return "SELECT 1", parameters
            cleaned = (
                statement.replace("DEFAULT gen_random_uuid()", "")
                .replace("DEFAULT now()", "DEFAULT CURRENT_TIMESTAMP")
                .replace("JSONB", "JSON")
                .replace("DROP INDEX IF EXISTS ", "DROP INDEX IF EXISTS ")
                .replace("DROP INDEX ", "DROP INDEX IF EXISTS ")
                .replace("DROP TABLE IF EXISTS ", "DROP TABLE IF EXISTS ")
                .replace("DROP TABLE ", "DROP TABLE IF EXISTS ")
            )
            cleaned = re.sub(r"::[a-zA-Z0-9_]+", "", cleaned)
            return cleaned, parameters
        elif connectable.dialect.name == "postgresql":
            if "ALTER TABLE " in statement and " ADD CONSTRAINT " in statement:
                statement = f"DO $$ BEGIN {statement}; EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
                return statement, parameters

            cleaned = (
                statement.replace("DROP INDEX IF EXISTS ", "DROP INDEX IF EXISTS ")
                .replace("DROP INDEX ", "DROP INDEX IF EXISTS ")
                .replace("DROP TABLE IF EXISTS ", "DROP TABLE IF EXISTS ")
                .replace("DROP TABLE ", "DROP TABLE IF EXISTS ")
                .replace("DROP CONSTRAINT IF EXISTS ", "DROP CONSTRAINT IF EXISTS ")
                .replace("DROP CONSTRAINT ", "DROP CONSTRAINT IF EXISTS ")
                .replace("DROP COLUMN IF EXISTS ", "DROP COLUMN IF EXISTS ")
                .replace("DROP COLUMN ", "DROP COLUMN IF EXISTS ")
                .replace("ADD COLUMN IF NOT EXISTS ", "ADD COLUMN IF NOT EXISTS ")
                .replace("ADD COLUMN ", "ADD COLUMN IF NOT EXISTS ")
            )
            return cleaned, parameters
        return statement, parameters

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=(connectable.dialect.name == "sqlite")
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
