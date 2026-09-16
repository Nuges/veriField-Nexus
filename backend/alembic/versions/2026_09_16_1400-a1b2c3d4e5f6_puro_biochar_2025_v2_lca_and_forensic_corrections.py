"""Puro Biochar 2025 V2 LCA, Char Streams, and Forensic Quantification Schema

Revision ID: a1b2c3d4e5f6
Revises: 9d3e2f5b6a4c
Create Date: 2026-09-16 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9d3e2f5b6a4c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    is_sqlite = bind.dialect.name == "sqlite"
    uuid_default = None if is_sqlite else sa.text('gen_random_uuid()')
    now_default = sa.text('CURRENT_TIMESTAMP') if is_sqlite else sa.text('now()')

    # Ensure organizations table has licensed_sectors and licensed_methodologies if missing
    if 'organizations' in existing_tables:
        org_cols = {c['name'] for c in insp.get_columns('organizations')}
        from sqlalchemy.dialects import postgresql
        json_col_type = sa.JSON() if is_sqlite else postgresql.JSONB()
        json_default = sa.text("'[]'") if is_sqlite else sa.text("'[]'::jsonb")
        if 'licensed_sectors' not in org_cols:
            op.add_column('organizations', sa.Column('licensed_sectors', json_col_type, server_default=json_default, nullable=False))
        if 'licensed_methodologies' not in org_cols:
            op.add_column('organizations', sa.Column('licensed_methodologies', json_col_type, server_default=json_default, nullable=False))

    # Ensure projects table aligns with ORM model (nullable methodology_id, sector_id)
    if 'projects' in existing_tables:
        proj_cols = {c['name'] for c in insp.get_columns('projects')}
        if 'sector_id' not in proj_cols:
            op.add_column('projects', sa.Column('sector_id', sa.UUID(), nullable=True))
        try:
            op.alter_column('projects', 'methodology_id', nullable=True)
        except Exception:
            pass

    # Ensure methodology_families and methodologies align with ORM models
    if 'methodology_families' in existing_tables:
        fam_cols = {c['name'] for c in insp.get_columns('methodology_families')}
        if 'is_active' not in fam_cols:
            op.add_column('methodology_families', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
        if 'project_types' not in fam_cols:
            op.add_column('methodology_families', sa.Column('project_types', json_col_type, server_default=json_default, nullable=False))

    if 'methodologies' in existing_tables:
        meth_cols = {c['name'] for c in insp.get_columns('methodologies')}
        if 'recommendation_rules' not in meth_cols:
            dict_default = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")
            op.add_column('methodologies', sa.Column('recommendation_rules', json_col_type, server_default=dict_default, nullable=False))


    # 1. New Tables

    # 1.1 puro_char_stream_records (Rule 3.5.2)
    if 'puro_char_stream_records' not in existing_tables:
        op.create_table(
            'puro_char_stream_records',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('stream_code', sa.String(length=50), nullable=False),
            sa.Column('stream_name', sa.String(length=255), nullable=False),
            sa.Column('feedstock_type', sa.String(length=100), nullable=False),
            sa.Column('pyrolyzer_unit', sa.String(length=100), nullable=False),
            sa.Column('operating_temperature_celsius', sa.Float(), nullable=False),
            sa.Column('residence_time_minutes', sa.Float(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_puro_char_stream_records_stream_code'), 'puro_char_stream_records', ['stream_code'], unique=False)
        op.create_index(op.f('ix_puro_char_stream_records_facility_id'), 'puro_char_stream_records', ['facility_id'], unique=False)

    # 1.2 puro_lca_models (Section 7)
    if 'puro_lca_models' not in existing_tables:
        op.create_table(
            'puro_lca_models',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('model_name', sa.String(length=255), nullable=False),
            sa.Column('system_boundary', sa.String(length=100), server_default='CRADLE_TO_GATE_PLUS_DISPOSITION', nullable=False),
            sa.Column('crediting_years', sa.Integer(), server_default='10', nullable=False),
            sa.Column('allocation_method', sa.String(length=50), server_default='ENERGY_LHV', nullable=False),
            sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_puro_lca_models_facility_id'), 'puro_lca_models', ['facility_id'], unique=False)

    # 1.3 puro_lci_entries (Section 7 inventory)
    if 'puro_lci_entries' not in existing_tables:
        op.create_table(
            'puro_lci_entries',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('lca_model_id', sa.UUID(), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('item_name', sa.String(length=255), nullable=False),
            sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('unit', sa.String(length=50), nullable=False),
            sa.Column('emission_factor', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('ef_unit', sa.String(length=50), nullable=False),
            sa.Column('ef_source', sa.String(length=255), nullable=False),
            sa.Column('ghg_emissions_tco2e', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.ForeignKeyConstraint(['lca_model_id'], ['puro_lca_models.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_puro_lci_entries_lca_model_id'), 'puro_lci_entries', ['lca_model_id'], unique=False)

    # 1.4 puro_cutoff_decisions (Section 7.2)
    if 'puro_cutoff_decisions' not in existing_tables:
        op.create_table(
            'puro_cutoff_decisions',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('lca_model_id', sa.UUID(), nullable=False),
            sa.Column('input_material_stream', sa.String(length=255), nullable=False),
            sa.Column('mass_energy_contribution_pct', sa.Float(), nullable=False),
            sa.Column('justified_reason', sa.Text(), nullable=False),
            sa.Column('auditor_approved', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.ForeignKeyConstraint(['lca_model_id'], ['puro_lca_models.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_puro_cutoff_decisions_lca_model_id'), 'puro_cutoff_decisions', ['lca_model_id'], unique=False)

    # 1.4b puro_co_product_records (Rule 7.5.2)
    if 'puro_co_product_records' not in existing_tables:
        op.create_table(
            'puro_co_product_records',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('production_run_id', sa.UUID(), nullable=False),
            sa.Column('co_product_type', sa.String(length=50), nullable=False),
            sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('unit', sa.String(length=20), server_default='MJ', nullable=False),
            sa.Column('disposition_fate', sa.String(length=50), server_default='ENERGY_RECOVERY', nullable=False),
            sa.Column('emissions_impact_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False),
            sa.Column('storage_containment_details', sa.String(length=255), nullable=True),
            sa.Column('overflow_control_verified', sa.Boolean(), server_default='true', nullable=True),
            sa.Column('authorization_permit_ref', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['production_run_id'], ['biochar_production_runs.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_puro_co_product_records_production_run_id'), 'puro_co_product_records', ['production_run_id'], unique=False)

    # 1.5 puro_coproduct_allocations (Rule 7.5.2b)
    if 'puro_coproduct_allocations' not in existing_tables:
        op.create_table(
            'puro_coproduct_allocations',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('production_run_id', sa.UUID(), nullable=False),
            sa.Column('co_product_record_id', sa.UUID(), nullable=False),
            sa.Column('allocation_basis', sa.String(length=50), server_default='ENERGY_LHV', nullable=False),
            sa.Column('biochar_lhv_mj_kg', sa.Float(), nullable=False),
            sa.Column('coproduct_lhv_mj_kg', sa.Float(), nullable=False),
            sa.Column('biochar_allocation_share_pct', sa.Float(), nullable=False),
            sa.Column('coproduct_allocation_share_pct', sa.Float(), nullable=False),
            sa.Column('allocated_emissions_tco2e', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('justification', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.ForeignKeyConstraint(['co_product_record_id'], ['puro_co_product_records.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['production_run_id'], ['biochar_production_runs.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # 2. Add columns to puro_end_use_categories if missing
    if 'puro_end_use_categories' in existing_tables:
        existing_cols = {c['name'] for c in insp.get_columns('puro_end_use_categories')}
        with op.batch_alter_table('puro_end_use_categories') as batch_op:
            if 'application_type' not in existing_cols:
                batch_op.add_column(sa.Column('application_type', sa.String(length=50), nullable=True))
            if 'min_environmental_quality' not in existing_cols:
                batch_op.add_column(sa.Column('min_environmental_quality', sa.String(length=50), nullable=True))
            if 'reversal_rules' not in existing_cols:
                batch_op.add_column(sa.Column('reversal_rules', sa.JSON(), server_default='{}', nullable=True))
            if 'cascading_conditions' not in existing_cols:
                batch_op.add_column(sa.Column('cascading_conditions', sa.JSON(), server_default='{}', nullable=True))
            if 'reversal_discount_factor_required' not in existing_cols:
                batch_op.add_column(sa.Column('reversal_discount_factor_required', sa.Boolean(), server_default='false', nullable=True))

    # 3. Add columns to puro_calculation_executions if missing
    if 'puro_calculation_executions' in existing_tables:
        existing_cols = {c['name'] for c in insp.get_columns('puro_calculation_executions')}
        with op.batch_alter_table('puro_calculation_executions') as batch_op:
            if 'calculation_mode' not in existing_cols:
                batch_op.add_column(sa.Column('calculation_mode', sa.String(length=50), server_default='AUTHORITATIVE', nullable=False))
            if 'persistence_fraction_pf' not in existing_cols:
                batch_op.add_column(sa.Column('persistence_fraction_pf', sa.Float(), server_default='0.0', nullable=False))
            if 'persistence_m_param' not in existing_cols:
                batch_op.add_column(sa.Column('persistence_m_param', sa.Float(), nullable=True))
            if 'persistence_a_param' not in existing_cols:
                batch_op.add_column(sa.Column('persistence_a_param', sa.Float(), nullable=True))
            if 'durability_class' not in existing_cols:
                batch_op.add_column(sa.Column('durability_class', sa.String(length=50), server_default='CORC200+', nullable=False))
            if 'e_ops_biomass_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('e_ops_biomass_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'e_ops_production_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('e_ops_production_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'e_ops_use_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('e_ops_use_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'e_ops_total_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('e_ops_total_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'e_emb_infra_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('e_emb_infra_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'e_emb_dluc_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('e_emb_dluc_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'e_emb_annualized_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('e_emb_annualized_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'leakage_eco_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('leakage_eco_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'leakage_ma_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('leakage_ma_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'leakage_iluc_tco2e' not in existing_cols:
                batch_op.add_column(sa.Column('leakage_iluc_tco2e', sa.Numeric(precision=18, scale=6), server_default='0.0', nullable=False))
            if 'reported_uncertainty_text' not in existing_cols:
                batch_op.add_column(sa.Column('reported_uncertainty_text', sa.String(length=100), nullable=True))
            if 'superseded_at' not in existing_cols:
                batch_op.add_column(sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True))
            if 'superseded_reason' not in existing_cols:
                batch_op.add_column(sa.Column('superseded_reason', sa.String(length=255), nullable=True))
            if 'replacement_engine_version' not in existing_cols:
                batch_op.add_column(sa.Column('replacement_engine_version', sa.String(length=50), nullable=True))


def downgrade() -> None:
    pass
