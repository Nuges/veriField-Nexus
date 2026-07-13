import asyncio
import os
import sys
from datetime import date

# Ensure backend path is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(backend_path)

from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.domains.methodologies.models import MethodologyFamily, MethodologyRegistry, Methodology, MethodologyVersion
from sqlalchemy import select

from app.domains.methodologies.metadata.seed_phase_1 import seed_data

async def validate_empty_db():
    print("🚀 Starting Empty Database Validation (Phase F & G)")
    db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/verifield_nexus_empty"
    
    engine = create_async_engine(db_url)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_factory() as db:
        print("Running seed_data()...")
        await seed_data(db)
        
        # Phase F: Verify seed metadata
        print("Checking seeded methodologies...")
        result = await db.execute(select(Methodology))
        methodologies = result.scalars().all()
        if not methodologies:
            print("❌ FAILED: No methodologies found. Seed failed or database is empty.")
            return False
            
        print(f"✅ Found {len(methodologies)} seeded methodologies.")

        # Phase G: Add a completely new methodology (Direct Air Capture)
        print("Adding Direct Air Capture methodology dynamically...")
        try:
            # Check for existing
            res = await db.execute(select(MethodologyRegistry).filter_by(code="VERRA"))
            verra = res.scalars().first()
            if not verra:
                verra = MethodologyRegistry(name="Verra", code="VERRA")
                db.add(verra)
                await db.flush()

            res = await db.execute(select(MethodologyFamily).filter_by(name="Engineered Removals"))
            family = res.scalars().first()
            if not family:
                family = MethodologyFamily(name="Engineered Removals", code="ENG_REM")
                db.add(family)
                await db.flush()

            dac_meth = Methodology(
                name="Direct Air Capture with Storage",
                code="VM0049",
                family_id=family.id,
                registry_id=verra.id
            )
            db.add(dac_meth)
            await db.flush()

            dac_version = MethodologyVersion(
                methodology_id=dac_meth.id,
                version="1.0",
                status="active",
                release_date=date.today()
            )
            db.add(dac_version)
            await db.commit()
            print("✅ Successfully provisioned Direct Air Capture without code changes!")
            
        except Exception as e:
            print(f"❌ FAILED: Could not dynamically provision DAC methodology. Error: {e}")
            return False

    print("🎉 Empty Database and Runtime Validation PASSED.")
    return True

if __name__ == "__main__":
    asyncio.run(validate_empty_db())
