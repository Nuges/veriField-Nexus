import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User
from app.schemas.user import UserResponse

async def main():
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            print("Successfully fetched user:", user.email if user else None)
            
            # This is what auth.py does
            resp = UserResponse.model_validate(user)
            print("Successfully validated UserResponse!")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
