"""Verification Package and Biochar Product Formulations Schema

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-16 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    is_sqlite = bind.dialect.name == "sqlite"
    uuid_default = None if is_sqlite else sa.text('gen_random_uuid()')
    now_default = sa.text('CURRENT_TIMESTAMP') if is_sqlite else sa.text('now()')

    from sqlalchemy.dialects import postgresql
    json_col_type = sa.JSON() if is_sqlite else postgresql.JSONB()
    dict_default = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")
    list_default = sa.text("'[]'") if is_sqlite else sa.text("'[]'::jsonb")

    # 1. verification_packages
    if 'verification_packages' not in existing_tables:
        op.create_table(
            'verification_packages',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('monitoring_period_start', sa.Date(), nullable=False),
            sa.Column('monitoring_period_end', sa.Date(), nullable=False),
            sa.Column('package_name', sa.String(255), nullable=False),
            sa.Column('package_version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('parent_package_id', sa.UUID(), sa.ForeignKey('verification_packages.id', ondelete='SET NULL'), nullable=True),
            sa.Column('package_status', sa.String(50), nullable=False, server_default='DRAFT'),
            sa.Column('registry_target', sa.String(50), nullable=False, server_default='PURO_STANDARD'),
            sa.Column('audit_type', sa.String(50), nullable=False, server_default='OUTPUT_AUDIT'),
            sa.Column('manifest_json', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('manifest_hash', sa.String(64), nullable=False),
            sa.Column('ledger_signature_id', sa.UUID(), sa.ForeignKey('signatures.id', ondelete='SET NULL'), nullable=True),
            sa.Column('sealed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sealed_by_user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('diff_summary_json', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('completeness_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('blocker_reasons', json_col_type, nullable=False, server_default=list_default),
            sa.Column('metadata_json', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default),
        )
        op.create_index('ix_verification_packages_status', 'verification_packages', ['package_status'])
        op.create_index('ix_verification_packages_project_period', 'verification_packages', ['project_id', 'monitoring_period_start', 'monitoring_period_end'])

    # 2. verification_package_findings
    if 'verification_package_findings' not in existing_tables:
        op.create_table(
            'verification_package_findings',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('package_id', sa.UUID(), sa.ForeignKey('verification_packages.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('finding_number', sa.String(50), nullable=False, index=True),
            sa.Column('finding_type', sa.String(50), nullable=False, server_default='CAR'),
            sa.Column('severity', sa.String(50), nullable=False, server_default='MAJOR'),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('target_domain', sa.String(100), nullable=False),
            sa.Column('target_record_id', sa.UUID(), nullable=True),
            sa.Column('target_field', sa.String(100), nullable=True),
            sa.Column('status', sa.String(50), nullable=False, server_default='OPEN', index=True),
            sa.Column('auditor_user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('auditor_organization', sa.String(255), nullable=True),
            sa.Column('project_response', sa.Text(), nullable=True),
            sa.Column('response_submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolution_notes', sa.Text(), nullable=True),
            sa.Column('resolution_package_id', sa.UUID(), sa.ForeignKey('verification_packages.id', ondelete='SET NULL'), nullable=True),
            sa.Column('metadata_json', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default),
        )

    # 3. verification_package_evidence
    if 'verification_package_evidence' not in existing_tables:
        op.create_table(
            'verification_package_evidence',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('package_id', sa.UUID(), sa.ForeignKey('verification_packages.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('evidence_category', sa.String(100), nullable=False, index=True),
            sa.Column('reference_domain', sa.String(100), nullable=False),
            sa.Column('reference_id', sa.UUID(), nullable=False, index=True),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('file_name', sa.String(255), nullable=False),
            sa.Column('file_uri', sa.String(500), nullable=False),
            sa.Column('file_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('sha256_hash', sa.String(64), nullable=False, index=True),
            sa.Column('verified_hash', sa.String(64), nullable=True),
            sa.Column('integrity_status', sa.String(50), nullable=False, server_default='VERIFIED'),
            sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('metadata_json', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default),
        )

    # 4. verification_access_grants
    if 'verification_access_grants' not in existing_tables:
        op.create_table(
            'verification_access_grants',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('package_id', sa.UUID(), sa.ForeignKey('verification_packages.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('auditor_user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column('auditor_email', sa.String(255), nullable=False, index=True),
            sa.Column('auditor_organization', sa.String(255), nullable=False),
            sa.Column('grantee_role', sa.String(50), nullable=False, server_default='AUDITOR'),
            sa.Column('access_key_hash', sa.String(64), nullable=True, index=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default),
        )

    # 5. biochar_product_formulations
    if 'biochar_product_formulations' not in existing_tables:
        op.create_table(
            'biochar_product_formulations',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column('product_name', sa.String(255), nullable=False),
            sa.Column('product_code', sa.String(50), nullable=False, unique=True, index=True),
            sa.Column('target_sector', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('biochar_target_ratio', sa.Float(), nullable=False, server_default='0.5'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('metadata_json', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default),
        )

    # 6. biochar_product_batches
    if 'biochar_product_batches' not in existing_tables:
        op.create_table(
            'biochar_product_batches',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column('formulation_id', sa.UUID(), sa.ForeignKey('biochar_product_formulations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('batch_number', sa.String(50), nullable=False, unique=True, index=True),
            sa.Column('production_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('total_product_mass_tonnes', sa.Numeric(18, 6), nullable=False),
            sa.Column('biochar_mass_tonnes', sa.Numeric(18, 6), nullable=False),
            sa.Column('non_biochar_mass_tonnes', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
            sa.Column('packaging_type', sa.String(100), nullable=True),
            sa.Column('storage_location', sa.String(255), nullable=True),
            sa.Column('qa_status', sa.String(50), nullable=False, server_default='APPROVED'),
            sa.Column('metadata_json', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default),
        )

    # 7. biochar_product_ingredient_allocations
    if 'biochar_product_ingredient_allocations' not in existing_tables:
        op.create_table(
            'biochar_product_ingredient_allocations',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('product_batch_id', sa.UUID(), sa.ForeignKey('biochar_product_batches.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('biochar_batch_id', sa.UUID(), sa.ForeignKey('biochar_batches.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('allocated_biochar_mass_tonnes', sa.Numeric(18, 6), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default),
        )

    # 8. biochar_product_non_biochar_ingredients
    if 'biochar_product_non_biochar_ingredients' not in existing_tables:
        op.create_table(
            'biochar_product_non_biochar_ingredients',
            sa.Column('id', sa.UUID(), primary_key=True, server_default=uuid_default),
            sa.Column('product_batch_id', sa.UUID(), sa.ForeignKey('biochar_product_batches.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('ingredient_name', sa.String(255), nullable=False),
            sa.Column('ingredient_type', sa.String(100), nullable=False),
            sa.Column('mass_tonnes', sa.Numeric(18, 6), nullable=False),
            sa.Column('mass_pct', sa.Float(), nullable=False),
            sa.Column('cas_number', sa.String(50), nullable=True),
            sa.Column('supplier', sa.String(255), nullable=True),
            sa.Column('metadata_json', json_col_type, nullable=False, server_default=dict_default),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default),
        )


def downgrade() -> None:
    op.drop_table('biochar_product_non_biochar_ingredients')
    op.drop_table('biochar_product_ingredient_allocations')
    op.drop_table('biochar_product_batches')
    op.drop_table('biochar_product_formulations')
    op.drop_table('verification_access_grants')
    op.drop_table('verification_package_evidence')
    op.drop_table('verification_package_findings')
    op.drop_table('verification_packages')
