"""PostGIS spatial geometry hardening

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-23 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if not is_sqlite:
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis;"))

    # Helper to check if column exists
    def column_exists(table_name: str, col_name: str) -> bool:
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return col_name in cols

    # Helper to check if index exists
    def index_exists(table_name: str, idx_name: str) -> bool:
        indexes = [i["name"] for i in insp.get_indexes(table_name)]
        return idx_name in indexes

    # 1. project_boundary_versions -> geom
    if not column_exists("project_boundary_versions", "geom"):
        if is_sqlite:
            op.add_column("project_boundary_versions", sa.Column("geom", sa.BLOB(), nullable=True))
        else:
            op.add_column(
                "project_boundary_versions",
                sa.Column("geom", Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True),
            )
            op.execute(sa.text("""
                UPDATE project_boundary_versions
                SET geom = ST_SetSRID(ST_GeomFromGeoJSON(boundary_geojson::text), 4326)
                WHERE boundary_geojson IS NOT NULL AND geom IS NULL;
            """))

    if not is_sqlite and not index_exists("project_boundary_versions", "idx_project_boundary_versions_geom"):
        op.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_project_boundary_versions_geom
            ON project_boundary_versions USING GIST (geom);
        """))

    # 2. eo_areas_of_interest -> geom
    if not column_exists("eo_areas_of_interest", "geom"):
        if is_sqlite:
            op.add_column("eo_areas_of_interest", sa.Column("geom", sa.BLOB(), nullable=True))
        else:
            op.add_column(
                "eo_areas_of_interest",
                sa.Column("geom", Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True),
            )
            op.execute(sa.text("""
                UPDATE eo_areas_of_interest
                SET geom = ST_SetSRID(ST_GeomFromGeoJSON(geometry_geojson::text), 4326)
                WHERE geometry_geojson IS NOT NULL AND geom IS NULL;
            """))

    if not is_sqlite and not index_exists("eo_areas_of_interest", "idx_eo_areas_of_interest_geom"):
        op.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_eo_areas_of_interest_geom
            ON eo_areas_of_interest USING GIST (geom);
        """))

    # 3. eo_observations -> footprint_geom
    if not column_exists("eo_observations", "footprint_geom"):
        if is_sqlite:
            op.add_column("eo_observations", sa.Column("footprint_geom", sa.BLOB(), nullable=True))
        else:
            op.add_column(
                "eo_observations",
                sa.Column("footprint_geom", Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True),
            )
            op.execute(sa.text("""
                UPDATE eo_observations
                SET footprint_geom = ST_SetSRID(ST_GeomFromGeoJSON(geometry_geojson::text), 4326)
                WHERE geometry_geojson IS NOT NULL AND footprint_geom IS NULL;
            """))

    if not is_sqlite and not index_exists("eo_observations", "idx_eo_observations_footprint_geom"):
        op.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_eo_observations_footprint_geom
            ON eo_observations USING GIST (footprint_geom);
        """))

    # 4. eo_spatial_anomalies -> geom
    if not column_exists("eo_spatial_anomalies", "geom"):
        if is_sqlite:
            op.add_column("eo_spatial_anomalies", sa.Column("geom", sa.BLOB(), nullable=True))
        else:
            op.add_column(
                "eo_spatial_anomalies",
                sa.Column("geom", Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True),
            )

    if not is_sqlite and not index_exists("eo_spatial_anomalies", "idx_eo_spatial_anomalies_geom"):
        op.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_eo_spatial_anomalies_geom
            ON eo_spatial_anomalies USING GIST (geom);
        """))


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if not is_sqlite:
        op.execute(sa.text("DROP INDEX IF EXISTS idx_eo_spatial_anomalies_geom;"))
        op.execute(sa.text("DROP INDEX IF EXISTS idx_eo_observations_footprint_geom;"))
        op.execute(sa.text("DROP INDEX IF EXISTS idx_eo_areas_of_interest_geom;"))
        op.execute(sa.text("DROP INDEX IF EXISTS idx_project_boundary_versions_geom;"))

    op.drop_column("eo_spatial_anomalies", "geom")
    op.drop_column("eo_observations", "footprint_geom")
    op.drop_column("eo_areas_of_interest", "geom")
    op.drop_column("project_boundary_versions", "geom")
