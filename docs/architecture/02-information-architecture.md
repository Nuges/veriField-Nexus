# 02 — Information Architecture & Navigation Map



## Workspace Navigation Hierarchy



VeriField Nexus structures application navigation around **human operational workflows** rather than individual feature links.



```

WORKSPACE PANEL (Read-Only Methodology & Org Sector Switcher)

├── Sector (Dropdown: Clean Cookstoves, Hybrid Energy, Biochar, EV Mobility)

├── Current Methodology (Read-Only Status Badge: e.g. AMS-II.G ✓ Active)

└── Project Context (Dropdown Filter)



OPERATIONAL WORKSPACES

├── 1. DASHBOARD (/dashboard)

│    ├── Locked 7-Module Enterprise Shell (KPIs, Spatial Map, Registry Cards, Analytics)

│    ├── Executive View Mode

│    └── Operations Telemetry View Mode

│

├── 2. FIELD OPERATIONS (/dashboard/operations)

│    ├── Tab 1: Field Activities & Logs (/dashboard/activities)

│    ├── Tab 2: Proof Evidence Vault (/dashboard/audits)

│    ├── Tab 3: Verifications Hub (/dashboard/verifications)

│    ├── Tab 4: Spatial GIS Cluster Map (/dashboard/map)

│    └── Tab 5: IoT Telemetry Feeds (/dashboard/sensors)

│

├── 3. PORTFOLIO (/dashboard/portfolio)

│    ├── Tab 1: Projects & Assets (/dashboard/properties)

│    ├── Tab 2: Programme of Activities (POA Portfolio) (/dashboard/poa)

│    ├── Tab 3: Carbon Credit Reports (/dashboard/carbon)

│    ├── Tab 4: Certified Registry Exports (/dashboard/registry)

│    └── Tab 5: Portfolio Analytics (/dashboard/analytics)

│

├── 4. MONITORING (/dashboard/monitoring)

│    ├── Tab 1: AI Trust Engine & Index Scores (/dashboard/trust-scores)

│    ├── Tab 2: Anomaly Centre & Alerts (/dashboard/anomalies)

│    └── Tab 3: Sync Pipeline & Community Validations (/dashboard/community)

│

├── 5. PEOPLE (/dashboard/people)

│    ├── Tab 1: Field Agent Management & Provisioning (/dashboard/agents)

│    └── Tab 2: Auditors & Access Control RBAC (/dashboard/access-control)

│

└── 6. ADMINISTRATION (/dashboard/settings)

     ├── Tab 1: Workspace System Parameters (/dashboard/settings)

     ├── Tab 2: Sector Licensing (/dashboard/settings/sectors)

     ├── Tab 3: User Profile & Security Credentials

     └── Tab 4: System Audit Logs & Organization Profile

```
