"""agriculture_mrv_phase3a_quantification_snapshots

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-25 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    op.create_table(
        'quantification_input_snapshots',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_code', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='LOCKED'),
        sa.Column('context', sa.String(length=30), nullable=False, server_default='MONITORING'),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('methodology_version_id', uuid_type, sa.ForeignKey('methodology_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('methodology_code', sa.String(length=50), nullable=False, server_default='VM0042'),
        sa.Column('methodology_version', sa.String(length=30), nullable=False, server_default='2.2'),
        sa.Column('rule_set_version', sa.String(length=50), nullable=False, server_default='VM0042_V2.2_RULES_V1.0'),
        sa.Column('project_boundary_version_id', uuid_type, sa.ForeignKey('project_boundary_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sampling_campaign_id', uuid_type, sa.ForeignKey('sampling_campaigns.id', ondelete='SET NULL'), nullable=True),
        sa.Column('snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('true' if not is_sqlite else '1')),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by_id', uuid_type, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by_id', uuid_type, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('total_eligible_measurements', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_excluded_measurements', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('readiness_summary', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('input_package', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('source_evidence_ids', json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_quantification_input_snapshots_organization_id', 'quantification_input_snapshots', ['organization_id'])
    op.create_index('ix_quantification_input_snapshots_project_id', 'quantification_input_snapshots', ['project_id'])
    op.create_index('ix_quantification_input_snapshots_snapshot_code', 'quantification_input_snapshots', ['snapshot_code'], unique=True)
    op.create_index('ix_quantification_input_snapshots_snapshot_hash', 'quantification_input_snapshots', ['snapshot_hash'])
    op.create_index('ix_quantification_input_snapshots_status', 'quantification_input_snapshots', ['status'])


def downgrade() -> None:
    op.drop_index('ix_quantification_input_snapshots_status', table_name='quantification_input_snapshots')
    op.drop_index('ix_quantification_input_snapshots_snapshot_hash', table_name='quantification_input_snapshots')
    op.drop_index('ix_quantification_input_snapshots_snapshot_code', table_name='quantification_input_snapshots')
    op.drop_index('ix_quantification_input_snapshots_project_id', table_name='quantification_input_snapshots')
    op.drop_index('ix_quantification_input_snapshots_organization_id', table_name='quantification_input_snapshots')
    op.drop_table('quantification_input_snapshots')
