# ADR 001: Adopt Event-Driven Architecture (EDA) for Cross-Domain Communication

## Context
As VeriField Nexus scales, synchronous API calls between Bounded Contexts (e.g., MRV Module calling the Ledger Module) create tight coupling, cascading failures, and performance bottlenecks.

## Decision
We will adopt an Event-Driven Architecture (EDA) using an Event Bus (e.g., Kafka or EventBridge). Bounded Contexts will communicate exclusively by publishing and subscribing to immutable Domain Events.

## Consequences
**Positive:**
- Modules can be deployed and scaled independently.
- Provides a natural, immutable audit trail of system behavior.
- Simplifies integrating new consumers (e.g., adding an AI Analytics module simply requires subscribing to the existing event stream).

**Negative:**
- Eventual consistency is harder to reason about and debug than synchronous transactions.
- Requires robust Dead Letter Queue (DLQ) and retry mechanisms.

## Alternatives Considered
- **Synchronous REST/gRPC APIs:** Rejected due to tight coupling and poor resilience under load.
- **Database Triggers:** Rejected as an anti-pattern that hides business logic in the infrastructure layer.
