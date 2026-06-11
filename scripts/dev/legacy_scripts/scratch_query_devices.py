import asyncio
import os
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv

load_dotenv('backend/.env')
from app.models.sensor_reading import SensorReading
from app.models.property import Property
from app.models.user import User

async def main():
    db_url = os.getenv('DATABASE_URL')
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
    engine = create_async_engine(os.getenv('DATABASE_URL').replace("postgres://", "postgresql+asyncpg://"))
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with SessionLocal() as db:
        # Check user
        res_user = await db.execute(select(User).where(User.email == 'segunoluwole22@gmail.com'))
        user = res_user.scalar_one_or_none()
        print(f"User: {user.email if user else None}, Role: {user.role if user else None}")
        
        # Aggregate query
        agg_query = (
            select(
                SensorReading.device_id,
                SensorReading.asset_id,
                func.count(SensorReading.id).label("reading_count"),
                func.max(SensorReading.timestamp).label("last_reading"),
                func.sum(case((SensorReading.usage_flag == True, 1), else_=0)).label("usage_true_count"),
            )
            .group_by(SensorReading.device_id, SensorReading.asset_id)
        )
        
        # Test query without filter
        result = await db.execute(agg_query)
        rows = result.all()
        print(f"Total aggregated devices without filter: {len(rows)}")
        for r in rows:
            print(dict(r._mapping))
            
        # Test query with filter (if user.role != admin)
        ownership_filter = []
        if user and user.role != "admin":
            ownership_filter.append(
                SensorReading.asset_id.in_(
                    select(Property.id).where(Property.owner_id == user.id)
                )
            )
        
        filtered_query = agg_query
        if ownership_filter:
            filtered_query = agg_query.where(and_(*ownership_filter))
            
        res_filtered = await db.execute(filtered_query)
        rows_filtered = res_filtered.all()
        print(f"Total aggregated devices WITH filter: {len(rows_filtered)}")
        for r in rows_filtered:
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(main())
