import asyncio
import json
from sqlalchemy import select
from app.db.session import async_session_factory
from app.domains.jurisdictions.models import Jurisdiction
from app.domains.jurisdictions.service import GovernanceMetadataResolver
import app.models  # Required for SQLAlchemy relationships

async def seed_blue_carbon():
    async with async_session_factory() as db:
        print("Seeding Blue Carbon Methodology for Nigeria...")
        
        # We assume Nigeria jurisdiction exists (code="NG")
        stmt = select(Jurisdiction).where(Jurisdiction.code == "NG")
        res = await db.execute(stmt)
        nigeria = res.scalar_one_or_none()
        
        if not nigeria:
            print("Nigeria jurisdiction not found. Run seed_jurisdictions.py first.")
            return
            
        # Add methodology metadata
        metadata = nigeria.metadata_context
        if "methodologies" not in metadata:
            metadata["methodologies"] = {}
            
        metadata["methodologies"]["blue_carbon_v1"] = {
            "name": "Mangrove Restoration (Blue Carbon)",
            "standard": "Verra VM0033",
            "local_parameters": {
                "mangrove_biomass_factor": 25.5,  # tC/ha
                "soil_carbon_density": 150.0,     # tC/ha
                "local_agency_approval": "NIMASA"
            }
        }
        
        nigeria.metadata_context = metadata
        await db.commit()
        
        print("Successfully seeded Blue Carbon methodology in Nigeria jurisdiction.")
        
        # Resolve to verify
        resolver = GovernanceMetadataResolver(db)
        resolved_context = await resolver.resolve_context(nigeria.id)
        resolved = resolved_context["metadata"]
        print("\nResolved Metadata:")
        print(json.dumps(resolved.get("methodologies", {}).get("blue_carbon_v1"), indent=2))
        
        print("\n✅ Blue Carbon Methodology Seeded!")

if __name__ == "__main__":
    asyncio.run(seed_blue_carbon())
