import asyncio
import sys
import os

sys.path.append(os.path.abspath("."))

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.activity import Activity

async def main():
    print("Connecting to DB to check activity data keys...")
    async with async_session_factory() as session:
        # Get the activity by ID
        result = await session.execute(
            select(Activity).where(Activity.id == "2e02843d-3e13-4967-a3be-a1a79dbe00db")
        )
        activity = result.scalar_one_or_none()
        if not activity:
            print("Activity not found!")
            # Let's search for any HYBRID_ENERGY activity
            result = await session.execute(
                select(Activity).where(Activity.activity_type == "HYBRID_ENERGY")
            )
            activity = result.scalars().first()
            if not activity:
                print("No HYBRID_ENERGY activity found at all.")
                return

        print(f"Found Activity: {activity.id}, Type: {activity.activity_type}")
        print("activity_data keys:")
        if activity.activity_data:
            for k, v in activity.activity_data.items():
                print(f"  - {k} (type: {type(v).__name__})")
        else:
            print("  - activity_data is empty or None")

if __name__ == "__main__":
    asyncio.run(main())
