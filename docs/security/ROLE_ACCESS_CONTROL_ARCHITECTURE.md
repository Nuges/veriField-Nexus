# VeriField Nexus — Authoritative Role & Access Control Architecture

**Document Version:** 5.4-PROD  
**Classification:** Enterprise Security & Regulatory Governance  
**Scope:** Frontend Navigation, Route Protection, API Endpoints, RBAC/ABAC Engines, Separation of Duties (SoD), Multi-Tenancy  

---

## 1. Executive Architecture Summary

VeriField Nexus CIOS operates an authoritative, least-privileged, multi-tier Role-Based and Attribute-Based Access Control (RBAC/ABAC) architecture. Every user persona operates within a purpose-built workspace containing only the tools, data, and permissions required for that role.

### Security Invariants:
1. **Server-Side Authorization Authority:** Frontend route hiding and component disabling are strictly for UX. All sensitive actions are validated independently on the backend with `require_permission(...)` and tenant validation.
2. **Separation of Duties (SoD):** A Project Developer cannot independently audit, verify, or sign off their own mitigation project. VVB auditor/verifier actions are strictly segregated from project operators.
3. **Multi-Tenant Isolation:** All queries for projects, activities, assets, ledger entries, and AI intelligence are strictly bounded by `organization_id`.
4. **Super Admin Invariant:** The `SUPER_ADMIN` role is globally locked to designated platform administrators and cannot be assigned by tenant administrators.
5. **Fail-Closed Default:** Any unknown or unmapped role defaults to the least-privileged `VIEWER` persona.

---

## 2. Canonical Role Inventory & Alias Resolution

| Canonical Role | Primary Aliases | Data Scope | Primary Persona Question |
|---|---|---|---|
| `SUPER_ADMIN` | `superadmin`, `platform_super_admin` | Global Platform | *"Is the global platform healthy and compliant?"* |
| `ORG_ADMIN` | `admin`, `org_owner`, `tenant_admin` | Tenant Organization | *"Is my organization secure, configured, and governed?"* |
| `PROJECT_MANAGER` | `project_developer`, `developer`, `portfolio_manager` | Tenant Organization | *"How are my carbon mitigation projects progressing?"* |
| `FIELD_SUPERVISOR` | `supervisor`, `team_lead` | Tenant Organization | *"Are my field teams operating efficiently and resolving anomalies?"* |
| `FIELD_AGENT` | `field_agent`, `operator`, `technician` | Assigned Activities | *"What field inspections and evidence captures must I complete today?"* |
| `QA_OFFICER` | `mrv_officer`, `mrv_manager`, `iot_engineer` | Tenant Organization | *"Is my MRV monitoring telemetry complete, accurate, and trustworthy?"* |
| `VERIFIER` | `vvb`, `vvb_verifier` | Assigned Engagements | *"Is the project evidence and calculation methodology verified for sign-off?"* |
| `AUDITOR` | `vvb_auditor`, `third_party_auditor` | Assigned Engagements | *"What evidence, findings, and NCRs require independent audit?"* |
| `COMPLIANCE_ADMIN` | `compliance_officer`, `regulator`, `jurisdiction_admin` | Tenant / Sovereign | *"Is this project eligible for Article 6 and host country NDC authorization?"* |
| `REGISTRY_ADMIN` | `registry_manager`, `registry_officer` | Tenant Organization | *"Is the multi-standard submission package complete and hash-verified?"* |
| `FINANCE` | `finance_officer`, `treasury` | Tenant Organization | *"What carbon assets require cryptographic minting and fee settlement?"* |
| `INVESTOR` | `executive` | Tenant Organization | *"What are the verified carbon yields and ESG impacts across my portfolio?"* |
| `VIEWER` | `observer`, `client`, `platform_support` | Permitted Scope | Read-only observation. |

---

## 3. Role × Module Capability Matrix

| Module | Super Admin | Org Admin | Project Manager | Field Agent | QA / MRV | VVB Auditor | Compliance | Registry | Finance | Investor / Viewer |
|---|---|---|---|---|---|---|---|---|---|---|
| **Mission Control** | ADMIN | MANAGE | MANAGE | EXECUTE | MANAGE | READ | READ | READ | MANAGE | READ |
| **Projects & Fleets** | ADMIN | MANAGE | MANAGE | NONE | READ | ASSIGNED READ | READ | READ | READ | READ |
| **Programmes (PoA)** | ADMIN | MANAGE | MANAGE | NONE | READ | ASSIGNED READ | READ | READ | NONE | READ |
| **Field Operations** | ADMIN | MANAGE | MANAGE | CREATE | VERIFY | NONE | NONE | NONE | NONE | READ |
| **Telemetry / IoT** | ADMIN | MANAGE | READ | READ | MANAGE | READ | NONE | NONE | NONE | READ |
| **Methodology & PDD** | ADMIN | MANAGE | MANAGE | NONE | MANAGE | READ | READ | READ | NONE | READ |
| **Verification & Audit** | ADMIN | READ | NONE | NONE | NONE | EXECUTE | READ | NONE | NONE | READ |
| **Carbon Ledger** | ADMIN | READ | READ | NONE | READ | READ | READ | READ | EXECUTE | READ |
| **Compliance & Art. 6** | ADMIN | READ | READ | NONE | NONE | READ | MANAGE | READ | NONE | READ |
| **Registry Packages** | ADMIN | READ | PREPARE | NONE | READ | READ | READ | MANAGE | NONE | READ |
| **People & Access** | ADMIN | MANAGE | NONE | NONE | NONE | NONE | NONE | NONE | NONE | NONE |
| **System Settings** | ADMIN | MANAGE | NONE | NONE | NONE | NONE | NONE | NONE | NONE | NONE |

---

## 4. Separation of Duties (SoD) Rules

1. **Rule SoD-01 (Developer ≠ Verifier):**
   A user who created or manages a project (`developer_id`) cannot submit an independent audit finding (`POST /verification/audits`) or sign a verification report for that project.
2. **Rule SoD-02 (Auditor ≠ Carbon Minter):**
   An independent VVB auditor cannot trigger on-chain carbon minting (`POST /ledger/mint`).
3. **Rule SoD-03 (Developer ≠ Article 6 Authorizer):**
   Sovereign Article 6 ITMO authorization (`POST /registry/itmo/authorize`) requires the `compliance:authorize` permission and cannot be self-authorized by a developer.
4. **Rule SoD-04 (Tenant Admin ≠ SuperAdmin Promotion):**
   An Organization Admin cannot update user roles to `SUPER_ADMIN` or modify the `organization_id` of accounts.

---

## 5. Implementation Reference

- **Backend RBAC Engine:** `backend/app/core/rbac.py`
- **Machine-Readable Registry:** `backend/app/core/role_capabilities.yaml`
- **Frontend Role Definitions:** `dashboard/src/lib/roles.ts`
- **Dynamic Navigation:** `dashboard/src/components/DynamicSidebar.tsx`
- **Route Interceptor:** `dashboard/src/app/dashboard/layout.tsx`
- **Action Control Gate:** `dashboard/src/components/RoleGate.tsx`
