with open("app/domains/activities/api.py", "r") as f:
    content = f.read()

content = "from typing import Any\nTrustScoreResponse = Any\n" + content

with open("app/domains/activities/api.py", "w") as f:
    f.write(content)
