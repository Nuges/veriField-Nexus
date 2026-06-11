import asyncio
import asyncpg
import os
import json
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    db_url = os.getenv('DATABASE_URL')
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(db_url)
    print("=== Connected to DB ===")
    
    # 1. Fetch properties of type cooking, cookstove, or CLEAN_COOKING
    props = await conn.fetch("""
        SELECT id, name, property_type 
        FROM properties 
        WHERE property_type IN ('cooking', 'cookstove', 'CLEAN_COOKING');
    """)
    print(f"Found {len(props)} Clean Cooking properties/assets.")
    
    if len(props) == 0:
        print("No Clean Cooking properties found. Exiting.")
        await conn.close()
        return

    # Clear existing sensor readings to ensure clean slate
    await conn.execute("DELETE FROM sensor_readings;")
    print("Cleaned existing sensor readings.")

    # 2. Seed Sensor Readings
    # We will generate readings for the last 7 days (hourly) for each property
    now = datetime.now(timezone.utc)
    readings_to_insert = []
    
    for p in props:
        prop_id = p['id']
        device_id = f"ESP32-CS-{str(prop_id)[:4].upper()}"
        
        print(f"Generating readings for asset '{p['name']}' ({prop_id}) with device {device_id}...")
        
        # 7 days of hourly readings = 168 readings
        for hour_offset in range(168):
            timestamp = now - timedelta(hours=hour_offset)
            hour = timestamp.hour
            
            # Simulate daily cooking pattern: breakfast (7-9), lunch (12-14), dinner (18-20)
            is_cooking_hour = (7 <= hour <= 8) or (12 <= hour <= 13) or (18 <= hour <= 19)
            
            if is_cooking_hour:
                # 85% probability of cooking actually happening in this window
                is_active = random.random() < 0.85
            else:
                # 5% probability of a random tea/snack cooking outside main hours
                is_active = random.random() < 0.05
            
            if is_active:
                temperature = random.uniform(85.0, 145.0)
                usage_flag = True
                fuel_weight_kg = random.uniform(1.2, 4.5)
            else:
                temperature = random.uniform(22.0, 28.0)
                usage_flag = False
                fuel_weight_kg = 0.0
                
            battery_voltage = random.uniform(3.6, 4.1) # Realistic lithium ion range
            
            readings_to_insert.append((
                prop_id, device_id, temperature, usage_flag, fuel_weight_kg, battery_voltage, timestamp
            ))

    # Insert sensor readings
    await conn.executemany("""
        INSERT INTO sensor_readings (asset_id, device_id, temperature, usage_flag, fuel_weight_kg, battery_voltage, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7);
    """, readings_to_insert)
    print(f"Successfully inserted {len(readings_to_insert)} sensor readings.")

    # 3. Update Activities Data to include utilization_rate and usage_hours
    activities = await conn.fetch("""
        SELECT id, activity_data 
        FROM activities 
        WHERE activity_type IN ('cooking', 'CLEAN_COOKING');
    """)
    print(f"Found {len(activities)} Clean Cooking activities to update.")
    
    updated_count = 0
    for act in activities:
        act_id = act['id']
        raw_data = act['activity_data']
        
        # Robustly parse JSONB
        data = {}
        if raw_data is not None:
            if isinstance(raw_data, str):
                try:
                    data = json.loads(raw_data)
                except Exception:
                    pass
            elif isinstance(raw_data, dict):
                data = dict(raw_data)
            else:
                try:
                    data = dict(raw_data)
                except Exception:
                    try:
                        data = json.loads(str(raw_data))
                    except Exception:
                        pass
        
        if not isinstance(data, dict):
            data = {}
            
        # Add utilization metrics
        data['utilization_rate'] = round(random.uniform(70.0, 95.0), 1)
        data['usage_hours'] = round(random.uniform(2.5, 5.5), 1)
        data['biomass_displaced_kg'] = round(random.uniform(8.0, 20.0), 1)
        data['fuel_saved'] = round(random.uniform(10.0, 25.0), 1)
        
        # Update record
        await conn.execute("""
            UPDATE activities 
            SET activity_data = $1 
            WHERE id = $2;
        """, json.dumps(data), act_id)
        updated_count += 1
        
    print(f"Successfully updated {updated_count} activities with utilization_rate and usage_hours.")
    await conn.close()
    print("=== Database Seeding Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
