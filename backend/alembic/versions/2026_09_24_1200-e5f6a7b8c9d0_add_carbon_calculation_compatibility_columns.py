"""Restore carbon calculation compatibility columns and schema harmonization

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    existing_cols = {c["name"] for c in insp.get_columns("carbon_calculations")}
    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    empty_json = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")
    now_default = sa.text("CURRENT_TIMESTAMP") if is_sqlite else sa.text("now()")

    # 1. Add backward-compatible columns if missing
    if "tco2e_generated" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("tco2e_generated", sa.Float(), nullable=True, server_default="0.0"))
    if "status" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("status", sa.String(50), nullable=True, server_default="calculated"))
    if "created_at" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=now_default))
    if "calculation_log" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("calculation_log", json_type, nullable=True, server_default=empty_json))
    if "methodology_used" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("methodology_used", sa.UUID(), nullable=True))

    # 2. Add modern CIOS columns if missing (e.g. if run in fresh SQLite test DB)
    if "tco2e_yield" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("tco2e_yield", sa.Float(), nullable=True, server_default="0.0"))
    if "methodology_version_id" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("methodology_version_id", sa.UUID(), nullable=True))
    if "uncertainty" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("uncertainty", sa.Float(), nullable=True, server_default="0.05"))
    if "execution_inputs" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("execution_inputs", json_type, nullable=True, server_default=empty_json))
    if "execution_outputs" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("execution_outputs", json_type, nullable=True, server_default=empty_json))
    if "audit_replay" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("audit_replay", json_type, nullable=True, server_default=empty_json))
    if "registry_references" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("registry_references", json_type, nullable=True, server_default=empty_json))
    if "executed_at" not in existing_cols:
        op.add_column("carbon_calculations", sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True, server_default=now_default))

    # 3. Soften non-null constraints and add server defaults on PostgreSQL if columns already existed
    if not is_sqlite:
        op.alter_column("carbon_calculations", "tco2e_yield", nullable=True, server_default="0.0")
        op.alter_column("carbon_calculations", "execution_inputs", nullable=True, server_default=empty_json)
        op.alter_column("carbon_calculations", "execution_outputs", nullable=True, server_default=empty_json)
        op.alter_column("carbon_calculations", "audit_replay", nullable=True, server_default=empty_json)

        # Synchronize any existing values
        op.execute(sa.text("""
            UPDATE carbon_calculations
            SET tco2e_generated = tco2e_yield
            WHERE tco2e_generated IS NULL AND tco2e_yield IS NOT NULL;
        """))
        op.execute(sa.text("""
            UPDATE carbon_calculations
            SET tco2e_yield = tco2e_generated
            WHERE tco2e_yield IS NULL AND tco2e_generated IS NOT NULL;
        """))
        op.execute(sa.text("""
            UPDATE carbon_calculations
            SET created_at = executed_at
            WHERE created_at IS NULL AND executed_at IS NOT NULL;
        """))
        op.execute(sa.text("""
            UPDATE carbon_calculations
            SET executed_at = created_at
            WHERE executed_at IS NULL AND created_at IS NOT NULL;
        """))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_cols = {c["name"] for c in insp.get_columns("carbon_calculations")}

    for col in ["tco2e_generated", "status", "created_at", "calculation_log", "methodology_used"]:
        if col in existing_cols:
            op.drop_column("carbon_calculations", col)
