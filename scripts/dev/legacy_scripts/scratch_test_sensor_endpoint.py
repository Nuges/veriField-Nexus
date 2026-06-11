import asyncio
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv('backend/.env')
# Set dev mode to true so it uses dev authentication / local token
os.environ["DEV_MODE"] = "true"

from app.main import app
from app.core.security import get_current_user
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async def test_endpoint():
    engine = create_async_engine(os.getenv('DATABASE_URL').replace("postgres://", "postgresql+asyncpg://"))
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with SessionLocal() as db:
        # Get the admin user
        result = await db.execute(select(User).where(User.email == 'segunoluwole22@gmail.com'))
        user = result.scalar_one_or_none()
        
    # We will override the dependency to return our test admin user
    app.dependency_overrides[get_current_user] = lambda: user
    
    client = TestClient(app)
    print("Sending GET /api/v1/sensors/devices...")
    response = client.get("/api/v1/sensors/devices", headers={"Authorization": "Bearer dummy-token"})
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    try:
        print(f"Response Body: {response.json()}")
    except Exception:
        print(f"Response Text: {response.text}")
        
    app.dependency_overrides.clear()

if __name__ == "__main__":
    asyncio.run(test_endpoint())
