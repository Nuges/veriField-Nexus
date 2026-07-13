import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.domains.methodologies.models.base_registry import MethodologyRegistry, MethodologyFamily, Methodology, MethodologyVersion
from datetime import date

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/verifield_nexus_empty"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def inject_metadata():
    async with async_session() as session:
        # 1. Create Registry
        registry = MethodologyRegistry(
            code="PURO",
            name="Puro.earth",
            description="Carbon Removal standard",
            website="https://puro.earth"
        )
        session.add(registry)
        
        # 2. Create Family
        family = MethodologyFamily(
            code="DAC",
            name="Direct Air Capture",
            description="Geological storage of CO2 captured from the atmosphere"
        )
        session.add(family)
        await session.flush()
        
        # 3. Create Methodology
        dac_form_schema = {
            "title": "Direct Air Capture Log",
            "type": "object",
            "properties": {
                "fan_speed": {"type": "number", "title": "Fan Speed (RPM)"},
                "sorbent_saturation": {"type": "number", "title": "Sorbent Saturation (%)"},
                "co2_captured_kg": {"type": "number", "title": "CO2 Captured (kg)"}
            },
            "required": ["fan_speed", "sorbent_saturation", "co2_captured_kg"]
        }
        
        dac_ui_config = {
            "icon": "Wind",
            "color": "indigo",
            "dashboard_widgets": ["co2_captured_kg", "fan_speed"]
        }
        
        methodology = Methodology(
            code="PURO-DAC-01",
            name="Direct Air Capture with Geological Storage",
            description="Quantification of carbon dioxide removal via DAC",
            registry_id=registry.id,
            family_id=family.id,
            is_active=True,
            ui_config=dac_ui_config,
            form_schema=dac_form_schema
        )
        session.add(methodology)
        await session.flush()
        
        # 4. Create Version
        version = MethodologyVersion(
            methodology_id=methodology.id,
            version="1.0.0",
            status="active",
            release_date=date.today()
        )
        session.add(version)
        
        await session.commit()
        print(f"SUCCESS: Injected Methodology {methodology.name} purely via metadata.")
        print(f"UI Config: {methodology.ui_config}")
        print(f"Form Schema dynamically generated fields: {list(methodology.form_schema['properties'].keys())}")

if __name__ == "__main__":
    asyncio.run(inject_metadata())
