"""
VeriField Nexus — Verra VM0044 v1.2 Live Full-Stack Helper
Creates synthetic database records and queries real PostgreSQL 18 for persistence proof.
"""

import sys
import os
import json
import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, date

from sqlalchemy import select, text
from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.biochar.models import (
    ProductionFacility,
    FeedstockSource,
    FeedstockLot,
    BiocharBatch,
    BiocharLabAnalysis,
    BiocharEndUseRecord,
)
from app.domains.biochar.vm0044_models import (
    VM0044MethodologyVersion,
    VM0044RuleDefinition,
    VM0044NormativeDependency,
    VM0044ApplicabilityEvaluation,
    VM0044AdditionalityAssessment,
    VM0044CalculationSnapshot,
    VM0044CalculationExecution,
)
from app.domains.biochar.vm0044_rules import seed_vm0044_normative_metadata
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash


async def setup_test_environment():
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        # 1. Seed normative metadata
        await seed_vm0044_normative_metadata(session)

        # 2. Organization & User
        org = Organization(
            id=uuid.uuid4(),
            name=f"VM0044 Live Verification Org {tag}",
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

        user = User(
            id=uuid.uuid4(),
            email=f"pm.{tag}@vm0044-live.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Verra Project Lead",
            role="ORG_ADMIN",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add(user)
        await session.flush()

        # 3. Project
        proj = Project(
            id=uuid.uuid4(),
            name=f"VM0044 Live Biochar Project {tag}",
            project_code=f"VM44-{tag[:6].upper()}",
            organization_id=org.id,
            country="Kenya",
        )
        session.add(proj)
        await session.flush()

        # 4. Greenfield Production Facility
        fac = ProductionFacility(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            facility_code=f"FAC-VM44-{tag[:6]}",
            facility_name="Nairobi Green Pyrolysis Facility",
            facility_status="NEW_OPERATIONAL",
            technology_type="HIGH_TEMPERATURE_PYROLYSIS",
        )
        session.add(fac)
        await session.flush()

        # 5. Feedstock Source & Lot
        src = FeedstockSource(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            source_code=f"SRC-COFFEE-{tag[:6]}",
            source_name="Kiambu Coffee Husk Residue",
            source_type="AGRICULTURAL_RESIDUE",
            biomass_type="COFFEE_HUSK",
            origin_location="Kiambu, Kenya",
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
            lot_number=f"LOT-HUSK-{tag[:6]}",
            feedstock_type="AGRICULTURAL_RESIDUE",
            mass_received_tonnes=Decimal("100.0"),
            moisture_content_pct=Decimal("12.0"),
            dry_mass_tonnes=Decimal("88.0"),
        )
        session.add(lot)
        await session.flush()

        # 6. Biochar Batch
        batch = BiocharBatch(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            batch_number=f"BATCH-VM44-{tag[:6].upper()}",
            facility_name="Nairobi Green Pyrolysis Facility",
            kiln_id="KILN-HT-01",
            feedstock_type="AGRICULTURAL_RESIDUE",
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
            status="ACTIVE",
        )
        session.add(batch)
        await session.flush()

        # 7. Lab Analysis
        lab = BiocharLabAnalysis(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            batch_id=batch.id,
            sample_id=f"SMP-VM44-{tag[:6]}",
            sampling_date=now,
            laboratory_name="Kenya Bureau of Standards Testing Laboratory",
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

        # 8. End Use Record (Soil Application outside wetlands)
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
        await session.commit()

        # 9. Generate JWT Token
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
        # Clean up in reverse foreign-key order
        await session.execute(text("DELETE FROM vm0044_calculation_executions WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM vm0044_calculation_snapshots WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM vm0044_additionality_assessments WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM vm0044_applicability_evaluations WHERE organization_id = :org_id"), {"org_id": org_id})

        await session.execute(text("DELETE FROM biochar_end_use_records WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_lab_analyses WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_batches WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_feedstock_lots WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_feedstock_sources WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM biochar_production_facilities WHERE organization_id = :org_id"), {"org_id": org_id})

        await session.execute(text("DELETE FROM projects WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM users WHERE organization_id = :org_id"), {"org_id": org_id})
        await session.execute(text("DELETE FROM organizations WHERE id = :org_id"), {"org_id": org_id})
        await session.commit()
        print(json.dumps({"status": "CLEANED", "organization_id": org_id_str}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        asyncio.run(setup_test_environment())
    elif len(sys.argv) > 2 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_environment(sys.argv[2]))
    else:
        print("Usage: python run_vm0044_live_helper.py [setup|cleanup <org_id>]")
        sys.exit(1)
