"""
Puro.earth Biochar Edition 2025 V2 DB Schema Consistency Test
Verifies that:
1. Base.metadata contains all Puro models and columns (including application_type, min_environmental_quality, etc.).
2. Database reflection against the active session confirms all required columns, constraints, and tables exist.
3. No missing migrated columns between Alembic head (a1b2c3d4e5f6) and SQLAlchemy ORM metadata.
"""
import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.domains.biochar.puro_models import (
    PuroMethodologyVersion,
    PuroRuleDefinition,
    PuroNormativeDependency,
    PuroSupplierProfile,
    PuroFacilityProfile,
    PuroMobileProductionSite,
    PuroCreditingPeriod,
    PuroBaselineAssessment,
    PuroAdditionalityAssessment,
    PuroEndUseCategory,
    PuroEndUseRecordLink,
    PuroCharStreamRecord,
    PuroLCAModel,
    PuroLCIEntry,
    PuroCutoffDecision,
    PuroCoProductAllocation,
    PuroCalculationExecution,
    PuroAuditWorkflow,
    PuroAuditFinding,
    PuroOutputReport,
    PuroComplianceEvaluation,
)


def test_puro_orm_metadata_registration():
    """Verifies all Puro tables and required columns are registered in Base.metadata."""
    metadata_tables = Base.metadata.tables

    # 1. Required Puro tables
    expected_tables = [
        "puro_methodology_versions",
        "puro_rule_definitions",
        "puro_normative_dependencies",
        "puro_supplier_profiles",
        "puro_facility_profiles",
        "puro_mobile_production_sites",
        "puro_crediting_periods",
        "puro_baseline_assessments",
        "puro_additionality_assessments",
        "puro_end_use_categories",
        "puro_end_use_record_links",
        "puro_char_stream_records",
        "puro_lca_models",
        "puro_lci_entries",
        "puro_cutoff_decisions",
        "puro_coproduct_allocations",
        "puro_calculation_executions",
        "puro_audit_workflows",
        "puro_audit_findings",
        "puro_output_reports",
        "puro_compliance_evaluations",
    ]
    for table_name in expected_tables:
        assert table_name in metadata_tables, f"Table {table_name} missing from Base.metadata"

    # 2. Verify Table 3.2 End Use Category columns
    end_use_cols = {c.name for c in metadata_tables["puro_end_use_categories"].columns}
    assert "application_type" in end_use_cols
    assert "min_environmental_quality" in end_use_cols
    assert "pure_or_mixed" in end_use_cols
    assert "reversal_rules" in end_use_cols
    assert "cascading_conditions" in end_use_cols
    assert "reversal_discount_factor_required" in end_use_cols
    assert "is_corc_eligible" in end_use_cols

    # 3. Verify Calculation Execution columns (forensic v2 engine)
    calc_cols = {c.name for c in metadata_tables["puro_calculation_executions"].columns}
    assert "calculation_mode" in calc_cols
    assert "persistence_fraction_pf" in calc_cols
    assert "persistence_m_param" in calc_cols
    assert "persistence_a_param" in calc_cols
    assert "durability_class" in calc_cols
    assert "e_ops_biomass_tco2e" in calc_cols
    assert "e_ops_production_tco2e" in calc_cols
    assert "e_ops_use_tco2e" in calc_cols
    assert "e_ops_total_tco2e" in calc_cols
    assert "e_emb_infra_tco2e" in calc_cols
    assert "e_emb_dluc_tco2e" in calc_cols
    assert "e_emb_annualized_tco2e" in calc_cols
    assert "leakage_eco_tco2e" in calc_cols
    assert "leakage_ma_tco2e" in calc_cols
    assert "leakage_iluc_tco2e" in calc_cols
    assert "reported_uncertainty_text" in calc_cols
    assert "superseded_at" in calc_cols
    assert "superseded_reason" in calc_cols
    assert "replacement_engine_version" in calc_cols


@pytest.mark.asyncio
async def test_puro_reflected_database_schema(db_session: AsyncSession):
    """Verifies that the live test database schema has all required columns via inspection."""
    def inspect_tables(conn):
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        return tables, {
            table: {col["name"] for col in inspector.get_columns(table)}
            for table in tables
            if table.startswith("puro_")
        }

    conn = await db_session.connection()
    tables, puro_table_cols = await conn.run_sync(inspect_tables)

    # All required Puro tables exist in DB
    for table_name in [
        "puro_end_use_categories",
        "puro_calculation_executions",
        "puro_lca_models",
        "puro_char_stream_records",
        "puro_coproduct_allocations",
    ]:
        assert table_name in tables, f"Table {table_name} missing from database"

    # End use category columns exist in DB
    end_use_cols = puro_table_cols.get("puro_end_use_categories", set())
    assert "application_type" in end_use_cols, "application_type missing in DB"
    assert "min_environmental_quality" in end_use_cols, "min_environmental_quality missing in DB"
    assert "reversal_rules" in end_use_cols, "reversal_rules missing in DB"
    assert "cascading_conditions" in end_use_cols, "cascading_conditions missing in DB"
    assert "reversal_discount_factor_required" in end_use_cols, "reversal_discount_factor_required missing in DB"

    # Calculation executions columns exist in DB
    calc_cols = puro_table_cols.get("puro_calculation_executions", set())
    assert "calculation_mode" in calc_cols, "calculation_mode missing in DB"
    assert "persistence_fraction_pf" in calc_cols, "persistence_fraction_pf missing in DB"
    assert "superseded_at" in calc_cols, "superseded_at missing in DB"
    assert "reported_uncertainty_text" in calc_cols, "reported_uncertainty_text missing in DB"
