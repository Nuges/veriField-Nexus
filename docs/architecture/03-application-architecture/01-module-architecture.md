# Enterprise Module Architecture

This document translates the conceptual capabilities into concrete, deployable software modules. The CIOS architecture avoids a monolithic structure in favor of decoupled, bounded modules.

## Core Modules

### 1. `identity-module`
- **Purpose:** Manages authentication, sessions, and token issuance.
- **APIs:** `/api/v1/auth/login`, `/api/v1/auth/register`, `/api/v1/auth/mfa`.
- **Entities:** `Session`, `MFAToken`, `AuditLog`.
- **Dependencies:** None.

### 2. `tenant-module`
- **Purpose:** Manages Organizations, Workspaces, and RBAC policies.
- **APIs:** `/api/v1/organizations`, `/api/v1/roles`, `/api/v1/users`.
- **Entities:** `Organization`, `User`, `Role`, `TenantPolicy`.
- **Dependencies:** `identity-module`.

### 3. `governance-module`
- **Purpose:** Executes the spatial and policy rule engine.
- **APIs:** `/api/v1/jurisdictions`, `/api/v1/methodologies`, `/api/v1/compliance/validate`.
- **Entities:** `Jurisdiction`, `SpatialBoundary`, `Methodology`, `RuleSet`.
- **Dependencies:** `tenant-module`.

### 4. `operations-module`
- **Purpose:** Manages the physical lifecycle of climate initiatives.
- **APIs:** `/api/v1/projects`, `/api/v1/assets`, `/api/v1/activities`.
- **Entities:** `Project`, `Asset`, `ActivityLog`.
- **Dependencies:** `tenant-module`, `governance-module` (for validation).

### 5. `mrv-module` (Monitoring, Reporting, Verification)
- **Purpose:** Handles massive ingestion of field data and workflow states for audits.
- **APIs:** `/api/v1/evidence`, `/api/v1/telemetry`, `/api/v1/verifications`, `/api/v1/audits`.
- **Entities:** `EvidenceRecord`, `VerificationTask`, `AuditReport`.
- **Dependencies:** `operations-module`, `governance-module`.

### 6. `ledger-module`
- **Purpose:** Minting and tracking the financial primitives (carbon credits).
- **APIs:** `/api/v1/ledger/issue`, `/api/v1/ledger/retire`, `/api/v1/credits`.
- **Entities:** `CarbonCredit`, `LedgerTransaction`, `Retirement`.
- **Dependencies:** `mrv-module`, `tenant-module`.

## Module Interaction & Boundaries

Modules are strictly forbidden from sharing database tables. If the `operations-module` needs to know if a user has permission to create a project, it does not query the `users` table directly. It extracts the claims from the verified JWT (provided by the `identity-module`) or calls an internal gRPC/HTTP interface exposed by the `tenant-module`.
