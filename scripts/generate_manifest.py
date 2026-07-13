import json

domains = [
    "Identity & Access", "Governance & Jurisdictions", "Organisations", "Methodology Engine",
    "Registry Federation", "Programmes (PoA)", "Portfolios", "Projects", "Assets", "Activities",
    "Evidence", "Verification", "Validation Bodies (VVB)", "Compliance Engine", "Carbon Accounting",
    "Carbon Credit Issuance", "Climate Finance", "Marketplace", "Reporting & Analytics",
    "AI & Intelligence", "Integrations", "Notifications", "Observability"
]

manifest = {
    "metadata": {
        "version": "2.0",
        "description": "Authoritative Execution Backlog mapping domains to implementation status according to the 13 attributes."
    },
    "domains": []
}

for d in domains:
    manifest["domains"].append({
        "element": d,
        "architecture_reference": f"docs/architecture/... (to be updated)",
        "domain": d,
        "owner": "To be determined",
        "implementation_status": "Not Started",
        "dependencies": [],
        "apis": {"status": "Pending", "routes": []},
        "events": {"status": "Pending", "published": [], "consumed": []},
        "ui": {"status": "Pending", "screens": []},
        "permissions": {"status": "Pending", "roles": [], "policies": []},
        "tests": {"status": "Pending", "coverage": "0%"},
        "audit_status": "Pending",
        "production_readiness": "0/5",
        "completion_percentage": "0%"
    })

with open("docs/architecture/architecture_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

print("Updated architecture_manifest.json")
