"""vm0044_v12_quantification_engine

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-10-02 02:00:00.000000

Verra VM0044 v1.2 Biochar Quantification Engine:
- Methodology versioning & locking (VM0044 v1.2 Scope 13 Removals).
- Normative rule definitions and external document dependencies.
- Section 4 Applicability evaluations and audit records.
- Section 7 Additionality & VT0008 assessments.
- Immutable canonical calculation input snapshots with SHA-256 digests.
- Authoritative calculation execution records with Equations (1)-(15) breakdown.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    # 1. vm0044_methodology_versions
    op.create_table(
        'vm0044_methodology_versions',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('sectoral_scope', sa.String(50), nullable=False),
        sa.Column('release_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('mitigation_outcome', sa.String(50), nullable=False, server_default='REMOVALS'),
        sa.Column('ccp_approved', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('source_url', sa.String(500), nullable=False),
        sa.Column('metadata_json', json_type, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_vm0044_meth_code', 'vm0044_methodology_versions', ['code'])
    op.create_index('ix_vm0044_meth_version', 'vm0044_methodology_versions', ['version'])

    # 2. vm0044_rule_definitions
    op.create_table(
        'vm0044_rule_definitions',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('methodology_version_id', uuid_type, sa.ForeignKey('vm0044_methodology_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', sa.String(50), nullable=False, unique=True),
        sa.Column('section_number', sa.String(50), nullable=False),
        sa.Column('rule_title', sa.String(255), nullable=False),
        sa.Column('requirement_type', sa.String(50), nullable=False),
        sa.Column('equation_reference', sa.String(50), nullable=True),
        sa.Column('is_blocking', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata_json', json_type, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_vm0044_rule_meth_ver', 'vm0044_rule_definitions', ['methodology_version_id'])
    op.create_index('ix_vm0044_rule_id', 'vm0044_rule_definitions', ['rule_id'])

    # 3. vm0044_normative_dependencies
    op.create_table(
        'vm0044_normative_dependencies',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('methodology_version_id', uuid_type, sa.ForeignKey('vm0044_methodology_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('source_reference', sa.String(500), nullable=True),
        sa.Column('checksum_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_vm0044_norm_meth_ver', 'vm0044_normative_dependencies', ['methodology_version_id'])
    op.create_index('ix_vm0044_norm_code', 'vm0044_normative_dependencies', ['code'])

    # 4. vm0044_applicability_evaluations
    op.create_table(
        'vm0044_applicability_evaluations',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_id', uuid_type, sa.ForeignKey('biochar_batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('evaluation_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('facility_greenfield_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('feedstock_biogenic_waste_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('feedstock_geographic_origin_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('process_technology_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('end_use_eligibility_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('wetland_exclusion_passed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('worker_health_safety_passed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('overall_applicability_status', sa.String(50), nullable=False, server_default='INELIGIBLE'),
        sa.Column('findings_json', json_type, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_vm0044_app_org', 'vm0044_applicability_evaluations', ['organization_id'])
    op.create_index('ix_vm0044_app_project', 'vm0044_applicability_evaluations', ['project_id'])
    op.create_index('ix_vm0044_app_batch', 'vm0044_applicability_evaluations', ['batch_id'])

    # 5. vm0044_additionality_assessments
    op.create_table(
        'vm0044_additionality_assessments',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assessment_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('step1_regulatory_surplus_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step1_regulatory_notes', sa.Text(), nullable=True),
        sa.Column('step2_positive_list_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step2_penetration_rate_pct', sa.Numeric(6, 3), nullable=False, server_default='5.0'),
        sa.Column('step3_investment_analysis_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step3_analysis_option', sa.String(50), nullable=False, server_default='OPTION_2_BENCHMARK_ANALYSIS'),
        sa.Column('project_irr_pct', sa.Numeric(6, 3), nullable=True),
        sa.Column('benchmark_irr_pct', sa.Numeric(6, 3), nullable=True),
        sa.Column('benchmark_source', sa.String(255), nullable=True),
        sa.Column('overall_additionality_status', sa.String(50), nullable=False, server_default='INCOMPLETE'),
        sa.Column('evidence_hashes_json', json_type, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_vm0044_add_org', 'vm0044_additionality_assessments', ['organization_id'])
    op.create_index('ix_vm0044_add_project', 'vm0044_additionality_assessments', ['project_id'])

    # 6. vm0044_calculation_snapshots
    op.create_table(
        'vm0044_calculation_snapshots',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_id', uuid_type, sa.ForeignKey('biochar_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('methodology_code', sa.String(50), nullable=False, server_default='VM0044'),
        sa.Column('methodology_version', sa.String(50), nullable=False, server_default='1.2'),
        sa.Column('snapshot_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('snapshot_canonical_json', sa.Text(), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('created_by_user_id', uuid_type, nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_vm0044_snap_org', 'vm0044_calculation_snapshots', ['organization_id'])
    op.create_index('ix_vm0044_snap_project', 'vm0044_calculation_snapshots', ['project_id'])
    op.create_index('ix_vm0044_snap_batch', 'vm0044_calculation_snapshots', ['batch_id'])
    op.create_index('ix_vm0044_snap_hash', 'vm0044_calculation_snapshots', ['snapshot_hash'])

    # 7. vm0044_calculation_executions
    op.create_table(
        'vm0044_calculation_executions',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_id', uuid_type, sa.ForeignKey('biochar_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_id', uuid_type, sa.ForeignKey('vm0044_calculation_snapshots.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('calculation_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('execution_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(50), nullable=False, server_default='CALCULATED'),
        sa.Column('technology_class', sa.String(50), nullable=False),
        sa.Column('end_use_pathway', sa.String(50), nullable=False),
        sa.Column('pyrolysis_temp_celsius', sa.Float(), nullable=False),
        sa.Column('biochar_dry_mass_tonnes', sa.Numeric(18, 6), nullable=False),
        sa.Column('c_org_fraction', sa.Numeric(8, 6), nullable=False),
        sa.Column('permanence_factor_pr_de', sa.Numeric(6, 4), nullable=False),
        sa.Column('organic_carbon_stored_cc_tonnes', sa.Numeric(18, 6), nullable=False),
        sa.Column('gross_co2e_stored_tonnes', sa.Numeric(18, 6), nullable=False),
        sa.Column('er_ss_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('pe_d_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('pe_p_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('pe_c_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('pe_ps_total_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('er_ps_tonnes', sa.Numeric(18, 6), nullable=False),
        sa.Column('pe_as_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('le_ts_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('le_tap_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('le_total_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('er_gross_removals_tonnes', sa.Numeric(18, 6), nullable=False),
        sa.Column('uncertainty_pct', sa.Numeric(6, 3), nullable=False, server_default='0.0'),
        sa.Column('uncertainty_deduction_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('er_net_removals_tonnes', sa.Numeric(18, 6), nullable=False),
        sa.Column('calculation_hash', sa.String(64), nullable=False),
        sa.Column('equation_breakdown_json', json_type, nullable=False, server_default='{}'),
        sa.Column('audit_trail_json', json_type, nullable=False, server_default='{}'),
        sa.Column('qa_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('verified_by_user_id', uuid_type, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_vm0044_calc_org', 'vm0044_calculation_executions', ['organization_id'])
    op.create_index('ix_vm0044_calc_project', 'vm0044_calculation_executions', ['project_id'])
    op.create_index('ix_vm0044_calc_batch', 'vm0044_calculation_executions', ['batch_id'])
    op.create_index('ix_vm0044_calc_snapshot', 'vm0044_calculation_executions', ['snapshot_id'])
    op.create_index('ix_vm0044_calc_hash', 'vm0044_calculation_executions', ['calculation_hash'])
    op.create_index('idx_vm0044_calc_project_status', 'vm0044_calculation_executions', ['project_id', 'status'])
    op.create_index('idx_vm0044_calc_batch_version', 'vm0044_calculation_executions', ['batch_id', 'calculation_version'])


def downgrade() -> None:
    op.drop_table('vm0044_calculation_executions')
    op.drop_table('vm0044_calculation_snapshots')
    op.drop_table('vm0044_additionality_assessments')
    op.drop_table('vm0044_applicability_evaluations')
    op.drop_table('vm0044_normative_dependencies')
    op.drop_table('vm0044_rule_definitions')
    op.drop_table('vm0044_methodology_versions')
