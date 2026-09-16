"""Biochar value chain schema migration

Revision ID: 8c2f1e4a5d3b
Revises: 7f9a1b2c3d4e
Create Date: 2026-09-16 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '8c2f1e4a5d3b'
down_revision = '7f9a1b2c3d4e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    is_sqlite = bind.dialect.name == "sqlite"
    uuid_default = None if is_sqlite else sa.text('gen_random_uuid()')
    now_default = sa.text('CURRENT_TIMESTAMP') if is_sqlite else sa.text('now()')

    # 1. biochar_feedstock_sources
    if 'biochar_feedstock_sources' not in existing_tables:
        op.create_table(
            'biochar_feedstock_sources',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=True),
            sa.Column('source_code', sa.String(length=50), nullable=False),
            sa.Column('source_name', sa.String(length=255), nullable=False),
            sa.Column('source_type', sa.String(length=50), nullable=False),
            sa.Column('biomass_type', sa.String(length=100), nullable=False),
            sa.Column('origin_location', sa.String(length=255), nullable=True),
            sa.Column('source_land_unit_id', sa.UUID(), nullable=True),
            sa.Column('supplier_name', sa.String(length=255), nullable=True),
            sa.Column('waste_status', sa.String(length=50), server_default='CONFIRMED_WASTE_BIOMASS', nullable=False),
            sa.Column('baseline_fate', sa.String(length=50), server_default='OPEN_BURNING', nullable=False),
            sa.Column('sustainability_status', sa.String(length=50), server_default='LOW_RISK', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['source_land_unit_id'], ['land_units.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('source_code')
        )
        op.create_index('ix_biochar_feedstock_sources_org_id', 'biochar_feedstock_sources', ['organization_id'])
        op.create_index('ix_biochar_feedstock_sources_project_id', 'biochar_feedstock_sources', ['project_id'])
        op.create_index('ix_biochar_feedstock_sources_land_unit_id', 'biochar_feedstock_sources', ['source_land_unit_id'])

    # 2. biochar_feedstock_lots
    if 'biochar_feedstock_lots' not in existing_tables:
        op.create_table(
            'biochar_feedstock_lots',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=True),
            sa.Column('source_id', sa.UUID(), nullable=False),
            sa.Column('lot_number', sa.String(length=50), nullable=False),
            sa.Column('feedstock_type', sa.String(length=100), nullable=False),
            sa.Column('mass_received_tonnes', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('moisture_content_pct', sa.Numeric(precision=6, scale=2), nullable=False),
            sa.Column('dry_mass_tonnes', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('allocated_mass_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=False),
            sa.Column('dry_basis_derivation_method', sa.String(length=100), server_default='OVEN_DRY_BASIS_ASTM_D4442', nullable=False),
            sa.Column('receipt_date', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.Column('storage_location', sa.String(length=255), nullable=True),
            sa.Column('chain_of_custody_ref', sa.String(length=100), nullable=True),
            sa.Column('evidence_hash', sa.String(length=64), nullable=True),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['source_id'], ['biochar_feedstock_sources.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('lot_number')
        )
        op.create_index('ix_biochar_feedstock_lots_org_id', 'biochar_feedstock_lots', ['organization_id'])
        op.create_index('ix_biochar_feedstock_lots_project_id', 'biochar_feedstock_lots', ['project_id'])
        op.create_index('ix_biochar_feedstock_lots_source_id', 'biochar_feedstock_lots', ['source_id'])

    # 3. biochar_production_facilities
    if 'biochar_production_facilities' not in existing_tables:
        op.create_table(
            'biochar_production_facilities',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=True),
            sa.Column('facility_code', sa.String(length=50), nullable=False),
            sa.Column('facility_name', sa.String(length=255), nullable=False),
            sa.Column('location', sa.String(length=255), nullable=True),
            sa.Column('commissioning_date', sa.Date(), nullable=True),
            sa.Column('first_biochar_production_date', sa.Date(), nullable=True),
            sa.Column('project_start_date', sa.Date(), nullable=True),
            sa.Column('facility_status', sa.String(length=50), server_default='NEW_OPERATIONAL', nullable=False),
            sa.Column('operator_name', sa.String(length=255), nullable=True),
            sa.Column('technology_type', sa.String(length=100), server_default='SLOW_PYROLYSIS', nullable=False),
            sa.Column('production_capacity_tpy', sa.Float(), nullable=True),
            sa.Column('permits_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('emissions_controls_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('energy_recovery_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1' if is_sqlite else 'true', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('facility_code')
        )
        op.create_index('ix_biochar_facilities_org_id', 'biochar_production_facilities', ['organization_id'])
        op.create_index('ix_biochar_facilities_project_id', 'biochar_production_facilities', ['project_id'])

    # 4. biochar_facility_reactors
    if 'biochar_facility_reactors' not in existing_tables:
        op.create_table(
            'biochar_facility_reactors',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('reactor_code', sa.String(length=50), nullable=False),
            sa.Column('manufacturer', sa.String(length=100), nullable=True),
            sa.Column('model', sa.String(length=100), nullable=True),
            sa.Column('technology_type', sa.String(length=100), server_default='SLOW_PYROLYSIS', nullable=False),
            sa.Column('design_capacity_kg_h', sa.Float(), nullable=True),
            sa.Column('operating_temp_min_c', sa.Float(), server_default='450.0', nullable=True),
            sa.Column('operating_temp_max_c', sa.Float(), server_default='700.0', nullable=True),
            sa.Column('residence_time_min_minutes', sa.Float(), server_default='20.0', nullable=True),
            sa.Column('residence_time_max_minutes', sa.Float(), server_default='60.0', nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1' if is_sqlite else 'true', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_biochar_reactors_facility_id', 'biochar_facility_reactors', ['facility_id'])

    # 5. biochar_production_runs
    if 'biochar_production_runs' not in existing_tables:
        op.create_table(
            'biochar_production_runs',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=True),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('reactor_id', sa.UUID(), nullable=True),
            sa.Column('run_number', sa.String(length=50), nullable=False),
            sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
            sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('total_feedstock_input_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=False),
            sa.Column('total_feedstock_dry_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=False),
            sa.Column('avg_pyrolysis_temp_celsius', sa.Float(), nullable=False),
            sa.Column('max_pyrolysis_temp_celsius', sa.Float(), nullable=True),
            sa.Column('residence_time_minutes', sa.Float(), nullable=False),
            sa.Column('electricity_kwh', sa.Float(), server_default='0', nullable=False),
            sa.Column('fuel_liters', sa.Float(), server_default='0', nullable=False),
            sa.Column('heat_recovered_mj', sa.Float(), server_default='0', nullable=False),
            sa.Column('output_biochar_mass_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=False),
            sa.Column('co_products_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('operator_id', sa.UUID(), nullable=True),
            sa.Column('qa_status', sa.String(length=50), server_default='LOGGED', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['reactor_id'], ['biochar_facility_reactors.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('run_number')
        )
        op.create_index('ix_biochar_runs_org_id', 'biochar_production_runs', ['organization_id'])
        op.create_index('ix_biochar_runs_facility_id', 'biochar_production_runs', ['facility_id'])

    # 6. biochar_feedstock_run_allocations
    if 'biochar_feedstock_run_allocations' not in existing_tables:
        op.create_table(
            'biochar_feedstock_run_allocations',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('lot_id', sa.UUID(), nullable=False),
            sa.Column('production_run_id', sa.UUID(), nullable=False),
            sa.Column('allocated_wet_mass_tonnes', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('allocated_dry_mass_tonnes', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['lot_id'], ['biochar_feedstock_lots.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['production_run_id'], ['biochar_production_runs.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_biochar_alloc_lot_id', 'biochar_feedstock_run_allocations', ['lot_id'])
        op.create_index('ix_biochar_alloc_run_id', 'biochar_feedstock_run_allocations', ['production_run_id'])

    # 7. Safely alter biochar_batches table
    if 'biochar_batches' in existing_tables:
        batch_cols = {col['name'] for col in insp.get_columns('biochar_batches')}
        with op.batch_alter_table('biochar_batches') as batch_op:
            if 'organization_id' not in batch_cols:
                batch_op.add_column(sa.Column('organization_id', sa.UUID(), nullable=True))
            if 'project_id' not in batch_cols:
                batch_op.add_column(sa.Column('project_id', sa.UUID(), nullable=True))
            if 'production_run_id' not in batch_cols:
                batch_op.add_column(sa.Column('production_run_id', sa.UUID(), nullable=True))
            if 'facility_name' not in batch_cols:
                batch_op.add_column(sa.Column('facility_name', sa.String(length=100), server_default='Facility', nullable=True))
            if 'feedstock_type' not in batch_cols:
                batch_op.add_column(sa.Column('feedstock_type', sa.String(length=100), server_default='Agricultural Residue', nullable=True))
            if 'feedstock_weight_tonnes' not in batch_cols:
                batch_op.add_column(sa.Column('feedstock_weight_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=True))
            if 'moisture_content_pct' not in batch_cols:
                batch_op.add_column(sa.Column('moisture_content_pct', sa.Numeric(precision=6, scale=2), server_default='0', nullable=True))
            if 'origin_location' not in batch_cols:
                batch_op.add_column(sa.Column('origin_location', sa.String(length=255), nullable=True))
            if 'pyrolysis_temp_celsius' not in batch_cols:
                batch_op.add_column(sa.Column('pyrolysis_temp_celsius', sa.Float(), server_default='550.0', nullable=True))
            if 'residence_time_minutes' not in batch_cols:
                batch_op.add_column(sa.Column('residence_time_minutes', sa.Float(), server_default='30.0', nullable=True))
            if 'kiln_operator_id' not in batch_cols:
                batch_op.add_column(sa.Column('kiln_operator_id', sa.UUID(), nullable=True))
            if 'biochar_yield_tonnes' not in batch_cols:
                batch_op.add_column(sa.Column('biochar_yield_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=True))
            if 'dry_mass_tonnes' not in batch_cols:
                batch_op.add_column(sa.Column('dry_mass_tonnes', sa.Numeric(precision=18, scale=6), nullable=True))
            if 'fixed_carbon_pct' not in batch_cols:
                batch_op.add_column(sa.Column('fixed_carbon_pct', sa.Float(), server_default='75.0', nullable=True))
            if 'ash_content_pct' not in batch_cols:
                batch_op.add_column(sa.Column('ash_content_pct', sa.Float(), server_default='5.0', nullable=True))
            if 'molar_h_c_ratio' not in batch_cols:
                batch_op.add_column(sa.Column('molar_h_c_ratio', sa.Float(), server_default='0.4', nullable=True))
            if 'carbon_permanence_factor' not in batch_cols:
                batch_op.add_column(sa.Column('carbon_permanence_factor', sa.Float(), server_default='0.85', nullable=True))
            if 'net_co2e_removed_tonnes' not in batch_cols:
                batch_op.add_column(sa.Column('net_co2e_removed_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=True))
            if 'lab_report_number' not in batch_cols:
                batch_op.add_column(sa.Column('lab_report_number', sa.String(length=100), nullable=True))
            if 'lab_sample_id' not in batch_cols:
                batch_op.add_column(sa.Column('lab_sample_id', sa.String(length=100), nullable=True))
            if 'quality_grade' not in batch_cols:
                batch_op.add_column(sa.Column('quality_grade', sa.String(length=20), server_default='GRADE_A', nullable=True))
            if 'lab_document_url' not in batch_cols:
                batch_op.add_column(sa.Column('lab_document_url', sa.Text(), nullable=True))
            if 'status' not in batch_cols:
                batch_op.add_column(sa.Column('status', sa.String(length=30), server_default='PRODUCED', nullable=True))
            if 'has_anomaly' not in batch_cols:
                batch_op.add_column(sa.Column('has_anomaly', sa.Boolean(), server_default='0' if is_sqlite else 'false', nullable=True))
            if 'anomaly_reason' not in batch_cols:
                batch_op.add_column(sa.Column('anomaly_reason', sa.Text(), nullable=True))
            if 'carbon_claim_project_id' not in batch_cols:
                batch_op.add_column(sa.Column('carbon_claim_project_id', sa.UUID(), nullable=True))
            if 'carbon_claim_registry' not in batch_cols:
                batch_op.add_column(sa.Column('carbon_claim_registry', sa.String(length=50), nullable=True))
            if 'carbon_claim_methodology' not in batch_cols:
                batch_op.add_column(sa.Column('carbon_claim_methodology', sa.String(length=50), nullable=True))
            if 'mass_balance_allocated_tonnes' not in batch_cols:
                batch_op.add_column(sa.Column('mass_balance_allocated_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=True))
            if 'mass_balance_status' not in batch_cols:
                batch_op.add_column(sa.Column('mass_balance_status', sa.String(length=50), server_default='IN_BALANCE', nullable=True))
            if 'batch_digest_hash' not in batch_cols:
                batch_op.add_column(sa.Column('batch_digest_hash', sa.String(length=64), nullable=True))
            if 'metadata_json' not in batch_cols:
                batch_op.add_column(sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True))
            if 'updated_at' not in batch_cols:
                batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True))
    else:
        op.create_table(
            'biochar_batches',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=True),
            sa.Column('project_id', sa.UUID(), nullable=False),
            sa.Column('batch_number', sa.String(length=50), nullable=False),
            sa.Column('facility_name', sa.String(length=100), server_default='Facility', nullable=True),
            sa.Column('kiln_id', sa.String(length=50), nullable=True),
            sa.Column('production_run_id', sa.UUID(), nullable=True),
            sa.Column('feedstock_type', sa.String(length=100), server_default='Agricultural Residue', nullable=True),
            sa.Column('feedstock_weight_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=True),
            sa.Column('moisture_content_pct', sa.Numeric(precision=6, scale=2), server_default='0', nullable=True),
            sa.Column('origin_location', sa.String(length=255), nullable=True),
            sa.Column('pyrolysis_temp_celsius', sa.Float(), server_default='550.0', nullable=True),
            sa.Column('residence_time_minutes', sa.Float(), server_default='30.0', nullable=True),
            sa.Column('kiln_operator_id', sa.UUID(), nullable=True),
            sa.Column('biochar_yield_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=True),
            sa.Column('dry_mass_tonnes', sa.Numeric(precision=18, scale=6), nullable=True),
            sa.Column('fixed_carbon_pct', sa.Float(), server_default='75.0', nullable=True),
            sa.Column('ash_content_pct', sa.Float(), server_default='5.0', nullable=True),
            sa.Column('molar_h_c_ratio', sa.Float(), server_default='0.4', nullable=True),
            sa.Column('carbon_permanence_factor', sa.Float(), server_default='0.85', nullable=True),
            sa.Column('net_co2e_removed_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=True),
            sa.Column('lab_report_number', sa.String(length=100), nullable=True),
            sa.Column('lab_sample_id', sa.String(length=100), nullable=True),
            sa.Column('quality_grade', sa.String(length=20), server_default='GRADE_A', nullable=True),
            sa.Column('lab_document_url', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=30), server_default='PRODUCED', nullable=True),
            sa.Column('has_anomaly', sa.Boolean(), server_default='0' if is_sqlite else 'false', nullable=True),
            sa.Column('anomaly_reason', sa.Text(), nullable=True),
            sa.Column('carbon_claim_project_id', sa.UUID(), nullable=True),
            sa.Column('carbon_claim_registry', sa.String(length=50), nullable=True),
            sa.Column('carbon_claim_methodology', sa.String(length=50), nullable=True),
            sa.Column('mass_balance_allocated_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=True),
            sa.Column('mass_balance_status', sa.String(length=50), server_default='IN_BALANCE', nullable=True),
            sa.Column('batch_digest_hash', sa.String(length=64), nullable=True),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['production_run_id'], ['biochar_production_runs.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('batch_number')
        )
        op.create_index('ix_biochar_batches_batch_number', 'biochar_batches', ['batch_number'])

    # 8. biochar_lab_analyses
    if 'biochar_lab_analyses' not in existing_tables:
        op.create_table(
            'biochar_lab_analyses',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=True),
            sa.Column('batch_id', sa.UUID(), nullable=False),
            sa.Column('sample_id', sa.String(length=100), nullable=False),
            sa.Column('sampling_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('testing_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('laboratory_name', sa.String(length=255), nullable=False),
            sa.Column('accreditation_standard', sa.String(length=100), nullable=True),
            sa.Column('test_method', sa.String(length=100), nullable=True),
            sa.Column('molar_h_c_ratio', sa.Float(), nullable=False),
            sa.Column('organic_carbon_pct', sa.Float(), nullable=False),
            sa.Column('fixed_carbon_pct', sa.Float(), nullable=False),
            sa.Column('moisture_pct', sa.Float(), nullable=False),
            sa.Column('ash_pct', sa.Float(), nullable=False),
            sa.Column('volatile_matter_pct', sa.Float(), nullable=True),
            sa.Column('heavy_metals_pass', sa.Boolean(), server_default='1' if is_sqlite else 'true', nullable=False),
            sa.Column('pah_content_mg_kg', sa.Float(), nullable=True),
            sa.Column('lab_report_hash', sa.String(length=64), nullable=True),
            sa.Column('lab_report_uri', sa.String(length=500), nullable=True),
            sa.Column('qa_status', sa.String(length=50), server_default='VERIFIED', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['biochar_batches.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_biochar_lab_org_id', 'biochar_lab_analyses', ['organization_id'])
        op.create_index('ix_biochar_lab_batch_id', 'biochar_lab_analyses', ['batch_id'])

    # 9. biochar_material_transactions
    if 'biochar_material_transactions' not in existing_tables:
        op.create_table(
            'biochar_material_transactions',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('batch_id', sa.UUID(), nullable=False),
            sa.Column('transaction_type', sa.String(length=50), nullable=False),
            sa.Column('quantity_tonnes', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('from_location', sa.String(length=255), nullable=True),
            sa.Column('to_location', sa.String(length=255), nullable=True),
            sa.Column('event_time', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.Column('source_event_id', sa.UUID(), nullable=True),
            sa.Column('evidence_hash', sa.String(length=64), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['biochar_batches.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_biochar_mat_tx_batch_id', 'biochar_material_transactions', ['batch_id'])
        op.create_index('ix_biochar_mat_tx_org_id', 'biochar_material_transactions', ['organization_id'])

    # 10. biochar_transport_events
    if 'biochar_transport_events' not in existing_tables:
        op.create_table(
            'biochar_transport_events',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=True),
            sa.Column('material_type', sa.String(length=50), nullable=False),
            sa.Column('reference_id', sa.UUID(), nullable=False),
            sa.Column('origin_address', sa.String(length=255), nullable=False),
            sa.Column('destination_address', sa.String(length=255), nullable=False),
            sa.Column('mass_transported_tonnes', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('distance_km', sa.Float(), nullable=False),
            sa.Column('distance_source', sa.String(length=100), server_default='VERIFIED_ODOMETER_LOGISTICS', nullable=False),
            sa.Column('transport_mode', sa.String(length=50), server_default='ROAD_DIESEL_TRUCK', nullable=False),
            sa.Column('carrier_name', sa.String(length=255), nullable=True),
            sa.Column('departure_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('proof_of_delivery_ref', sa.String(length=100), nullable=True),
            sa.Column('pod_document_hash', sa.String(length=64), nullable=True),
            sa.Column('status', sa.String(length=50), server_default='DELIVERED', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_biochar_trans_org_id', 'biochar_transport_events', ['organization_id'])
        op.create_index('ix_biochar_trans_ref_id', 'biochar_transport_events', ['reference_id'])

    # 11. biochar_storage_events
    if 'biochar_storage_events' not in existing_tables:
        op.create_table(
            'biochar_storage_events',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('batch_id', sa.UUID(), nullable=False),
            sa.Column('storage_facility_name', sa.String(length=255), nullable=False),
            sa.Column('storage_location', sa.String(length=255), nullable=False),
            sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('quantity_stored_tonnes', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('loss_or_damage_tonnes', sa.Numeric(precision=18, scale=6), server_default='0', nullable=False),
            sa.Column('storage_conditions', sa.String(length=255), server_default='COVERED_DRY_VENTILATED', nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['biochar_batches.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_biochar_storage_batch_id', 'biochar_storage_events', ['batch_id'])

    # 12. biochar_end_use_records
    if 'biochar_end_use_records' not in existing_tables:
        op.create_table(
            'biochar_end_use_records',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=True),
            sa.Column('batch_id', sa.UUID(), nullable=False),
            sa.Column('end_use_type', sa.String(length=50), nullable=False),
            sa.Column('applied_quantity_tonnes', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('source_land_unit_id', sa.UUID(), nullable=True),
            sa.Column('application_rate_tonnes_per_ha', sa.Numeric(precision=12, scale=4), nullable=True),
            sa.Column('area_hectares', sa.Numeric(precision=12, scale=4), nullable=True),
            sa.Column('application_method', sa.String(length=100), nullable=True),
            sa.Column('gps_coordinates', sa.String(length=100), nullable=True),
            sa.Column('wetland_exclusion_screened', sa.Boolean(), server_default='1' if is_sqlite else 'true', nullable=False),
            sa.Column('crop_type', sa.String(length=100), nullable=True),
            sa.Column('product_category', sa.String(length=100), nullable=True),
            sa.Column('recipient_organization', sa.String(length=255), nullable=True),
            sa.Column('durability_classification', sa.String(length=100), nullable=True),
            sa.Column('proof_photos_json', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('verification_status', sa.String(length=50), server_default='PENDING_VERIFICATION', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['biochar_batches.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['source_land_unit_id'], ['land_units.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_biochar_end_use_batch_id', 'biochar_end_use_records', ['batch_id'])
        op.create_index('ix_biochar_end_use_land_unit_id', 'biochar_end_use_records', ['source_land_unit_id'])

    # 13. biochar_carbon_pool_claims
    if 'biochar_carbon_pool_claims' not in existing_tables:
        op.create_table(
            'biochar_carbon_pool_claims',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=False),
            sa.Column('batch_id', sa.UUID(), nullable=True),
            sa.Column('land_unit_id', sa.UUID(), nullable=True),
            sa.Column('methodology_code', sa.String(length=50), nullable=False),
            sa.Column('carbon_pool', sa.String(length=50), server_default='SOIL_ORGANIC_CARBON', nullable=False),
            sa.Column('claim_type', sa.String(length=50), server_default='EX_POST', nullable=False),
            sa.Column('period_start_date', sa.Date(), nullable=False),
            sa.Column('period_end_date', sa.Date(), nullable=False),
            sa.Column('claim_status', sa.String(length=50), server_default='PROPOSED', nullable=False),
            sa.Column('conflict_flag', sa.Boolean(), server_default='0' if is_sqlite else 'false', nullable=False),
            sa.Column('conflict_details', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('claimed_tco2e', sa.Numeric(precision=18, scale=6), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['biochar_batches.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['land_unit_id'], ['land_units.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_biochar_claim_org_id', 'biochar_carbon_pool_claims', ['organization_id'])
        op.create_index('ix_biochar_claim_project_id', 'biochar_carbon_pool_claims', ['project_id'])
        op.create_index('ix_biochar_claim_land_unit_id', 'biochar_carbon_pool_claims', ['land_unit_id'])
        op.create_index('ix_biochar_claim_pool', 'biochar_carbon_pool_claims', ['carbon_pool'])


def downgrade() -> None:
    op.drop_table('biochar_carbon_pool_claims')
    op.drop_table('biochar_end_use_records')
    op.drop_table('biochar_storage_events')
    op.drop_table('biochar_transport_events')
    op.drop_table('biochar_material_transactions')
    op.drop_table('biochar_lab_analyses')
    op.drop_table('biochar_feedstock_run_allocations')
    op.drop_table('biochar_production_runs')
    op.drop_table('biochar_facility_reactors')
    op.drop_table('biochar_production_facilities')
    op.drop_table('biochar_feedstock_lots')
    op.drop_table('biochar_feedstock_sources')
