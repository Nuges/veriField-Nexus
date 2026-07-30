# 06 — Level 5 CIOS Permanent Dashboard Shell



## Locked Shell Module Layout



The Level 5 Climate Information Operating System (CIOS) shell is governed by the non-negotiable architectural rule:

> *"The dashboard shell is permanent. Only the content changes. Never the layout."*



```

+-----------------------------------------------------------------------------------+

| Module 1: Dashboard Header (Engine Badge, Sector Title, Read-Only Methodology)     |

+-----------------------------------------------------------------------------------+

| Module 2: Operations View Banner (When in Operations Telemetry mode)             |

+-----------------------------------------------------------------------------------+

| Module 3: KPI Row (4 Equal Terminal Metric Cards with HSL Accent Badges)          |

+-----------------------------------------------------------------------------------+

| Module 4: Spatial GIS Module (8/12)       | Module 5: Certified Registry (4/12)  |

| (OpenStreetMap / Leaflet Cluster Plot)    | (Verra & Gold Standard Exports)       |

+-----------------------------------------------------------------------------------+

| Module 6 & 7: Platform Analytics Workspace (5 Tabs, Charts & Live Activity Feed)  |

+-----------------------------------------------------------------------------------+

```



---



## 7 Permanent Core Modules



1. **Dashboard Header (`DashboardHeader.tsx`)**: Engine title, sector name, project, and read-only methodology badge (`✓ Active`).

2. **Operations Telemetry Banner (`EnterpriseDashboard.tsx`)**: Live streaming hardware telemetry indicator.

3. **KPI Row (`WidgetRenderer.tsx`)**: 4 high-density Bloomberg/Stripe-quality cards displaying sector-specific metrics.

4. **MRV Spatial Integrity Module (`SpatialModule.tsx`)**: 8/12 grid Leaflet map plot with 30m spatial radius check.

5. **Certified Registry Export Module (`RegistryModule.tsx`)**: 4/12 grid Verra VCS and Gold Standard export triggers.

6. **Analytics Workspace (`AnalyticsTabs.tsx`)**: 5 sub-tabs displaying sector-specific area and bar charts.

7. **Live Activity Feed (`AnalyticsTabs.tsx`)**: High-density table featuring asset IDs, trust index, status chips, SHA-256 evidence hashes, and timestamps.
