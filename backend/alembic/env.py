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
    if name.endswith('.models'):
        try:
            importlib.import_module(name)
        except ImportError:
            pass

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    # Replace +asyncpg with standard postgresql for sync driver
    url = str(settings.database_url).replace("+asyncpg", "").split("?")[0]
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

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
