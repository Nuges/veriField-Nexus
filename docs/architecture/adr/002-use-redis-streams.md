# ADR 002: Adopt Redis Streams for Event-Driven Architecture Broker

## Context
ADR-001 approved the adoption of an Event-Driven Architecture (EDA) to enable asynchronous choreographies, decoupled domains, and audit logging. A decision is required on the underlying message broker technology. The primary candidates are Apache Kafka and Redis Streams.

The enterprise architecture demands high scalability, persistence, consumer groups, and retry mechanisms with Dead-Letter Queues (DLQ). The platform currently uses Redis for caching and RBAC session management.

## Decision
We will use **Redis Streams** as the primary event broker for the VeriField Nexus CIOS.

## Rationale
- **Infrastructure Simplicity:** Redis is already a deployed dependency. Introducing Kafka at this stage adds significant operational overhead (Zookeeper/Kraft, JVM tuning) without an immediate necessity for extreme log-retention scale.
- **Consumer Groups:** Redis Streams natively supports Consumer Groups, allowing for reliable at-least-once delivery, competing consumers, and message acknowledgement (`XACK`).
- **Pending Entries List (PEL):** Redis Streams tracks unacknowledged messages, allowing us to implement robust retry loops and DLQ mechanics via `XPENDING` and `XCLAIM`.
- **Latency & Performance:** Redis Streams operates entirely in-memory (with RDB/AOF persistence), providing sub-millisecond latency for event publishing.

## Consequences
### Positive
- Zero new infrastructural dependencies to manage.
- Immediate developer velocity with the existing `redis-py` async client.
- Built-in support for the required EDA capabilities (at-least-once delivery, consumer groups).

### Negative
- Redis Streams does not have the massive disk-based retention capacity of Kafka. We must configure `MAXLEN` limits and ensure consumers are actively processing streams to prevent memory exhaustion.
- Less mature ecosystem for stream processing compared to Kafka Streams or Flink, though sufficient for our current orchestration and audit needs.

## Alternatives Considered
- **Apache Kafka:** Excellent for massive scale and event sourcing, but introduces heavy operational burden. It remains an upgrade path if throughput exceeds Redis capabilities in Version 3.x (Platform Roadmap).
- **RabbitMQ:** Good for routing, but less suitable for immutable event logs where multiple distinct services (Audit, Reporting, Webhooks) need to consume the same event independently without complex exchange routing.
