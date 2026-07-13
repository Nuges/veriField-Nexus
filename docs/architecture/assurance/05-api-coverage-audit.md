# 05 — API Coverage Audit

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Existing API Routes (Backend)

### Legacy API Layer (`backend/app/api/v1/`)
| Route File | Domain | CRUD | Auth | Pagination | Filtering | Validation | Idempotency | OpenAPI | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `auth.py` | Identity | ✅ | ✅ | N/A | N/A | ✅ | ❌ | ⚠️ | ✅ Functional |
| `activities.py` | Activities | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ❌ | ⚠️ | ✅ Functional |
| `assets.py` | Assets | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ❌ | ⚠️ | ⚠️ Partial |
| `projects.py` | Projects | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ❌ | ⚠️ | ⚠️ Partial |
| `jurisdictions.py` | Jurisdictions | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ❌ | ⚠️ | ⚠️ Partial |
| `compliance.py` | Compliance | ⚠️ | ✅ | ⚠️ | ❌ | ⚠️ | ❌ | ⚠️ | ⚠️ Partial |
| `carbon.py` | Carbon | ⚠️ | ✅ | ⚠️ | ❌ | ⚠️ | ❌ | ⚠️ | ⚠️ Partial |
| `registry.py` | Registries | ⚠️ | ✅ | ❌ | ❌ | ⚠️ | ❌ | ⚠️ | ⚠️ Partial |
| `sensors.py` | IoT | ⚠️ | ✅ | ⚠️ | ❌ | ⚠️ | ❌ | ⚠️ | ⚠️ Partial |
| `audits.py` | Audit | ⚠️ | ✅ | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `analytics.py` | Reporting | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `export.py` | Reporting | ⚠️ | ✅ | N/A | N/A | ⚠️ | ❌ | ⚠️ | ⚠️ Partial |
| `accreditations.py` | VVB | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `community.py` | Community | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `settings.py` | Config | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `regulator.py` | Governance | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `energy.py` | Energy | ⚠️ | ✅ | ❌ | ❌ | ⚠️ | ❌ | ⚠️ | ⚠️ Partial |
| `properties.py` | Assets | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `access_requests.py` | RBAC | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `csink.py` | Carbon Sinks | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `cross_verification.py` | Verification | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |

### Domain API Layer (`backend/app/domains/*/api.py`)
| Domain Module | API Exists | Status |
| :--- | :--- | :--- |
| `activities` | ✅ | ⚠️ Scaffolded |
| `ai_trust_engine` | ✅ | ⚠️ Scaffolded |
| `assets` | ✅ | ⚠️ Scaffolded |
| `authentication` | ✅ | ⚠️ Scaffolded |
| `compliance_engine` | ✅ | ⚠️ Scaffolded |
| `ledger` | ✅ | ⚠️ Scaffolded |
| `notifications` | ✅ | ⚠️ Scaffolded |
| `organizations` | ✅ | ⚠️ Scaffolded |
| `plugin_runtime` | ✅ | ⚠️ Scaffolded |
| `projects` | ✅ | ⚠️ Scaffolded |
| `registry_integrations` | ✅ | ⚠️ Scaffolded |
| `reporting` | ✅ | ⚠️ Scaffolded |
| `workspaces` | ✅ | ⚠️ Scaffolded |

## Missing APIs (No Route Exists)

| Capability | Required APIs | Severity |
| :--- | :--- | :--- |
| **Programmes** | CRUD, inclusion, lifecycle transitions | 🔴 Critical |
| **Portfolios** | CRUD, aggregation, investor views | 🔴 Critical |
| **Validation (VVB)** | Sampling, review, statement submission | 🔴 Critical |
| **Evidence** | Upload, hash verification, provenance chain | 🔴 Critical |
| **Marketplace** | Listings, orders, settlement | 🟡 Future |
| **Climate Finance** | Escrow, distribution, benefit sharing | 🟡 Future |
| **Workflow Engine** | Task queue, approvals, escalations | 🔴 Critical |
| **Webhooks** | Event subscription, delivery, retry | 🟠 High |

## Cross-Cutting Concerns

| Concern | Status | Notes |
| :--- | :--- | :--- |
| API Versioning (`/v1/`) | ✅ | Prefix-based versioning in place. |
| Authentication | ✅ | Supabase JWT tokens enforced on all routes. |
| Authorization (RBAC) | ⚠️ | `has_permission()` exists but not uniformly applied to all endpoints. |
| Pagination | ⚠️ | Some routes use `skip`/`limit`; not standardized. |
| Filtering / Sorting | ❌ | No standardized query parameter convention. |
| Idempotency Keys | ❌ | Not implemented on any endpoint. |
| OpenAPI Spec | ⚠️ | FastAPI auto-generates docs, but schemas are incomplete for many routes. |
| Error Handling | ⚠️ | HTTPException used inconsistently. No standard error envelope. |

> [!CAUTION]
> 4 critical business capabilities (Programmes, Portfolios, Validation, Evidence) have zero API coverage. API standardization (pagination, filtering, error envelopes, idempotency) is not enforced.
