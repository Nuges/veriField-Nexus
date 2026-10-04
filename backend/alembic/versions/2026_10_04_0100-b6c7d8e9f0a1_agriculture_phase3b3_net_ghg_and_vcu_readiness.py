"""agriculture_phase3b3_net_ghg_and_vcu_readiness

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-10-04 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b6c7d8e9f0a1'
down_revision = 'a5b6c7d8e9f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    # 1. Create agriculture_net_ghg_results table
    op.create_table(
        'agriculture_net_ghg_results',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('soc_change_result_id', uuid_type, sa.ForeignKey('agriculture_soc_change_results.id', ondelete='SET NULL'), nullable=True),
        sa.Column('prerequisite_assessment_id', uuid_type, sa.ForeignKey('agriculture_prerequisite_assessments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('result_code', sa.String(length=100), nullable=False),
        sa.Column('methodology_version', sa.String(length=30), nullable=False, server_default='2.2'),
        sa.Column('corrections_clarifications_version', sa.String(length=30), nullable=False, server_default='2026-06-11'),
        sa.Column('calculation_engine_version', sa.String(length=50), nullable=False, server_default='VM0042_V2_2_NET_GHG_V1.0'),
        sa.Column('ruleset_version', sa.String(length=50), nullable=False, server_default='VM0042_V2.2_RULES_CC20260611_V1.0'),
        sa.Column('verification_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verification_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('elapsed_years', sa.Numeric(8, 4), nullable=False),
        sa.Column('applicability_matrix', json_type, nullable=False, server_default='{}'),
        sa.Column('total_baseline_emissions_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_project_emissions_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_emission_reductions_from_sources_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('eq44_baseline_total_carbon_stock_change_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('eq45_project_total_carbon_stock_change_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('eq44_eq45_status', sa.String(length=50), nullable=False, server_default='CALCULATED'),
        sa.Column('gross_reductions_er_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('gross_removals_cr_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_leakage_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('leakage_allocation_er_lker_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('leakage_allocation_cr_lkcr_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('net_reductions_ernet_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('net_removals_crnet_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_net_ghg_errnet_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('npr_rating_pct', sa.Numeric(8, 4), nullable=True),
        sa.Column('risk_assessment_id', sa.String(length=100), nullable=True),
        sa.Column('buffer_deduction_reductions_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('buffer_deduction_removals_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('total_buffer_deduction_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('internal_vcu_eligible_reductions_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('internal_vcu_eligible_removals_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('internal_vcu_eligible_total_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('vcu_readiness_status', sa.String(length=50), nullable=False, server_default='NOT_CONFIGURED'),
        sa.Column('internal_mrv_status', sa.String(length=50), nullable=False, server_default='CALCULATED'),
        sa.Column('vvb_status', sa.String(length=50), nullable=False, server_default='NOT_CONFIGURED / EXTERNAL'),
        sa.Column('registry_status', sa.String(length=50), nullable=False, server_default='NOT_CONFIGURED / EXTERNAL'),
        sa.Column('ledger_status', sa.String(length=50), nullable=False, server_default='BLOCKED_FOR_AGRICULTURE'),
        sa.Column('result_status', sa.String(length=30), nullable=False, server_default='CALCULATED'),
        sa.Column('calculation_hash', sa.String(length=64), nullable=False),
        sa.Column('input_snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('created_by_id', uuid_type, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('superseded_by_id', uuid_type, sa.ForeignKey('agriculture_net_ghg_results.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('component_breakdown', json_type, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    op.create_index('ix_agriculture_net_ghg_results_result_code', 'agriculture_net_ghg_results', ['result_code'], unique=True)
    op.create_index('ix_agriculture_net_ghg_results_org_id', 'agriculture_net_ghg_results', ['organization_id'])
    op.create_index('ix_agriculture_net_ghg_results_project_id', 'agriculture_net_ghg_results', ['project_id'])
    op.create_index('ix_agriculture_net_ghg_results_calc_hash', 'agriculture_net_ghg_results', ['calculation_hash'])

    # 2. Create agriculture_vintage_ghg_results table
    op.create_table(
        'agriculture_vintage_ghg_results',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('net_ghg_result_id', uuid_type, sa.ForeignKey('agriculture_net_ghg_results.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vintage_year', sa.Integer(), nullable=False),
        sa.Column('total_baseline_emissions_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_project_emissions_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_emission_reductions_from_sources_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('eq44_baseline_total_carbon_stock_change_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('eq45_project_total_carbon_stock_change_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('gross_reductions_er_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('gross_removals_cr_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_leakage_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('leakage_allocation_er_lker_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('leakage_allocation_cr_lkcr_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('net_reductions_ernet_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('net_removals_crnet_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_net_ghg_errnet_tco2e', sa.Numeric(14, 4), nullable=False, server_default='0.0000'),
        sa.Column('buffer_deduction_reductions_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('buffer_deduction_removals_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('total_buffer_deduction_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('internal_vcu_eligible_reductions_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('internal_vcu_eligible_removals_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('internal_vcu_eligible_total_tco2e', sa.Numeric(14, 4), nullable=True),
        sa.Column('vintage_details', json_type, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    op.create_index('ix_agriculture_vintage_ghg_results_net_result_id', 'agriculture_vintage_ghg_results', ['net_ghg_result_id'])
    op.create_index('ix_agriculture_vintage_ghg_results_year', 'agriculture_vintage_ghg_results', ['vintage_year'])


def downgrade() -> None:
    op.drop_table('agriculture_vintage_ghg_results')
    op.drop_table('agriculture_net_ghg_results')
