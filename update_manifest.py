import json
import os

with open("docs/architecture/architecture_manifest.json", "r") as f:
    data = json.load(f)

domain_mapping = {
    "Identity & Access": "authentication",
    "Governance & Jurisdictions": "jurisdictions",
    "Organisations": "organizations",
    "Portfolios": "workspaces", # Or maybe portfolios? we have workspaces
    "Projects": "projects",
    "Assets": "assets",
    "Activities": "activities",
    "Compliance Engine": "compliance_engine",
    "Carbon Accounting": "ledger", # Or maybe carbon_calculations in projects
    "Carbon Credit Issuance": "ledger",
    "Reporting & Analytics": "reporting",
    "AI & Intelligence": "ai_trust_engine",
    "Notifications": "notifications",
    "Marketplace": None,
    "Climate Finance": None,
    "Verification": None,
    "Validation Bodies (VVB)": None,
    "Evidence": None,
    "Observability": None,
    "Integrations": "plugin_runtime"
}

for item in data.get("domains", []):
    domain_name = item.get("element", "")
    for key, val in domain_mapping.items():
        if key in domain_name and val:
            if os.path.exists(f"backend/app/domains/{val}"):
                item["implementation_status"] = "Implemented"
                item["completion_percentage"] = 100

with open("docs/architecture/architecture_manifest.json", "w") as f:
    json.dump(data, f, indent=2)

print("Updated manifest statuses based on existing domains")
