import asyncio
import sys
import uuid
import json

from app.db.session import async_session_factory
from app.domains.activities.models import Activity
from sqlalchemy import select
from app.core.events.dispatcher import _handle_activity_created
from app.core.events.base import BaseEvent

async def main():
    async with async_session_factory() as db:
        # Find all verified activities without an asset
        stmt = select(Activity).where(Activity.status == "verified", Activity.asset_id == None)
        result = await db.execute(stmt)
        activities = result.scalars().all()
        
        print(f"Found {len(activities)} verified activities missing assets.")
        
        for activity in activities:
            print(f"Processing activity {activity.id}...")
            
            # Recreate the event payload
            payload_data = {
                "activity_id": str(activity.id),
                "organization_id": str(activity.organization_id),
                "activity_type": activity.activity_type,
                "captured_at": activity.captured_at.isoformat() if activity.captured_at else None,
                "latitude": activity.latitude,
                "longitude": activity.longitude,
                "image_url": activity.image_url,
                "image_hash": activity.image_hash,
                "client_id": activity.client_id,
                "data": activity.activity_data,
            }
            
            event = BaseEvent(
                event_type="activity.created",
                organization_id=str(activity.organization_id),
                payload=payload_data,
            )
            
            # Manually invoke the handler
            await _handle_activity_created(event)
            print(f"Successfully reprocessed activity {activity.id}.")

if __name__ == "__main__":
    asyncio.run(main())
