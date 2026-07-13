import asyncio
import json
from sqlalchemy import select
from app.db.session import async_session_factory
from app.domains.jurisdictions.models import Jurisdiction, JurisdictionLevel
import app.models  # Required for SQLAlchemy relationships

SEED_JURISDICTIONS = [
    {
        "name": "Global",
        "code": "GLB",
        "level": JurisdictionLevel.GLOBAL,
        "metadata_context": {
            "default_standards": ["Gold Standard", "Verra"],
            "currency": "USD"
        }
    },
    {
        "name": "Africa",
        "code": "AFR",
        "level": JurisdictionLevel.CONTINENTAL,
        "parent_code": "GLB",
        "metadata_context": {
            "regional_framework": "African Carbon Markets Initiative (ACMI)"
        }
    },
    {
        "name": "Nigeria",
        "code": "NG",
        "level": JurisdictionLevel.NATIONAL,
        "parent_code": "AFR",
        "metadata_context": {
            "national_registry": "Nigeria Climate Change Council (NCCC)",
            "ndc_target": "20% unconditional reduction by 2030",
            "compliance_requirements": ["Article 6.2 eligibility"]
        }
    },
    {
        "name": "Lagos State",
        "code": "NG-LA",
        "level": JurisdictionLevel.STATE,
        "parent_code": "NG",
        "metadata_context": {
            "state_agency": "LASEPA"
        }
    },
    {
        "name": "Kenya",
        "code": "KE",
        "level": JurisdictionLevel.NATIONAL,
        "parent_code": "AFR",
        "metadata_context": {
            "national_registry": "Kenya Carbon Registry",
            "climate_act": "Climate Change Act 2016"
        }
    },
    {
        "name": "Acme Corp (Corporate)",
        "code": "CORP-ACME",
        "level": JurisdictionLevel.CORPORATE_GOVERNANCE,
        "metadata_context": {
            "reporting_standard": "SBTi",
            "target_year": 2040
        }
    },
    {
        "name": "World Bank (MDB)",
        "code": "MDB-WB",
        "level": JurisdictionLevel.CUSTOM,
        "metadata_context": {
            "fund": "Carbon Initiative for Development (Ci-Dev)"
        }
    }
]

async def seed_jurisdictions():
    async with async_session_factory() as db:
        print("Seeding diverse governance jurisdictions...")
        
        j_map = {}
        
        # Insert or update
        for j_data in SEED_JURISDICTIONS:
            # Check if exists
            stmt = select(Jurisdiction).where(Jurisdiction.code == j_data["code"])
            res = await db.execute(stmt)
            jur = res.scalar_one_or_none()
            
            if not jur:
                jur = Jurisdiction(
                    name=j_data["name"],
                    code=j_data["code"],
                    level=j_data["level"],
                    metadata_context=j_data["metadata_context"]
                )
                db.add(jur)
                print(f"Created jurisdiction: {jur.name}")
            else:
                jur.name = j_data["name"]
                jur.level = j_data["level"]
                jur.metadata_context = j_data["metadata_context"]
                print(f"Updated jurisdiction: {jur.name}")
                
            j_map[jur.code] = jur
            
        await db.commit()
        
        # Second pass for parent hierarchy
        for j_data in SEED_JURISDICTIONS:
            parent_code = j_data.get("parent_code")
            if parent_code and parent_code in j_map:
                child = j_map[j_data["code"]]
                parent = j_map[parent_code]
                child.parent_id = parent.id
                print(f"Linked {child.name} -> {parent.name}")
                
        await db.commit()
        print("Seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_jurisdictions())
