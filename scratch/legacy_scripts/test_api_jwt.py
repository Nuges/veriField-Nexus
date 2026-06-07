import asyncio
import jwt
from datetime import datetime, timedelta
from app.core.config import settings
import httpx

async def main():
    payload = {
        "sub": "192a5308-6e3c-404c-a644-c021a9e7884c",
        "email": "segunoluwole22@gmail.com",
        "dev_mode": True,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "http://127.0.0.1:8000/api/v1/activities",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = res.json()
        print(f"Status Code: {res.status_code}")
        if "total" in data:
            print(f"Total from API: {data['total']}")
        else:
            print(f"Response: {data}")

asyncio.run(main())
