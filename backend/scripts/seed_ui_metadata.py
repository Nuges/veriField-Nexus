import asyncio
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import async_session_factory
from app.domains.methodologies.models.base_registry import Methodology, MethodologyRegistry, MethodologyFamily

async def seed():
    with open("../dashboard/module_registry.json", "r") as f:
        registry_data = json.load(f)
        
    async with async_session_factory() as db:
        # Ensure we have a default registry and family
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
        
        for key, config in registry_data.items():
            result = await db.execute(select(Methodology).where(Methodology.code == key))
            meth = result.scalars().first()
            if not meth:
                meth = Methodology(
                    code=key,
                    name=config.get("name", key),
                    description=config.get("badge", ""),
                    registry_id=reg.id,
                    family_id=fam.id
                )
                db.add(meth)
            
            # Map ui config excluding standard fields
            ui_config = {
                "badge": config.get("badge"),
                "themeColor": config.get("themeColor"),
                "markerColor": config.get("markerColor"),
                "allowedRoles": config.get("allowedRoles"),
                "labels": config.get("labels"),
                "kpis": config.get("kpis"),
                "charts": config.get("charts"),
                "tableColumns": config.get("tableColumns"),
                "filterOptions": config.get("filterOptions")
            }
            
            meth.ui_config = ui_config
            meth.form_schema = config.get("formSchema", {})
            meth.is_active = True
            
        await db.commit()
        print("UI Metadata seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
