# VeriField Nexus: Operations Manual & SRE Runbook

## 1. System Overview
VeriField Nexus is a Level 5 Climate Infrastructure Operating System (CIOS) designed for high-frequency IIoT telemetry ingestion and cryptographic digital twin validation. The architecture relies on an asynchronous event-driven core powered by FastAPI, PostgreSQL, Redis, and MQTT.

## 2. Standard Operating Procedures (SOPs)

### 2.1 Deployment Checklist
1. **Infrastructure Provisioning**: Deploy isolated VPCs, managed PostgreSQL (with PgBouncer), Redis Cluster, and MQTT Brokers.
2. **Database Migrations**: Run `alembic upgrade head` pre-flight. Ensure no breaking schema changes.
3. **Environment Variables**: Inject all secrets (`SUPABASE_KEY`, `JWT_SECRET`) securely via Vault or AWS Secrets Manager.
4. **Health Check Validation**: Verify `/api/v1/system/health` returns `200 OK` across all nodes.
5. **Load Balancer Cutover**: Route 10% traffic (Canary) -> 100% traffic.

### 2.2 Rollback Plan
1. **Detect Issue**: Alert triggers on P95 latency > 200ms or Error Rate > 1%.
2. **Traffic Reversal**: Route LB traffic back to the previous stable release.
3. **Database Downgrade**: If schema changes are breaking, execute `alembic downgrade -1`.
4. **Post-Mortem**: Collect `ERROR` level logs and Dead-Letter Queue (DLQ) payloads for analysis.

### 2.3 Disaster Recovery (DR)
- **Database Partition**: Services automatically fall back to PgBouncer connection queueing. 
- **Redis Node Failure**: High Availability (HA) cluster promotes replica to master in < 2 seconds.
- **MQTT Broker Split-Brain**: Edge devices buffer offline via SQLite until broker quorum is re-established. Payloads are replayed with internal sequence IDs to prevent deduplication logic drops.

## 3. Known Limitations
- **Sequence Buffering**: Edge devices holding more than 50,000 offline payloads may experience a spike in CPU overhead during the replay burst.
- **Twin Re-calculation Limits**: Modifying a historical calculation configuration will trigger a cascading re-evaluation of all child assets. This should be performed during off-peak hours to avoid blocking the primary ingestion queue.
