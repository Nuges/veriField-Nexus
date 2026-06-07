import jwt
from datetime import datetime, timedelta, timezone
import urllib.request
import urllib.error
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
sys.path.append(os.path.abspath('backend'))
from app.core.config import settings

def main():
    payload = {
        "sub": "192a5308-6e3c-404c-a644-c021a9e7884c",
        "email": "segunoluwole22@gmail.com",
        "dev_mode": True,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    
    # Test 1: Get activities
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/activities",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print("Sending request to /api/v1/activities...")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print("Status Code: 200")
            print("Total Activities:", data.get("total"))
    except urllib.error.HTTPError as e:
        print("HTTP Error:", e.code, e.read().decode())
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
