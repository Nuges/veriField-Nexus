import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.carbon_calculation import CarbonCalculation
from sqlalchemy import select

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres")
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as db:
        res = await db.execute(select(CarbonCalculation))
        calcs = res.scalars().all()
        print(f"Total calculations scanned: {len(calcs)}")
        string_records = 0
        dict_records = 0
        null_records = 0
        for c in calcs:
            if c.calculation_log is None:
                null_records += 1
            elif isinstance(c.calculation_log, str):
                string_records += 1
                print(f"String record found! ID: {c.id}")
            elif isinstance(c.calculation_log, dict):
                dict_records += 1
        print(f"Summary: dict={dict_records}, string={string_records}, null={null_records}")

asyncio.run(main())
