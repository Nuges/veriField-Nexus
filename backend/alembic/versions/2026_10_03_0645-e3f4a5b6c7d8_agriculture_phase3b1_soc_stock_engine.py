"""agriculture_phase3b1_soc_stock_engine

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-10-03 06:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    # 1. agriculture_soc_stock_snapshots
    op.create_table(
        'agriculture_soc_stock_snapshots',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('prerequisite_assessment_id', uuid_type, sa.ForeignKey('agriculture_prerequisite_assessments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('snapshot_code', sa.String(length=60), nullable=False),
        sa.Column('measurement_period_type', sa.String(length=30), nullable=False),
        sa.Column('snapshot_payload', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_agri_soc_stock_snapshots_org_id', 'agriculture_soc_stock_snapshots', ['organization_id'])
    op.create_index('ix_agri_soc_stock_snapshots_project_id', 'agriculture_soc_stock_snapshots', ['project_id'])
    op.create_index('ix_agri_soc_stock_snapshots_prereq_id', 'agriculture_soc_stock_snapshots', ['prerequisite_assessment_id'])
    op.create_index('ix_agri_soc_stock_snapshots_code', 'agriculture_soc_stock_snapshots', ['snapshot_code'], unique=True)
    op.create_index('ix_agri_soc_stock_snapshots_hash', 'agriculture_soc_stock_snapshots', ['snapshot_hash'], unique=True)

    # 2. agriculture_soc_stock_results
    op.create_table(
        'agriculture_soc_stock_results',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quantification_unit_id', uuid_type, sa.ForeignKey('land_units.id', ondelete='SET NULL'), nullable=True),
        sa.Column('stratum_id', uuid_type, sa.ForeignKey('agriculture_strata.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sampling_point_id', uuid_type, sa.ForeignKey('sampling_points.id', ondelete='SET NULL'), nullable=True),
        sa.Column('campaign_id', uuid_type, sa.ForeignKey('sampling_campaigns.id', ondelete='SET NULL'), nullable=True),
        sa.Column('prerequisite_assessment_id', uuid_type, sa.ForeignKey('agriculture_prerequisite_assessments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('input_snapshot_id', uuid_type, sa.ForeignKey('quantification_input_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('stock_snapshot_id', uuid_type, sa.ForeignKey('agriculture_soc_stock_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('result_code', sa.String(length=60), nullable=False),
        sa.Column('measurement_period_type', sa.String(length=30), nullable=False),
        sa.Column('aggregation_level', sa.String(length=30), nullable=False, server_default='SAMPLE_POINT'),
        sa.Column('methodology_version', sa.String(length=30), nullable=False, server_default='2.2'),
        sa.Column('corrections_clarifications_version', sa.String(length=30), nullable=False, server_default='2026-06-11'),
        sa.Column('calculation_engine_version', sa.String(length=60), nullable=False, server_default='VM0042_V2_2_ESM_ENGINE_V1.0'),
        sa.Column('esm_algorithm', sa.String(length=50), nullable=False, server_default='LAYER_MASS_PROPORTIONING'),
        sa.Column('reference_soil_mass_t_ha', sa.Numeric(14, 4), nullable=False),
        sa.Column('reference_depth_cm', sa.Numeric(6, 2), nullable=False, server_default='30.00'),
        sa.Column('equivalent_depth_cm', sa.Numeric(6, 2), nullable=True),
        sa.Column('total_sampled_soil_mass_t_ha', sa.Numeric(14, 4), nullable=True),
        sa.Column('max_sampled_depth_cm', sa.Numeric(6, 2), nullable=True),
        sa.Column('soc_stock_t_c_per_ha', sa.Numeric(12, 4), nullable=False),
        sa.Column('unadjusted_stock_t_c_per_ha', sa.Numeric(12, 4), nullable=True),
        sa.Column('shallow_soil_exception_applied', sa.Boolean(), nullable=False, server_default=sa.text('false' if not is_sqlite else '0')),
        sa.Column('depth_sufficiency_status', sa.String(length=50), nullable=False, server_default='DEPTH_SUFFICIENT'),
        sa.Column('area_ha', sa.Numeric(14, 4), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('strata_weights', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('component_breakdown', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('result_status', sa.String(length=30), nullable=False, server_default='CALCULATED'),
        sa.Column('calculation_hash', sa.String(length=64), nullable=False),
        sa.Column('input_snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('created_by_id', uuid_type, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('superseded_by_id', uuid_type, sa.ForeignKey('agriculture_soc_stock_results.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_agri_soc_stock_results_org_id', 'agriculture_soc_stock_results', ['organization_id'])
    op.create_index('ix_agri_soc_stock_results_project_id', 'agriculture_soc_stock_results', ['project_id'])
    op.create_index('ix_agri_soc_stock_results_code', 'agriculture_soc_stock_results', ['result_code'], unique=True)
    op.create_index('ix_agri_soc_stock_results_period_type', 'agriculture_soc_stock_results', ['measurement_period_type'])
    op.create_index('ix_agri_soc_stock_results_calc_hash', 'agriculture_soc_stock_results', ['calculation_hash'])
    op.create_index('ix_agri_soc_stock_results_input_hash', 'agriculture_soc_stock_results', ['input_snapshot_hash'])

    # 3. agriculture_soc_layer_results
    op.create_table(
        'agriculture_soc_layer_results',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('stock_result_id', uuid_type, sa.ForeignKey('agriculture_soc_stock_results.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sample_id', uuid_type, sa.ForeignKey('physical_samples.id', ondelete='SET NULL'), nullable=True),
        sa.Column('layer_index', sa.Integer(), nullable=False),
        sa.Column('depth_upper_cm', sa.Numeric(6, 2), nullable=False),
        sa.Column('depth_lower_cm', sa.Numeric(6, 2), nullable=False),
        sa.Column('layer_thickness_cm', sa.Numeric(6, 2), nullable=False),
        sa.Column('bulk_density_g_cm3', sa.Numeric(8, 4), nullable=True),
        sa.Column('bulk_density_provenance', sa.String(length=50), nullable=False, server_default='MEASURED'),
        sa.Column('coarse_fragment_fraction', sa.Numeric(6, 4), nullable=True, server_default='0.0000'),
        sa.Column('coarse_fragment_provenance', sa.String(length=50), nullable=False, server_default='MEASURED'),
        sa.Column('soc_concentration_g_kg', sa.Numeric(10, 4), nullable=False),
        sa.Column('laboratory_result_id', uuid_type, sa.ForeignKey('laboratory_results.id', ondelete='SET NULL'), nullable=True),
        sa.Column('layer_soil_mass_t_ha', sa.Numeric(14, 4), nullable=False),
        sa.Column('layer_soc_mass_t_c_ha', sa.Numeric(12, 4), nullable=False),
        sa.Column('cumulative_soil_mass_t_ha', sa.Numeric(14, 4), nullable=False),
        sa.Column('cumulative_soc_mass_t_c_ha', sa.Numeric(12, 4), nullable=False),
        sa.Column('fraction_in_reference_mass', sa.Numeric(6, 4), nullable=True),
        sa.Column('included_soil_mass_t_ha', sa.Numeric(14, 4), nullable=True),
        sa.Column('included_soc_mass_t_c_ha', sa.Numeric(12, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_agri_soc_layer_results_stock_result_id', 'agriculture_soc_layer_results', ['stock_result_id'])
    op.create_index('ix_agri_soc_layer_results_sample_id', 'agriculture_soc_layer_results', ['sample_id'])


def downgrade() -> None:
    op.drop_index('ix_agri_soc_layer_results_sample_id', table_name='agriculture_soc_layer_results')
    op.drop_index('ix_agri_soc_layer_results_stock_result_id', table_name='agriculture_soc_layer_results')
    op.drop_table('agriculture_soc_layer_results')

    op.drop_index('ix_agri_soc_stock_results_input_hash', table_name='agriculture_soc_stock_results')
    op.drop_index('ix_agri_soc_stock_results_calc_hash', table_name='agriculture_soc_stock_results')
    op.drop_index('ix_agri_soc_stock_results_period_type', table_name='agriculture_soc_stock_results')
    op.drop_index('ix_agri_soc_stock_results_code', table_name='agriculture_soc_stock_results')
    op.drop_index('ix_agri_soc_stock_results_project_id', table_name='agriculture_soc_stock_results')
    op.drop_index('ix_agri_soc_stock_results_org_id', table_name='agriculture_soc_stock_results')
    op.drop_table('agriculture_soc_stock_results')

    op.drop_index('ix_agri_soc_stock_snapshots_hash', table_name='agriculture_soc_stock_snapshots')
    op.drop_index('ix_agri_soc_stock_snapshots_code', table_name='agriculture_soc_stock_snapshots')
    op.drop_index('ix_agri_soc_stock_snapshots_prereq_id', table_name='agriculture_soc_stock_snapshots')
    op.drop_index('ix_agri_soc_stock_snapshots_project_id', table_name='agriculture_soc_stock_snapshots')
    op.drop_index('ix_agri_soc_stock_snapshots_org_id', table_name='agriculture_soc_stock_snapshots')
    op.drop_table('agriculture_soc_stock_snapshots')
