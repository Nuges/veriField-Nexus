# 08 — Permission Coverage Audit

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Existing RBAC Implementation

The platform uses a `ROLE_PERMISSIONS_MAP` in `backend/app/domains/authentication/permissions.py` with Redis caching. The `has_permission()` function checks atomic permissions against this map.

### Known Atomic Permissions
Based on code analysis, the following atomic permissions are defined and referenced:
- `CREATE_ACTIVITY`
- `READ_ACTIVITY`
- `APPROVE_ACTIVITY`
- `CREATE_PROJECT`
- `MANAGE_ORG`

### Known Roles
Based on database and code analysis:
- `super_admin`
- `org_admin`
- `regulator`
- `developer`
- `field_agent`
- `auditor`
- `verifier`

## Required Roles (per Architecture `05-security/01-auth-rbac.md`)

| Role | Exists in Code | Explicit Permissions Defined | UI Access Scoping | Status |
| :--- | :--- | :--- | :--- | :--- |
| Platform Super Admin | ✅ | ⚠️ | ⚠️ | ⚠️ Partial |
| Platform Admin | ❌ | ❌ | ❌ | ❌ Missing |
| Organization Admin | ✅ | ⚠️ | ⚠️ | ⚠️ Partial |
| Programme Manager | ❌ | ❌ | ❌ | ❌ Missing |
| Project Manager | ❌ | ❌ | ❌ | ❌ Missing |
| Field Supervisor | ❌ | ❌ | ❌ | ❌ Missing |
| Field Agent | ✅ | ⚠️ | ⚠️ | ⚠️ Partial |
| Verifier | ✅ | ⚠️ | ⚠️ | ⚠️ Partial |
| Validator | ❌ | ❌ | ❌ | ❌ Missing |
| VVB (External) | ❌ | ❌ | ❌ | ❌ Missing |
| Auditor | ✅ | ⚠️ | ⚠️ | ⚠️ Partial |
| Government / Regulator | ✅ | ⚠️ | ⚠️ | ⚠️ Partial |
| Registry Operator | ❌ | ❌ | ❌ | ❌ Missing |
| Corporate Buyer | ❌ | ❌ | ❌ | ❌ Missing |
| Investor | ❌ | ❌ | ❌ | ❌ Missing |
| API Client (System) | ❌ | ❌ | ❌ | ❌ Missing |

## Missing Permissions (Not Defined in Code)

| Permission | Required For | Severity |
| :--- | :--- | :--- |
| `CREATE_PROGRAMME` | Programme Managers | 🔴 Critical |
| `MANAGE_PROGRAMME` | Programme Managers | 🔴 Critical |
| `CREATE_PORTFOLIO` | Investors | 🔴 Critical |
| `ISSUE_CREDIT` | Registry, Carbon Engine | 🔴 Critical |
| `RETIRE_CREDIT` | Corporate Buyer | 🔴 Critical |
| `TRANSFER_CREDIT` | Ledger | 🔴 Critical |
| `MANAGE_JURISDICTION` | Regulator | 🔴 Critical |
| `VALIDATE_PROJECT` | VVB/Validator | 🔴 Critical |
| `VERIFY_EVIDENCE` | Verifier | 🔴 Critical |
| `MANAGE_METHODOLOGY` | Registry Admin | 🟠 High |
| `VIEW_ANALYTICS` | Various | 🟠 High |
| `EXPORT_DATA` | Various | 🟠 High |
| `MANAGE_REGISTRY` | Registry Admin | 🟠 High |
| `MANAGE_SPATIAL` | Regulator | 🟠 High |

## ABAC (Attribute-Based Access Control) Assessment

| Concern | Status | Notes |
| :--- | :--- | :--- |
| Role-based (RBAC) | ⚠️ | Implemented but incomplete (only 5 permissions defined). |
| Attribute-based (ABAC) | ❌ | No ABAC implementation. Architecture requires checking org ownership, spatial containment, project membership. |
| Resource-level scoping | ⚠️ | `organization_id` filtering exists in some queries, but not enforced universally. |
| API-level enforcement | ⚠️ | `has_permission()` called in some routes, not all. |
| UI-level enforcement | ⚠️ | Sidebar shows/hides items by role, but inconsistent. |

> [!CAUTION]
> 9 of 16 required roles do not exist. Only 5 atomic permissions are defined in code. ABAC is not implemented. There is no implicit-deny enforcement — if a permission check is missing from a route, the route is effectively open to any authenticated user.
