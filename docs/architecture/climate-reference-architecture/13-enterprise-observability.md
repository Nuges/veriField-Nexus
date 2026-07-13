# Enterprise Observability

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. Operating a Global Climate Node

VeriField Nexus acts as a central node in the global climate infrastructure network. Because its outputs (Carbon Credits, Article 6 adjustments) have sovereign and financial consequences, the system must be entirely observable. "Black box" operations are fundamentally incompatible with climate trust.

## 2. Layers of Observability

Observability extends far beyond simple CPU/Memory metrics. The CIOS monitors health across six distinct layers.

### 2.1 Platform Health (Infrastructure)
- **Metrics:** Uptime (target: 99.99%), API Gateway Latency, Database Connection Pool Saturation, Background Worker Queue Depth.
- **Tools:** Datadog, Prometheus, Grafana, AWS CloudWatch.

### 2.2 Integration Health (Federation)
- **Metrics:** 
  - *Registry Sync Success Rate:* Percentage of `IssueCredit` API calls to Verra/Gold Standard that return 200 OK.
  - *IoT Ingestion Lag:* Time difference between a sensor emitting a payload and the CIOS inserting it into TimescaleDB.
  - *Dead Letter Queue (DLQ) Volume:* Number of failed outgoing webhooks to Corporate ERPs.

### 2.3 AI & Intelligence Health
- **Metrics:**
  - *Model Drift:* Monitoring if the Computer Vision anomaly detection is generating significantly more false positives than historical baselines.
  - *Auto-Verification Rate:* The percentage of evidence automatically verified by AI without human intervention (key efficiency KPI).

### 2.4 Compliance Health
- **Metrics:**
  - *Policy Violations:* Number of projects transitioning to `SUSPENDED` due to real-time spatial overlaps or leakage detected by satellite.
  - *Audit Failure Rate:* Percentage of Evidence batches rejected by third-party VVBs. A high rate indicates poor internal verification processes.

### 2.5 Operational Health (Business KPIs)
- **Metrics:**
  - *Active Field Agents:* Number of distinct users submitting evidence daily.
  - *Time-to-Issuance:* The average duration (in days) between an Asset being deployed and its first Carbon Credit being minted on the ledger.
  - *Total AUM (Assets Under Management):* Physical climate assets currently active and reporting telemetry.

### 2.6 Ecosystem Health (Macro)
- **Metrics:**
  - *Global Registry Synchronization:* Uptime of external standard bodies. If the Verra API is down, the Nexus dashboard displays an "Ecosystem Degradation" warning, letting users know syncs are delayed but internal operations remain unaffected.

## 3. Transparency & Incident Response
In a CIOS, certain alerts do not just page DevOps; they page Compliance Officers. If a massive batch of evidence is retroactively found to be spoofed, an automated incident response workflow freezes the associated Carbon Credits from trading until the anomaly is resolved.
