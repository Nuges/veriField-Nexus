import asyncio
import json
from sqlalchemy import select
from app.db.session import async_session_factory
from app.domains.jurisdictions.models import Jurisdiction
from app.domains.jurisdictions.service import GovernanceMetadataResolver
import app.models  # Required for SQLAlchemy relationships

async def test_inheritance():
    async with async_session_factory() as db:
        print("Testing Jurisdiction Metadata Inheritance...")
        resolver = GovernanceMetadataResolver(db)
        
        # Test Lagos State
        stmt = select(Jurisdiction).where(Jurisdiction.code == "NG-LA")
        res = await db.execute(stmt)
        lagos = res.scalar_one_or_none()
        
        if not lagos:
            print("Lagos jurisdiction not found. Did you run the seed script?")
            return
            
        metadata_context = await resolver.resolve_context(lagos.id)
        metadata = metadata_context["metadata"]
        
        print(f"\nResolved Metadata for {lagos.name}:")
        print(json.dumps(metadata, indent=2))
        
        # Verify inheritance
        assert "state_agency" in metadata, "Missing local metadata"
        assert "national_registry" in metadata, "Missing inherited national metadata"
        assert "regional_framework" in metadata, "Missing inherited regional metadata"
        assert "default_standards" in metadata, "Missing inherited global metadata"
        
        print("\n✅ Inheritance validation passed!")

if __name__ == "__main__":
    asyncio.run(test_inheritance())
