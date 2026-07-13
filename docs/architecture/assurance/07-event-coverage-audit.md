# 07 — Event Coverage Audit

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Existing Domain Events

The platform uses a custom event publishing system (`app.core.events.publisher.publish_event`).

| Event Type | Producer Domain | Consumer(s) | Payload | Trigger | Retries | Ordering | Idempotency | Audit | Notifications | Jobs | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `activity.created` | `activities` | ❌ None documented | ⚠️ | Service create | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Fire-and-forget |
| `activity.updated` | `activities` | ❌ | ⚠️ | Service update | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Fire-and-forget |
| `asset.created` | `assets` | ❌ | ⚠️ | Service create | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Fire-and-forget |
| `user.created` | `authentication` | ❌ | ⚠️ | Service create | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Fire-and-forget |
| `organization.created` | `organizations` | ❌ | ⚠️ | Service create | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Fire-and-forget |
| `project.created` | `projects` | ❌ | ⚠️ | Service create | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Fire-and-forget |
| `project.approved` | `projects` | ❌ | ⚠️ | Service approve | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Fire-and-forget |
| `workspace.created` | `workspaces` | ❌ | ⚠️ | Service create | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Fire-and-forget |

## Missing Events (Required by Architecture)

| Event Type | Architecture Source | Severity | Notes |
| :--- | :--- | :--- | :--- |
| `evidence.uploaded` | `04-digital-mrv` | 🔴 Critical | Core MRV lifecycle event. |
| `anomaly.detected` | `04-digital-mrv` | 🔴 Critical | Trust Engine output. |
| `verification.completed` | `04-digital-mrv` | 🔴 Critical | Internal QA completion. |
| `audit.approved` | `04-digital-mrv` | 🔴 Critical | VVB approval. Triggers carbon quantification. |
| `credit.issued` | `05-registry-fed` | 🔴 Critical | Ledger minting event. |
| `credit.retired` | `05-registry-fed` | 🔴 Critical | Permanent burn event. |
| `credit.transferred` | `05-registry-fed` | 🔴 Critical | Ownership change. |
| `programme.created` | `08-programme` | 🔴 Critical | Programme lifecycle. |
| `programme.approved` | `08-programme` | 🔴 Critical | Programme lifecycle. |
| `jurisdiction.created` | `07-spatial` | 🟠 High | Governance lifecycle. |
| `compliance.violated` | `06-governance` | 🟠 High | Policy enforcement. |
| `registry.sync.failed` | `05-registry-fed` | 🟠 High | Federation health. |
| `benefit.distributed` | `03-climate-finance` | 🟡 Future | Revenue sharing. |

## Event Infrastructure Assessment

| Concern | Status | Notes |
| :--- | :--- | :--- |
| Event Bus / Broker | ❌ | No Kafka, RabbitMQ, or Redis Streams. Events are published in-process only. |
| Event Persistence | ❌ | Events are not stored. No event sourcing or replay capability. |
| Dead Letter Queue (DLQ) | ❌ | No DLQ for failed event processing. |
| Event Ordering Guarantees | ❌ | No ordering. |
| Subscriber Registration | ❌ | No subscriber pattern. Events are fire-and-forget. |
| Idempotency | ❌ | No event IDs for deduplication. |

> [!CAUTION]
> The Event-Driven Architecture (ADR-001) is architecturally approved but fundamentally not implemented. All 8 existing events are fire-and-forget with no consumers, no persistence, no retries, and no broker. 13 critical domain events required by the architecture are entirely missing.
