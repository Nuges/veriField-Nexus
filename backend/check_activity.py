import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.activity import Activity

async def check():
    async with async_session_factory() as db:
        result = await db.execute(select(Activity).order_by(Activity.created_at.desc()).limit(1))
        activity = result.scalar_one_or_none()
        if activity:
            print("ACTIVITY ID:", activity.id)
            print("ACTIVITY TYPE:", activity.activity_type)
            print("IMAGE URL:", activity.image_url)
            print("ACTIVITY DATA:", activity.activity_data)
            print("STATUS:", activity.status)
        else:
            print("No activities found")

if __name__ == "__main__":
    asyncio.run(check())
