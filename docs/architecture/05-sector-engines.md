# 05 — Sector Engines & Methodology Matrix



## Production Sector Specifications



VeriField Nexus supports 4 independent sector engines sharing the permanent Level 5 CIOS shell.



| Sector Code | Sector Name | Primary Methodology | Standard Registry | Key KPI Metrics | Primary Variables |

| :--- | :--- | :--- | :--- | :--- | :--- |

| **COOKSTOVES** | Clean Cookstoves | `AMS-II.G` / `VM0006` | Gold Standard / Verra | • Total CO₂ Reduced (`tCO₂e`)<br>• Households Reached<br>• Stove Usage Rate (`%`) | Stove ID, Household ID, Fuel Type |

| **HYBRID_ENERGY** | Hybrid Energy & Mini-grids | `AMS-I.F` / `ACM0002` | Verra VCS | • Total CO₂ Displaced (`tCO₂e`)<br>• Energy Generated (`MWh`)<br>• Diesel Avoided (`Liters`) | System ID, Site Location, Energy Source |

| **BIOCHAR** | Biochar Carbon Removal | `VM0044` | Verra VCS / Carbonfuture | • Carbon Removed (`tCO₂e`)<br>• Biochar Produced (`Tonnes`)<br>• Permanence (`Years`) | Kiln ID, Sink Location, Biomass Type |

| **EV_MOBILITY** | Electric Mobility & Fleet | `AMS-III.C` | Gold Standard | • CO₂ Displaced (`tCO₂e`)<br>• Charging Sessions<br>• Energy Delivered (`MWh`) | Charger ID, Station Hub, Charging Speed |



---



## Sector Isolation Principles

- Each sector contains its own calculation algorithms, trust index weights, spatial pin configurations, chart telemetry series, and registry export templates.

- Switching sectors in the workspace panel re-binds metrics and calculations without modifying the structural shell layout.
