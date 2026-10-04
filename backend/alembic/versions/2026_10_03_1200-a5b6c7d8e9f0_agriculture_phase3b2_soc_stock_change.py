"""agriculture_phase3b2_soc_stock_change

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-10-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a5b6c7d8e9f0'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    # agriculture_soc_change_results
    op.create_table(
        'agriculture_soc_change_results',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('baseline_stock_result_id', uuid_type, sa.ForeignKey('agriculture_soc_stock_results.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('monitoring_stock_result_id', uuid_type, sa.ForeignKey('agriculture_soc_stock_results.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('prerequisite_assessment_id', uuid_type, sa.ForeignKey('agriculture_prerequisite_assessments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('result_code', sa.String(length=100), nullable=False),
        sa.Column('methodology_version', sa.String(length=30), nullable=False, server_default='2.2'),
        sa.Column('corrections_clarifications_version', sa.String(length=30), nullable=False, server_default='2026-06-11'),
        sa.Column('calculation_engine_version', sa.String(length=50), nullable=False, server_default='VM0042_V2_2_SOC_CHANGE_V1.0'),
        sa.Column('quantification_approach', sa.String(length=30), nullable=False, server_default='APPROACH_2'),
        sa.Column('t_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('t_final', sa.DateTime(timezone=True), nullable=False),
        sa.Column('elapsed_years', sa.Numeric(8, 4), nullable=False),
        sa.Column('esm_algorithm', sa.String(length=50), nullable=False, server_default='WENDT_HAUSER_2013_CUBIC_SPLINE'),
        sa.Column('reference_soil_mass_t_ha', sa.Numeric(14, 4), nullable=False),
        sa.Column('reference_depth_cm', sa.Numeric(6, 2), nullable=False, server_default='30.00'),
        sa.Column('total_project_area_ha', sa.Numeric(14, 4), nullable=False),
        sa.Column('baseline_mean_soc_t_c_per_ha', sa.Numeric(12, 4), nullable=False),
        sa.Column('monitoring_mean_soc_t_c_per_ha', sa.Numeric(12, 4), nullable=False),
        sa.Column('delta_soc_project_t_c_ha_yr', sa.Numeric(12, 4), nullable=False),
        sa.Column('delta_soc_baseline_t_c_ha_yr', sa.Numeric(12, 4), nullable=False, server_default='0.0000'),
        sa.Column('delta_soc_net_t_c_ha_yr', sa.Numeric(12, 4), nullable=False),
        sa.Column('delta_co2_project_tco2e_ha_yr', sa.Numeric(12, 4), nullable=False),
        sa.Column('delta_co2_baseline_tco2e_ha_yr', sa.Numeric(12, 4), nullable=False, server_default='0.0000'),
        sa.Column('delta_co2_net_tco2e_ha_yr', sa.Numeric(12, 4), nullable=False),
        sa.Column('total_project_delta_co2_tco2e_yr', sa.Numeric(14, 4), nullable=False),
        sa.Column('total_baseline_delta_co2_tco2e_yr', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_net_delta_co2_tco2e_yr', sa.Numeric(14, 4), nullable=False),
        sa.Column('baseline_soc_change_tco2e_yr', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('project_soc_change_tco2e_yr', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('qa2_net_soc_effect_tco2e_yr', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('uncertainty_adjusted_soc_effect_tco2e_yr', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('sign_indicator', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('eq44_eq45_status', sa.String(length=50), nullable=False, server_default='PARTIALLY_CONFIGURED_SOC_ONLY'),
        sa.Column('df_estimator', sa.String(length=50), nullable=False, server_default='DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR'),
        sa.Column('co2_to_c_ratio', sa.Numeric(10, 8), nullable=False, server_default='3.66666667'),
        sa.Column('variance_delta_soc_project', sa.Numeric(16, 8), nullable=False),
        sa.Column('variance_delta_soc_baseline', sa.Numeric(16, 8), nullable=False, server_default='0.00000000'),
        sa.Column('total_variance_delta_soc', sa.Numeric(16, 8), nullable=False),
        sa.Column('standard_error_delta_soc_t_c_ha_yr', sa.Numeric(14, 6), nullable=False),
        sa.Column('standard_error_tco2e_yr', sa.Numeric(14, 4), nullable=False),
        sa.Column('degrees_of_freedom', sa.Integer(), nullable=False),
        sa.Column('student_t_value_0667', sa.Numeric(8, 4), nullable=False),
        sa.Column('relative_uncertainty_pct', sa.Numeric(8, 4), nullable=False),
        sa.Column('allowable_uncertainty_pct', sa.Numeric(8, 4), nullable=False, server_default='0.0000'),
        sa.Column('uncertainty_deduction_pct', sa.Numeric(8, 4), nullable=False, server_default='0.0000'),
        sa.Column('uncertainty_deduction_fraction', sa.Numeric(8, 6), nullable=False, server_default='0.000000'),
        sa.Column('adjusted_net_delta_co2_tco2e_yr', sa.Numeric(14, 4), nullable=False),
        sa.Column('measurement_error_status', sa.String(length=50), nullable=False, server_default='NEGLIGIBLE_PER_VM0042_CONDITIONS'),
        sa.Column('measurement_error_router', sa.String(length=50), nullable=False, server_default='CONVENTIONAL_DRY_COMBUSTION'),
        sa.Column('strata_results', json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column('component_breakdown', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('carbon_accounting_status', sa.String(length=50), nullable=False, server_default='NOT_CONFIGURED'),
        sa.Column('ledger_status', sa.String(length=50), nullable=False, server_default='BLOCKED_FOR_AGRICULTURE'),
        sa.Column('result_status', sa.String(length=30), nullable=False, server_default='CALCULATED'),
        sa.Column('calculation_hash', sa.String(length=64), nullable=False),
        sa.Column('input_snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('created_by_id', uuid_type, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('superseded_by_id', uuid_type, sa.ForeignKey('agriculture_soc_change_results.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_agri_soc_change_results_org_id', 'agriculture_soc_change_results', ['organization_id'])
    op.create_index('ix_agri_soc_change_results_project_id', 'agriculture_soc_change_results', ['project_id'])
    op.create_index('ix_agri_soc_change_results_code', 'agriculture_soc_change_results', ['result_code'], unique=True)
    op.create_index('ix_agri_soc_change_results_calc_hash', 'agriculture_soc_change_results', ['calculation_hash'])
    op.create_index('ix_agri_soc_change_results_input_hash', 'agriculture_soc_change_results', ['input_snapshot_hash'])
    op.create_index('ix_agri_soc_change_results_bsl_id', 'agriculture_soc_change_results', ['baseline_stock_result_id'])
    op.create_index('ix_agri_soc_change_results_mon_id', 'agriculture_soc_change_results', ['monitoring_stock_result_id'])


def downgrade() -> None:
    op.drop_index('ix_agri_soc_change_results_mon_id', table_name='agriculture_soc_change_results')
    op.drop_index('ix_agri_soc_change_results_bsl_id', table_name='agriculture_soc_change_results')
    op.drop_index('ix_agri_soc_change_results_input_hash', table_name='agriculture_soc_change_results')
    op.drop_index('ix_agri_soc_change_results_calc_hash', table_name='agriculture_soc_change_results')
    op.drop_index('ix_agri_soc_change_results_code', table_name='agriculture_soc_change_results')
    op.drop_index('ix_agri_soc_change_results_project_id', table_name='agriculture_soc_change_results')
    op.drop_index('ix_agri_soc_change_results_org_id', table_name='agriculture_soc_change_results')
    op.drop_table('agriculture_soc_change_results')
