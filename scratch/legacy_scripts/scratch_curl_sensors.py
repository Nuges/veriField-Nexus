import httpx
import json

def main():
    login_url = "http://127.0.0.1:8000/api/v1/auth/login"
    login_payload = {
        "email": "segunoluwole22@gmail.com",
        "password": "any-password"
    }
    
    print("Logging in...")
    with httpx.Client() as client:
        r = client.post(login_url, json=login_payload)
        print(f"Login status: {r.status_code}")
        if r.status_code != 200:
            print(r.text)
            return
            
        auth_data = r.json()
        token = auth_data["access_token"]
        print("Logged in successfully. Token obtained.")
        
        devices_url = "http://127.0.0.1:8000/api/v1/sensors/devices"
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\nFetching devices...")
        r_dev = client.get(devices_url, headers=headers)
        print(f"Devices status: {r_dev.status_code}")
        print("Response Body:")
        print(json.dumps(r_dev.json(), indent=2))

if __name__ == "__main__":
    main()
