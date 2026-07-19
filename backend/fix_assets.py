import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.db.session import async_session_factory
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        # Get all activities that have an asset_id
        res = await session.execute(select(Activity).where(Activity.asset_id.isnot(None)))
        activities = res.scalars().all()
        
        for activity in activities:
            # Get the asset
            asset = await session.get(Asset, activity.asset_id)
            if asset:
                data = activity.activity_data or {}
                
                # Update name if it looks like mock
                if asset.name.startswith("Asset from Activity"):
                    asset_ident = data.get("stove_id") or data.get("serial_number") or data.get("head_name")
                    if asset_ident:
                        asset.name = f"{activity.activity_type.replace('_', ' ').title()} - {asset_ident}"
                
                # Update attributes
                new_attrs = dict(asset.attributes or {})
                for k, v in data.items():
                    if k not in new_attrs:
                        new_attrs[k] = v
                
                # Try to find carbon calculation for this activity
                calc_res = await session.execute(text(f"SELECT tco2e_generated FROM carbon_calculations WHERE activity_id = '{activity.id}'"))
                calc = calc_res.fetchone()
                if calc:
                    new_attrs["carbon_offset_kg"] = calc[0]
                
                asset.attributes = new_attrs
                session.add(asset)
                print(f"Updated asset {asset.id}: {asset.name}")
        
        await session.commit()

asyncio.run(main())
