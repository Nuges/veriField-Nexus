import asyncio
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session_factory
from app.domains.methodologies.models.base_registry import Methodology, MethodologyRegistry, MethodologyFamily, MethodologyVersion
from app.domains.methodologies.models.components import CalculationRule, VersionCalculationRule
from app.models.activity import Activity
from app.services.quantification_engine import QuantificationEngine
from app.core.event_bus import EventBus

async def run_dac_validation():
    print("Starting Stream 3 Data Schema & Integrity Validation (DAC)...")
    
    async with async_session_factory() as db:
        # 1. Ensure Registry and Family exist
        result = await db.execute(select(MethodologyRegistry).where(MethodologyRegistry.code == "SYS_DEFAULT"))
        reg = result.scalars().first()
        if not reg:
            reg = MethodologyRegistry(code="SYS_DEFAULT", name="System Default Registry")
            db.add(reg)
            
        result = await db.execute(select(MethodologyFamily).where(MethodologyFamily.code == "SYS_DEFAULT"))
        fam = result.scalars().first()
        if not fam:
            fam = MethodologyFamily(code="SYS_DEFAULT", name="System Default Family")
            db.add(fam)
            
        await db.flush()

        # 2. Provision DAC Methodology (No hardcoding)
        meth_code = "DAC_V1"
        result = await db.execute(select(Methodology).where(Methodology.code == meth_code))
        meth = result.scalars().first()
        if not meth:
            meth = Methodology(
                code=meth_code,
                name="Direct Air Capture (DAC)",
                description="Dynamic test for DAC telemetry",
                registry_id=reg.id,
                family_id=fam.id,
                is_active=True
            )
            db.add(meth)
            await db.flush()

        from datetime import datetime
        # 3. Provision Methodology Version
        result = await db.execute(select(MethodologyVersion).where(MethodologyVersion.methodology_id == meth.id))
        version = result.scalars().first()
        if not version:
            version = MethodologyVersion(
                methodology_id=meth.id,
                version="1.0.0",
                status="active",
                release_date=datetime.now().date()
            )
            db.add(version)
            await db.flush()

        # 4. Provision Calculation Rule for DAC
        # Base rule: credit = co2_extracted_tons * 1.0
        result = await db.execute(select(CalculationRule).where(CalculationRule.code == "DAC_BASE_CREDIT"))
        rule = result.scalars().first()
        if not rule:
            rule = CalculationRule(
                code="DAC_BASE_CREDIT",
                name="DAC Base Credit Calculation",
                formula="co2_extracted_tons * 1.0"
            )
            db.add(rule)
            await db.flush()

        # Link rule to version
        result = await db.execute(select(VersionCalculationRule).where(VersionCalculationRule.version_id == version.id))
        link = result.scalars().first()
        if not link:
            link = VersionCalculationRule(
                version_id=version.id,
                rule_id=rule.id,
                execution_order=1
            )
            db.add(link)
            await db.flush()

        # 5. Create Organization, User, Project, Activity
        from app.models.organization import Organization
        from app.models.user import User
        from app.models.project import Project

        org = Organization(name="DAC Validation Org")
        db.add(org)
        await db.flush()

        user = User(
            email="dac_user@org.com",
            full_name="DAC User",
            password_hash="mock",
            organization_id=org.id
        )
        db.add(user)
        await db.flush()

        project = Project(
            name="DAC Test Project",
            methodology_id=meth.id,
            organization_id=org.id
        )
        db.add(project)
        await db.flush()

        telemetry_payload = {"co2_extracted_tons": 5.5, "fan_speed": 1200}
        
        from datetime import datetime, timezone
        act = Activity(
            activity_type=meth.code,
            organization_id=org.id,
            user_id=user.id,
            property_id=None,
            asset_id=None,
            activity_data=telemetry_payload,
            status="verified",
            captured_at=datetime.now(timezone.utc)
        )
        db.add(act)
        await db.flush()

        print(f"Provisioned DAC Methodology, Rule, and Activity {act.id}")

        # 6. Push to Event Bus
        print("Publishing telemetry event to EventBus...")
        msg_id = await EventBus.publish("nexus_telemetry_stream", "TELEMETRY_INGESTED", {
            "activity_id": str(act.id),
            "project_id": str(project.id),
            "methodology": meth.code,
            "payload": telemetry_payload
        })
        print(f"Event published with ID: {msg_id}")

        # 7. Execute Quantification Engine Dynamically
        print("Executing Quantification Engine...")
        engine = QuantificationEngine(db)
        calc_result = await engine.quantify_activity(act.id, project_id=project.id)
        
        await db.commit()

        print(f"Quantification Result: {calc_result.tco2e_generated} tCO2e")
        if calc_result:
            if float(calc_result.tco2e_generated) == 5.5:
                print("VALIDATION SUCCESS: DAC telemetry quantified successfully via metadata engine!")
                return True
            else:
                print(f"VALIDATION FAILED: Expected 5.5 credits, got {calc_result.tco2e_generated}")
                return False
        else:
            print("VALIDATION FAILED: No calculation result returned or calculation engine failed to process dynamically.")
            return False

if __name__ == "__main__":
    asyncio.run(run_dac_validation())
