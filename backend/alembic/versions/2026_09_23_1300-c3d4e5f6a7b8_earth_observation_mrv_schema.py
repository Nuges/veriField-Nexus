"""Earth Observation and Satellite MRV Schema

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-23 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    is_sqlite = bind.dialect.name == "sqlite"
    uuid_default = None if is_sqlite else sa.text('gen_random_uuid()')
    now_default = sa.text('CURRENT_TIMESTAMP') if is_sqlite else sa.text('now()')

    json_col_type = sa.JSON() if is_sqlite else postgresql.JSONB()
    dict_default = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")
    list_default = sa.text("'[]'") if is_sqlite else sa.text("'[]'::jsonb")

    if not is_sqlite:
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis;"))

    # 1. project_boundary_versions
    if 'project_boundary_versions' not in existing_tables:
        op.create_table(
            'project_boundary_versions',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('effective_date', sa.Date(), nullable=False),
            sa.Column('boundary_geojson', json_col_type, nullable=False),
            sa.Column('source', sa.String(50), nullable=False, server_default='DECLARED'),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('area_ha', sa.Float(), nullable=False),
            sa.Column('perimeter_m', sa.Float(), nullable=True),
            sa.Column('centroid_lat', sa.Float(), nullable=True),
            sa.Column('centroid_lon', sa.Float(), nullable=True),
            sa.Column('crs', sa.String(20), nullable=False, server_default='EPSG:4326'),
            sa.Column('created_by_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
        )
        op.create_index(
            'ix_project_boundary_ver_unique',
            'project_boundary_versions',
            ['project_id', 'version_number'],
            unique=True,
        )

    # 2. eo_areas_of_interest
    if 'eo_areas_of_interest' not in existing_tables:
        op.create_table(
            'eo_areas_of_interest',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('name', sa.String(150), nullable=False),
            sa.Column('aoi_type', sa.String(50), nullable=False, server_default='PROJECT_BOUNDARY'),
            sa.Column('source_entity_id', sa.UUID(), nullable=True),
            sa.Column('boundary_version_id', sa.UUID(), sa.ForeignKey('project_boundary_versions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('geometry_geojson', json_col_type, nullable=False),
            sa.Column('bbox', json_col_type, nullable=False),
            sa.Column('area_ha', sa.Float(), nullable=False),
            sa.Column('crs', sa.String(20), nullable=False, server_default='EPSG:4326'),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
        )

    # 3. eo_providers
    if 'eo_providers' not in existing_tables:
        op.create_table(
            'eo_providers',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('code', sa.String(50), unique=True, nullable=False, index=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('provider_type', sa.String(50), nullable=False),
            sa.Column('capability_state', sa.String(30), nullable=False, server_default='NOT_CONFIGURED'),
            sa.Column('endpoint_url', sa.String(255), nullable=True),
            sa.Column('auth_configured', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('verification_notes', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
        )

    # 4. eo_products
    if 'eo_products' not in existing_tables:
        op.create_table(
            'eo_products',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('provider_code', sa.String(50), sa.ForeignKey('eo_providers.code', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('product_code', sa.String(50), unique=True, nullable=False, index=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('platform', sa.String(50), nullable=False),
            sa.Column('sensor', sa.String(50), nullable=False),
            sa.Column('observation_type', sa.String(50), nullable=False),
            sa.Column('spatial_resolution_m', sa.Float(), nullable=False),
            sa.Column('default_processing_level', sa.String(20), server_default='L2A', nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        )

    # 5. eo_observations
    has_land_units = 'land_units' in existing_tables
    if 'eo_observations' not in existing_tables:
        cols = [
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('aoi_id', sa.UUID(), sa.ForeignKey('eo_areas_of_interest.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column(
                'land_unit_id',
                sa.UUID(),
                sa.ForeignKey('land_units.id', ondelete='SET NULL') if has_land_units else None,
                nullable=True,
                index=True,
            ),
            sa.Column('boundary_version_id', sa.UUID(), sa.ForeignKey('project_boundary_versions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('provider_code', sa.String(50), nullable=False, index=True),
            sa.Column('platform', sa.String(50), nullable=False),
            sa.Column('sensor', sa.String(50), nullable=False),
            sa.Column('product_code', sa.String(50), nullable=False),
            sa.Column('scene_id', sa.String(150), nullable=False, index=True),
            sa.Column('acquisition_timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column('processing_timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('spatial_resolution_m', sa.Float(), nullable=False),
            sa.Column('cloud_cover_pct', sa.Float(), nullable=True),
            sa.Column('crs', sa.String(20), nullable=False, server_default='EPSG:4326'),
            sa.Column('geometry_geojson', json_col_type, nullable=False),
            sa.Column('bbox', json_col_type, nullable=False),
            sa.Column('observation_type', sa.String(50), nullable=False),
            sa.Column('processing_level', sa.String(20), nullable=False, server_default='L2A'),
            sa.Column('processing_version', sa.String(50), nullable=False, server_default='1.0.0'),
            sa.Column('quality_status', sa.String(30), nullable=False, server_default='USABLE'),
            sa.Column('quality_flags', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('raw_band_uris', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('raw_band_checksums', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('asset_uri', sa.String(500), nullable=True),
            sa.Column('checksum_sha256', sa.String(64), nullable=True),
            sa.Column('provenance_hash', sa.String(64), nullable=False, index=True),
            sa.Column('lineage_manifest', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('is_baseline', sa.Boolean(), server_default='false', nullable=False, index=True),
            sa.Column('baseline_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
        ]
        op.create_table('eo_observations', *cols)
        op.create_index('ix_eo_obs_proj_acq', 'eo_observations', ['project_id', 'acquisition_timestamp'])
        op.create_index('ix_eo_obs_org_prov', 'eo_observations', ['organization_id', 'provider_code'])

    # 6. eo_derived_layers
    if 'eo_derived_layers' not in existing_tables:
        op.create_table(
            'eo_derived_layers',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('observation_id', sa.UUID(), sa.ForeignKey('eo_observations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('aoi_id', sa.UUID(), sa.ForeignKey('eo_areas_of_interest.id', ondelete='SET NULL'), nullable=True),
            sa.Column('layer_type', sa.String(50), nullable=False, index=True),
            sa.Column('formula_identifier', sa.String(100), nullable=False),
            sa.Column('formula', sa.String(255), nullable=False),
            sa.Column('band_mapping', json_col_type, nullable=False),
            sa.Column('processor_version', sa.String(50), nullable=False),
            sa.Column('spatial_resolution_m', sa.Float(), nullable=False),
            sa.Column('statistics', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('asset_uri', sa.String(500), nullable=True),
            sa.Column('checksum_sha256', sa.String(64), nullable=False),
            sa.Column('quality_status', sa.String(30), nullable=False, server_default='USABLE'),
            sa.Column('provenance_hash', sa.String(64), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
        )

    # 7. eo_processing_runs
    if 'eo_processing_runs' not in existing_tables:
        op.create_table(
            'eo_processing_runs',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('run_type', sa.String(50), nullable=False),
            sa.Column('status', sa.String(30), nullable=False, server_default='COMPLETED'),
            sa.Column('parameters', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('input_observation_ids', json_col_type, nullable=False, server_default=list_default),
            sa.Column('output_layer_ids', json_col_type, nullable=False, server_default=list_default),
            sa.Column('execution_time_ms', sa.Integer(), nullable=True),
            sa.Column('provenance_hash', sa.String(64), nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
        )

    # 8. eo_spatial_anomalies
    has_verification_tasks = 'verification_tasks' in existing_tables
    if 'eo_spatial_anomalies' not in existing_tables:
        anom_cols = [
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('aoi_id', sa.UUID(), sa.ForeignKey('eo_areas_of_interest.id', ondelete='SET NULL'), nullable=True),
            sa.Column('observation_id', sa.UUID(), sa.ForeignKey('eo_observations.id', ondelete='SET NULL'), nullable=True),
            sa.Column('anomaly_type', sa.String(50), nullable=False, server_default='VEGETATION_INDEX_CHANGE'),
            sa.Column('severity', sa.String(20), nullable=False, server_default='MEDIUM'),
            sa.Column('status', sa.String(30), nullable=False, server_default='OBSERVED'),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('review_recommendation', sa.Text(), nullable=False),
            sa.Column('baseline_observation_id', sa.UUID(), nullable=True),
            sa.Column('comparison_metric', sa.String(50), nullable=True),
            sa.Column('delta_value', sa.Float(), nullable=True),
            sa.Column(
                'verification_task_id',
                sa.UUID(),
                sa.ForeignKey('verification_tasks.id', ondelete='SET NULL') if has_verification_tasks else None,
                nullable=True,
            ),
            sa.Column('corroborating_activity_id', sa.UUID(), nullable=True),
            sa.Column('corroboration_notes', sa.Text(), nullable=True),
            sa.Column('corroborated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('detected_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
        ]
        op.create_table('eo_spatial_anomalies', *anom_cols)


def downgrade() -> None:
    op.drop_table('eo_spatial_anomalies')
    op.drop_table('eo_processing_runs')
    op.drop_table('eo_derived_layers')
    op.drop_table('eo_observations')
    op.drop_table('eo_products')
    op.drop_table('eo_providers')
    op.drop_table('eo_areas_of_interest')
    op.drop_table('project_boundary_versions')
