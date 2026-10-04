"""agriculture_laboratory_bulk_import

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-01 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    # 1. Create laboratory_import_batches
    op.create_table(
        'laboratory_import_batches',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sampling_campaign_id', uuid_type, sa.ForeignKey('sampling_campaigns.id', ondelete='SET NULL'), nullable=True),
        sa.Column('laboratory_name', sa.String(length=150), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=10), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_sha256', sa.String(length=64), nullable=False),
        sa.Column('evidence_id', uuid_type, sa.ForeignKey('evidence_records.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='UPLOADED'),
        sa.Column('source_type', sa.String(length=30), nullable=False, server_default='FILE_IMPORT'),
        sa.Column('uploaded_by', uuid_type, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('mapping_version', sa.String(length=30), nullable=False, server_default='V1.0'),
        sa.Column('mapping_config', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warning_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_summary', json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_laboratory_import_batches_organization_id', 'laboratory_import_batches', ['organization_id'])
    op.create_index('ix_laboratory_import_batches_project_id', 'laboratory_import_batches', ['project_id'])
    op.create_index('ix_laboratory_import_batches_sampling_campaign_id', 'laboratory_import_batches', ['sampling_campaign_id'])
    op.create_index('ix_laboratory_import_batches_file_sha256', 'laboratory_import_batches', ['file_sha256'])
    op.create_index('ix_laboratory_import_batches_evidence_id', 'laboratory_import_batches', ['evidence_id'])
    op.create_index('ix_laboratory_import_batches_status', 'laboratory_import_batches', ['status'])

    # 2. Create laboratory_import_rows
    op.create_table(
        'laboratory_import_rows',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('import_batch_id', uuid_type, sa.ForeignKey('laboratory_import_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_sheet_name', sa.String(length=100), nullable=True),
        sa.Column('source_row_number', sa.Integer(), nullable=False),
        sa.Column('raw_row_payload', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('mapped_payload', json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column('validation_status', sa.String(length=30), nullable=False, server_default='VALID'),
        sa.Column('validation_messages', json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column('matched_sample_id', uuid_type, sa.ForeignKey('physical_samples.id', ondelete='SET NULL'), nullable=True),
        sa.Column('matched_sample_code', sa.String(length=50), nullable=True),
        sa.Column('canonical_analyte', sa.String(length=50), nullable=True),
        sa.Column('raw_value', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('raw_unit', sa.String(length=30), nullable=True),
        sa.Column('normalized_value', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('normalized_unit', sa.String(length=30), nullable=True),
        sa.Column('resulting_lab_result_id', uuid_type, sa.ForeignKey('laboratory_results.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_laboratory_import_rows_import_batch_id', 'laboratory_import_rows', ['import_batch_id'])
    op.create_index('ix_laboratory_import_rows_organization_id', 'laboratory_import_rows', ['organization_id'])
    op.create_index('ix_laboratory_import_rows_project_id', 'laboratory_import_rows', ['project_id'])
    op.create_index('ix_laboratory_import_rows_validation_status', 'laboratory_import_rows', ['validation_status'])
    op.create_index('ix_laboratory_import_rows_matched_sample_id', 'laboratory_import_rows', ['matched_sample_id'])
    op.create_index('ix_laboratory_import_rows_resulting_lab_result_id', 'laboratory_import_rows', ['resulting_lab_result_id'])


def downgrade() -> None:
    op.drop_index('ix_laboratory_import_rows_resulting_lab_result_id', table_name='laboratory_import_rows')
    op.drop_index('ix_laboratory_import_rows_matched_sample_id', table_name='laboratory_import_rows')
    op.drop_index('ix_laboratory_import_rows_validation_status', table_name='laboratory_import_rows')
    op.drop_index('ix_laboratory_import_rows_project_id', table_name='laboratory_import_rows')
    op.drop_index('ix_laboratory_import_rows_organization_id', table_name='laboratory_import_rows')
    op.drop_index('ix_laboratory_import_rows_import_batch_id', table_name='laboratory_import_rows')
    op.drop_table('laboratory_import_rows')

    op.drop_index('ix_laboratory_import_batches_status', table_name='laboratory_import_batches')
    op.drop_index('ix_laboratory_import_batches_evidence_id', table_name='laboratory_import_batches')
    op.drop_index('ix_laboratory_import_batches_file_sha256', table_name='laboratory_import_batches')
    op.drop_index('ix_laboratory_import_batches_sampling_campaign_id', table_name='laboratory_import_batches')
    op.drop_index('ix_laboratory_import_batches_project_id', table_name='laboratory_import_batches')
    op.drop_index('ix_laboratory_import_batches_organization_id', table_name='laboratory_import_batches')
    op.drop_table('laboratory_import_batches')
