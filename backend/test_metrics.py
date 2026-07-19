import requests

# Login as superadmin
login_res = requests.post(
    "http://127.0.0.1:8000/api/v1/auth/login",
    json={"email": "superadmin@verifield.io", "password": "CHANGE_THIS_ON_FIRST_LOGIN"}
)
if login_res.status_code != 200:
    print("Login failed!", login_res.text)
else:
    token = login_res.json()["access_token"]
    print("Logged in!")
    
    # Request metrics
    metrics_res = requests.get(
        "http://127.0.0.1:8000/api/v1/reporting/metrics/agents",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Metrics Response ({metrics_res.status_code}):", metrics_res.text)
