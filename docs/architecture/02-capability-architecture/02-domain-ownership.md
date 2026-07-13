# Domain Ownership Architecture

To prevent the "Big Ball of Mud" anti-pattern, the VeriField Nexus CIOS enforces strict Domain Ownership. Every capability and module must belong to a specific Bounded Context, owned by a defined engineering or business domain.

## Principles of Domain Ownership

1. **Database Isolation:** A domain is the sole owner of its database tables. Other domains CANNOT read or write directly to those tables.
2. **Explicit Contracts:** Cross-domain communication must occur via explicit, versioned APIs or Published Domain Events.
3. **Autonomous Evolution:** A domain team should be able to deploy updates to their module without requiring coordinated deployments across the platform.

## Domain Matrix

| Bounded Context | Owner Team | Primary Modules | Subscribed Events | Published Events | Direct Database Access |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IAM Domain** | Platform Security | `auth`, `users`, `roles` | `OrgSuspended` | `UserCreated`, `RoleGranted` | `users`, `sessions`, `policies` |
| **Organization Domain** | Platform Admin | `organizations`, `tenants` | `None` | `OrgCreated`, `OrgArchived` | `organizations`, `tenant_configs` |
| **Governance Domain** | Compliance Engineering | `jurisdictions`, `frameworks` | `ProjectSubmitted` | `PolicyUpdated`, `ComplianceFailed` | `jurisdictions`, `methodologies` |
| **Operations Domain** | Asset Engineering | `projects`, `assets` | `CompliancePassed` | `ProjectRegistered`, `AssetCreated` | `projects`, `assets`, `programmes` |
| **MRV Domain** | Field Engineering | `monitoring`, `verification` | `AssetCreated` | `EvidenceSubmitted`, `VerificationDone` | `evidence`, `telemetry`, `audits` |
| **Ledger Domain** | Financial Engineering | `accounting`, `issuance` | `AuditApproved` | `CreditIssued`, `CreditRetired` | `ledger_transactions`, `credits` |
| **Analytics Domain** | Data Engineering | `reports`, `dashboards` | `* (All Events)` | `ReportGenerated` | `analytics_snapshots` (Read-Only Replica) |

## Event Choreography vs. Orchestration

- **Choreography (Default):** Domains react to events organically. For example, the `MRV Domain` listens for `AssetCreated` from the `Operations Domain` to automatically schedule a baseline verification task. Neither domain knows about the internal logic of the other.
- **Orchestration (Exception):** Used only for complex, multi-stage, distributed transactions (e.g., processing a multi-jurisdictional registry sync) where a dedicated Workflow Engine coordinates the state across domains using the Saga pattern.
