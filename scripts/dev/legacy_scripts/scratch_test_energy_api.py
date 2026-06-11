import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # We need an admin user token to authenticate.
        # Let's call login first or bypass if we can query the database for token.
        # Actually, let's fetch the admin user from DB, get their email, and generate a token or just call the endpoints.
        # But wait, we can just run the query from python using SQLAlchemy directly, which is even more direct!
        pass

if __name__ == "__main__":
    # Let's write a python script to run the local API endpoints using TestClient.
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.config import settings
    
    # We can get a token or override dependency.
    # Let's override require_admin dependency to return a mock admin user.
    from app.core.security import require_admin
    from app.models.user import User
    import uuid
    
    mock_admin = User(
        id=uuid.uuid4(),
        email="admin@verifield.org",
        role="admin",
        organization="VeriField",
        sector="cookstove"
    )
    
    app.dependency_overrides[require_admin] = lambda: mock_admin
    
    client = TestClient(app)
    
    print("=== GET /api/v1/energy/portfolio ===")
    r = client.get("/api/v1/energy/portfolio")
    print(r.status_code)
    print(r.json())
    
    print("\n=== GET /api/v1/energy/activities ===")
    r = client.get("/api/v1/energy/activities")
    print(r.status_code)
    print(r.json())

