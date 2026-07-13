import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def main():
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "cue@gmail.com", "password": "password"}
        )
        print(response.status_code)
        print(response.text)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
