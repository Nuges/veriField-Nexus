import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.property import Property

async def check():
    async with async_session_factory() as db:
        result = await db.execute(select(Property).order_by(Property.created_at.desc()).limit(1))
        prop = result.scalar_one_or_none()
        if prop:
            print("PROPERTY ID:", prop.id)
            print("PROPERTY NAME:", prop.name)
            print("PROPERTY TYPE:", prop.property_type)
            print("METRICS:", prop.sustainability_metrics)
        else:
            print("No properties found")

if __name__ == "__main__":
    asyncio.run(check())
