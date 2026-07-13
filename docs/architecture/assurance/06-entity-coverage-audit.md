# 06 — Entity Coverage Audit

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Existing Entities (Database Models)

### Legacy Models (`backend/app/models/`)
| Entity | Lifecycle | Relationships | Ownership (`org_id`) | Soft Delete | Versioning | Audit Trail | Permissions | State Machine | Indexes | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `User` | ✅ | ✅ Org, Activities | ⚠️ | ❌ | ❌ | ⚠️ | ✅ | ❌ | ⚠️ | ⚠️ Partial |
| `Organization` | ⚠️ | ✅ Users, Projects | ✅ (self) | ❌ | ❌ | ⚠️ | ✅ | ❌ | ⚠️ | ⚠️ Partial |
| `Project` | ⚠️ | ✅ Org, Assets | ✅ | ❌ | ❌ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ Partial |
| `Asset` | ⚠️ | ✅ Project | ✅ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ⚠️ | ⚠️ Partial |
| `Activity` | ✅ | ✅ User, Asset | ✅ | ❌ | ❌ | ⚠️ | ✅ | ✅ | ⚠️ | ✅ Functional |
| `Jurisdiction` | ⚠️ | ✅ Org | ✅ | ❌ | ✅ (`version`) | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ Partial |
| `AuditTrail` | ✅ | ✅ User | ⚠️ | N/A | N/A | ✅ (self) | ⚠️ | N/A | ⚠️ | ⚠️ Partial |
| `AuditTask` | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ⚠️ | ❌ | ⚠️ | ⚠️ | ⚠️ Partial |
| `CarbonCalculation` | ⚠️ | ✅ Activity | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `CarbonSink` | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Partial |
| `SensorReading` | ✅ | ✅ Asset | ✅ | N/A | N/A | ❌ | ❌ | N/A | ⚠️ | ⚠️ Partial |
| `AnomalyFlag` | ✅ | ✅ Activity | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ Partial |
| `TrustLog` | ✅ | ✅ Activity | ✅ | N/A | N/A | ✅ (self) | ❌ | N/A | ⚠️ | ⚠️ Partial |
| `Compliance` | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ⚠️ Partial |
| `Accreditation` | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Partial |
| `CommunityValidation` | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Partial |
| `Property` | ✅ | ✅ Activity | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ⚠️ | ⚠️ Partial |
| `Signature` | ✅ | ⚠️ | ⚠️ | N/A | N/A | ✅ (self) | ❌ | N/A | ❌ | ⚠️ Partial |
| `AccessRequest` | ⚠️ | ✅ User | ⚠️ | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ Partial |
| `SystemSetting` | ✅ | N/A | ⚠️ | N/A | ❌ | ❌ | ❌ | N/A | ❌ | ⚠️ Partial |
| `JobExecution` | ✅ | ⚠️ | ⚠️ | N/A | N/A | ⚠️ | ❌ | ✅ | ✅ | ✅ Functional |

### Domain Models (`backend/app/domains/*/models.py`)
Each of the 13 domain modules contains a `models.py` file. These are predominantly scaffolded with base structure but require verification of completeness.

## Missing Entities (Required by Architecture, Not in Database)

| Entity | Architecture Source | Severity | Notes |
| :--- | :--- | :--- | :--- |
| `Programme` | `08-climate-programme` | 🔴 Critical | No model. No table. |
| `Portfolio` | `09-portfolio` | 🔴 Critical | No model. No table. |
| `Evidence` | `04-digital-mrv` | 🔴 Critical | Evidence is implicit in `Activity`. Needs dedicated entity with hash, provenance. |
| `VerificationBatch` | `04-digital-mrv` | 🔴 Critical | No model for grouping evidence into audit batches. |
| `CarbonCredit` | `09-portfolio` | 🔴 Critical | No model. Ledger domain exists but no credit entity with serial numbers. |
| `MethodologyTemplate` | `06-methodology` | 🟠 High | Methodology Registry has models but no `MethodologyTemplate` entity for versioned, deployable configs. |
| `ValidationStatement` | `04-digital-mrv` | 🟠 High | No model for VVB formal statements. |
| `RegistryAdapter` | `05-registry-fed` | 🟠 High | No model tracking external registry connections and health. |
| `BenefitSharingRule` | `03-climate-finance` | 🟡 Medium | No model for automated revenue distribution. |
| `SpatialLayer` | `07-spatial` | 🟡 Medium | Jurisdiction has `spatial_boundary`, but no dedicated hierarchical spatial layer entity. |

## Cross-Cutting Entity Concerns

| Concern | Status | Notes |
| :--- | :--- | :--- |
| Soft Delete (all entities) | ❌ | No entity implements soft delete. Hard deletes possible. |
| Versioning (all entities) | ❌ | Only `Jurisdiction` has a `version` column. |
| `organization_id` scoping (RLS) | ⚠️ | Most entities have `organization_id` but RLS is not enforced at DB level. |
| Metadata (`metadata` JSONB column) | ❌ | Not standardized across entities. |
| `created_at` / `updated_at` | ✅ | Generally present via `TimestampMixin`. |

> [!CAUTION]
> 6 critical entities required by the architecture (Programme, Portfolio, Evidence, VerificationBatch, CarbonCredit, MethodologyTemplate) do not exist in the database. No entity implements soft delete. Versioning is absent. Row-Level Security is not enforced at the database level.
