"""Puro Biochar Edition 2025 V2 methodology schema migration

Revision ID: 9d3e2f5b6a4c
Revises: 8c2f1e4a5d3b
Create Date: 2026-09-16 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '9d3e2f5b6a4c'
down_revision = '8c2f1e4a5d3b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    is_sqlite = bind.dialect.name == "sqlite"
    uuid_default = None if is_sqlite else sa.text('gen_random_uuid()')
    now_default = sa.text('CURRENT_TIMESTAMP') if is_sqlite else sa.text('now()')

    # 1. puro_methodology_versions
    if 'puro_methodology_versions' not in existing_tables:
        op.create_table(
            'puro_methodology_versions',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('edition', sa.String(length=50), server_default='Edition 2025 v2', nullable=False),
            sa.Column('approval_date', sa.Date(), nullable=False),
            sa.Column('effective_date', sa.Date(), nullable=False),
            sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
            sa.Column('source_url', sa.String(length=500), nullable=True),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code', name='uq_puro_meth_versions_code')
        )

    # 2. puro_rule_definitions
    if 'puro_rule_definitions' not in existing_tables:
        op.create_table(
            'puro_rule_definitions',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('methodology_version_id', sa.UUID(), nullable=False),
            sa.Column('section_number', sa.Integer(), nullable=False),
            sa.Column('section_title', sa.String(length=255), nullable=False),
            sa.Column('rule_number', sa.String(length=50), nullable=False),
            sa.Column('rule_title', sa.String(length=255), nullable=False),
            sa.Column('applicability_condition', sa.String(length=255), nullable=True),
            sa.Column('requirement_type', sa.String(length=100), nullable=False),
            sa.Column('implementation_handler', sa.String(length=100), nullable=False),
            sa.Column('required_evidence_types', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('is_blocking', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('rule_number', name='uq_puro_rule_definitions_number'),
            sa.ForeignKeyConstraint(['methodology_version_id'], ['puro_methodology_versions.id'], ondelete='CASCADE')
        )

    # 3. puro_normative_dependencies
    if 'puro_normative_dependencies' not in existing_tables:
        op.create_table(
            'puro_normative_dependencies',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('version', sa.String(length=50), nullable=False),
            sa.Column('document_type', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
            sa.Column('effective_date', sa.Date(), nullable=False),
            sa.Column('source_reference', sa.String(length=500), nullable=True),
            sa.Column('required_by_rules', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('implementation_state', sa.String(length=50), server_default='DEPENDENCY_REQUIRED', nullable=False),
            sa.Column('checksum_hash', sa.String(length=64), nullable=True),
            sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code', name='uq_puro_normative_deps_code')
        )

    # 4. puro_supplier_profiles
    if 'puro_supplier_profiles' not in existing_tables:
        op.create_table(
            'puro_supplier_profiles',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('supplier_legal_name', sa.String(length=255), nullable=False),
            sa.Column('registration_number', sa.String(length=100), nullable=True),
            sa.Column('jurisdiction_country', sa.String(length=100), nullable=False),
            sa.Column('supplier_role', sa.String(length=50), server_default='PRODUCER', nullable=False),
            sa.Column('claim_rights_status', sa.String(length=50), server_default='PENDING_AUTHORIZATION', nullable=False),
            sa.Column('authorization_agreement_ref', sa.String(length=255), nullable=True),
            sa.Column('rights_declaration_doc_hash', sa.String(length=64), nullable=True),
            sa.Column('contract_effective_date', sa.Date(), nullable=True),
            sa.Column('contract_expiry_date', sa.Date(), nullable=True),
            sa.Column('validation_state', sa.String(length=50), server_default='PENDING_AUDIT', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE')
        )

    # 5. puro_facility_profiles
    if 'puro_facility_profiles' not in existing_tables:
        op.create_table(
            'puro_facility_profiles',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('facility_classification', sa.String(length=50), server_default='STATIONARY', nullable=False),
            sa.Column('host_country', sa.String(length=100), nullable=False),
            sa.Column('reference_coordinates', sa.String(length=100), nullable=True),
            sa.Column('spatial_extent_geojson', sa.JSON(), nullable=True),
            sa.Column('receiving_location', sa.String(length=255), nullable=True),
            sa.Column('pretreatment_location', sa.String(length=255), nullable=True),
            sa.Column('conversion_location', sa.String(length=255), nullable=True),
            sa.Column('packaging_location', sa.String(length=255), nullable=True),
            sa.Column('technology_similarity_verified', sa.Boolean(), server_default='true', nullable=True),
            sa.Column('commissioned_status', sa.String(length=50), server_default='COMMISSIONED', nullable=False),
            sa.Column('operating_status', sa.String(length=50), server_default='ACTIVE', nullable=False),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('facility_id', name='uq_puro_fac_profile_fac_id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE')
        )

    # 6. puro_mobile_production_sites
    if 'puro_mobile_production_sites' not in existing_tables:
        op.create_table(
            'puro_mobile_production_sites',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('facility_profile_id', sa.UUID(), nullable=False),
            sa.Column('site_code', sa.String(length=50), nullable=False),
            sa.Column('site_name', sa.String(length=255), nullable=False),
            sa.Column('coordinates', sa.String(length=100), nullable=False),
            sa.Column('owner_operator', sa.String(length=255), nullable=True),
            sa.Column('date_range_start', sa.Date(), nullable=False),
            sa.Column('date_range_end', sa.Date(), nullable=True),
            sa.Column('regulatory_permit_ref', sa.String(length=255), nullable=True),
            sa.Column('stakeholder_evidence_ref', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['facility_profile_id'], ['puro_facility_profiles.id'], ondelete='CASCADE')
        )

    # 7. puro_crediting_periods
    if 'puro_crediting_periods' not in existing_tables:
        op.create_table(
            'puro_crediting_periods',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('sequence_number', sa.Integer(), server_default='1', nullable=False),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('crediting_duration_years', sa.Integer(), server_default='10', nullable=False),
            sa.Column('methodology_version_id', sa.UUID(), nullable=True),
            sa.Column('facility_audit_id', sa.UUID(), nullable=True),
            sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
            sa.Column('renewal_type', sa.String(length=50), nullable=True),
            sa.Column('renewal_eligibility', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('previous_period_id', sa.UUID(), nullable=True),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE')
        )

    # 8. puro_baseline_assessments
    if 'puro_baseline_assessments' not in existing_tables:
        op.create_table(
            'puro_baseline_assessments',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('scenario', sa.String(length=50), nullable=False),
            sa.Column('is_locked', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('historical_char_production_tpy', sa.Numeric(18, 6), server_default='0.0', nullable=False),
            sa.Column('baseline_removal_tco2e_per_year', sa.Numeric(18, 6), server_default='0.0', nullable=False),
            sa.Column('historical_products_description', sa.Text(), nullable=True),
            sa.Column('prior_use_fate', sa.String(length=255), nullable=True),
            sa.Column('baseline_land_use_evidence_type', sa.String(length=100), nullable=True),
            sa.Column('land_use_evidence_ref', sa.String(length=255), nullable=True),
            sa.Column('assessment_status', sa.String(length=50), server_default='LOCKED_VALIDATED', nullable=False),
            sa.Column('reviewed_by', sa.String(length=255), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE')
        )

    # 9. puro_additionality_assessments
    if 'puro_additionality_assessments' not in existing_tables:
        op.create_table(
            'puro_additionality_assessments',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('carbon_additionality_status', sa.String(length=50), server_default='PASS', nullable=False),
            sa.Column('regulatory_additionality_status', sa.String(length=50), server_default='PASS', nullable=False),
            sa.Column('financial_additionality_status', sa.String(length=50), server_default='PASS', nullable=False),
            sa.Column('overall_status', sa.String(length=50), server_default='PASS', nullable=False),
            sa.Column('opex_per_tonne', sa.Numeric(14, 2), nullable=True),
            sa.Column('capex_investment', sa.Numeric(14, 2), nullable=True),
            sa.Column('biomass_cost_per_tonne', sa.Numeric(14, 2), nullable=True),
            sa.Column('biochar_market_price_per_tonne', sa.Numeric(14, 2), nullable=True),
            sa.Column('carbon_finance_dependency_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('legal_mandate_evidence_ref', sa.String(length=255), nullable=True),
            sa.Column('financial_model_evidence_hash', sa.String(length=64), nullable=True),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE')
        )

    # 10. puro_end_use_categories
    if 'puro_end_use_categories' not in existing_tables:
        op.create_table(
            'puro_end_use_categories',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('category_code', sa.String(length=20), nullable=False),
            sa.Column('category_name', sa.String(length=255), nullable=False),
            sa.Column('sector', sa.String(length=100), nullable=False),
            sa.Column('product_type', sa.String(length=100), nullable=False),
            sa.Column('pure_or_mixed', sa.String(length=20), server_default='PURE', nullable=False),
            sa.Column('is_corc_eligible', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('default_durability_years', sa.Integer(), server_default='100', nullable=False),
            sa.Column('persistence_factor_non_soil', sa.Float(), nullable=True),
            sa.Column('required_evidence_types', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('rule_references', sa.JSON(), server_default='[]', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('category_code', name='uq_puro_end_use_cat_code')
        )

    # 11. puro_end_use_record_links
    if 'puro_end_use_record_links' not in existing_tables:
        op.create_table(
            'puro_end_use_record_links',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('batch_id', sa.UUID(), nullable=False),
            sa.Column('end_use_record_id', sa.UUID(), nullable=False),
            sa.Column('category_id', sa.UUID(), nullable=False),
            sa.Column('is_pure_biochar', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('formulation_biochar_pct', sa.Float(), server_default='100.0', nullable=False),
            sa.Column('manufacturer_name', sa.String(length=255), nullable=True),
            sa.Column('intermediary_entity_name', sa.String(length=255), nullable=True),
            sa.Column('intermediary_agreement_ref', sa.String(length=255), nullable=True),
            sa.Column('cascade_stage', sa.String(length=50), server_default='SINGLE_USE', nullable=False),
            sa.Column('final_durable_fate_verified', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('proof_of_delivery_ref', sa.String(length=255), nullable=True),
            sa.Column('application_attestation_ref', sa.String(length=255), nullable=True),
            sa.Column('gps_verified', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('geotagged_photos_verified', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('corc_point_reached', sa.String(length=50), server_default='CORC_POINT_ELIGIBLE', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['batch_id'], ['biochar_batches.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['end_use_record_id'], ['biochar_end_use_records.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['category_id'], ['puro_end_use_categories.id'], ondelete='CASCADE')
        )

    # 12. puro_calculation_executions
    if 'puro_calculation_executions' not in existing_tables:
        op.create_table(
            'puro_calculation_executions',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('project_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('batch_id', sa.UUID(), nullable=False),
            sa.Column('monitoring_period_id', sa.String(length=100), nullable=True),
            sa.Column('calculation_timestamp', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.Column('methodology_version', sa.String(length=50), server_default='PURO_BIOCHAR_2025_V2', nullable=False),
            sa.Column('coefficient_version', sa.String(length=50), server_default='PURO_2025_V2_PERSISTENCE_MATRIX', nullable=False),
            sa.Column('calculation_status', sa.String(length=50), server_default='SUCCESS', nullable=False),
            sa.Column('eligible_dry_biochar_mass_tonnes', sa.Numeric(18, 6), nullable=False),
            sa.Column('c_org_pct', sa.Float(), nullable=False),
            sa.Column('molar_h_c', sa.Float(), nullable=False),
            sa.Column('soil_temperature_celsius', sa.Float(), server_default='15.0', nullable=False),
            sa.Column('c_stored_tco2e', sa.Numeric(18, 6), nullable=False),
            sa.Column('c_baseline_tco2e', sa.Numeric(18, 6), server_default='0.0', nullable=False),
            sa.Column('c_loss_tco2e', sa.Numeric(18, 6), nullable=False),
            sa.Column('e_project_tco2e', sa.Numeric(18, 6), nullable=False),
            sa.Column('e_leakage_tco2e', sa.Numeric(18, 6), server_default='0.0', nullable=False),
            sa.Column('net_corcs_calculated', sa.Numeric(18, 6), nullable=False),
            sa.Column('combined_uncertainty_pct', sa.Float(), server_default='5.0', nullable=False),
            sa.Column('deductible_uncertainty_pct', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('final_corcs_issuable', sa.Numeric(18, 6), nullable=False),
            sa.Column('input_manifest_json', sa.JSON(), nullable=False),
            sa.Column('calculation_hash', sa.String(length=64), nullable=False),
            sa.Column('engine_version', sa.String(length=50), server_default='1.0.0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['batch_id'], ['biochar_batches.id'], ondelete='CASCADE')
        )

    # 13. puro_audit_workflows
    if 'puro_audit_workflows' not in existing_tables:
        op.create_table(
            'puro_audit_workflows',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('monitoring_period_id', sa.String(length=100), nullable=True),
            sa.Column('audit_type', sa.String(length=50), nullable=False),
            sa.Column('auditor_organization', sa.String(length=255), nullable=False),
            sa.Column('lead_auditor_name', sa.String(length=255), nullable=True),
            sa.Column('audit_status', sa.String(length=50), server_default='READY_FOR_AUDIT', nullable=False),
            sa.Column('scheduled_date', sa.Date(), nullable=True),
            sa.Column('completion_date', sa.Date(), nullable=True),
            sa.Column('audit_dossier_hash', sa.String(length=64), nullable=True),
            sa.Column('certificate_number', sa.String(length=100), nullable=True),
            sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE')
        )

    # 14. puro_audit_findings
    if 'puro_audit_findings' not in existing_tables:
        op.create_table(
            'puro_audit_findings',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('audit_id', sa.UUID(), nullable=False),
            sa.Column('rule_ref', sa.String(length=50), nullable=False),
            sa.Column('finding_type', sa.String(length=50), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('evidence_ref', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=50), server_default='OPEN', nullable=False),
            sa.Column('detected_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.Column('response_due_date', sa.Date(), nullable=True),
            sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['audit_id'], ['puro_audit_workflows.id'], ondelete='CASCADE')
        )

    # 15. puro_output_reports
    if 'puro_output_reports' not in existing_tables:
        op.create_table(
            'puro_output_reports',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('crediting_period_id', sa.UUID(), nullable=True),
            sa.Column('monitoring_period_id', sa.String(length=100), nullable=False),
            sa.Column('report_number', sa.String(length=50), nullable=False),
            sa.Column('report_version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('report_status', sa.String(length=50), server_default='DRAFT', nullable=False),
            sa.Column('total_eligible_biochar_mass_tonnes', sa.Numeric(18, 6), server_default='0.0', nullable=False),
            sa.Column('total_net_corcs', sa.Numeric(18, 6), server_default='0.0', nullable=False),
            sa.Column('manifest_json', sa.JSON(), nullable=False),
            sa.Column('manifest_hash', sa.String(length=64), nullable=False),
            sa.Column('ledger_signature_id', sa.UUID(), nullable=True),
            sa.Column('generated_at', sa.DateTime(timezone=True), server_default=now_default, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('report_number', name='uq_puro_output_report_number'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE')
        )

    # 16. puro_monitoring_plans
    if 'puro_monitoring_plans' not in existing_tables:
        op.create_table(
            'puro_monitoring_plans',
            sa.Column('id', sa.UUID(), server_default=uuid_default, nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('facility_id', sa.UUID(), nullable=False),
            sa.Column('plan_version', sa.String(length=20), server_default='1.0', nullable=False),
            sa.Column('monitoring_parameters_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('responsible_roles_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('monitoring_frequencies_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('calibration_schedule_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('status', sa.String(length=50), server_default='VALIDATED', nullable=False),
            sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('auditor_id', sa.UUID(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=now_default, nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['facility_id'], ['biochar_production_facilities.id'], ondelete='CASCADE')
        )


def downgrade() -> None:
    pass
