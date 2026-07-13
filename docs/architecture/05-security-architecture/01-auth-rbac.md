# Enterprise Security Architecture

Security is intrinsic to the VeriField Nexus CIOS. The architecture assumes a Zero Trust environment, heavily utilizing Role-Based Access Control (RBAC) and Attribute-Based Access Control (ABAC).

## 1. Authentication (Identity)

- **Identity Provider (IdP):** The system relies on an external Identity Provider (e.g., Supabase Auth, Auth0, or Okta) for handling passwords, MFA, and OAuth integrations.
- **Tokens:** Upon successful authentication, the IdP issues a signed JSON Web Token (JWT). The API Gateway and microservices cryptographically verify this JWT; they do not query the database for session validation.
- **Machine Identities:** APIs consumed by IoT devices, external Registries, or CI/CD pipelines authenticate using long-lived API Keys or client-credentials OAuth flows. These identities are bound to specific `ServiceAccounts` rather than human users.

## 2. Authorization (RBAC & ABAC)

Authorization determines what an authenticated identity is allowed to do.

### Role-Based Access Control (RBAC)
Users are assigned Roles within their Organization.
- **Roles:** `SUPER_ADMIN`, `ORG_ADMIN`, `PROGRAMME_MANAGER`, `FIELD_AGENT`, `VERIFIER`, `AUDITOR`.
- **Permission Matrix:** Each role maps to a static set of privileges (e.g., `project:create`, `evidence:read`). 

### Attribute-Based Access Control (ABAC)
RBAC is insufficient for a multi-tenant enterprise. A `FIELD_AGENT` cannot view *all* projects, only the ones they are assigned to. ABAC dynamically evaluates context:
1. **Tenant Context:** Does the resource belong to the user's `organization_id`?
2. **Spatial Context:** Does the project fall within the Regulator's `jurisdiction_id`?
3. **Assignment Context:** Is the user explicitly listed in the `assigned_users` array for this task?

## 3. Policy Engine

The ABAC rules are evaluated centrally by a Policy Engine (e.g., Open Policy Agent - OPA) or via strict middleware logic in the API layer. 
- A request to `/api/v1/projects/123/approve` is first intercepted.
- The Engine evaluates the user's JWT (Role, Org ID) against the requested resource (Project 123's Org ID and Status).
- If the evaluation fails, an immediate HTTP 403 Forbidden is returned, preventing the core module logic from executing.

## 4. Encryption & Key Management

- **Data in Transit:** All traffic is encrypted via TLS 1.3.
- **Data at Rest:** Databases and Object Storage are encrypted at the disk level (AES-256).
- **Secrets Management:** API keys for external integrations (e.g., Verra credentials) are never stored in plaintext. They are stored in a dedicated Secrets Manager (e.g., AWS KMS, HashiCorp Vault).

## 5. Audit Logging

Every write operation (POST, PUT, DELETE) triggers an asynchronous audit event.
- **Payload:** `Actor (User ID)`, `Action (e.g., UPDATE_PROJECT)`, `Resource (Project ID)`, `Timestamp`, `IP Address`, `Diff (Old State -> New State)`.
- **Storage:** Audit logs are written to an append-only, immutable datastore separate from the operational database, ensuring that even Database Administrators cannot erase the trail.
