# 14 — Gap Analysis

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Complete Gap Register

### 🔴 Critical Gaps (Must be resolved before any production deployment)

| # | Gap | Category | Impact | Recommendation | Priority | Estimated Effort |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| G-01 | **Programme domain module missing** | Feature | Cannot manage PoAs. Programmes are a core financial and governance entity. | Create `domains/programmes` with full DDD structure (model, service, API, schemas, events, permissions, repository, validators). | P0 | 2-3 weeks |
| G-02 | **Portfolio domain module missing** | Feature | No investor view, no aggregation, no portfolio-level reporting. | Create `domains/portfolios` with full DDD structure. | P0 | 2 weeks |
| G-03 | **Validation/VVB domain module missing** | Feature | External audit workflow is entirely absent. No third-party verification possible. | Create `domains/validation` with VVB role, sampling engine, audit statement entity. | P0 | 3-4 weeks |
| G-04 | **Evidence entity missing** | Entity | Evidence is conflated with Activities. No cryptographic hashing, no provenance chain, no blob reference. | Create `Evidence` model with hash, GPS, timestamp, blob_uri, device_id. Separate from Activity. | P0 | 2 weeks |
| G-05 | **CarbonCredit entity missing** | Entity | Ledger domain exists but has no minted credit entity with serial numbers. | Create `CarbonCredit` model (serial_number, vintage, status, owner_org_id). | P0 | 1-2 weeks |
| G-06 | **VerificationBatch entity missing** | Entity | No mechanism to group evidence into auditable batches for VVB review. | Create `VerificationBatch` model (project_id, monitoring_period, status, assigned_vvb). | P0 | 1 week |
| G-07 | **Event bus not implemented** | Architecture | ADR-001 (EDA) is approved but no broker exists. Events are fire-and-forget with zero consumers. | Implement Redis Streams or Kafka as event broker. Register consumers. Add DLQ. | P0 | 3-4 weeks |
| G-08 | **RBAC incomplete** | Security | Only 5 of 30+ required permissions defined. 9 of 16 roles missing. Routes without permission checks are open. | Complete ROLE_PERMISSIONS_MAP. Add implicit-deny middleware. Define all roles. | P0 | 2-3 weeks |
| G-09 | **No soft delete on any entity** | Data Integrity | Hard deletes are possible. Audit trails can be destroyed. Violates climate data permanence. | Add `is_deleted`, `deleted_at` to all entities. Override delete methods. | P0 | 1-2 weeks |
| G-10 | **No CI/CD pipeline** | Infrastructure | No automated testing, linting, or deployment. Manual deploys are error-prone. | Configure GitHub Actions with lint, test, build, deploy stages. | P0 | 1-2 weeks |

### 🟠 High Gaps (Should be resolved before beta/pilot deployment)

| # | Gap | Category | Impact | Recommendation | Priority | Estimated Effort |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| G-11 | **Hardcoded calculation engines** | Architecture Principle | `energy_carbon_engine`, `quantification_engine` contain hardcoded formulas. Violates "Configuration over Code". | Migrate all formulas to `MethodologyTemplate` entities with parameterized ASTs. | P1 | 3-4 weeks |
| G-12 | **No MFA** | Security | Government and financial users require MFA. | Enable Supabase MFA. Enforce for high-privilege roles. | P1 | 1 week |
| G-13 | **No monitoring or observability** | Operations | Zero visibility into platform health, API latency, error rates. | Deploy Prometheus + Grafana. Add `/metrics` endpoint. Configure alerts. | P1 | 2 weeks |
| G-14 | **No standardized API conventions** | API | Inconsistent pagination, filtering, error envelopes across routes. | Create shared middleware for pagination, filtering, sorting, error responses. | P1 | 1-2 weeks |
| G-15 | **No idempotency on write APIs** | API | Retry-unsafe. Network failures can cause duplicate records. | Add idempotency key header support on all POST/PUT routes. | P1 | 1-2 weeks |
| G-16 | **No rate limiting** | Security | API is vulnerable to abuse and DDoS. | Add rate limiter middleware (e.g., slowapi). | P1 | 3 days |
| G-17 | **Missing Project/Asset UI pages** | UI | Core entity management screens are absent. Users cannot manage projects or assets visually. | Build dedicated CRUD pages for Projects and Assets. | P1 | 2 weeks |
| G-18 | **PostGIS spatial queries not implemented** | Feature | Spatial containment, overlap detection, inheritance are documented but not coded. | Implement `ST_Contains`, `ST_Intersects` queries for jurisdiction and project validation. | P1 | 2 weeks |
| G-19 | **Audit trail not auto-populated** | Compliance | Most state changes do not create audit records. | Add event subscriber that writes AuditTrail on every domain event. | P1 | 1-2 weeks |
| G-20 | **No containerization (Docker)** | Infrastructure | Cannot deploy consistently. No environment parity. | Create Dockerfile and docker-compose.yml. | P1 | 3 days |

### 🟡 Medium Gaps (Should be resolved before general availability)

| # | Gap | Category | Impact | Recommendation | Priority | Estimated Effort |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| G-21 | **No entity versioning** | Data | Only Jurisdiction has version. Architecture requires all entities to be versioned. | Add `version` column to all models. Implement optimistic concurrency. | P2 | 1-2 weeks |
| G-22 | **No ABAC implementation** | Security | Cannot enforce resource-level policies (org ownership, spatial containment). | Implement ABAC engine checking attributes before CRUD operations. | P2 | 2-3 weeks |
| G-23 | **No offline PWA** | UI | Field agents cannot work without connectivity. Architecture requires offline-first. | Implement service worker data sync, IndexedDB local storage. | P2 | 3-4 weeks |
| G-24 | **No Marketplace module** | Feature | No carbon credit trading capability. | Design and build marketplace module per architecture roadmap. | P2 | 4-6 weeks |
| G-25 | **No Climate Finance module** | Feature | No escrow, benefit sharing, or payment integration. | Design per `03-climate-finance-architecture.md`. | P2 | 4-6 weeks |
| G-26 | **No Workflow Engine** | Architecture | No generic approval/escalation/routing engine. | Evaluate temporal.io or build lightweight state-machine-based engine. | P2 | 3-4 weeks |
| G-27 | **No metadata JSONB on entities** | Architecture | Entities cannot carry extensible metadata. Violates "Metadata over Conditionals". | Add `metadata` JSONB column to all entities. | P2 | 1 week |
| G-28 | **Registry adapters not implemented** | Integration | Cannot sync with Verra, Gold Standard, or any external registry. | Build adapter interface and first concrete adapter (CSI or Gold Standard). | P2 | 3-4 weeks |
| G-29 | **No data residency controls** | Compliance | Required for multi-country government deployments. | Design data residency layer per `09-infrastructure-architecture`. | P2 | 2-3 weeks |
| G-30 | **No Developer Platform / SDK** | Feature | External developers cannot build on VeriField Nexus. | Design API documentation, webhook subscriptions, SDK. | P2 | 4-6 weeks |

---

## Gap Summary

| Severity | Count | Estimated Total Effort |
| :--- | :--- | :--- |
| 🔴 Critical (P0) | 10 | 17-26 weeks |
| 🟠 High (P1) | 10 | 13-20 weeks |
| 🟡 Medium (P2) | 10 | 24-37 weeks |
| **Total** | **30** | **54-83 weeks** |

> [!CAUTION]
> 30 architectural gaps have been identified. 10 are critical and block any production deployment. The estimated effort to close all critical gaps is 17-26 weeks of engineering time.
