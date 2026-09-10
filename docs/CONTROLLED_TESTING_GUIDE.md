# VeriField Nexus — Controlled External Testing & Data Isolation Guide

**Version**: 1.0  
**Security Level**: Restricted / Enterprise Standard Operating Procedure  
**Classification**: CIOS Operational Governance  

---

## 1. Purpose & Scope
This guide outlines the end-to-end procedures for conducting controlled external testing of VeriField Nexus with external testers (field agents, supervisors, QA officers, and third-party verifiers) while strictly guaranteeing:
1. **Separation of Duties (SoD)** between data submitters and approvers.
2. **Isolation of Non-Production Data** (`TEST`, `DEMO`, `PILOT`) from official MRV quantification, carbon credit minting, and registry bundles.
3. **Multi-Tenant Boundaries** preventing cross-tenant information leakage (IDOR / BOLA protection).

---

## 2. Controlled Tester Provisioning Flow

VeriField Nexus provides two authoritative, non-duplicative flows for onboarding testers:

### Flow A: Direct Super Admin User Provisioning
1. Log in as `SUPER_ADMIN` (`segunoluwole22@gmail.com`).
2. Navigate to **Governance / People Management** or execute `POST /api/v1/admin/users`.
3. Provide:
   - `full_name`: Tester full legal name
   - `email`: Tester corporate or verified email
   - `role`: Restricted role (`FIELD_AGENT`, `QA_OFFICER`, `VERIFIER`, or `VIEWER`)
   - `organization_id`: Explicitly assign to the dedicated TEST organization
4. A temporary activation credential is generated with `requires_password_change: true`.
5. The tester activates their account and establishes their password on first sign-in.

### Flow B: External Tester Request & Approval Queue
1. The external tester submits an application via `POST /api/v1/access-requests`.
2. The submission enters the **Access Requests Queue** in `/dashboard/access-control`.
3. The `SUPER_ADMIN` reviews the requested methodology, use case, and jurisdiction.
4. Upon approval via `POST /api/v1/access-requests/{id}/approve`:
   - An organization and workspace are provisioned automatically.
   - The user account is provisioned with role `ORG_ADMIN` or specified role.
   - Designated methodology licenses are assigned.

---

## 3. Creating a Test Project & Test Workspace
1. In `/dashboard/projects`, create a new project with non-production classification:
   - Set `baseline_parameters`:
     ```json
     {
       "data_classification": "TEST",
       "is_test": true,
       "test_environment": "STAGING_SANDBOX"
     }
     ```
2. Assign the invited tester(s) to the project via `POST /api/v1/admin/projects/{project_id}/members`.
3. Restrict membership role to `FIELD_AGENT` or `QA_OFFICER`.

---

## 4. Field Capture & Mobile Workflow
1. The tester opens the VeriField mobile app or Web Capture at `/capture`.
2. The user signs in using their scoped credentials.
3. Only assigned projects and permitted methodology forms (e.g. Cookstoves, Biochar, Hybrid Energy, EV Mobility) are visible.
4. During activity capture:
   - Geotagged coordinates (latitude, longitude, GPS accuracy) are acquired.
   - Cryptographic SHA-256 hashes of all photos/evidence payloads are computed.
   - The payload metadata records `"data_classification": "TEST"`.
5. When offline, activities queue in encrypted local storage.
6. Upon connectivity restoration, sync executes with cryptographic idempotency.

---

## 5. Separation of Duties (SoD) Enforcement

VeriField Nexus enforces non-negotiable Separation of Duties across both backend APIs and dashboard UI:

1. **Submitting Agent Self-Approval Block**:
   - A field agent who submitted an activity is **strictly blocked** by the backend from approving or verifying their own submission (`PUT /api/v1/activities/{id}` and `PATCH /api/v1/activities/{id}/status`).
   - The UI disables the "Approve & Quantify Credit" button and displays an explicit banner:  
     `Separation of Duties: You cannot verify or approve your own activity submission.`
2. **QA & Supervisor Independence**:
   - Only independent users holding `QA_OFFICER`, `FIELD_SUPERVISOR`, `VERIFIER`, `ORG_ADMIN`, or `SUPER_ADMIN` roles can verify activities.
3. **Auditor / Verifier Impartiality**:
   - Project developers cannot verify or sign off on their own project verification tasks.
   - Verification tasks (`/api/v1/verification/tasks/{id}`) enforce strict tenant scoping and verifier ownership to prevent cross-tenant IDOR/BOLA.

---

## 6. Test Data Isolation & Exclusion Guarantees

| Subsystem | Behavior on TEST / DEMO Data | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Dashboard Activity View** | Marked with subtle `TEST RECORD` badge | Header badge in `/dashboard/activities/[id]` |
| **Ledger Minting** | Strictly rejected (HTTP 400 Bad Request) | `execute_carbon_minting` checks `data_classification` & `is_test` |
| **Registry Packaging** | Rejects packaging (HTTP 404 / ValueError) | `generate_registry_package` blocks non-production projects |
| **Registry Asset Export** | Test assets filtered out from export | SQL queries filter `is_test != true` & `data_classification NOT IN (TEST, DEMO)` |
| **MRV PDF Generation** | Watermarked as Test / Pilot | Dynamic ReportLab security seal checks project metadata |

---

## 7. Account Suspension, Revocation & Data Cleanup
1. **Suspension**:
   - An administrator can instantly freeze a tester account via `POST /api/v1/admin/users/{id}/suspend`.
   - All active JWT sessions for the user are invalidated.
2. **Revocation**:
   - An administrator can soft-delete tester accounts via `DELETE /api/v1/admin/users/{id}`.
3. **Test Data Archival & Cleanup**:
   - Test projects and activities are logically soft-deleted without cascading to production audit trails.
   - Test calculations are purged cleanly from active pipelines without altering production ledger sequences.
