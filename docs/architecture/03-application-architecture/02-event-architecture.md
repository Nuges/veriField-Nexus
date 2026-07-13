# Enterprise Event Architecture

VeriField Nexus heavily utilizes an Event-Driven Architecture (EDA) to ensure modules remain decoupled and to provide an immutable audit trail of system behavior.

## Event Principles

1. **Events are Facts:** They represent something that *has already happened* in the past (e.g., `ProjectRegistered`). They are immutable.
2. **Fat Payloads vs. Thin Payloads:** The system uses "Event-Carried State Transfer" (fat payloads) for internal module communication to reduce callback API queries, but uses "Event Notification" (thin payloads with URIs) for external webhooks.
3. **At-Least-Once Delivery:** The event bus guarantees delivery. Consumers must be idempotent.

## Core Event Catalogue

### Operations Domain Events

| Event Name | Producer | Trigger | Payload Summary | Primary Consumers |
| :--- | :--- | :--- | :--- | :--- |
| `ProjectSubmitted` | `operations-module` | Developer submits a draft PDD. | `projectId`, `tenantId`, `metadata` | `governance-module` (validation), `notification-module` |
| `ProjectRegistered` | `operations-module` | Project passes compliance. | `projectId`, `methodologyId` | `mrv-module` (baseline creation) |
| `AssetDeployed` | `operations-module` | Field agent registers a new asset. | `assetId`, `gpsCoords`, `type` | `mrv-module` (start telemetry listeners) |

### MRV Domain Events

| Event Name | Producer | Trigger | Payload Summary | Primary Consumers |
| :--- | :--- | :--- | :--- | :--- |
| `EvidenceUploaded` | `mrv-module` | Blob storage accepts new evidence. | `evidenceId`, `projectId`, `uri` | `analytics-module` (AI scanning) |
| `VerificationCompleted` | `mrv-module` | Verifier signs off on evidence. | `verificationId`, `status` | `mrv-module` (triggers Audit workflow) |
| `AuditApproved` | `mrv-module` | VVB issues a positive validation statement. | `auditId`, `projectId`, `tCO2e` | `ledger-module` (trigger issuance) |

### Ledger & Governance Events

| Event Name | Producer | Trigger | Payload Summary | Primary Consumers |
| :--- | :--- | :--- | :--- | :--- |
| `CreditIssued` | `ledger-module` | Credits are minted on the ledger. | `batchId`, `serialNumbers` | `registry-adapter` (external sync), `notification-module` |
| `PolicyUpdated` | `governance-module` | Regulator changes a jurisdiction rule. | `jurisdictionId`, `policyDiff` | `operations-module` (flag non-compliant projects) |

## Event Infrastructure

The CIOS will utilize a robust message broker (e.g., Apache Kafka or AWS EventBridge) for domain events.
- **Topics:** Events are partitioned by Bounded Context (e.g., `mrv-events`, `ledger-events`).
- **Schema Registry:** All event payloads are strongly typed using Protobuf or JSON Schema to prevent breaking changes for downstream consumers.
- **Dead Letter Queues (DLQ):** Failed event processing (e.g., a database timeout in a consumer) is routed to a DLQ for manual intervention and replay.
