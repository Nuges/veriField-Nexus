import asyncio
import httpx
import os
from dotenv import load_dotenv
load_dotenv('backend/.env')

async def check_buckets():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{url}/storage/v1/bucket",
            headers={"Authorization": f"Bearer {key}", "apikey": key}
        )
        print("Buckets:", res.status_code, res.text)
        
        # If activity-photos doesn't exist, create it
        buckets = res.json()
        if isinstance(buckets, list):
            names = [b['name'] for b in buckets]
            if 'activity-photos' not in names:
                print("Creating bucket activity-photos...")
                res2 = await client.post(
                    f"{url}/storage/v1/bucket",
                    headers={"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"},
                    json={"id": "activity-photos", "name": "activity-photos", "public": True}
                )
                print("Create result:", res2.status_code, res2.text)

asyncio.run(check_buckets())
