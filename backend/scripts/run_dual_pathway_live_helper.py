"""
VeriField Nexus — Dual-Pathway Live E2E Helper
Creates shared synthetic physical records for Puro and VM0044 full-stack verification.
Queries real PostgreSQL 18.1 for direct database verification.
"""

import sys
import os
import json
import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, date

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, text
from app.db.session import async_session_factory
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.authentication.models import User
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharLabAnalysis,
    FeedstockLot,
    FeedstockSource,
    ProductionFacility,
    ProductionRun,
)
from app.domains.biochar.puro_models import (
    PuroBiomassSourceDeclaration,
    PuroCalculationExecution,
    PuroCounterfactualStorageAssessment,
    PuroCreditingPeriod,
    PuroEndUseCategory,
    PuroEndUseRecordLink,
    PuroLCAModel,
    PuroLCIEntry,
    PuroMethodologyVersion,
)
from app.domains.biochar.puro_rules import seed_puro_biochar_normative_metadata
from app.domains.biochar.vm0044_models import (
    VM0044CalculationExecution,
    VM0044CalculationSnapshot,
)
from app.domains.biochar.vm0044_rules import seed_vm0044_normative_metadata
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash


async def setup_test_environment():
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        # 1. Seed normative metadata for both methodologies
        await seed_puro_biochar_normative_metadata(session)
        await seed_vm0044_normative_metadata(session)

        # 2. Organization
        org = Organization(
            id=uuid.uuid4(),
            name=f"Dual-Pathway Live Verification Org {tag}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
            status="ACTIVE",
            max_installations=100,
            max_agents=5,
            api_calls_count=0,
            version=1,
            is_deleted=False,
        )
        session.add(org)
        await session.flush()

        # 3. User (ORG_ADMIN)
        user = User(
            id=uuid.uuid4(),
            email=f"lead.{tag}@dual-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Biochar Verification Lead",
            role="ORG_ADMIN",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add(user)
        await session.flush()

        # 4. Project
        proj = Project(
            id=uuid.uuid4(),
            name=f"Dual Biochar Project {tag}",
            project_code=f"DUAL-{tag[:6].upper()}",
            organization_id=org.id,
            country="Finland",
        )
        session.add(proj)
        await session.flush()

        # 5. Production Facility
        fac = ProductionFacility(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            facility_code=f"FAC-DUAL-{tag[:6]}",
            facility_name="Dual-Pathway Pyrolysis Facility",
            facility_status="NEW_OPERATIONAL",
            technology_type="HIGH_TEMPERATURE_PYROLYSIS",
            commissioning_date=date(2025, 1, 1),
            production_capacity_tpy=5000.0,
        )
        session.add(fac)
        await session.flush()

        # 6. Feedstock Source & Lot
        src = FeedstockSource(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            source_code=f"SRC-WOOD-{tag[:6]}",
            source_name="Sustainable Pine Residues",
            source_type="FORESTRY_RESIDUE",
            biomass_type="WOOD_CHIPS",
            origin_location="Helsinki, Finland",
            waste_status="CONFIRMED_WASTE_BIOMASS",
            baseline_fate="OPEN_BURNING",
            sustainability_status="LOW_RISK",
        )
        session.add(src)
        await session.flush()

        lot = FeedstockLot(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            source_id=src.id,
            lot_number=f"LOT-WOOD-{tag[:6]}",
            feedstock_type="FORESTRY_RESIDUE",
            mass_received_tonnes=Decimal("150.0"),
            moisture_content_pct=Decimal("15.0"),
            dry_mass_tonnes=Decimal("127.5"),
        )
        session.add(lot)
        await session.flush()

        # 7. Production Run
        run = ProductionRun(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            facility_id=fac.id,
            run_number=f"RUN-{tag[:6]}",
            start_time=datetime(2025, 2, 1, 8, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 2, 2, 18, 0, tzinfo=timezone.utc),
            total_feedstock_input_tonnes=Decimal("150.0"),
            total_feedstock_dry_tonnes=Decimal("127.5"),
            avg_pyrolysis_temp_celsius=650.0,
            residence_time_minutes=45.0,
            electricity_kwh=100.0,
            fuel_liters=10.0,
            output_biochar_mass_tonnes=Decimal("30.0"),
            qa_status="QA_PASSED",
        )
        session.add(run)
        await session.flush()

        # 8. Biochar Batch
        batch = BiocharBatch(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            production_run_id=run.id,
            batch_number=f"BATCH-DUAL-{tag[:6].upper()}",
            facility_name="Dual-Pathway Pyrolysis Facility",
            kiln_id="KILN-HT-01",
            feedstock_type="FORESTRY_RESIDUE",
            feedstock_weight_tonnes=Decimal("100.0"),
            moisture_content_pct=Decimal("12.0"),
            pyrolysis_temp_celsius=650.0,
            residence_time_minutes=45.0,
            biochar_yield_tonnes=Decimal("30.0"),
            dry_mass_tonnes=Decimal("30.0"),
            fixed_carbon_pct=82.0,
            molar_h_c_ratio=0.35,
            carbon_permanence_factor=0.89,
            net_co2e_removed_tonnes=Decimal("80.2062"),
            quality_grade="GRADE_A",
            status="LAB_TESTED",
            metadata_json={"feedstock_lot_id": str(lot.id)},
        )
        session.add(batch)
        await session.flush()

        # 9. Lab Analysis
        lab = BiocharLabAnalysis(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            batch_id=batch.id,
            sample_id=f"SMP-DUAL-{tag[:6]}",
            sampling_date=now,
            laboratory_name="Eurofins Agroscience Testing Laboratory",
            organic_carbon_pct=82.0,
            fixed_carbon_pct=78.0,
            molar_h_c_ratio=0.35,
            moisture_pct=5.0,
            ash_pct=2.5,
            heavy_metals_pass=True,
            qa_status="VERIFIED",
        )
        session.add(lab)
        await session.flush()

        # 10. End Use Record
        eu = BiocharEndUseRecord(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            batch_id=batch.id,
            end_use_type="SOIL_APPLICATION",
            applied_quantity_tonnes=Decimal("30.0"),
            event_date=now,
            wetland_exclusion_screened=True,
            metadata_json={"incorporation_depth_cm": 15.0},
            verification_status="VERIFIED",
        )
        session.add(eu)
        await session.flush()

        # 11. Puro Biomass Source Declaration
        decl = PuroBiomassSourceDeclaration(
            id=uuid.uuid4(),
            organization_id=org.id,
            feedstock_source_id=src.id,
            source_declaration_code=f"DECL-{tag[:6]}",
            declared_validity_start=date(2025, 1, 1),
            declared_validity_end=date(2030, 1, 1),
            puro_category_ref="FORESTRY_RESIDUE",
            risk_classification="LOW_RISK",
            is_active=True,
        )
        session.add(decl)

        # 12. Puro Crediting Period
        cp = PuroCreditingPeriod(
            id=uuid.uuid4(),
            organization_id=org.id,
            facility_id=fac.id,
            sequence_number=1,
            start_date=date(2025, 1, 1),
            end_date=date(2034, 12, 31),
            status="ACTIVE",
        )
        session.add(cp)

        # 13. Puro End-Use Record Link
        stmt_cat = select(PuroEndUseCategory).where(PuroEndUseCategory.category_code == "AF1")
        res_cat = await session.execute(stmt_cat)
        cat = res_cat.scalar_one_or_none()
        if not cat:
            cat = PuroEndUseCategory(
                id=uuid.uuid4(),
                category_code="AF1",
                category_name="Agricultural Soil Application",
                application_type="SOIL",
                persistence_model="TABLE_6_1",
                is_corc_eligible=True,
            )
            session.add(cat)
            await session.flush()

        link = PuroEndUseRecordLink(
            id=uuid.uuid4(),
            organization_id=org.id,
            batch_id=batch.id,
            end_use_record_id=eu.id,
            category_id=cat.id,
            corc_point_reached="CORC_POINT_ELIGIBLE",
        )
        session.add(link)

        # 14. Puro LCA Model & LCI Entries
        lca = PuroLCAModel(
            id=uuid.uuid4(),
            organization_id=org.id,
            facility_id=fac.id,
            model_name="LCA-DUAL-2025",
            status="ACTIVE",
            crediting_years=10,
        )
        session.add(lca)
        await session.flush()

        lci1 = PuroLCIEntry(
            id=uuid.uuid4(),
            organization_id=org.id,
            lca_model_id=lca.id,
            category="OPERATIONAL_BIOMASS",
            item_name="Biomass Transport",
            quantity=Decimal("100.0"),
            unit="tonne",
            emission_factor=Decimal("0.0185"),
            ef_unit="tCO2e/tonne",
            ef_source="Ecoinvent 3.9",
            ghg_emissions_tco2e=Decimal("1.85"),
        )
        session.add(lci1)

        lci2 = PuroLCIEntry(
            id=uuid.uuid4(),
            organization_id=org.id,
            lca_model_id=lca.id,
            category="OPERATIONAL_PRODUCTION",
            item_name="Electricity",
            quantity=Decimal("1.0"),
            unit="batch",
            emission_factor=Decimal("2.10"),
            ef_unit="tCO2e/batch",
            ef_source="Facility Sub-meter",
            ghg_emissions_tco2e=Decimal("2.10"),
        )
        session.add(lci2)

        # 15. Puro Counterfactual Storage Assessment
        cf = PuroCounterfactualStorageAssessment(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            facility_id=fac.id,
            batch_id=batch.id,
            feedstock_lot_id=lot.id,
            criteria_version="v1.3",
            counterfactual_path="PATH_A_NEGLIGIBLE_STORAGE",
            baseline_fate="OPEN_BURNING",
            evidence_status="VERIFIED",
            evidence_reference="DOC-REF-001",
            counterfactual_carbon_stored_tco2e=Decimal("0.0"),
            assessment_status="COMPLIANT",
            notes="Default field decay baseline",
        )
        session.add(cf)

        await session.commit()

        # Generate JWT Token
        token = AuthenticationService.generate_token_static(user)

        output = {
            "organization_id": str(org.id),
            "project_id": str(proj.id),
            "project_name": proj.name,
            "project_code": proj.project_code,
            "user_id": str(user.id),
            "user_email": user.email,
            "token": token,
            "facility_id": str(fac.id),
            "source_id": str(src.id),
            "lot_id": str(lot.id),
            "batch_id": str(batch.id),
            "batch_number": batch.batch_number,
            "lab_id": str(lab.id),
            "end_use_id": str(eu.id),
            "tag": tag,
        }
        print(json.dumps(output))


async def cleanup_test_environment(org_id_str: str):
    org_id = uuid.UUID(org_id_str)
    async with async_session_factory() as session:
        # Reverse FK deletion
        await session.execute(text("DELETE FROM vm0044_calculation_executions WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM vm0044_calculation_snapshots WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM vm0044_additionality_assessments WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM vm0044_applicability_evaluations WHERE organization_id = :org_id"), {"org_id": org_id})

        await session.execute(text("DELETE FROM puro_calculation_executions WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM puro_counterfactual_storage_assessments WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM puro_lci_entries WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM puro_lca_models WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM puro_end_use_record_links WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM puro_crediting_periods WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM puro_biomass_source_declarations WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM puro_facility_profiles WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM puro_supplier_profiles WHERE organization_id = :org_id"), {"org_id": org_id})

        await session.execute(text("DELETE FROM biochar_end_use_records WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_lab_analyses WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_batches WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_production_runs WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_feedstock_lots WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_feedstock_sources WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_production_facilities WHERE organization_id = :org_id"), {"org_id": org_id})

        await session.execute(text("DELETE FROM projects WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM users WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM organizations WHERE id = :org_id"), {"org_id": org_id})
        await session.commit()
        print(json.dumps({"status": "CLEANED", "organization_id": org_id_str}))


async def verify_puro_db(batch_id_str: str):
    batch_id = uuid.UUID(batch_id_str)
    async with async_session_factory() as session:
        stmt = select(PuroCalculationExecution).where(
            PuroCalculationExecution.batch_id == batch_id,
            PuroCalculationExecution.calculation_mode == "AUTHORITATIVE",
            PuroCalculationExecution.calculation_status == "SUCCESS",
            PuroCalculationExecution.superseded_at.is_(None),
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            print(json.dumps({"verified": False, "error": "No authoritative Puro calculation found."}))
            sys.exit(1)

        print(json.dumps({
            "verified": True,
            "id": str(record.id),
            "batch_id": str(record.batch_id),
            "calculation_mode": record.calculation_mode,
            "calculation_status": record.calculation_status,
            "final_corcs_issuable": str(record.final_corcs_issuable),
            "calculation_hash": record.calculation_hash,
            "durability_class": record.durability_class,
        }))


async def verify_vm0044_db(batch_id_str: str):
    batch_id = uuid.UUID(batch_id_str)
    async with async_session_factory() as session:
        stmt = select(VM0044CalculationExecution).where(
            VM0044CalculationExecution.batch_id == batch_id,
            VM0044CalculationExecution.status.in_(["CALCULATED", "VERIFIED"]),
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            print(json.dumps({"verified": False, "error": "No authoritative VM0044 calculation found."}))
            sys.exit(1)

        print(json.dumps({
            "verified": True,
            "id": str(record.id),
            "batch_id": str(record.batch_id),
            "net_removal_tco2e": str(record.net_removal_tco2e),
            "calculation_hash": record.calculation_hash,
            "status": record.status,
        }))


async def verify_conflict_db(batch_id_str: str):
    batch_id = uuid.UUID(batch_id_str)
    async with async_session_factory() as session:
        stmt_puro = select(PuroCalculationExecution).where(
            PuroCalculationExecution.batch_id == batch_id,
            PuroCalculationExecution.calculation_mode == "AUTHORITATIVE",
            PuroCalculationExecution.calculation_status == "SUCCESS",
            PuroCalculationExecution.superseded_at.is_(None),
        )
        puro_exec = (await session.execute(stmt_puro)).scalar_one_or_none()

        stmt_vm = select(VM0044CalculationExecution).where(
            VM0044CalculationExecution.batch_id == batch_id,
            VM0044CalculationExecution.status.in_(["CALCULATED", "VERIFIED"]),
        )
        vm_exec = (await session.execute(stmt_vm)).scalar_one_or_none()

        puro_count = 1 if puro_exec else 0
        vm_count = 1 if vm_exec else 0
        total_authoritative = puro_count + vm_count

        print(json.dumps({
            "conflict_verified": total_authoritative <= 1,
            "total_authoritative_claims": total_authoritative,
            "puro_claimed": puro_exec is not None,
            "vm0044_claimed": vm_exec is not None,
            "puro_id": str(puro_exec.id) if puro_exec else None,
            "vm0044_id": str(vm_exec.id) if vm_exec else None,
        }))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        asyncio.run(setup_test_environment())
    elif len(sys.argv) > 2 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_environment(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_puro":
        asyncio.run(verify_puro_db(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_vm0044":
        asyncio.run(verify_vm0044_db(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "verify_conflict":
        asyncio.run(verify_conflict_db(sys.argv[2]))
    else:
        print("Usage: python run_dual_pathway_live_helper.py [setup|cleanup <org_id>|verify_puro <batch_id>|verify_vm0044 <batch_id>|verify_conflict <batch_id>]")
        sys.exit(1)
