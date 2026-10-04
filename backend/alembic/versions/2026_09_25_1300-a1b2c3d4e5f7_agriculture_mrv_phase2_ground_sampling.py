"""Agriculture MRV Phase 2: Ground Sampling, Chain of Custody & Laboratory Evidence

Revision ID: a1b2c3d4e5f7
Revises: f6a7b8c9d0e1
Create Date: 2026-09-25 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f7'
down_revision = 'f6a7b8c9d0e1'
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
    uuid_server_default = None if is_sqlite else sa.text("gen_random_uuid()")

    def column_exists(table_name: str, col_name: str) -> bool:
        if table_name not in existing_tables:
            return False
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return col_name in cols

    def index_exists(table_name: str, idx_name: str) -> bool:
        if table_name not in existing_tables:
            return False
        indexes = [i["name"] for i in insp.get_indexes(table_name)]
        return idx_name in indexes

    if not is_sqlite:
        try:
            op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        except Exception:
            pass

    # 0. Corroboration on agriculture_management_records
    if "agriculture_management_records" in existing_tables:
        if not column_exists("agriculture_management_records", "corroboration"):
            op.add_column(
                "agriculture_management_records",
                sa.Column("corroboration", sa.String(50), nullable=False, server_default="NONE"),
            )

    # 1. sampling_campaigns
    if "sampling_campaigns" not in existing_tables:
        op.create_table(
            "sampling_campaigns",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_code", sa.String(50), nullable=False, index=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("purpose", sa.String(50), nullable=False, server_default="BASELINE_SOC_DETERMINATION"),
            sa.Column("baseline_or_monitoring_context", sa.String(30), nullable=False, server_default="BASELINE"),
            sa.Column("planned_start_date", sa.Date(), nullable=False),
            sa.Column("planned_end_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
            sa.Column("methodology_lock_snapshot", json_type, nullable=False, server_default=empty_json),
            sa.Column("project_boundary_version_id", uuid_type, sa.ForeignKey("project_boundary_versions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_by_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 2. sampling_plan_versions
    if "sampling_plan_versions" not in existing_tables:
        op.create_table(
            "sampling_plan_versions",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", uuid_type, sa.ForeignKey("sampling_campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
            sa.Column("effective_as_of_date", sa.Date(), nullable=False),
            sa.Column("stratum_membership_snapshot", json_type, nullable=False, server_default=empty_json),
            sa.Column("sampling_design_method", sa.String(50), nullable=False, server_default="STRATIFIED_RANDOM"),
            sa.Column("design_provenance", sa.String(50), nullable=False, server_default="MANUAL"),
            sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("locked_by_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 3. sampling_points
    if "sampling_points" not in existing_tables:
        op.create_table(
            "sampling_points",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", uuid_type, sa.ForeignKey("sampling_campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("plan_version_id", uuid_type, sa.ForeignKey("sampling_plan_versions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("land_unit_id", uuid_type, sa.ForeignKey("land_units.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("stratum_id", uuid_type, sa.ForeignKey("agriculture_strata.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("point_code", sa.String(50), nullable=False, index=True),
            sa.Column("planned_lat", sa.Float(), nullable=False),
            sa.Column("planned_lon", sa.Float(), nullable=False),
            sa.Column("geom", sa.BLOB() if is_sqlite else Geometry(geometry_type="POINT", srid=4326), nullable=True),
            sa.Column("depth_from_cm", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("depth_to_cm", sa.Float(), nullable=False, server_default="30.0"),
            sa.Column("depth_class_label", sa.String(50), nullable=True),
            sa.Column("sampling_purpose", sa.String(50), nullable=False, server_default="SOC_STOCK"),
            sa.Column("replicate_group", sa.String(50), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="PLANNED"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 4. physical_samples
    if "physical_samples" not in existing_tables:
        op.create_table(
            "physical_samples",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", uuid_type, sa.ForeignKey("sampling_campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("plan_version_id", uuid_type, sa.ForeignKey("sampling_plan_versions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("sampling_point_id", uuid_type, sa.ForeignKey("sampling_points.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("land_unit_id", uuid_type, sa.ForeignKey("land_units.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("stratum_id", uuid_type, sa.ForeignKey("agriculture_strata.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("sample_code", sa.String(100), nullable=False, unique=True, index=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="PLANNED"),
            sa.Column("qr_barcode_code", sa.String(150), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 5. sample_collection_events
    if "sample_collection_events" not in existing_tables:
        op.create_table(
            "sample_collection_events",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("physical_sample_id", uuid_type, sa.ForeignKey("physical_samples.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("sampling_point_id", uuid_type, sa.ForeignKey("sampling_points.id", ondelete="CASCADE"), nullable=False),
            sa.Column("actual_lat", sa.Float(), nullable=False),
            sa.Column("actual_lon", sa.Float(), nullable=False),
            sa.Column("actual_geom", sa.BLOB() if is_sqlite else Geometry(geometry_type="POINT", srid=4326), nullable=True),
            sa.Column("deviation_distance_m", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("deviation_reason", sa.Text(), nullable=True),
            sa.Column("collection_timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("collector_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("collector_name", sa.String(100), nullable=False),
            sa.Column("actual_depth_from_cm", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("actual_depth_to_cm", sa.Float(), nullable=False, server_default="30.0"),
            sa.Column("sample_condition", sa.String(50), nullable=False, server_default="GOOD"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("photo_evidence_id", uuid_type, sa.ForeignKey("evidence_records.id", ondelete="SET NULL"), nullable=True),
            sa.Column("photo_hash", sa.String(64), nullable=True),
            sa.Column("device_metadata", json_type, nullable=False, server_default=empty_json),
            sa.Column("idempotency_key", sa.String(100), nullable=True, unique=True),
            sa.Column("sync_timestamp", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 6. chain_of_custody_events
    if "chain_of_custody_events" not in existing_tables:
        op.create_table(
            "chain_of_custody_events",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("physical_sample_id", uuid_type, sa.ForeignKey("physical_samples.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("custodian_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("custodian_name", sa.String(100), nullable=False),
            sa.Column("custodian_organization", sa.String(150), nullable=False),
            sa.Column("from_location", sa.String(150), nullable=True),
            sa.Column("to_location", sa.String(150), nullable=True),
            sa.Column("condition", sa.String(50), nullable=False, server_default="INTACT"),
            sa.Column("seal_intact", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("seal_identifier", sa.String(100), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("evidence_id", uuid_type, sa.ForeignKey("evidence_records.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 7. laboratory_receipts
    if "laboratory_receipts" not in existing_tables:
        op.create_table(
            "laboratory_receipts",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("physical_sample_id", uuid_type, sa.ForeignKey("physical_samples.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("laboratory_name", sa.String(150), nullable=False),
            sa.Column("laboratory_id_ref", sa.String(100), nullable=True),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("received_by_name", sa.String(100), nullable=False),
            sa.Column("condition_on_receipt", sa.String(50), nullable=False, server_default="ACCEPTABLE"),
            sa.Column("seal_status", sa.String(50), nullable=False, server_default="SEALED_INTACT"),
            sa.Column("intake_status", sa.String(30), nullable=False, server_default="ACCEPTED"),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("receipt_evidence_id", uuid_type, sa.ForeignKey("evidence_records.id", ondelete="SET NULL"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 8. laboratory_analyses
    if "laboratory_analyses" not in existing_tables:
        op.create_table(
            "laboratory_analyses",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("physical_sample_id", uuid_type, sa.ForeignKey("physical_samples.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("laboratory_name", sa.String(150), nullable=False),
            sa.Column("laboratory_accreditation", sa.String(100), nullable=True),
            sa.Column("analysis_batch_id", sa.String(100), nullable=True),
            sa.Column("analytical_method", sa.String(100), nullable=False, server_default="DRY_COMBUSTION"),
            sa.Column("method_standard_code", sa.String(100), nullable=True),
            sa.Column("analysis_date", sa.Date(), nullable=False),
            sa.Column("report_reference_number", sa.String(100), nullable=True),
            sa.Column("analyst_name", sa.String(100), nullable=True),
            sa.Column("qa_status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("evidence_id", uuid_type, sa.ForeignKey("evidence_records.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 9. laboratory_results
    if "laboratory_results" not in existing_tables:
        op.create_table(
            "laboratory_results",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("analysis_id", uuid_type, sa.ForeignKey("laboratory_analyses.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("physical_sample_id", uuid_type, sa.ForeignKey("physical_samples.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("analyte", sa.String(50), nullable=False, index=True),
            sa.Column("raw_value", sa.Numeric(12, 4), nullable=False),
            sa.Column("raw_unit", sa.String(30), nullable=False),
            sa.Column("normalized_value", sa.Numeric(12, 4), nullable=True),
            sa.Column("normalized_unit", sa.String(30), nullable=True),
            sa.Column("normalization_method", sa.String(100), nullable=True),
            sa.Column("detection_limit", sa.Numeric(12, 4), nullable=True),
            sa.Column("uncertainty_pct", sa.Numeric(6, 2), nullable=True),
            sa.Column("qualifier", sa.String(20), nullable=False, server_default="="),
            sa.Column("is_superseded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("superseded_by_id", uuid_type, sa.ForeignKey("laboratory_results.id", ondelete="SET NULL"), nullable=True),
            sa.Column("revision_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 10. sample_qa_reviews
    if "sample_qa_reviews" not in existing_tables:
        op.create_table(
            "sample_qa_reviews",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("physical_sample_id", uuid_type, sa.ForeignKey("physical_samples.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("reviewer_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reviewer_name", sa.String(100), nullable=False),
            sa.Column("review_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("overall_qa_status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("location_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("deviation_acceptable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("depth_valid", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("custody_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("lab_receipt_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("required_assays_present", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 11. soil_samples physical_sample_id FK
    if "soil_samples" in existing_tables:
        if not column_exists("soil_samples", "physical_sample_id"):
            op.add_column(
                "soil_samples",
                sa.Column("physical_sample_id", uuid_type, sa.ForeignKey("physical_samples.id", ondelete="SET NULL"), nullable=True),
            )

    # 12. PostGIS spatial GiST indexes
    if not is_sqlite:
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sampling_points') THEN
                    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_sampling_points_geom') THEN
                        CREATE INDEX idx_sampling_points_geom ON sampling_points USING GIST (geom);
                    END IF;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sample_collection_events') THEN
                    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_sample_collection_events_geom') THEN
                        CREATE INDEX idx_sample_collection_events_geom ON sample_collection_events USING GIST (actual_geom);
                    END IF;
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    tables_to_drop = [
        "sample_qa_reviews",
        "laboratory_results",
        "laboratory_analyses",
        "laboratory_receipts",
        "chain_of_custody_events",
        "sample_collection_events",
        "physical_samples",
        "sampling_points",
        "sampling_plan_versions",
        "sampling_campaigns",
    ]

    for tbl in tables_to_drop:
        if tbl in existing_tables:
            op.drop_table(tbl)
