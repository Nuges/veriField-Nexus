"""reconcile missing agriculture schema without replaying history

Revision ID: 615d2865c464
Revises: c7d8e9f0a1b2
Create Date: 2026-10-23 15:09:13.761242

"""
from alembic import op
import sqlalchemy as sa

revision = "615d2865c464"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None

REPAIR_TABLES = ('agriculture_management_records', 'agriculture_model_runs', 'agriculture_net_ghg_results', 'agriculture_prerequisite_assessments', 'agriculture_soc_change_results', 'agriculture_soc_layer_results', 'agriculture_soc_stock_results', 'agriculture_soc_stock_snapshots', 'agriculture_strata', 'agriculture_stratum_memberships', 'agriculture_vintage_ghg_results', 'chain_of_custody_events', 'laboratory_analyses', 'laboratory_import_batches', 'laboratory_import_rows', 'laboratory_receipts', 'laboratory_results', 'land_units', 'physical_samples', 'project_boundary_versions', 'quantification_input_snapshots', 'sample_collection_events', 'sample_qa_reviews', 'sampling_campaigns', 'sampling_plan_versions', 'sampling_points', 'satellite_observations', 'soil_samples', 'tree_observations')

# This literal is independently reviewed/tested before controlled production use.
REPAIR_SQL = r"""
-- Frozen from application source 1f606c7; no existing data or assignments are rewritten.
-- Execute this one DO statement transactionally; do not replay the historical migration chain.
DO $agriculture_repair$
DECLARE
    target_tables text[] := ARRAY['agriculture_management_records', 'agriculture_model_runs', 'agriculture_net_ghg_results', 'agriculture_prerequisite_assessments', 'agriculture_soc_change_results', 'agriculture_soc_layer_results', 'agriculture_soc_stock_results', 'agriculture_soc_stock_snapshots', 'agriculture_strata', 'agriculture_stratum_memberships', 'agriculture_vintage_ghg_results', 'chain_of_custody_events', 'laboratory_analyses', 'laboratory_import_batches', 'laboratory_import_rows', 'laboratory_receipts', 'laboratory_results', 'land_units', 'physical_samples', 'project_boundary_versions', 'quantification_input_snapshots', 'sample_collection_events', 'sample_qa_reviews', 'sampling_campaigns', 'sampling_plan_versions', 'sampling_points', 'satellite_observations', 'soil_samples', 'tree_observations'];
    table_name text;
    role_name text;
BEGIN
    PERFORM pg_catalog.set_config('lock_timeout', '3s', true);
    PERFORM pg_catalog.set_config('statement_timeout', '60s', true);
    PERFORM pg_catalog.set_config('search_path', 'pg_catalog, public, extensions', true);
    PERFORM pg_catalog.pg_advisory_xact_lock(6152865464);
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_extension WHERE extname = 'postgis')
       OR pg_catalog.to_regtype('geometry') IS NULL THEN
        RAISE EXCEPTION 'Existing PostGIS geometry type is required; no extension will be installed';
    END IF;
    FOREACH table_name IN ARRAY target_tables LOOP
        IF pg_catalog.to_regclass('public.' || table_name) IS NOT NULL THEN
            RAISE EXCEPTION 'Repair preflight: target table % already exists; inspect drift before proceeding', table_name;
        END IF;
    END LOOP;
    FOREACH table_name IN ARRAY ARRAY['organizations', 'projects', 'users', 'evidence_records', 'methodology_versions'] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = pg_catalog.to_regclass('public.' || table_name)
              AND a.attname = 'id' AND a.atttypid = 'uuid'::regtype AND NOT a.attisdropped
        ) THEN
            RAISE EXCEPTION 'Repair preflight: required UUID key missing on %', table_name;
        END IF;
    END LOOP;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_attribute
        WHERE attrelid = 'public.projects'::regclass
          AND attname = 'methodology_id' AND atttypid = 'uuid'::regtype AND NOT attisdropped
    ) THEN
        RAISE EXCEPTION 'Repair preflight: expected projects.methodology_id UUID missing';
    END IF;

    -- Widen the constraint only; preserve existing methodology values and foreign key.
    ALTER TABLE public.projects ALTER COLUMN methodology_id DROP NOT NULL;
    CREATE TABLE public.agriculture_model_runs (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        model_name VARCHAR(100) NOT NULL,
        model_type VARCHAR(50) NOT NULL,
        version VARCHAR(30) NOT NULL,
        run_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        status VARCHAR(30) NOT NULL,
        input_parameters JSONB NOT NULL,
        input_dataset_hashes JSONB NOT NULL,
        performance_metrics JSONB NOT NULL,
        uncertainty_metrics JSONB NOT NULL,
        output_manifest JSONB NOT NULL,
        provenance_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_model_runs PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_model_runs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_model_runs_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_agriculture_model_runs_organization_id ON public.agriculture_model_runs (organization_id);

    CREATE INDEX ix_public_agriculture_model_runs_project_id ON public.agriculture_model_runs (project_id);

    CREATE TABLE public.agriculture_strata (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        code VARCHAR(50) NOT NULL,
        name VARCHAR(150) NOT NULL,
        description TEXT,
        stratum_type VARCHAR(50) NOT NULL,
        area_ha FLOAT NOT NULL,
        is_active BOOLEAN NOT NULL,
        properties JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_strata PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_strata_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_strata_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_agriculture_strata_code ON public.agriculture_strata (code);

    CREATE INDEX ix_public_agriculture_strata_organization_id ON public.agriculture_strata (organization_id);

    CREATE INDEX ix_public_agriculture_strata_project_id ON public.agriculture_strata (project_id);

    CREATE TABLE public.land_units (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        parent_id UUID,
        unit_type VARCHAR(30) NOT NULL,
        name VARCHAR(150) NOT NULL,
        code VARCHAR(50),
        boundary_geojson JSONB NOT NULL,
        geom geometry(GEOMETRY,4326),
        boundary_source VARCHAR(30) NOT NULL,
        boundary_crs VARCHAR(20) NOT NULL,
        area_ha FLOAT NOT NULL,
        perimeter_m FLOAT,
        centroid_lat FLOAT,
        centroid_lon FLOAT,
        land_use_category VARCHAR(50),
        soil_type VARCHAR(50),
        slope_pct FLOAT,
        is_active BOOLEAN NOT NULL,
        properties JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_land_units PRIMARY KEY (id),
        CONSTRAINT fk_land_units_parent_id_land_units FOREIGN KEY(parent_id) REFERENCES public.land_units (id) ON DELETE CASCADE,
        CONSTRAINT fk_land_units_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_land_units_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE
    );

    CREATE INDEX idx_land_units_geom ON public.land_units USING gist (geom);

    CREATE INDEX ix_public_land_units_code ON public.land_units (code);

    CREATE INDEX ix_public_land_units_organization_id ON public.land_units (organization_id);

    CREATE INDEX ix_public_land_units_parent_id ON public.land_units (parent_id);

    CREATE INDEX ix_public_land_units_project_id ON public.land_units (project_id);

    CREATE INDEX ix_public_land_units_unit_type ON public.land_units (unit_type);

    CREATE TABLE public.project_boundary_versions (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        version_number INTEGER NOT NULL,
        effective_date DATE NOT NULL,
        boundary_geojson JSONB NOT NULL,
        geom geometry(GEOMETRY,4326),
        source VARCHAR(50) NOT NULL,
        reason TEXT,
        area_ha FLOAT NOT NULL,
        perimeter_m FLOAT,
        centroid_lat FLOAT,
        centroid_lon FLOAT,
        crs VARCHAR(20) NOT NULL,
        created_by_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_project_boundary_versions PRIMARY KEY (id),
        CONSTRAINT fk_project_boundary_versions_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_project_boundary_versions_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_project_boundary_versions_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES public.users (id) ON DELETE SET NULL
    );

    CREATE INDEX idx_project_boundary_versions_geom ON public.project_boundary_versions USING gist (geom);

    CREATE UNIQUE INDEX ix_project_boundary_ver_unique ON public.project_boundary_versions (project_id, version_number);

    CREATE INDEX ix_public_project_boundary_versions_organization_id ON public.project_boundary_versions (organization_id);

    CREATE INDEX ix_public_project_boundary_versions_project_id ON public.project_boundary_versions (project_id);

    CREATE INDEX ix_repair_project_boundary_versions_created_by_id ON public.project_boundary_versions (created_by_id);

    CREATE TABLE public.agriculture_management_records (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        land_unit_id UUID,
        record_type VARCHAR(50) NOT NULL,
        practice_category VARCHAR(50) NOT NULL,
        event_date DATE NOT NULL,
        end_date DATE,
        data_source VARCHAR(50) NOT NULL,
        corroboration VARCHAR(50) DEFAULT 'NONE' NOT NULL,
        details JSONB NOT NULL,
        evidence_id UUID,
        entered_by_id UUID,
        qa_status VARCHAR(30) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_management_records PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_management_records_entered_by_id_users FOREIGN KEY(entered_by_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_management_records_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_management_records_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_management_records_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_management_records_evidence_id_evidence_records FOREIGN KEY(evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_agriculture_management_records_land_unit_id ON public.agriculture_management_records (land_unit_id);

    CREATE INDEX ix_public_agriculture_management_records_organization_id ON public.agriculture_management_records (organization_id);

    CREATE INDEX ix_public_agriculture_management_records_project_id ON public.agriculture_management_records (project_id);

    CREATE INDEX ix_public_agriculture_management_records_record_type ON public.agriculture_management_records (record_type);

    CREATE INDEX ix_repair_agriculture_management_records_entered_by_id ON public.agriculture_management_records (entered_by_id);

    CREATE INDEX ix_repair_agriculture_management_records_evidence_id ON public.agriculture_management_records (evidence_id);

    CREATE TABLE public.agriculture_stratum_memberships (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        stratum_id UUID NOT NULL,
        land_unit_id UUID NOT NULL,
        valid_from DATE NOT NULL,
        valid_to DATE,
        status VARCHAR(30) NOT NULL,
        properties JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_stratum_memberships PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_stratum_memberships_organization_id_orga_dc39 FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_stratum_memberships_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_stratum_memberships_stratum_id_agricultu_1ffe FOREIGN KEY(stratum_id) REFERENCES public.agriculture_strata (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_agriculture_stratum_memberships_land_unit_id ON public.agriculture_stratum_memberships (land_unit_id);

    CREATE INDEX ix_public_agriculture_stratum_memberships_organization_id ON public.agriculture_stratum_memberships (organization_id);

    CREATE INDEX ix_public_agriculture_stratum_memberships_stratum_id ON public.agriculture_stratum_memberships (stratum_id);

    CREATE TABLE public.sampling_campaigns (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        campaign_code VARCHAR(50) NOT NULL,
        name VARCHAR(150) NOT NULL,
        purpose VARCHAR(50) NOT NULL,
        baseline_or_monitoring_context VARCHAR(30) NOT NULL,
        planned_start_date DATE NOT NULL,
        planned_end_date DATE,
        status VARCHAR(30) NOT NULL,
        methodology_lock_snapshot JSONB NOT NULL,
        project_boundary_version_id UUID,
        created_by_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_sampling_campaigns PRIMARY KEY (id),
        CONSTRAINT fk_sampling_campaigns_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_sampling_campaigns_project_boundary_version_id_proje_cd8a FOREIGN KEY(project_boundary_version_id) REFERENCES public.project_boundary_versions (id) ON DELETE SET NULL,
        CONSTRAINT fk_sampling_campaigns_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_sampling_campaigns_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_sampling_campaigns_campaign_code ON public.sampling_campaigns (campaign_code);

    CREATE INDEX ix_public_sampling_campaigns_organization_id ON public.sampling_campaigns (organization_id);

    CREATE INDEX ix_public_sampling_campaigns_project_id ON public.sampling_campaigns (project_id);

    CREATE INDEX ix_repair_sampling_campaigns_created_by_id ON public.sampling_campaigns (created_by_id);

    CREATE INDEX ix_repair_sampling_campaigns_project_boundary_version_id ON public.sampling_campaigns (project_boundary_version_id);

    CREATE TABLE public.satellite_observations (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        land_unit_id UUID,
        provider VARCHAR(50) NOT NULL,
        scene_id VARCHAR(100) NOT NULL,
        acquisition_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        cloud_coverage_pct FLOAT,
        spatial_resolution_m FLOAT NOT NULL,
        observation_type VARCHAR(50) NOT NULL,
        raw_band_uris JSONB NOT NULL,
        derived_indices JSONB NOT NULL,
        provenance_hash VARCHAR(64) NOT NULL,
        processing_level VARCHAR(20) NOT NULL,
        lineage_manifest JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_satellite_observations PRIMARY KEY (id),
        CONSTRAINT fk_satellite_observations_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_satellite_observations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_satellite_observations_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_satellite_observations_land_unit_id ON public.satellite_observations (land_unit_id);

    CREATE INDEX ix_public_satellite_observations_organization_id ON public.satellite_observations (organization_id);

    CREATE INDEX ix_public_satellite_observations_project_id ON public.satellite_observations (project_id);

    CREATE INDEX ix_public_satellite_observations_scene_id ON public.satellite_observations (scene_id);

    CREATE TABLE public.tree_observations (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        land_unit_id UUID NOT NULL,
        sampling_approach VARCHAR(30) NOT NULL,
        tag_number VARCHAR(50),
        species_scientific VARCHAR(100) NOT NULL,
        species_common VARCHAR(100),
        dbh_cm FLOAT NOT NULL,
        height_m FLOAT,
        crown_diameter_m FLOAT,
        health_status VARCHAR(30) NOT NULL,
        latitude FLOAT,
        longitude FLOAT,
        measurement_date DATE NOT NULL,
        allometric_equation_id VARCHAR(100),
        belowground_model_id VARCHAR(100),
        derived_aboveground_biomass_kg FLOAT,
        derived_belowground_biomass_kg FLOAT,
        derived_carbon_stock_t_co2e FLOAT,
        calculation_run_id UUID,
        evidence_photo_hash VARCHAR(64),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_tree_observations PRIMARY KEY (id),
        CONSTRAINT fk_tree_observations_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_tree_observations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_tree_observations_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_tree_observations_land_unit_id ON public.tree_observations (land_unit_id);

    CREATE INDEX ix_public_tree_observations_organization_id ON public.tree_observations (organization_id);

    CREATE INDEX ix_public_tree_observations_project_id ON public.tree_observations (project_id);

    CREATE INDEX ix_public_tree_observations_tag_number ON public.tree_observations (tag_number);

    CREATE TABLE public.laboratory_import_batches (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        sampling_campaign_id UUID,
        laboratory_name VARCHAR(150),
        original_filename VARCHAR(255) NOT NULL,
        file_type VARCHAR(10) NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        file_sha256 VARCHAR(64) NOT NULL,
        evidence_id UUID,
        status VARCHAR(30) NOT NULL,
        source_type VARCHAR(30) NOT NULL,
        uploaded_by UUID,
        uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        mapping_version VARCHAR(30) NOT NULL,
        mapping_config JSONB NOT NULL,
        total_rows INTEGER NOT NULL,
        valid_rows INTEGER NOT NULL,
        warning_rows INTEGER NOT NULL,
        error_rows INTEGER NOT NULL,
        imported_rows INTEGER NOT NULL,
        skipped_rows INTEGER NOT NULL,
        error_summary JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_laboratory_import_batches PRIMARY KEY (id),
        CONSTRAINT fk_laboratory_import_batches_uploaded_by_users FOREIGN KEY(uploaded_by) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_laboratory_import_batches_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_laboratory_import_batches_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_laboratory_import_batches_evidence_id_evidence_records FOREIGN KEY(evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL,
        CONSTRAINT fk_laboratory_import_batches_sampling_campaign_id_sampl_883b FOREIGN KEY(sampling_campaign_id) REFERENCES public.sampling_campaigns (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_laboratory_import_batches_evidence_id ON public.laboratory_import_batches (evidence_id);

    CREATE INDEX ix_public_laboratory_import_batches_file_sha256 ON public.laboratory_import_batches (file_sha256);

    CREATE INDEX ix_public_laboratory_import_batches_organization_id ON public.laboratory_import_batches (organization_id);

    CREATE INDEX ix_public_laboratory_import_batches_project_id ON public.laboratory_import_batches (project_id);

    CREATE INDEX ix_public_laboratory_import_batches_sampling_campaign_id ON public.laboratory_import_batches (sampling_campaign_id);

    CREATE INDEX ix_public_laboratory_import_batches_status ON public.laboratory_import_batches (status);

    CREATE INDEX ix_repair_laboratory_import_batches_uploaded_by ON public.laboratory_import_batches (uploaded_by);

    CREATE TABLE public.quantification_input_snapshots (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        snapshot_code VARCHAR(50) NOT NULL,
        status VARCHAR(30) NOT NULL,
        context VARCHAR(30) NOT NULL,
        period_start DATE,
        period_end DATE,
        methodology_version_id UUID,
        methodology_code VARCHAR(50) NOT NULL,
        methodology_version VARCHAR(30) NOT NULL,
        rule_set_version VARCHAR(50) NOT NULL,
        project_boundary_version_id UUID,
        sampling_campaign_id UUID,
        snapshot_hash VARCHAR(64) NOT NULL,
        is_locked BOOLEAN NOT NULL,
        locked_at TIMESTAMP WITH TIME ZONE,
        locked_by_id UUID,
        created_by_id UUID,
        total_eligible_measurements INTEGER NOT NULL,
        total_excluded_measurements INTEGER NOT NULL,
        readiness_summary JSONB NOT NULL,
        input_package JSONB NOT NULL,
        source_evidence_ids JSONB NOT NULL,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_quantification_input_snapshots PRIMARY KEY (id),
        CONSTRAINT fk_quantification_input_snapshots_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_quantification_input_snapshots_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_quantification_input_snapshots_project_boundary_vers_297d FOREIGN KEY(project_boundary_version_id) REFERENCES public.project_boundary_versions (id) ON DELETE SET NULL,
        CONSTRAINT fk_quantification_input_snapshots_locked_by_id_users FOREIGN KEY(locked_by_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_quantification_input_snapshots_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_quantification_input_snapshots_sampling_campaign_id__7a19 FOREIGN KEY(sampling_campaign_id) REFERENCES public.sampling_campaigns (id) ON DELETE SET NULL,
        CONSTRAINT fk_quantification_input_snapshots_methodology_version_i_a48d FOREIGN KEY(methodology_version_id) REFERENCES public.methodology_versions (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_quantification_input_snapshots_organization_id ON public.quantification_input_snapshots (organization_id);

    CREATE INDEX ix_public_quantification_input_snapshots_project_id ON public.quantification_input_snapshots (project_id);

    CREATE UNIQUE INDEX ix_public_quantification_input_snapshots_snapshot_code ON public.quantification_input_snapshots (snapshot_code);

    CREATE INDEX ix_public_quantification_input_snapshots_snapshot_hash ON public.quantification_input_snapshots (snapshot_hash);

    CREATE INDEX ix_repair_quantification_input_snapshots_created_by_id ON public.quantification_input_snapshots (created_by_id);

    CREATE INDEX ix_repair_quantification_input_snapshots_locked_by_id ON public.quantification_input_snapshots (locked_by_id);

    CREATE INDEX ix_repair_quantification_input_snapshots_methodology_version_id ON public.quantification_input_snapshots (methodology_version_id);

    CREATE INDEX ix_repair_quantification_input_snapshots_project_bou_e2cd2fc01c ON public.quantification_input_snapshots (project_boundary_version_id);

    CREATE INDEX ix_repair_quantification_input_snapshots_sampling_campaign_id ON public.quantification_input_snapshots (sampling_campaign_id);

    CREATE TABLE public.sampling_plan_versions (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        campaign_id UUID NOT NULL,
        version_number INTEGER NOT NULL,
        status VARCHAR(30) NOT NULL,
        effective_as_of_date DATE NOT NULL,
        stratum_membership_snapshot JSONB NOT NULL,
        sampling_design_method VARCHAR(50) NOT NULL,
        design_provenance VARCHAR(50) NOT NULL,
        is_locked BOOLEAN NOT NULL,
        locked_at TIMESTAMP WITH TIME ZONE,
        locked_by_id UUID,
        plan_lock_snapshot JSONB NOT NULL,
        notes TEXT,
        created_by_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_sampling_plan_versions PRIMARY KEY (id),
        CONSTRAINT fk_sampling_plan_versions_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_sampling_plan_versions_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_sampling_plan_versions_campaign_id_sampling_campaigns FOREIGN KEY(campaign_id) REFERENCES public.sampling_campaigns (id) ON DELETE CASCADE,
        CONSTRAINT fk_sampling_plan_versions_locked_by_id_users FOREIGN KEY(locked_by_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_sampling_plan_versions_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_sampling_plan_versions_campaign_id ON public.sampling_plan_versions (campaign_id);

    CREATE INDEX ix_public_sampling_plan_versions_organization_id ON public.sampling_plan_versions (organization_id);

    CREATE INDEX ix_public_sampling_plan_versions_project_id ON public.sampling_plan_versions (project_id);

    CREATE INDEX ix_repair_sampling_plan_versions_created_by_id ON public.sampling_plan_versions (created_by_id);

    CREATE INDEX ix_repair_sampling_plan_versions_locked_by_id ON public.sampling_plan_versions (locked_by_id);

    CREATE TABLE public.agriculture_prerequisite_assessments (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        snapshot_id UUID,
        assessment_code VARCHAR(50) NOT NULL,
        version INTEGER NOT NULL,
        status VARCHAR(30) NOT NULL,
        overall_readiness VARCHAR(30) NOT NULL,
        methodology_code VARCHAR(50) NOT NULL,
        methodology_version VARCHAR(30) NOT NULL,
        corrections_clarifications_version VARCHAR(30) NOT NULL,
        rule_set_version VARCHAR(60) NOT NULL,
        vcs_standard_version VARCHAR(30) NOT NULL,
        vcs_resolution_metadata JSONB NOT NULL,
        quantification_route_map JSONB NOT NULL,
        esm_input_dossier JSONB NOT NULL,
        sampling_design_assessment JSONB NOT NULL,
        uncertainty_input_readiness JSONB NOT NULL,
        baseline_monitoring_pairing JSONB NOT NULL,
        dimensions JSONB NOT NULL,
        blocking_reasons JSONB NOT NULL,
        advisory_notes JSONB NOT NULL,
        assessment_hash VARCHAR(64) NOT NULL,
        is_locked BOOLEAN NOT NULL,
        locked_at TIMESTAMP WITH TIME ZONE,
        locked_by_id UUID,
        created_by_id UUID,
        superseded_by_id UUID,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_prerequisite_assessments PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_prerequisite_assessments_snapshot_id_qua_fde5 FOREIGN KEY(snapshot_id) REFERENCES public.quantification_input_snapshots (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_prerequisite_assessments_superseded_by_i_0c5a FOREIGN KEY(superseded_by_id) REFERENCES public.agriculture_prerequisite_assessments (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_prerequisite_assessments_organization_id_61f5 FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_prerequisite_assessments_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_prerequisite_assessments_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_prerequisite_assessments_locked_by_id_users FOREIGN KEY(locked_by_id) REFERENCES public.users (id) ON DELETE SET NULL
    );

    CREATE UNIQUE INDEX ix_public_agriculture_prerequisite_assessments_assessment_code ON public.agriculture_prerequisite_assessments (assessment_code);

    CREATE INDEX ix_public_agriculture_prerequisite_assessments_assessment_hash ON public.agriculture_prerequisite_assessments (assessment_hash);

    CREATE INDEX ix_public_agriculture_prerequisite_assessments_organization_id ON public.agriculture_prerequisite_assessments (organization_id);

    CREATE INDEX ix_public_agriculture_prerequisite_assessments_project_id ON public.agriculture_prerequisite_assessments (project_id);

    CREATE INDEX ix_public_agriculture_prerequisite_assessments_snapshot_id ON public.agriculture_prerequisite_assessments (snapshot_id);

    CREATE INDEX ix_repair_agriculture_prerequisite_assessments_created_by_id ON public.agriculture_prerequisite_assessments (created_by_id);

    CREATE INDEX ix_repair_agriculture_prerequisite_assessments_locked_by_id ON public.agriculture_prerequisite_assessments (locked_by_id);

    CREATE INDEX ix_repair_agriculture_prerequisite_assessments_superseded_by_id ON public.agriculture_prerequisite_assessments (superseded_by_id);

    CREATE TABLE public.sampling_points (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        campaign_id UUID NOT NULL,
        plan_version_id UUID NOT NULL,
        land_unit_id UUID NOT NULL,
        stratum_id UUID,
        point_code VARCHAR(50) NOT NULL,
        planned_lat FLOAT NOT NULL,
        planned_lon FLOAT NOT NULL,
        geom geometry(POINT,4326),
        depth_from_cm FLOAT NOT NULL,
        depth_to_cm FLOAT NOT NULL,
        depth_class_label VARCHAR(50),
        sampling_purpose VARCHAR(50) NOT NULL,
        replicate_group VARCHAR(50),
        soil_profile_id VARCHAR(100),
        status VARCHAR(30) NOT NULL,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_sampling_points PRIMARY KEY (id),
        CONSTRAINT fk_sampling_points_stratum_id_agriculture_strata FOREIGN KEY(stratum_id) REFERENCES public.agriculture_strata (id) ON DELETE SET NULL,
        CONSTRAINT fk_sampling_points_campaign_id_sampling_campaigns FOREIGN KEY(campaign_id) REFERENCES public.sampling_campaigns (id) ON DELETE CASCADE,
        CONSTRAINT fk_sampling_points_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_sampling_points_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_sampling_points_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE CASCADE,
        CONSTRAINT fk_sampling_points_plan_version_id_sampling_plan_versions FOREIGN KEY(plan_version_id) REFERENCES public.sampling_plan_versions (id) ON DELETE CASCADE
    );

    CREATE INDEX idx_sampling_points_geom ON public.sampling_points USING gist (geom);

    CREATE INDEX ix_public_sampling_points_campaign_id ON public.sampling_points (campaign_id);

    CREATE INDEX ix_public_sampling_points_land_unit_id ON public.sampling_points (land_unit_id);

    CREATE INDEX ix_public_sampling_points_organization_id ON public.sampling_points (organization_id);

    CREATE INDEX ix_public_sampling_points_plan_version_id ON public.sampling_points (plan_version_id);

    CREATE INDEX ix_public_sampling_points_point_code ON public.sampling_points (point_code);

    CREATE INDEX ix_public_sampling_points_project_id ON public.sampling_points (project_id);

    CREATE INDEX ix_public_sampling_points_soil_profile_id ON public.sampling_points (soil_profile_id);

    CREATE INDEX ix_public_sampling_points_stratum_id ON public.sampling_points (stratum_id);

    CREATE TABLE public.agriculture_soc_stock_snapshots (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        prerequisite_assessment_id UUID NOT NULL,
        snapshot_code VARCHAR(60) NOT NULL,
        measurement_period_type VARCHAR(30) NOT NULL,
        snapshot_payload JSONB NOT NULL,
        snapshot_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_soc_stock_snapshots PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_soc_stock_snapshots_organization_id_orga_765f FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_soc_stock_snapshots_prerequisite_assessm_81c2 FOREIGN KEY(prerequisite_assessment_id) REFERENCES public.agriculture_prerequisite_assessments (id) ON DELETE RESTRICT,
        CONSTRAINT fk_agriculture_soc_stock_snapshots_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_agriculture_soc_stock_snapshots_organization_id ON public.agriculture_soc_stock_snapshots (organization_id);

    CREATE INDEX ix_public_agriculture_soc_stock_snapshots_prerequisite__e041 ON public.agriculture_soc_stock_snapshots (prerequisite_assessment_id);

    CREATE INDEX ix_public_agriculture_soc_stock_snapshots_project_id ON public.agriculture_soc_stock_snapshots (project_id);

    CREATE UNIQUE INDEX ix_public_agriculture_soc_stock_snapshots_snapshot_code ON public.agriculture_soc_stock_snapshots (snapshot_code);

    CREATE UNIQUE INDEX ix_public_agriculture_soc_stock_snapshots_snapshot_hash ON public.agriculture_soc_stock_snapshots (snapshot_hash);

    CREATE TABLE public.physical_samples (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        campaign_id UUID NOT NULL,
        plan_version_id UUID,
        sampling_point_id UUID NOT NULL,
        land_unit_id UUID NOT NULL,
        stratum_id UUID,
        sample_code VARCHAR(100) NOT NULL,
        soil_profile_id VARCHAR(100),
        core_count INTEGER NOT NULL,
        sample_dry_mass_g NUMERIC(10, 2),
        core_diameter_mm NUMERIC(6, 2),
        status VARCHAR(30) NOT NULL,
        qr_barcode_code VARCHAR(150),
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_physical_samples PRIMARY KEY (id),
        CONSTRAINT uq_physical_samples_sampling_point_id UNIQUE (sampling_point_id),
        CONSTRAINT fk_physical_samples_stratum_id_agriculture_strata FOREIGN KEY(stratum_id) REFERENCES public.agriculture_strata (id) ON DELETE SET NULL,
        CONSTRAINT fk_physical_samples_plan_version_id_sampling_plan_versions FOREIGN KEY(plan_version_id) REFERENCES public.sampling_plan_versions (id) ON DELETE SET NULL,
        CONSTRAINT fk_physical_samples_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE CASCADE,
        CONSTRAINT fk_physical_samples_sampling_point_id_sampling_points FOREIGN KEY(sampling_point_id) REFERENCES public.sampling_points (id) ON DELETE CASCADE,
        CONSTRAINT fk_physical_samples_campaign_id_sampling_campaigns FOREIGN KEY(campaign_id) REFERENCES public.sampling_campaigns (id) ON DELETE CASCADE,
        CONSTRAINT fk_physical_samples_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_physical_samples_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_physical_samples_campaign_id ON public.physical_samples (campaign_id);

    CREATE INDEX ix_public_physical_samples_land_unit_id ON public.physical_samples (land_unit_id);

    CREATE INDEX ix_public_physical_samples_organization_id ON public.physical_samples (organization_id);

    CREATE INDEX ix_public_physical_samples_project_id ON public.physical_samples (project_id);

    CREATE UNIQUE INDEX ix_public_physical_samples_sample_code ON public.physical_samples (sample_code);

    CREATE INDEX ix_public_physical_samples_soil_profile_id ON public.physical_samples (soil_profile_id);

    CREATE INDEX ix_public_physical_samples_stratum_id ON public.physical_samples (stratum_id);

    CREATE INDEX ix_repair_physical_samples_plan_version_id ON public.physical_samples (plan_version_id);

    CREATE TABLE public.agriculture_soc_stock_results (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        quantification_unit_id UUID,
        stratum_id UUID,
        sampling_point_id UUID,
        soil_profile_id VARCHAR(100),
        campaign_id UUID,
        prerequisite_assessment_id UUID NOT NULL,
        input_snapshot_id UUID,
        stock_snapshot_id UUID,
        result_code VARCHAR(60) NOT NULL,
        measurement_period_type VARCHAR(30) NOT NULL,
        aggregation_level VARCHAR(30) NOT NULL,
        methodology_version VARCHAR(30) NOT NULL,
        corrections_clarifications_version VARCHAR(30) NOT NULL,
        calculation_engine_version VARCHAR(60) NOT NULL,
        esm_algorithm VARCHAR(50) NOT NULL,
        reference_soil_mass_t_ha NUMERIC(14, 4) NOT NULL,
        reference_depth_cm NUMERIC(6, 2) NOT NULL,
        equivalent_depth_cm NUMERIC(6, 2),
        total_sampled_soil_mass_t_ha NUMERIC(14, 4),
        max_sampled_depth_cm NUMERIC(6, 2),
        soc_stock_t_c_per_ha NUMERIC(12, 4) NOT NULL,
        unadjusted_stock_t_c_per_ha NUMERIC(12, 4),
        shallow_soil_exception_applied BOOLEAN NOT NULL,
        depth_sufficiency_status VARCHAR(50) NOT NULL,
        area_ha NUMERIC(14, 4),
        sample_count INTEGER NOT NULL,
        strata_weights JSONB NOT NULL,
        component_breakdown JSONB NOT NULL,
        result_status VARCHAR(30) NOT NULL,
        calculation_hash VARCHAR(64) NOT NULL,
        input_snapshot_hash VARCHAR(64) NOT NULL,
        created_by_id UUID,
        superseded_by_id UUID,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_soc_stock_results PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_soc_stock_results_stratum_id_agriculture_strata FOREIGN KEY(stratum_id) REFERENCES public.agriculture_strata (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_stock_results_prerequisite_assessmen_136a FOREIGN KEY(prerequisite_assessment_id) REFERENCES public.agriculture_prerequisite_assessments (id) ON DELETE RESTRICT,
        CONSTRAINT fk_agriculture_soc_stock_results_campaign_id_sampling_campaigns FOREIGN KEY(campaign_id) REFERENCES public.sampling_campaigns (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_stock_results_quantification_unit_id_efe2 FOREIGN KEY(quantification_unit_id) REFERENCES public.land_units (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_stock_results_stock_snapshot_id_agri_6bea FOREIGN KEY(stock_snapshot_id) REFERENCES public.agriculture_soc_stock_snapshots (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_stock_results_superseded_by_id_agric_e73c FOREIGN KEY(superseded_by_id) REFERENCES public.agriculture_soc_stock_results (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_stock_results_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_soc_stock_results_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_soc_stock_results_sampling_point_id_samp_a40a FOREIGN KEY(sampling_point_id) REFERENCES public.sampling_points (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_stock_results_input_snapshot_id_quan_c111 FOREIGN KEY(input_snapshot_id) REFERENCES public.quantification_input_snapshots (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_stock_results_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES public.users (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_agriculture_soc_stock_results_calculation_hash ON public.agriculture_soc_stock_results (calculation_hash);

    CREATE INDEX ix_public_agriculture_soc_stock_results_campaign_id ON public.agriculture_soc_stock_results (campaign_id);

    CREATE INDEX ix_public_agriculture_soc_stock_results_input_snapshot_hash ON public.agriculture_soc_stock_results (input_snapshot_hash);

    CREATE INDEX ix_public_agriculture_soc_stock_results_input_snapshot_id ON public.agriculture_soc_stock_results (input_snapshot_id);

    CREATE INDEX ix_public_agriculture_soc_stock_results_measurement_period_type ON public.agriculture_soc_stock_results (measurement_period_type);

    CREATE INDEX ix_public_agriculture_soc_stock_results_organization_id ON public.agriculture_soc_stock_results (organization_id);

    CREATE INDEX ix_public_agriculture_soc_stock_results_prerequisite_as_1a34 ON public.agriculture_soc_stock_results (prerequisite_assessment_id);

    CREATE INDEX ix_public_agriculture_soc_stock_results_project_id ON public.agriculture_soc_stock_results (project_id);

    CREATE INDEX ix_public_agriculture_soc_stock_results_quantification_unit_id ON public.agriculture_soc_stock_results (quantification_unit_id);

    CREATE UNIQUE INDEX ix_public_agriculture_soc_stock_results_result_code ON public.agriculture_soc_stock_results (result_code);

    CREATE INDEX ix_public_agriculture_soc_stock_results_sampling_point_id ON public.agriculture_soc_stock_results (sampling_point_id);

    CREATE INDEX ix_public_agriculture_soc_stock_results_soil_profile_id ON public.agriculture_soc_stock_results (soil_profile_id);

    CREATE INDEX ix_public_agriculture_soc_stock_results_stock_snapshot_id ON public.agriculture_soc_stock_results (stock_snapshot_id);

    CREATE INDEX ix_public_agriculture_soc_stock_results_stratum_id ON public.agriculture_soc_stock_results (stratum_id);

    CREATE INDEX ix_repair_agriculture_soc_stock_results_created_by_id ON public.agriculture_soc_stock_results (created_by_id);

    CREATE INDEX ix_repair_agriculture_soc_stock_results_superseded_by_id ON public.agriculture_soc_stock_results (superseded_by_id);

    CREATE TABLE public.chain_of_custody_events (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        physical_sample_id UUID NOT NULL,
        event_type VARCHAR(50) NOT NULL,
        event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        custodian_id UUID,
        custodian_name VARCHAR(100) NOT NULL,
        custodian_organization VARCHAR(150) NOT NULL,
        from_location VARCHAR(150),
        to_location VARCHAR(150),
        condition VARCHAR(50) NOT NULL,
        seal_intact BOOLEAN NOT NULL,
        seal_identifier VARCHAR(100),
        notes TEXT,
        evidence_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_chain_of_custody_events PRIMARY KEY (id),
        CONSTRAINT fk_chain_of_custody_events_evidence_id_evidence_records FOREIGN KEY(evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL,
        CONSTRAINT fk_chain_of_custody_events_physical_sample_id_physical_samples FOREIGN KEY(physical_sample_id) REFERENCES public.physical_samples (id) ON DELETE CASCADE,
        CONSTRAINT fk_chain_of_custody_events_custodian_id_users FOREIGN KEY(custodian_id) REFERENCES public.users (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_chain_of_custody_events_physical_sample_id ON public.chain_of_custody_events (physical_sample_id);

    CREATE INDEX ix_repair_chain_of_custody_events_custodian_id ON public.chain_of_custody_events (custodian_id);

    CREATE INDEX ix_repair_chain_of_custody_events_evidence_id ON public.chain_of_custody_events (evidence_id);

    CREATE TABLE public.laboratory_analyses (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        physical_sample_id UUID NOT NULL,
        laboratory_name VARCHAR(150) NOT NULL,
        laboratory_accreditation VARCHAR(100),
        accreditation_status VARCHAR(30) NOT NULL,
        accreditation_evidence_id UUID,
        analysis_batch_id VARCHAR(100),
        analytical_method VARCHAR(100) NOT NULL,
        method_standard_code VARCHAR(100),
        analysis_date DATE NOT NULL,
        report_reference_number VARCHAR(100),
        analyst_name VARCHAR(100),
        qa_status VARCHAR(30) NOT NULL,
        evidence_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_laboratory_analyses PRIMARY KEY (id),
        CONSTRAINT fk_laboratory_analyses_accreditation_evidence_id_eviden_c9c0 FOREIGN KEY(accreditation_evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL,
        CONSTRAINT fk_laboratory_analyses_physical_sample_id_physical_samples FOREIGN KEY(physical_sample_id) REFERENCES public.physical_samples (id) ON DELETE CASCADE,
        CONSTRAINT fk_laboratory_analyses_evidence_id_evidence_records FOREIGN KEY(evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_laboratory_analyses_physical_sample_id ON public.laboratory_analyses (physical_sample_id);

    CREATE INDEX ix_repair_laboratory_analyses_accreditation_evidence_id ON public.laboratory_analyses (accreditation_evidence_id);

    CREATE INDEX ix_repair_laboratory_analyses_evidence_id ON public.laboratory_analyses (evidence_id);

    CREATE TABLE public.laboratory_receipts (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        physical_sample_id UUID NOT NULL,
        laboratory_name VARCHAR(150) NOT NULL,
        laboratory_id_ref VARCHAR(100),
        received_at TIMESTAMP WITH TIME ZONE NOT NULL,
        received_by_name VARCHAR(100) NOT NULL,
        condition_on_receipt VARCHAR(50) NOT NULL,
        seal_status VARCHAR(50) NOT NULL,
        intake_status VARCHAR(30) NOT NULL,
        rejection_reason TEXT,
        receipt_evidence_id UUID,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_laboratory_receipts PRIMARY KEY (id),
        CONSTRAINT uq_laboratory_receipts_physical_sample_id UNIQUE (physical_sample_id),
        CONSTRAINT fk_laboratory_receipts_receipt_evidence_id_evidence_records FOREIGN KEY(receipt_evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL,
        CONSTRAINT fk_laboratory_receipts_physical_sample_id_physical_samples FOREIGN KEY(physical_sample_id) REFERENCES public.physical_samples (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_repair_laboratory_receipts_receipt_evidence_id ON public.laboratory_receipts (receipt_evidence_id);

    CREATE TABLE public.sample_collection_events (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        physical_sample_id UUID NOT NULL,
        sampling_point_id UUID NOT NULL,
        actual_lat FLOAT NOT NULL,
        actual_lon FLOAT NOT NULL,
        actual_geom geometry(POINT,4326),
        deviation_distance_m FLOAT NOT NULL,
        deviation_reason TEXT,
        collection_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        collector_id UUID,
        collector_name VARCHAR(100) NOT NULL,
        actual_depth_from_cm FLOAT NOT NULL,
        actual_depth_to_cm FLOAT NOT NULL,
        sample_condition VARCHAR(50) NOT NULL,
        notes TEXT,
        photo_evidence_id UUID,
        photo_hash VARCHAR(64),
        device_metadata JSONB NOT NULL,
        idempotency_key VARCHAR(100),
        sync_timestamp TIMESTAMP WITH TIME ZONE,
        server_received_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_sample_collection_events PRIMARY KEY (id),
        CONSTRAINT uq_sample_collection_events_physical_sample_id UNIQUE (physical_sample_id),
        CONSTRAINT uq_sample_collection_events_idempotency_key UNIQUE (idempotency_key),
        CONSTRAINT fk_sample_collection_events_physical_sample_id_physical_samples FOREIGN KEY(physical_sample_id) REFERENCES public.physical_samples (id) ON DELETE CASCADE,
        CONSTRAINT fk_sample_collection_events_collector_id_users FOREIGN KEY(collector_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_sample_collection_events_photo_evidence_id_evidence_records FOREIGN KEY(photo_evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL,
        CONSTRAINT fk_sample_collection_events_sampling_point_id_sampling_points FOREIGN KEY(sampling_point_id) REFERENCES public.sampling_points (id) ON DELETE CASCADE
    );

    CREATE INDEX idx_sample_collection_events_actual_geom ON public.sample_collection_events USING gist (actual_geom);

    CREATE INDEX ix_repair_sample_collection_events_collector_id ON public.sample_collection_events (collector_id);

    CREATE INDEX ix_repair_sample_collection_events_photo_evidence_id ON public.sample_collection_events (photo_evidence_id);

    CREATE INDEX ix_repair_sample_collection_events_sampling_point_id ON public.sample_collection_events (sampling_point_id);

    CREATE TABLE public.sample_qa_reviews (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        physical_sample_id UUID NOT NULL,
        reviewer_id UUID,
        reviewer_name VARCHAR(100) NOT NULL,
        review_date TIMESTAMP WITH TIME ZONE NOT NULL,
        overall_qa_status VARCHAR(30) NOT NULL,
        location_verified BOOLEAN NOT NULL,
        deviation_acceptable BOOLEAN NOT NULL,
        depth_valid BOOLEAN NOT NULL,
        custody_complete BOOLEAN NOT NULL,
        lab_receipt_verified BOOLEAN NOT NULL,
        required_assays_present BOOLEAN NOT NULL,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_sample_qa_reviews PRIMARY KEY (id),
        CONSTRAINT uq_sample_qa_reviews_physical_sample_id UNIQUE (physical_sample_id),
        CONSTRAINT fk_sample_qa_reviews_physical_sample_id_physical_samples FOREIGN KEY(physical_sample_id) REFERENCES public.physical_samples (id) ON DELETE CASCADE,
        CONSTRAINT fk_sample_qa_reviews_reviewer_id_users FOREIGN KEY(reviewer_id) REFERENCES public.users (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_repair_sample_qa_reviews_reviewer_id ON public.sample_qa_reviews (reviewer_id);

    CREATE TABLE public.soil_samples (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        land_unit_id UUID,
        sample_code VARCHAR(50) NOT NULL,
        sampling_date DATE NOT NULL,
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        depth_upper_cm FLOAT NOT NULL,
        depth_lower_cm FLOAT NOT NULL,
        bulk_density_g_cm3 FLOAT,
        soc_stock_pct FLOAT NOT NULL,
        total_organic_carbon_g_kg FLOAT,
        computed_soc_stock_t_c_ha FLOAT,
        coarse_fragments_pct FLOAT NOT NULL,
        ph FLOAT,
        electrical_conductivity_ds_m FLOAT,
        texture_class VARCHAR(30),
        lab_method VARCHAR(50) NOT NULL,
        lab_name VARCHAR(100),
        lab_accreditation VARCHAR(100),
        qa_status VARCHAR(30) NOT NULL,
        compliance_classification VARCHAR(50) NOT NULL,
        model_represents_30cm BOOLEAN NOT NULL,
        extrapolation_method VARCHAR(200),
        compliance_notes TEXT,
        evidence_id UUID,
        physical_sample_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_soil_samples PRIMARY KEY (id),
        CONSTRAINT fk_soil_samples_evidence_id_evidence_records FOREIGN KEY(evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL,
        CONSTRAINT fk_soil_samples_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE CASCADE,
        CONSTRAINT fk_soil_samples_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_soil_samples_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_soil_samples_physical_sample_id_physical_samples FOREIGN KEY(physical_sample_id) REFERENCES public.physical_samples (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_soil_samples_land_unit_id ON public.soil_samples (land_unit_id);

    CREATE INDEX ix_public_soil_samples_organization_id ON public.soil_samples (organization_id);

    CREATE INDEX ix_public_soil_samples_physical_sample_id ON public.soil_samples (physical_sample_id);

    CREATE INDEX ix_public_soil_samples_project_id ON public.soil_samples (project_id);

    CREATE INDEX ix_public_soil_samples_sample_code ON public.soil_samples (sample_code);

    CREATE INDEX ix_repair_soil_samples_evidence_id ON public.soil_samples (evidence_id);

    CREATE TABLE public.agriculture_soc_change_results (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        baseline_stock_result_id UUID NOT NULL,
        monitoring_stock_result_id UUID NOT NULL,
        prerequisite_assessment_id UUID NOT NULL,
        result_code VARCHAR(100) NOT NULL,
        methodology_version VARCHAR(30) NOT NULL,
        corrections_clarifications_version VARCHAR(30) NOT NULL,
        calculation_engine_version VARCHAR(50) NOT NULL,
        quantification_approach VARCHAR(30) NOT NULL,
        t_start TIMESTAMP WITH TIME ZONE NOT NULL,
        t_final TIMESTAMP WITH TIME ZONE NOT NULL,
        elapsed_years NUMERIC(8, 4) NOT NULL,
        esm_algorithm VARCHAR(50) NOT NULL,
        reference_soil_mass_t_ha NUMERIC(14, 4) NOT NULL,
        reference_depth_cm NUMERIC(6, 2) NOT NULL,
        total_project_area_ha NUMERIC(14, 4) NOT NULL,
        baseline_mean_soc_t_c_per_ha NUMERIC(12, 4) NOT NULL,
        monitoring_mean_soc_t_c_per_ha NUMERIC(12, 4) NOT NULL,
        delta_soc_project_t_c_ha_yr NUMERIC(12, 4) NOT NULL,
        delta_soc_baseline_t_c_ha_yr NUMERIC(12, 4) NOT NULL,
        delta_soc_net_t_c_ha_yr NUMERIC(12, 4) NOT NULL,
        delta_co2_project_tco2e_ha_yr NUMERIC(12, 4) NOT NULL,
        delta_co2_baseline_tco2e_ha_yr NUMERIC(12, 4) NOT NULL,
        delta_co2_net_tco2e_ha_yr NUMERIC(12, 4) NOT NULL,
        total_project_delta_co2_tco2e_yr NUMERIC(14, 4) NOT NULL,
        total_baseline_delta_co2_tco2e_yr NUMERIC(14, 4) NOT NULL,
        total_net_delta_co2_tco2e_yr NUMERIC(14, 4) NOT NULL,
        baseline_soc_change_tco2e_yr NUMERIC(14, 4) NOT NULL,
        project_soc_change_tco2e_yr NUMERIC(14, 4) NOT NULL,
        qa2_net_soc_effect_tco2e_yr NUMERIC(14, 4) NOT NULL,
        uncertainty_adjusted_soc_effect_tco2e_yr NUMERIC(14, 4) NOT NULL,
        sign_indicator INTEGER NOT NULL,
        eq44_eq45_status VARCHAR(50) NOT NULL,
        df_estimator VARCHAR(50) NOT NULL,
        co2_to_c_ratio NUMERIC(10, 8) NOT NULL,
        variance_delta_soc_project NUMERIC(16, 8) NOT NULL,
        variance_delta_soc_baseline NUMERIC(16, 8) NOT NULL,
        total_variance_delta_soc NUMERIC(16, 8) NOT NULL,
        standard_error_delta_soc_t_c_ha_yr NUMERIC(14, 6) NOT NULL,
        standard_error_tco2e_yr NUMERIC(14, 4) NOT NULL,
        degrees_of_freedom INTEGER NOT NULL,
        student_t_value_0667 NUMERIC(8, 4) NOT NULL,
        relative_uncertainty_pct NUMERIC(8, 4) NOT NULL,
        allowable_uncertainty_pct NUMERIC(8, 4) NOT NULL,
        uncertainty_deduction_pct NUMERIC(8, 4) NOT NULL,
        uncertainty_deduction_fraction NUMERIC(8, 6) NOT NULL,
        adjusted_net_delta_co2_tco2e_yr NUMERIC(14, 4) NOT NULL,
        measurement_error_status VARCHAR(50) NOT NULL,
        measurement_error_router VARCHAR(50) NOT NULL,
        strata_results JSONB NOT NULL,
        component_breakdown JSONB NOT NULL,
        carbon_accounting_status VARCHAR(50) NOT NULL,
        ledger_status VARCHAR(50) NOT NULL,
        result_status VARCHAR(30) NOT NULL,
        calculation_hash VARCHAR(64) NOT NULL,
        input_snapshot_hash VARCHAR(64) NOT NULL,
        created_by_id UUID,
        superseded_by_id UUID,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_soc_change_results PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_soc_change_results_baseline_stock_result_8509 FOREIGN KEY(baseline_stock_result_id) REFERENCES public.agriculture_soc_stock_results (id) ON DELETE RESTRICT,
        CONSTRAINT fk_agriculture_soc_change_results_superseded_by_id_agri_f07d FOREIGN KEY(superseded_by_id) REFERENCES public.agriculture_soc_change_results (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_change_results_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_soc_change_results_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_soc_change_results_monitoring_stock_resu_b143 FOREIGN KEY(monitoring_stock_result_id) REFERENCES public.agriculture_soc_stock_results (id) ON DELETE RESTRICT,
        CONSTRAINT fk_agriculture_soc_change_results_prerequisite_assessme_11fa FOREIGN KEY(prerequisite_assessment_id) REFERENCES public.agriculture_prerequisite_assessments (id) ON DELETE RESTRICT,
        CONSTRAINT fk_agriculture_soc_change_results_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES public.users (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_agriculture_soc_change_results_baseline_stock_08fe ON public.agriculture_soc_change_results (baseline_stock_result_id);

    CREATE INDEX ix_public_agriculture_soc_change_results_calculation_hash ON public.agriculture_soc_change_results (calculation_hash);

    CREATE INDEX ix_public_agriculture_soc_change_results_input_snapshot_hash ON public.agriculture_soc_change_results (input_snapshot_hash);

    CREATE INDEX ix_public_agriculture_soc_change_results_monitoring_sto_4321 ON public.agriculture_soc_change_results (monitoring_stock_result_id);

    CREATE INDEX ix_public_agriculture_soc_change_results_organization_id ON public.agriculture_soc_change_results (organization_id);

    CREATE INDEX ix_public_agriculture_soc_change_results_prerequisite_a_f8a9 ON public.agriculture_soc_change_results (prerequisite_assessment_id);

    CREATE INDEX ix_public_agriculture_soc_change_results_project_id ON public.agriculture_soc_change_results (project_id);

    CREATE UNIQUE INDEX ix_public_agriculture_soc_change_results_result_code ON public.agriculture_soc_change_results (result_code);

    CREATE INDEX ix_repair_agriculture_soc_change_results_created_by_id ON public.agriculture_soc_change_results (created_by_id);

    CREATE INDEX ix_repair_agriculture_soc_change_results_superseded_by_id ON public.agriculture_soc_change_results (superseded_by_id);

    CREATE TABLE public.laboratory_results (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        analysis_id UUID NOT NULL,
        physical_sample_id UUID NOT NULL,
        analyte VARCHAR(50) NOT NULL,
        raw_value NUMERIC(12, 4) NOT NULL,
        raw_unit VARCHAR(30) NOT NULL,
        normalized_value NUMERIC(12, 4),
        normalized_unit VARCHAR(30),
        normalization_method VARCHAR(100),
        normalization_version VARCHAR(30),
        detection_limit NUMERIC(12, 4),
        quantification_limit NUMERIC(12, 4),
        uncertainty_pct NUMERIC(6, 2),
        qualifier VARCHAR(20) NOT NULL,
        is_superseded BOOLEAN NOT NULL,
        superseded_by_id UUID,
        supersedes_id UUID,
        revision_reason TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_laboratory_results PRIMARY KEY (id),
        CONSTRAINT fk_laboratory_results_physical_sample_id_physical_samples FOREIGN KEY(physical_sample_id) REFERENCES public.physical_samples (id) ON DELETE CASCADE,
        CONSTRAINT fk_laboratory_results_analysis_id_laboratory_analyses FOREIGN KEY(analysis_id) REFERENCES public.laboratory_analyses (id) ON DELETE CASCADE,
        CONSTRAINT fk_laboratory_results_superseded_by_id_laboratory_results FOREIGN KEY(superseded_by_id) REFERENCES public.laboratory_results (id) ON DELETE SET NULL,
        CONSTRAINT fk_laboratory_results_supersedes_id_laboratory_results FOREIGN KEY(supersedes_id) REFERENCES public.laboratory_results (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_laboratory_results_analysis_id ON public.laboratory_results (analysis_id);

    CREATE INDEX ix_public_laboratory_results_analyte ON public.laboratory_results (analyte);

    CREATE INDEX ix_public_laboratory_results_physical_sample_id ON public.laboratory_results (physical_sample_id);

    CREATE INDEX ix_repair_laboratory_results_superseded_by_id ON public.laboratory_results (superseded_by_id);

    CREATE INDEX ix_repair_laboratory_results_supersedes_id ON public.laboratory_results (supersedes_id);

    CREATE TABLE public.agriculture_net_ghg_results (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        soc_change_result_id UUID,
        prerequisite_assessment_id UUID NOT NULL,
        result_code VARCHAR(100) NOT NULL,
        methodology_version VARCHAR(30) NOT NULL,
        corrections_clarifications_version VARCHAR(30) NOT NULL,
        calculation_engine_version VARCHAR(50) NOT NULL,
        ruleset_version VARCHAR(50) NOT NULL,
        verification_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
        verification_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
        elapsed_years NUMERIC(8, 4) NOT NULL,
        applicability_matrix JSONB NOT NULL,
        total_baseline_emissions_tco2e NUMERIC(14, 4) NOT NULL,
        total_project_emissions_tco2e NUMERIC(14, 4) NOT NULL,
        total_emission_reductions_from_sources_tco2e NUMERIC(14, 4) NOT NULL,
        eq44_baseline_total_carbon_stock_change_tco2e NUMERIC(14, 4) NOT NULL,
        eq45_project_total_carbon_stock_change_tco2e NUMERIC(14, 4) NOT NULL,
        eq44_eq45_status VARCHAR(50) NOT NULL,
        gross_reductions_er_tco2e NUMERIC(14, 4) NOT NULL,
        gross_removals_cr_tco2e NUMERIC(14, 4) NOT NULL,
        total_leakage_tco2e NUMERIC(14, 4) NOT NULL,
        leakage_allocation_er_lker_tco2e NUMERIC(14, 4) NOT NULL,
        leakage_allocation_cr_lkcr_tco2e NUMERIC(14, 4) NOT NULL,
        net_reductions_ernet_tco2e NUMERIC(14, 4) NOT NULL,
        net_removals_crnet_tco2e NUMERIC(14, 4) NOT NULL,
        total_net_ghg_errnet_tco2e NUMERIC(14, 4) NOT NULL,
        npr_rating_pct NUMERIC(8, 4),
        risk_assessment_id VARCHAR(100),
        buffer_deduction_reductions_tco2e NUMERIC(14, 4),
        buffer_deduction_removals_tco2e NUMERIC(14, 4),
        total_buffer_deduction_tco2e NUMERIC(14, 4),
        internal_vcu_eligible_reductions_tco2e NUMERIC(14, 4),
        internal_vcu_eligible_removals_tco2e NUMERIC(14, 4),
        internal_vcu_eligible_total_tco2e NUMERIC(14, 4),
        vcu_readiness_status VARCHAR(50) NOT NULL,
        internal_mrv_status VARCHAR(50) NOT NULL,
        vvb_status VARCHAR(50) NOT NULL,
        registry_status VARCHAR(50) NOT NULL,
        ledger_status VARCHAR(50) NOT NULL,
        result_status VARCHAR(30) NOT NULL,
        calculation_hash VARCHAR(64) NOT NULL,
        input_snapshot_hash VARCHAR(64) NOT NULL,
        created_by_id UUID,
        superseded_by_id UUID,
        notes TEXT,
        component_breakdown JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_net_ghg_results PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_net_ghg_results_soc_change_result_id_agr_4503 FOREIGN KEY(soc_change_result_id) REFERENCES public.agriculture_soc_change_results (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_net_ghg_results_superseded_by_id_agricul_6166 FOREIGN KEY(superseded_by_id) REFERENCES public.agriculture_net_ghg_results (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_net_ghg_results_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_net_ghg_results_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES public.users (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_net_ghg_results_prerequisite_assessment__93ba FOREIGN KEY(prerequisite_assessment_id) REFERENCES public.agriculture_prerequisite_assessments (id) ON DELETE RESTRICT,
        CONSTRAINT fk_agriculture_net_ghg_results_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_agriculture_net_ghg_results_calculation_hash ON public.agriculture_net_ghg_results (calculation_hash);

    CREATE INDEX ix_public_agriculture_net_ghg_results_input_snapshot_hash ON public.agriculture_net_ghg_results (input_snapshot_hash);

    CREATE INDEX ix_public_agriculture_net_ghg_results_organization_id ON public.agriculture_net_ghg_results (organization_id);

    CREATE INDEX ix_public_agriculture_net_ghg_results_prerequisite_asse_733a ON public.agriculture_net_ghg_results (prerequisite_assessment_id);

    CREATE INDEX ix_public_agriculture_net_ghg_results_project_id ON public.agriculture_net_ghg_results (project_id);

    CREATE UNIQUE INDEX ix_public_agriculture_net_ghg_results_result_code ON public.agriculture_net_ghg_results (result_code);

    CREATE INDEX ix_public_agriculture_net_ghg_results_soc_change_result_id ON public.agriculture_net_ghg_results (soc_change_result_id);

    CREATE INDEX ix_repair_agriculture_net_ghg_results_created_by_id ON public.agriculture_net_ghg_results (created_by_id);

    CREATE INDEX ix_repair_agriculture_net_ghg_results_superseded_by_id ON public.agriculture_net_ghg_results (superseded_by_id);

    CREATE TABLE public.agriculture_soc_layer_results (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        stock_result_id UUID NOT NULL,
        sample_id UUID,
        layer_index INTEGER NOT NULL,
        depth_upper_cm NUMERIC(6, 2) NOT NULL,
        depth_lower_cm NUMERIC(6, 2) NOT NULL,
        layer_thickness_cm NUMERIC(6, 2) NOT NULL,
        bulk_density_g_cm3 NUMERIC(8, 4),
        bulk_density_provenance VARCHAR(50) NOT NULL,
        soil_mass_provenance VARCHAR(50) NOT NULL,
        coarse_fragment_fraction NUMERIC(6, 4),
        coarse_fragment_provenance VARCHAR(50) NOT NULL,
        coarse_fragment_mass_g NUMERIC(10, 2),
        fine_soil_mass_g NUMERIC(10, 2),
        soc_concentration_g_kg NUMERIC(10, 4) NOT NULL,
        laboratory_result_id UUID,
        layer_soil_mass_t_ha NUMERIC(14, 4) NOT NULL,
        layer_soc_mass_t_c_ha NUMERIC(12, 4) NOT NULL,
        cumulative_soil_mass_t_ha NUMERIC(14, 4) NOT NULL,
        cumulative_soc_mass_t_c_ha NUMERIC(12, 4) NOT NULL,
        fraction_in_reference_mass NUMERIC(6, 4),
        included_soil_mass_t_ha NUMERIC(14, 4),
        included_soc_mass_t_c_ha NUMERIC(12, 4),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_soc_layer_results PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_soc_layer_results_sample_id_physical_samples FOREIGN KEY(sample_id) REFERENCES public.physical_samples (id) ON DELETE SET NULL,
        CONSTRAINT fk_agriculture_soc_layer_results_stock_result_id_agricu_2ef8 FOREIGN KEY(stock_result_id) REFERENCES public.agriculture_soc_stock_results (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_soc_layer_results_laboratory_result_id_l_9747 FOREIGN KEY(laboratory_result_id) REFERENCES public.laboratory_results (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_agriculture_soc_layer_results_sample_id ON public.agriculture_soc_layer_results (sample_id);

    CREATE INDEX ix_public_agriculture_soc_layer_results_stock_result_id ON public.agriculture_soc_layer_results (stock_result_id);

    CREATE INDEX ix_repair_agriculture_soc_layer_results_laboratory_result_id ON public.agriculture_soc_layer_results (laboratory_result_id);

    CREATE TABLE public.laboratory_import_rows (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        import_batch_id UUID NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        source_sheet_name VARCHAR(100),
        source_row_number INTEGER NOT NULL,
        raw_row_payload JSONB NOT NULL,
        mapped_payload JSONB NOT NULL,
        validation_status VARCHAR(30) NOT NULL,
        validation_messages JSONB NOT NULL,
        matched_sample_id UUID,
        matched_sample_code VARCHAR(50),
        canonical_analyte VARCHAR(50),
        raw_value NUMERIC(12, 4),
        raw_unit VARCHAR(30),
        normalized_value NUMERIC(12, 4),
        normalized_unit VARCHAR(30),
        resulting_lab_result_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_laboratory_import_rows PRIMARY KEY (id),
        CONSTRAINT fk_laboratory_import_rows_matched_sample_id_physical_samples FOREIGN KEY(matched_sample_id) REFERENCES public.physical_samples (id) ON DELETE SET NULL,
        CONSTRAINT fk_laboratory_import_rows_import_batch_id_laboratory_im_c781 FOREIGN KEY(import_batch_id) REFERENCES public.laboratory_import_batches (id) ON DELETE CASCADE,
        CONSTRAINT fk_laboratory_import_rows_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_laboratory_import_rows_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_laboratory_import_rows_resulting_lab_result_id_labor_9a0a FOREIGN KEY(resulting_lab_result_id) REFERENCES public.laboratory_results (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_laboratory_import_rows_import_batch_id ON public.laboratory_import_rows (import_batch_id);

    CREATE INDEX ix_public_laboratory_import_rows_matched_sample_id ON public.laboratory_import_rows (matched_sample_id);

    CREATE INDEX ix_public_laboratory_import_rows_organization_id ON public.laboratory_import_rows (organization_id);

    CREATE INDEX ix_public_laboratory_import_rows_project_id ON public.laboratory_import_rows (project_id);

    CREATE INDEX ix_public_laboratory_import_rows_resulting_lab_result_id ON public.laboratory_import_rows (resulting_lab_result_id);

    CREATE INDEX ix_public_laboratory_import_rows_validation_status ON public.laboratory_import_rows (validation_status);

    CREATE TABLE public.agriculture_vintage_ghg_results (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        net_ghg_result_id UUID NOT NULL,
        vintage_year INTEGER NOT NULL,
        total_baseline_emissions_tco2e NUMERIC(14, 4) NOT NULL,
        total_project_emissions_tco2e NUMERIC(14, 4) NOT NULL,
        total_emission_reductions_from_sources_tco2e NUMERIC(14, 4) NOT NULL,
        eq44_baseline_total_carbon_stock_change_tco2e NUMERIC(14, 4) NOT NULL,
        eq45_project_total_carbon_stock_change_tco2e NUMERIC(14, 4) NOT NULL,
        gross_reductions_er_tco2e NUMERIC(14, 4) NOT NULL,
        gross_removals_cr_tco2e NUMERIC(14, 4) NOT NULL,
        total_leakage_tco2e NUMERIC(14, 4) NOT NULL,
        leakage_allocation_er_lker_tco2e NUMERIC(14, 4) NOT NULL,
        leakage_allocation_cr_lkcr_tco2e NUMERIC(14, 4) NOT NULL,
        net_reductions_ernet_tco2e NUMERIC(14, 4) NOT NULL,
        net_removals_crnet_tco2e NUMERIC(14, 4) NOT NULL,
        total_net_ghg_errnet_tco2e NUMERIC(14, 4) NOT NULL,
        buffer_deduction_reductions_tco2e NUMERIC(14, 4),
        buffer_deduction_removals_tco2e NUMERIC(14, 4),
        total_buffer_deduction_tco2e NUMERIC(14, 4),
        internal_vcu_eligible_reductions_tco2e NUMERIC(14, 4),
        internal_vcu_eligible_removals_tco2e NUMERIC(14, 4),
        internal_vcu_eligible_total_tco2e NUMERIC(14, 4),
        vintage_details JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_vintage_ghg_results PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_vintage_ghg_results_net_ghg_result_id_ag_e2f4 FOREIGN KEY(net_ghg_result_id) REFERENCES public.agriculture_net_ghg_results (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_agriculture_vintage_ghg_results_net_ghg_result_id ON public.agriculture_vintage_ghg_results (net_ghg_result_id);

    CREATE INDEX ix_public_agriculture_vintage_ghg_results_vintage_year ON public.agriculture_vintage_ghg_results (vintage_year);

    -- FastAPI uses its existing owner connection and its tenant/RBAC checks.
    -- Supabase client roles receive no direct access and no guessed JWT policy.
    FOREACH table_name IN ARRAY target_tables LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC', table_name);
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = role_name) THEN
                EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I', table_name, role_name);
            END IF;
        END LOOP;
    END LOOP;
END;
$agriculture_repair$;
"""

# The repository history creates 25 target tables but omitted these four legacy models.
HISTORICAL_MISSING_TABLES = ('agriculture_model_runs', 'satellite_observations', 'soil_samples', 'tree_observations')
HISTORICAL_COMPLETION_SQL = r"""
-- Frozen from application source 1f606c7; no existing data or assignments are rewritten.
-- Execute this one DO statement transactionally; do not replay the historical migration chain.
DO $agriculture_repair$
DECLARE
    target_tables text[] := ARRAY['agriculture_model_runs', 'satellite_observations', 'soil_samples', 'tree_observations'];
    table_name text;
    role_name text;
BEGIN
    PERFORM pg_catalog.set_config('lock_timeout', '3s', true);
    PERFORM pg_catalog.set_config('statement_timeout', '60s', true);
    PERFORM pg_catalog.set_config('search_path', 'pg_catalog, public, extensions', true);
    PERFORM pg_catalog.pg_advisory_xact_lock(6152865464);
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_extension WHERE extname = 'postgis')
       OR pg_catalog.to_regtype('geometry') IS NULL THEN
        RAISE EXCEPTION 'Existing PostGIS geometry type is required; no extension will be installed';
    END IF;
    FOREACH table_name IN ARRAY target_tables LOOP
        IF pg_catalog.to_regclass('public.' || table_name) IS NOT NULL THEN
            RAISE EXCEPTION 'Repair preflight: target table % already exists; inspect drift before proceeding', table_name;
        END IF;
    END LOOP;
    FOREACH table_name IN ARRAY ARRAY['organizations', 'projects', 'users', 'evidence_records', 'methodology_versions'] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = pg_catalog.to_regclass('public.' || table_name)
              AND a.attname = 'id' AND a.atttypid = 'uuid'::regtype AND NOT a.attisdropped
        ) THEN
            RAISE EXCEPTION 'Repair preflight: required UUID key missing on %', table_name;
        END IF;
    END LOOP;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_attribute
        WHERE attrelid = 'public.projects'::regclass
          AND attname = 'methodology_id' AND atttypid = 'uuid'::regtype AND NOT attisdropped
    ) THEN
        RAISE EXCEPTION 'Repair preflight: expected projects.methodology_id UUID missing';
    END IF;

    -- Widen the constraint only; preserve existing methodology values and foreign key.
    ALTER TABLE public.projects ALTER COLUMN methodology_id DROP NOT NULL;
    CREATE TABLE public.agriculture_model_runs (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        model_name VARCHAR(100) NOT NULL,
        model_type VARCHAR(50) NOT NULL,
        version VARCHAR(30) NOT NULL,
        run_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        status VARCHAR(30) NOT NULL,
        input_parameters JSONB NOT NULL,
        input_dataset_hashes JSONB NOT NULL,
        performance_metrics JSONB NOT NULL,
        uncertainty_metrics JSONB NOT NULL,
        output_manifest JSONB NOT NULL,
        provenance_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_agriculture_model_runs PRIMARY KEY (id),
        CONSTRAINT fk_agriculture_model_runs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_agriculture_model_runs_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_agriculture_model_runs_organization_id ON public.agriculture_model_runs (organization_id);

    CREATE INDEX ix_public_agriculture_model_runs_project_id ON public.agriculture_model_runs (project_id);

    CREATE TABLE public.satellite_observations (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        land_unit_id UUID,
        provider VARCHAR(50) NOT NULL,
        scene_id VARCHAR(100) NOT NULL,
        acquisition_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        cloud_coverage_pct FLOAT,
        spatial_resolution_m FLOAT NOT NULL,
        observation_type VARCHAR(50) NOT NULL,
        raw_band_uris JSONB NOT NULL,
        derived_indices JSONB NOT NULL,
        provenance_hash VARCHAR(64) NOT NULL,
        processing_level VARCHAR(20) NOT NULL,
        lineage_manifest JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_satellite_observations PRIMARY KEY (id),
        CONSTRAINT fk_satellite_observations_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_satellite_observations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_satellite_observations_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_satellite_observations_land_unit_id ON public.satellite_observations (land_unit_id);

    CREATE INDEX ix_public_satellite_observations_organization_id ON public.satellite_observations (organization_id);

    CREATE INDEX ix_public_satellite_observations_project_id ON public.satellite_observations (project_id);

    CREATE INDEX ix_public_satellite_observations_scene_id ON public.satellite_observations (scene_id);

    CREATE TABLE public.tree_observations (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        land_unit_id UUID NOT NULL,
        sampling_approach VARCHAR(30) NOT NULL,
        tag_number VARCHAR(50),
        species_scientific VARCHAR(100) NOT NULL,
        species_common VARCHAR(100),
        dbh_cm FLOAT NOT NULL,
        height_m FLOAT,
        crown_diameter_m FLOAT,
        health_status VARCHAR(30) NOT NULL,
        latitude FLOAT,
        longitude FLOAT,
        measurement_date DATE NOT NULL,
        allometric_equation_id VARCHAR(100),
        belowground_model_id VARCHAR(100),
        derived_aboveground_biomass_kg FLOAT,
        derived_belowground_biomass_kg FLOAT,
        derived_carbon_stock_t_co2e FLOAT,
        calculation_run_id UUID,
        evidence_photo_hash VARCHAR(64),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_tree_observations PRIMARY KEY (id),
        CONSTRAINT fk_tree_observations_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_tree_observations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_tree_observations_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE CASCADE
    );

    CREATE INDEX ix_public_tree_observations_land_unit_id ON public.tree_observations (land_unit_id);

    CREATE INDEX ix_public_tree_observations_organization_id ON public.tree_observations (organization_id);

    CREATE INDEX ix_public_tree_observations_project_id ON public.tree_observations (project_id);

    CREATE INDEX ix_public_tree_observations_tag_number ON public.tree_observations (tag_number);

    CREATE TABLE public.soil_samples (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        organization_id UUID NOT NULL,
        project_id UUID NOT NULL,
        land_unit_id UUID,
        sample_code VARCHAR(50) NOT NULL,
        sampling_date DATE NOT NULL,
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        depth_upper_cm FLOAT NOT NULL,
        depth_lower_cm FLOAT NOT NULL,
        bulk_density_g_cm3 FLOAT,
        soc_stock_pct FLOAT NOT NULL,
        total_organic_carbon_g_kg FLOAT,
        computed_soc_stock_t_c_ha FLOAT,
        coarse_fragments_pct FLOAT NOT NULL,
        ph FLOAT,
        electrical_conductivity_ds_m FLOAT,
        texture_class VARCHAR(30),
        lab_method VARCHAR(50) NOT NULL,
        lab_name VARCHAR(100),
        lab_accreditation VARCHAR(100),
        qa_status VARCHAR(30) NOT NULL,
        compliance_classification VARCHAR(50) NOT NULL,
        model_represents_30cm BOOLEAN NOT NULL,
        extrapolation_method VARCHAR(200),
        compliance_notes TEXT,
        evidence_id UUID,
        physical_sample_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_soil_samples PRIMARY KEY (id),
        CONSTRAINT fk_soil_samples_evidence_id_evidence_records FOREIGN KEY(evidence_id) REFERENCES public.evidence_records (id) ON DELETE SET NULL,
        CONSTRAINT fk_soil_samples_land_unit_id_land_units FOREIGN KEY(land_unit_id) REFERENCES public.land_units (id) ON DELETE CASCADE,
        CONSTRAINT fk_soil_samples_project_id_projects FOREIGN KEY(project_id) REFERENCES public.projects (id) ON DELETE CASCADE,
        CONSTRAINT fk_soil_samples_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE,
        CONSTRAINT fk_soil_samples_physical_sample_id_physical_samples FOREIGN KEY(physical_sample_id) REFERENCES public.physical_samples (id) ON DELETE SET NULL
    );

    CREATE INDEX ix_public_soil_samples_land_unit_id ON public.soil_samples (land_unit_id);

    CREATE INDEX ix_public_soil_samples_organization_id ON public.soil_samples (organization_id);

    CREATE INDEX ix_public_soil_samples_physical_sample_id ON public.soil_samples (physical_sample_id);

    CREATE INDEX ix_public_soil_samples_project_id ON public.soil_samples (project_id);

    CREATE INDEX ix_public_soil_samples_sample_code ON public.soil_samples (sample_code);

    CREATE INDEX ix_repair_soil_samples_evidence_id ON public.soil_samples (evidence_id);

    -- FastAPI uses its existing owner connection and its tenant/RBAC checks.
    -- Supabase client roles receive no direct access and no guessed JWT policy.
    FOREACH table_name IN ARRAY target_tables LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC', table_name);
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = role_name) THEN
                EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I', table_name, role_name);
            END IF;
        END LOOP;
    END LOOP;
END;
$agriculture_repair$;
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite development schemas continue to use the existing ORM setup.
    present = set(sa.inspect(bind).get_table_names(schema="public")) & set(REPAIR_TABLES)
    if present == set(REPAIR_TABLES):
        # Normal fresh Alembic installs already created these in the historical chain.
        # Do not change existing grants, policies, data or structures here.
        op.execute("ALTER TABLE public.projects ALTER COLUMN methodology_id DROP NOT NULL")
        return
    if present == set(REPAIR_TABLES) - set(HISTORICAL_MISSING_TABLES):
        # Explicitly supported historical gap; leave the existing 25 tables intact.
        op.execute(sa.text(HISTORICAL_COMPLETION_SQL))
        return
    if present:
        raise RuntimeError("Partial agriculture schema: inspect before applying repair")
    op.execute(sa.text(REPAIR_SQL))


def downgrade() -> None:
    raise RuntimeError(
        "Data-preserving migration: retain additive tables and nullable methodology. "
        "Review an explicit recovery plan instead of dropping records."
    )
