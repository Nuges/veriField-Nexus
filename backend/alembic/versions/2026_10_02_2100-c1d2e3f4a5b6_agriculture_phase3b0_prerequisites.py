"""agriculture_phase3b0_prerequisites

Revision ID: c1d2e3f4a5b6
Revises: b3c4d5e6f7a8
Create Date: 2026-10-02 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    op.create_table(
        'agriculture_prerequisite_assessments',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_id', uuid_type, sa.ForeignKey('quantification_input_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assessment_code', sa.String(length=50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PREVIEW'),
        sa.Column('overall_readiness', sa.String(length=30), nullable=False, server_default='INCOMPLETE'),
        sa.Column('methodology_code', sa.String(length=50), nullable=False, server_default='VM0042'),
        sa.Column('methodology_version', sa.String(length=30), nullable=False, server_default='2.2'),
        sa.Column('corrections_clarifications_version', sa.String(length=30), nullable=False, server_default='2026-06-11'),
        sa.Column('rule_set_version', sa.String(length=60), nullable=False, server_default='VM0042_V2.2_RULES_CC20260611_V1.0'),
        sa.Column('vcs_standard_version', sa.String(length=30), nullable=False, server_default='VCS_V4.7'),
        sa.Column('vcs_resolution_metadata', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('quantification_route_map', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('esm_input_dossier', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('sampling_design_assessment', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('uncertainty_input_readiness', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('baseline_monitoring_pairing', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('dimensions', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('blocking_reasons', json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column('advisory_notes', json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column('assessment_hash', sa.String(length=64), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false' if not is_sqlite else '0')),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by_id', uuid_type, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by_id', uuid_type, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('superseded_by_id', uuid_type, sa.ForeignKey('agriculture_prerequisite_assessments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_agri_prereq_assessments_org_id', 'agriculture_prerequisite_assessments', ['organization_id'])
    op.create_index('ix_agri_prereq_assessments_project_id', 'agriculture_prerequisite_assessments', ['project_id'])
    op.create_index('ix_agri_prereq_assessments_snapshot_id', 'agriculture_prerequisite_assessments', ['snapshot_id'])
    op.create_index('ix_agri_prereq_assessments_code', 'agriculture_prerequisite_assessments', ['assessment_code'], unique=True)
    op.create_index('ix_agri_prereq_assessments_hash', 'agriculture_prerequisite_assessments', ['assessment_hash'])
    op.create_index('ix_agri_prereq_assessments_status', 'agriculture_prerequisite_assessments', ['status'])


def downgrade() -> None:
    op.drop_index('ix_agri_prereq_assessments_status', table_name='agriculture_prerequisite_assessments')
    op.drop_index('ix_agri_prereq_assessments_hash', table_name='agriculture_prerequisite_assessments')
    op.drop_index('ix_agri_prereq_assessments_code', table_name='agriculture_prerequisite_assessments')
    op.drop_index('ix_agri_prereq_assessments_snapshot_id', table_name='agriculture_prerequisite_assessments')
    op.drop_index('ix_agri_prereq_assessments_project_id', table_name='agriculture_prerequisite_assessments')
    op.drop_index('ix_agri_prereq_assessments_org_id', table_name='agriculture_prerequisite_assessments')
    op.drop_table('agriculture_prerequisite_assessments')
