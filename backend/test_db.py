import requests
resp = requests.get("http://127.0.0.1:8000/api/v1/verification/tasks")
print(resp.json())
