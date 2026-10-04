"""puro_biochar_2026_standards_closure

Revision ID: a2b3c4d5e6f7
Revises: e6f7a8b9c0d1
Create Date: 2026-10-01 22:00:00.000000

Puro Biochar 2026 Standards Closure:
- Add c_counterfactual_tco2e and sourcing_criteria_version to puro_calculation_executions.
- Create puro_counterfactual_storage_assessments table for Puro Biomass Sourcing Criteria v1.3 Section 3 counterfactual storage compliance.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    # 1. Add columns to puro_calculation_executions
    op.add_column(
        'puro_calculation_executions',
        sa.Column('c_counterfactual_tco2e', sa.Numeric(18, 6), nullable=False, server_default='0.0')
    )
    op.add_column(
        'puro_calculation_executions',
        sa.Column('sourcing_criteria_version', sa.String(50), nullable=False, server_default='v1.3')
    )

    # 2. Create puro_counterfactual_storage_assessments
    op.create_table(
        'puro_counterfactual_storage_assessments',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('facility_id', uuid_type, sa.ForeignKey('biochar_production_facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_id', uuid_type, sa.ForeignKey('biochar_batches.id', ondelete='CASCADE'), nullable=True),
        sa.Column('feedstock_lot_id', uuid_type, sa.ForeignKey('biochar_feedstock_lots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('criteria_version', sa.String(50), nullable=False, server_default='v1.3'),
        sa.Column('counterfactual_path', sa.String(50), nullable=False),
        sa.Column('baseline_fate', sa.String(100), nullable=False),
        sa.Column('evidence_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('evidence_reference', sa.String(255), nullable=True),
        sa.Column('evidence_hash', sa.String(64), nullable=True),
        sa.Column('counterfactual_carbon_stored_tco2e', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('assessment_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('reason_code', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', json_type, nullable=False, server_default='{}'),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        'ix_puro_counterfactual_storage_assessments_org_id',
        'puro_counterfactual_storage_assessments',
        ['organization_id']
    )
    op.create_index(
        'ix_puro_counterfactual_storage_assessments_proj_id',
        'puro_counterfactual_storage_assessments',
        ['project_id']
    )
    op.create_index(
        'ix_puro_counterfactual_storage_assessments_fac_id',
        'puro_counterfactual_storage_assessments',
        ['facility_id']
    )
    op.create_index(
        'ix_puro_counterfactual_storage_assessments_batch_id',
        'puro_counterfactual_storage_assessments',
        ['batch_id']
    )
    op.create_index(
        'ix_puro_counterfactual_storage_assessments_lot_id',
        'puro_counterfactual_storage_assessments',
        ['feedstock_lot_id']
    )


def downgrade() -> None:
    op.drop_index('ix_puro_counterfactual_storage_assessments_lot_id', table_name='puro_counterfactual_storage_assessments')
    op.drop_index('ix_puro_counterfactual_storage_assessments_batch_id', table_name='puro_counterfactual_storage_assessments')
    op.drop_index('ix_puro_counterfactual_storage_assessments_fac_id', table_name='puro_counterfactual_storage_assessments')
    op.drop_index('ix_puro_counterfactual_storage_assessments_proj_id', table_name='puro_counterfactual_storage_assessments')
    op.drop_index('ix_puro_counterfactual_storage_assessments_org_id', table_name='puro_counterfactual_storage_assessments')
    op.drop_table('puro_counterfactual_storage_assessments')
    op.drop_column('puro_calculation_executions', 'sourcing_criteria_version')
    op.drop_column('puro_calculation_executions', 'c_counterfactual_tco2e')
