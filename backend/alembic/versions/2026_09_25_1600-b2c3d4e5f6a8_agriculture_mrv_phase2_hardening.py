"""Agriculture MRV Phase 2: Scientific Precision, Accreditation Evidence, and Snapshot Hardening

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-09-25 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a8'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = insp.get_table_names()

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    empty_json = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")
    now_default = sa.text("CURRENT_TIMESTAMP") if is_sqlite else sa.text("now()")
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    def column_exists(table_name: str, col_name: str) -> bool:
        if table_name not in existing_tables:
            return False
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return col_name in cols

    # 1. sampling_plan_versions -> plan_lock_snapshot
    if "sampling_plan_versions" in existing_tables:
        if not column_exists("sampling_plan_versions", "plan_lock_snapshot"):
            op.add_column(
                "sampling_plan_versions",
                sa.Column("plan_lock_snapshot", json_type, nullable=False, server_default=empty_json),
            )

    # 2. sample_collection_events -> server_received_at
    if "sample_collection_events" in existing_tables:
        if not column_exists("sample_collection_events", "server_received_at"):
            op.add_column(
                "sample_collection_events",
                sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
            )

    # 3. laboratory_analyses -> accreditation_status & accreditation_evidence_id
    if "laboratory_analyses" in existing_tables:
        if not column_exists("laboratory_analyses", "accreditation_status"):
            op.add_column(
                "laboratory_analyses",
                sa.Column("accreditation_status", sa.String(30), nullable=False, server_default="UNVERIFIED"),
            )
        if not column_exists("laboratory_analyses", "accreditation_evidence_id"):
            op.add_column(
                "laboratory_analyses",
                sa.Column(
                    "accreditation_evidence_id",
                    uuid_type,
                    sa.ForeignKey("evidence_records.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )

    # 4. laboratory_results -> quantification_limit, normalization_version, supersedes_id
    if "laboratory_results" in existing_tables:
        if not column_exists("laboratory_results", "quantification_limit"):
            op.add_column(
                "laboratory_results",
                sa.Column("quantification_limit", sa.Numeric(12, 4), nullable=True),
            )
        if not column_exists("laboratory_results", "normalization_version"):
            op.add_column(
                "laboratory_results",
                sa.Column("normalization_version", sa.String(30), nullable=True),
            )
        if not column_exists("laboratory_results", "supersedes_id"):
            op.add_column(
                "laboratory_results",
                sa.Column(
                    "supersedes_id",
                    uuid_type,
                    sa.ForeignKey("laboratory_results.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    def column_exists(table_name: str, col_name: str) -> bool:
        if table_name not in existing_tables:
            return False
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return col_name in cols

    if "laboratory_results" in existing_tables:
        for col in ["supersedes_id", "normalization_version", "quantification_limit"]:
            if column_exists("laboratory_results", col):
                op.drop_column("laboratory_results", col)

    if "laboratory_analyses" in existing_tables:
        for col in ["accreditation_evidence_id", "accreditation_status"]:
            if column_exists("laboratory_analyses", col):
                op.drop_column("laboratory_analyses", col)

    if "sample_collection_events" in existing_tables:
        if column_exists("sample_collection_events", "server_received_at"):
            op.drop_column("sample_collection_events", "server_received_at")

    if "sampling_plan_versions" in existing_tables:
        if column_exists("sampling_plan_versions", "plan_lock_snapshot"):
            op.drop_column("sampling_plan_versions", "plan_lock_snapshot")
