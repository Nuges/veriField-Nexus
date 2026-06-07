import asyncio
import jwt
from datetime import datetime, timedelta, timezone
import httpx
import sys
import os
from dotenv import load_dotenv

# Load backend environment variables
load_dotenv('backend/.env')

# Add backend to path so we can import settings
sys.path.append(os.path.abspath('backend'))
from app.core.config import settings

async def main():
    # Generate admin token
    payload = {
        "sub": "192a5308-6e3c-404c-a644-c021a9e7884c",
        "email": "segunoluwole22@gmail.com",
        "dev_mode": True,
        # datetime.now(timezone.utc) is safe and modern
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Query with human-readable site_id
        site_id = "VF-EN-LAG-1001"
        res1 = await client.get(
            f"http://127.0.0.1:8000/api/v1/energy/telemetry/{site_id}",
            headers=headers
        )
        print("=== Test 1: Human-readable site_id (VF-EN-LAG-1001) ===")
        print(f"Status Code: {res1.status_code}")
        data1 = res1.json()
        print(f"Response keys: {list(data1.keys()) if isinstance(data1, dict) else type(data1)}")
        if isinstance(data1, dict) and "readings" in data1:
            print(f"Readings count: {len(data1['readings'])}")
            print(f"Uptime list: {data1.get('uptime')}")
            print(f"Daily generation list: {data1.get('daily_generation_kwh')}")
        else:
            print(f"Response: {data1}")
            
        print("\n" + "="*50 + "\n")
        
        # Test 2: Query with UUID (activity ID)
        activity_uuid = "2e02843d-3e13-4967-a3be-a1a79dbe00db"
        res2 = await client.get(
            f"http://127.0.0.1:8000/api/v1/energy/telemetry/{activity_uuid}",
            headers=headers
        )
        print("=== Test 2: Activity UUID (2e02843d-3e13-4967-a3be-a1a79dbe00db) ===")
        print(f"Status Code: {res2.status_code}")
        data2 = res2.json()
        print(f"Response keys: {list(data2.keys()) if isinstance(data2, dict) else type(data2)}")
        if isinstance(data2, dict) and "readings" in data2:
            print(f"Readings count: {len(data2['readings'])}")
        else:
            print(f"Response: {data2}")
            
        print("\n" + "="*50 + "\n")
        
        # Test 3: Query with non-existent site_id (should NOT be 404, should be custom empty response)
        fake_site = "VF-EN-FAKE-9999"
        res3 = await client.get(
            f"http://127.0.0.1:8000/api/v1/energy/telemetry/{fake_site}",
            headers=headers
        )
        print("=== Test 3: Non-existent site_id (VF-EN-FAKE-9999) ===")
        print(f"Status Code: {res3.status_code}")
        print(f"Response: {res3.json()}")

if __name__ == "__main__":
    asyncio.run(main())
