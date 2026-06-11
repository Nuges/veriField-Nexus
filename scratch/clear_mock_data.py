import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def clear_data():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Real cookstove IDs to keep
    REAL_PROP_ID = "be14e265-71f7-4d5e-8342-9d553dcc8506" # Alao Household Clean Stove
    REAL_ACT_ID = "e2ae56ca-73c6-469b-ac4a-7f45e46c3dd5"  # Alao Household Activity
    
    async with async_session() as session:
        # 1. Fetch properties to delete
        find_props_q = text("""
            SELECT id FROM properties
            WHERE (
                property_type IN ('farming', 'sustainability', 'other', 'AGRICULTURE', 'FORESTRY_LAND_USE', 'TRANSPORT_MOBILITY', 'commercial')
                OR (property_type IN ('cooking', 'cookstove', 'CLEAN_COOKING') AND id != :real_prop_id)
            )
        """)
        res_props = await session.execute(find_props_q, {"real_prop_id": REAL_PROP_ID})
        props_to_delete = [row[0] for row in res_props.all()]
        print(f"Found {len(props_to_delete)} properties to delete.")
        
        # 2. Fetch activities to delete
        find_acts_q = text("""
            SELECT id FROM activities
            WHERE (
                property_id IN (
                    SELECT id FROM properties
                    WHERE (
                        property_type IN ('farming', 'sustainability', 'other', 'AGRICULTURE', 'FORESTRY_LAND_USE', 'TRANSPORT_MOBILITY', 'commercial')
                        OR (property_type IN ('cooking', 'cookstove', 'CLEAN_COOKING') AND id != :real_prop_id)
                    )
                )
                OR (activity_type IN ('cooking', 'cookstove', 'CLEAN_COOKING', 'TRANSPORT_MOBILITY', 'AGRICULTURE', 'FORESTRY_LAND_USE') AND id != :real_act_id)
            )
        """)
        res_acts = await session.execute(find_acts_q, {"real_prop_id": REAL_PROP_ID, "real_act_id": REAL_ACT_ID})
        acts_to_delete = [row[0] for row in res_acts.all()]
        print(f"Found {len(acts_to_delete)} activities to delete.")
        
        if not props_to_delete and not acts_to_delete:
            print("No mock properties or activities found to clear.")
            await engine.dispose()
            return

        # 3. Delete from dependent tables
        # A. carbon_calculations
        if acts_to_delete:
            del_carbon_q = text("DELETE FROM carbon_calculations WHERE activity_id = ANY(:act_ids)")
            res_carbon = await session.execute(del_carbon_q, {"act_ids": acts_to_delete})
            print(f"Deleted {res_carbon.rowcount} carbon calculations.")
            
        # B. anomaly_flags
        if acts_to_delete:
            del_flags_q = text("DELETE FROM anomaly_flags WHERE activity_id = ANY(:act_ids)")
            res_flags = await session.execute(del_flags_q, {"act_ids": acts_to_delete})
            print(f"Deleted {res_flags.rowcount} anomaly flags.")
            
        # C. ndvi_records
        if props_to_delete:
            del_ndvi_q = text("DELETE FROM ndvi_records WHERE asset_id = ANY(:prop_ids)")
            res_ndvi = await session.execute(del_ndvi_q, {"prop_ids": props_to_delete})
            print(f"Deleted {res_ndvi.rowcount} ndvi records.")
            
        # D. audit_tasks
        if props_to_delete:
            del_audits_q = text("DELETE FROM audit_tasks WHERE asset_id = ANY(:prop_ids)")
            res_audits = await session.execute(del_audits_q, {"prop_ids": props_to_delete})
            print(f"Deleted {res_audits.rowcount} audit tasks.")
            
        # E. community_validations
        if props_to_delete:
            del_validations_q = text("DELETE FROM community_validations WHERE asset_id = ANY(:prop_ids)")
            res_validations = await session.execute(del_validations_q, {"prop_ids": props_to_delete})
            print(f"Deleted {res_validations.rowcount} community validations.")
            
        # 4. Delete from activities
        if acts_to_delete:
            del_acts_q = text("DELETE FROM activities WHERE id = ANY(:act_ids)")
            res_acts_del = await session.execute(del_acts_q, {"act_ids": acts_to_delete})
            print(f"Deleted {res_acts_del.rowcount} activities.")
            
        # 5. Delete from properties
        if props_to_delete:
            del_props_q = text("DELETE FROM properties WHERE id = ANY(:prop_ids)")
            res_props_del = await session.execute(del_props_q, {"prop_ids": props_to_delete})
            print(f"Deleted {res_props_del.rowcount} properties.")

        await session.commit()
        print("Successfully committed deletions.")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(clear_data())
