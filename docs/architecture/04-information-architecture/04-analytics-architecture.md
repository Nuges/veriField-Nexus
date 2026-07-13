# Enterprise Analytics Architecture

VeriField Nexus distinguishes sharply between Operational Reporting (real-time, transactional) and Enterprise Analytics (macroscopic, historical, predictive).

## 1. Analytics Typology

1. **Operational Dashboards:**
   - **Audience:** Developers, Field Agents.
   - **Data:** Live queries against the Operational DB (e.g., "Pending Verifications", "Assets Deployed Today").
   - **SLA:** < 1 second latency.
2. **Executive Dashboards:**
   - **Audience:** C-Suite, Portfolio Managers.
   - **Data:** Aggregated performance across multiple projects or geographies.
3. **National / Programme Dashboards:**
   - **Audience:** Regulators, Registries.
   - **Data:** Rollups of all projects within a Jurisdiction, tracking against Nationally Determined Contributions (NDCs).
4. **AI Insights & Forecasting:**
   - **Audience:** Financiers, Programme Managers.
   - **Data:** Predictive models (e.g., "Predicted credit yield based on historical asset degradation").

## 2. Infrastructure

Directly running complex analytical aggregations against the Operational Database (`OLTP`) will cause lock contention and degrade platform performance. 
Instead, the CIOS implements an `OLAP` (Online Analytical Processing) pattern:

1. **Data Warehouse / Data Lake:** (e.g., Snowflake, BigQuery, or a dedicated ClickHouse cluster).
2. **ETL Pipeline:** 
   - A nightly batch process extracts data from the Operational Database, transforms it (flattening JSONB metadata, resolving spatial intersections), and loads it into the Data Warehouse.
   - For near-real-time needs, Kafka Streams process domain events (e.g., `CreditIssued`) and update materialized views in the Data Warehouse.

## 3. Data Products

The Analytics Domain exposes pre-computed "Data Products" to the rest of the application via a read-only GraphQL or REST API. This ensures the frontend doesn't need to perform complex aggregations.

- `NationalCarbonYieldSnapshot`
- `VVBPerformanceMetrics`
- `AssetDegradationCurve`
