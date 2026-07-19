import asyncio
from app.db.session import async_session_factory
from app.domains.projects.models import CarbonCalculation, Project
from sqlalchemy import select, func

async def test_ledger():
    async with async_session_factory() as db:
        print("Executing ledger query...")
        stmt = select(CarbonCalculation, Project).outerjoin(Project, CarbonCalculation.project_id == Project.id).order_by(CarbonCalculation.created_at.desc())
        res = await db.execute(stmt)
        for calc, proj in res.all():
            print(calc.id, proj.name if proj else None)
        print("Done!")

asyncio.run(test_ledger())
