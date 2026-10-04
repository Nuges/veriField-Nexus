"""Agriculture MRV Phase 1: Project Foundation, Land Structure, and Management Baseline

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-25 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
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

    # Helper to check if column exists
    def column_exists(table_name: str, col_name: str) -> bool:
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return col_name in cols

    # Helper to check if index exists
    def index_exists(table_name: str, idx_name: str) -> bool:
        indexes = [i["name"] for i in insp.get_indexes(table_name)]
        return idx_name in indexes

    if not is_sqlite:
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis;"))

    # 1. land_units -> ensure table and all domain columns exist
    if "land_units" not in existing_tables:
        op.create_table(
            "land_units",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True),
            sa.Column("parent_id", uuid_type, sa.ForeignKey("land_units.id", ondelete="CASCADE"), nullable=True, index=True),
            sa.Column("unit_type", sa.String(30), nullable=False, server_default="FIELD"),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("code", sa.String(50), nullable=True, index=True),
            sa.Column("boundary_geojson", json_type, nullable=False, server_default=empty_json),
            sa.Column("geom", sa.BLOB() if is_sqlite else Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True),
            sa.Column("boundary_source", sa.String(30), nullable=False, server_default="DECLARED"),
            sa.Column("boundary_crs", sa.String(20), nullable=False, server_default="EPSG:4326"),
            sa.Column("area_ha", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("perimeter_m", sa.Float(), nullable=True),
            sa.Column("centroid_lat", sa.Float(), nullable=True),
            sa.Column("centroid_lon", sa.Float(), nullable=True),
            sa.Column("land_use_category", sa.String(50), nullable=True),
            sa.Column("soil_type", sa.String(50), nullable=True),
            sa.Column("slope_pct", sa.Float(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("properties", json_type, nullable=False, server_default=empty_json),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )
    else:
        # Table exists (e.g. from foreign key stub) -> ensure all columns exist
        if not column_exists("land_units", "project_id"):
            op.add_column("land_units", sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True))
            if not index_exists("land_units", "ix_land_units_project_id"):
                op.create_index("ix_land_units_project_id", "land_units", ["project_id"])
        if not column_exists("land_units", "parent_id"):
            op.add_column("land_units", sa.Column("parent_id", uuid_type, sa.ForeignKey("land_units.id", ondelete="CASCADE"), nullable=True))
            if not index_exists("land_units", "ix_land_units_parent_id"):
                op.create_index("ix_land_units_parent_id", "land_units", ["parent_id"])
        if not column_exists("land_units", "unit_type"):
            op.add_column("land_units", sa.Column("unit_type", sa.String(30), nullable=False, server_default="FIELD"))
        if not column_exists("land_units", "code"):
            op.add_column("land_units", sa.Column("code", sa.String(50), nullable=True))
            if not index_exists("land_units", "ix_land_units_code"):
                op.create_index("ix_land_units_code", "land_units", ["code"])
        if not column_exists("land_units", "boundary_geojson"):
            op.add_column("land_units", sa.Column("boundary_geojson", json_type, nullable=False, server_default=empty_json))
        if not column_exists("land_units", "boundary_source"):
            op.add_column("land_units", sa.Column("boundary_source", sa.String(30), nullable=False, server_default="DECLARED"))
        if not column_exists("land_units", "boundary_crs"):
            op.add_column("land_units", sa.Column("boundary_crs", sa.String(20), nullable=False, server_default="EPSG:4326"))
        if not column_exists("land_units", "area_ha"):
            op.add_column("land_units", sa.Column("area_ha", sa.Float(), nullable=False, server_default="0.0"))
        if not column_exists("land_units", "perimeter_m"):
            op.add_column("land_units", sa.Column("perimeter_m", sa.Float(), nullable=True))
        if not column_exists("land_units", "centroid_lat"):
            op.add_column("land_units", sa.Column("centroid_lat", sa.Float(), nullable=True))
        if not column_exists("land_units", "centroid_lon"):
            op.add_column("land_units", sa.Column("centroid_lon", sa.Float(), nullable=True))
        if not column_exists("land_units", "land_use_category"):
            op.add_column("land_units", sa.Column("land_use_category", sa.String(50), nullable=True))
        if not column_exists("land_units", "soil_type"):
            op.add_column("land_units", sa.Column("soil_type", sa.String(50), nullable=True))
        if not column_exists("land_units", "slope_pct"):
            op.add_column("land_units", sa.Column("slope_pct", sa.Float(), nullable=True))
        if not column_exists("land_units", "is_active"):
            op.add_column("land_units", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        if not column_exists("land_units", "properties"):
            op.add_column("land_units", sa.Column("properties", json_type, nullable=False, server_default=empty_json))
        if not column_exists("land_units", "created_at"):
            op.add_column("land_units", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default))
        if not column_exists("land_units", "updated_at"):
            op.add_column("land_units", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default))

        if not column_exists("land_units", "geom"):
            if is_sqlite:
                op.add_column("land_units", sa.Column("geom", sa.BLOB(), nullable=True))
            else:
                op.add_column(
                    "land_units",
                    sa.Column("geom", Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True),
                )
                op.execute(sa.text("""
                    UPDATE land_units
                    SET geom = ST_SetSRID(ST_GeomFromGeoJSON(boundary_geojson::text), 4326)
                    WHERE boundary_geojson IS NOT NULL
                      AND boundary_geojson::text != '{}'
                      AND geom IS NULL;
                """))

    if not is_sqlite and not index_exists("land_units", "idx_land_units_geom"):
        op.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_land_units_geom
            ON land_units USING GIST (geom);
        """))

    # 2. agriculture_strata
    if "agriculture_strata" not in existing_tables:
        op.create_table(
            "agriculture_strata",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("code", sa.String(50), nullable=False, index=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("stratum_type", sa.String(50), nullable=False, server_default="MANAGEMENT_PRACTICE"),
            sa.Column("area_ha", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("properties", json_type, nullable=False, server_default=empty_json),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 3. agriculture_stratum_memberships
    if "agriculture_stratum_memberships" not in existing_tables:
        op.create_table(
            "agriculture_stratum_memberships",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("stratum_id", uuid_type, sa.ForeignKey("agriculture_strata.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("land_unit_id", uuid_type, sa.ForeignKey("land_units.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("valid_from", sa.Date(), nullable=False),
            sa.Column("valid_to", sa.Date(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
            sa.Column("properties", json_type, nullable=False, server_default=empty_json),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )

    # 4. agriculture_management_records
    if "agriculture_management_records" not in existing_tables:
        op.create_table(
            "agriculture_management_records",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_server_default),
            sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("land_unit_id", uuid_type, sa.ForeignKey("land_units.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("record_type", sa.String(50), nullable=False, index=True),
            sa.Column("practice_category", sa.String(50), nullable=False, server_default="BASELINE"),
            sa.Column("event_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("data_source", sa.String(50), nullable=False, server_default="REPORTED"),
            sa.Column("details", json_type, nullable=False, server_default=empty_json),
            sa.Column("evidence_id", uuid_type, sa.ForeignKey("evidence_records.id", ondelete="SET NULL"), nullable=True),
            sa.Column("entered_by_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("qa_status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = insp.get_table_names()

    if "agriculture_management_records" in existing_tables:
        op.drop_table("agriculture_management_records")
    if "agriculture_stratum_memberships" in existing_tables:
        op.drop_table("agriculture_stratum_memberships")
    if "agriculture_strata" in existing_tables:
        op.drop_table("agriculture_strata")

    if "land_units" in existing_tables:
        if not is_sqlite:
            op.execute(sa.text("DROP INDEX IF EXISTS idx_land_units_geom;"))
        cols = [c["name"] for c in insp.get_columns("land_units")]
        if "geom" in cols:
            op.drop_column("land_units", "geom")
