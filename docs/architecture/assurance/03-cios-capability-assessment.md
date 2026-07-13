# 03 — CIOS Capability Assessment

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Assessment Legend
- **Complete:** Architecture + Domain Module + API + Entity + UI + Workflow all exist.
- **Partial:** Architecture exists, implementation is incomplete (missing module, API, or UI).
- **Missing:** No implementation artefact exists beyond architecture documents.
- **N/A:** Not applicable to current platform version.

---

| # | Capability | Status | Justification |
| :--- | :--- | :--- | :--- |
| 1 | **Identity & Authentication** | **Complete** | Supabase Auth + `authentication` domain module + `auth.py` API + `login` UI + RBAC permissions engine with Redis cache. |
| 2 | **Organizations** | **Partial** | Domain module exists (`organizations`), API and model exist. Missing: dedicated onboarding UI workflow, KYB verification, explicit org-level settings page. |
| 3 | **Jurisdictions** | **Partial** | Domain module exists (`jurisdictions`), model, service, API, and UI page exist. Missing: complete event emission, dedicated lifecycle state machine, full RBAC enforcement. |
| 4 | **Governance / Policy Resolution** | **Partial** | Documented in `06-governance-architecture`. Backend `compliance_engine` provides partial coverage. Missing: hierarchical policy resolution engine (Platform > Government > Standard layering). |
| 5 | **Projects** | **Partial** | Domain module (`projects`) with full DDD structure (api, service, repository, schemas, events, permissions, validators). Missing: dedicated UI page, full lifecycle state machine in code. |
| 6 | **Assets** | **Partial** | Domain module (`assets`) with full DDD structure. Missing: dedicated UI management page, decommission workflow, QR/barcode integration. |
| 7 | **Activities** | **Complete** | Domain module, API, model, events, permissions, UI page (`activities/page.tsx`), capture flow. The most mature operational domain. |
| 8 | **Programmes (PoA)** | **Missing** | Architecture fully documented (`08-climate-programme-architecture.md`). No backend domain module, no model, no API, no service. Only a placeholder UI page (`poa/page.tsx`). |
| 9 | **Portfolios** | **Missing** | Architecture documented (`09-portfolio-architecture.md`). Zero implementation artefacts exist. |
| 10 | **Methodologies** | **Partial** | Dedicated `methodology_registry` package with models, services, routers, calculators, and plugin-based sector methodologies (cookstove, biochar, ev_mobility, hybrid_energy). Missing: UI for methodology authoring, versioning workflow, runtime parameter override validation. |
| 11 | **Registries / Federation** | **Partial** | Domain module (`registry_integrations`) exists with DDD structure. `registry_provider` service exists. Missing: concrete adapter implementations for Verra/Gold Standard, DLQ, conflict resolution, health monitoring. |
| 12 | **Compliance** | **Partial** | Domain module (`compliance_engine`) with full DDD structure + `compliance_engine` service + `compliance.py` API + `compliance.py` model + UI page. Missing: automated rule evaluation, policy layering, compliance scoring. |
| 13 | **Verification** | **Partial** | `verification_worker` job exists, `cross_verification.py` API exists, `verifications/page` UI exists. Missing: dedicated domain module, sampling algorithm, VVB interface, verification batch entity. |
| 14 | **Validation (VVB)** | **Missing** | Architecture fully documented. No domain module, no API, no entity, no UI. VVB workflow is entirely absent from implementation. |
| 15 | **Evidence / Digital MRV** | **Partial** | Capture page exists (`capture/page.tsx`). Evidence is handled implicitly through activities. Missing: dedicated `Evidence` entity, cryptographic hashing on ingestion, provenance chain, blob storage integration. |
| 16 | **Carbon Accounting** | **Partial** | `quantification_engine` service, `energy_carbon_engine`, `energy_displacement_engine` services exist. `carbon_calculation.py` model and `carbon.py` API exist. Missing: methodology-driven calculation (currently hardcoded engines), issuance state machine. |
| 17 | **Issuance** | **Partial** | `ledger` domain module with full DDD structure. Missing: actual credit minting workflow, serial number generation, registry sync on issuance. |
| 18 | **Marketplace / Trading** | **Missing** | Documented in roadmap only (`14-platform-roadmap.md`). Zero implementation. Future V5.x capability. |
| 19 | **Climate Finance** | **Missing** | Documented in `03-climate-finance-architecture.md`. Zero implementation. No escrow, no benefit sharing, no payment integration. |
| 20 | **Spatial / GIS** | **Partial** | `gps_validator` service exists. Map UI page exists. Jurisdiction model has `spatial_boundary` (GeoJSON). Missing: PostGIS spatial queries, `ST_Contains`/`ST_Intersects` enforcement, spatial inheritance engine. |
| 21 | **IoT / Sensors** | **Partial** | `sensor_reading.py` model, `sensors.py` API, `sensor_processor` job, `sensors/page` UI. Missing: MQTT broker integration, real-time streaming, edge device management. |
| 22 | **Satellite / Remote Sensing** | **Missing** | Documented in `10-climate-intelligence-architecture.md`. Zero implementation. |
| 23 | **AI / Trust Engine** | **Partial** | `ai_trust_engine` domain module with full DDD structure. `trust_engine` and `ai_detector` services. `trust_log.py`, `anomaly_flag.py` models. UI pages for trust scores and anomalies. Missing: Computer Vision integration, vector database, LLM integration. |
| 24 | **Reporting / Analytics** | **Partial** | `reporting` domain module, `analytics.py` and `export.py` APIs, `executive/page` UI. Missing: OLAP cube, NDC reporting, ESG reporting templates. |
| 25 | **Notifications** | **Partial** | `notifications` domain module with full DDD structure. Missing: dedicated notification center UI, email/SMS delivery integration (SMS service exists but is basic). |
| 26 | **Workflow Engine** | **Missing** | Documented in `10-operational-architecture`. No generic workflow engine exists. Workflows are implicit in service methods. |
| 27 | **Audit Trail** | **Partial** | `audit_trail.py` and `audit_task.py` models, `audits.py` API, `audits/page` UI. Missing: automatic audit record creation on every state change, audit export, compliance audit reporting. |
| 28 | **Workspaces** | **Partial** | `workspaces` domain module with full DDD structure. Missing: workspace switching UI, multi-sector workspace isolation. |
| 29 | **Plugin Runtime** | **Partial** | `plugin_runtime` domain module. `plugins/` directory with sector plugins (cookstove, biochar, ev_mobility, hybrid_energy). Missing: dynamic plugin loading, plugin marketplace, plugin versioning. |
| 30 | **Accreditation** | **Partial** | `accreditation.py` model and `accreditations.py` API exist. Missing: VVB accreditation lifecycle, accreditation expiry tracking, re-accreditation workflow. |
| 31 | **Community Validation** | **Partial** | `community_validation.py` model, `community.py` API, `community/page` UI. Missing: benefit sharing calculations, community consent tracking. |
| 32 | **Carbon Sinks** | **Partial** | `carbon_sink.py` model, `csink.py` API exist. Missing: dedicated domain module, blue carbon methodology. |
| 33 | **Settings / Config** | **Partial** | `system_setting.py` model, `settings.py` API, `settings/page` UI. Missing: per-organization config, feature flags. |
| 34 | **Job Execution Service** | **Partial** | `job.py` model, `job_scheduler.py` service, `JobPollingWidget` UI. Missing: job retry logic, DLQ, admin job dashboard. |
| 35 | **Developer Platform / SDK** | **Missing** | `sdk/` directory exists at repo root. No documented or implemented developer API. |
| 36 | **Digital Twins** | **N/A** | Future V4.x capability per roadmap. |
| 37 | **Blockchain** | **Partial** | `blockchain.py` service exists. Missing: actual chain integration, smart contract deployment. |
| 38 | **Energy** | **Partial** | `energy.py` API and energy calculation engines exist. Covers hybrid_energy sector. |

---

## Summary

| Status | Count | Percentage |
| :--- | :--- | :--- |
| **Complete** | 2 | 5.3% |
| **Partial** | 25 | 65.8% |
| **Missing** | 9 | 23.7% |
| **N/A** | 2 | 5.3% |

> [!CAUTION]
> Only 2 of 38 capabilities (Identity and Activities) are fully complete. 9 critical capabilities (Programmes, Portfolios, Validation, Marketplace, Climate Finance, Satellite, Workflow Engine, Developer Platform, and a dedicated Verification domain) have zero implementation despite being fully documented in the architecture.
