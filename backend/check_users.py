import asyncio
from app.db.session import async_session_factory
from sqlalchemy import text
from app.core.security import verify_password

async def test():
    async with async_session_factory() as session:
        res = await session.execute(text("SELECT password_hash FROM users WHERE email = 'segunoluwole22@gmail.com'"))
        h = res.scalar()
        print('Hash:', h)
        print('Verifies?', verify_password('Lovelyday1', h))

asyncio.run(test())
