# Enterprise Operational Model

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. The Day-to-Day Execution

Architecture is meaningless if it does not translate into efficient daily operations for the humans running the ecosystem. This document defines the operational sequences for the primary actors in VeriField Nexus.

## 2. Actor Operational Sequences

### 2.1 The Field Agent (Data Collection)
*Operates in low-bandwidth, harsh environments.*
1. **Morning Sync:** Connects to Wi-Fi at the regional office, opens the Nexus Mobile App, and clicks "Sync Tasks".
2. **Offline Execution:** Travels to a rural village. Scans a cookstove QR code. The app captures a geo-tagged photo and records a usage survey. All data is saved to the local device database and hashed.
3. **Evening Upload:** Returns to connectivity. The app automatically pushes the queue to the Nexus Ingestion Gateway.

### 2.2 The Internal Verifier (QA)
*Operates from a Developer's regional HQ.*
1. **Dashboard Review:** Logs into Nexus Web. The dashboard prioritizes a queue of newly uploaded evidence.
2. **Anomaly Investigation:** The AI Trust Engine flags an evidence photo as `HIGH RISK: POTENTIAL GPS SPOOFING`. The Verifier investigates the map overlay.
3. **Decisioning:** The Verifier either clicks "Request Rework" (sending a task back to the Field Agent) or clicks "Override & Verify" (attaching their digital signature).

### 2.3 The VVB Auditor (Independent Assurance)
*Operates globally.*
1. **Sampling:** Logs into their isolated Tenant. Uses the Audit Engine to generate a statistically random 5% sample of all Verified evidence for `Project Alpha`.
2. **Desk Review:** Reviews the photo, the telemetry, and the Verifier's notes for each sampled item.
3. **Issuance Request:** Confirms the sample passes. Digitally signs the "Validation Statement", triggering the Carbon Quantification engine.

### 2.4 The National Regulator (Government)
*Operates from an Environment Ministry.*
1. **National Dashboard:** Logs in to view a live map of the country. Sees every active project aggregated by Developer.
2. **NDC Tracking:** Views a real-time widget showing "Total tCO2e Reduced This Year" against the National Paris Agreement targets.
3. **Authorization:** Reviews a pending Article 6 export request. Clicks "Issue Letter of Authorization (LOA)", digitally recording the Corresponding Adjustment in the Nexus Ledger.

### 2.5 The Corporate Buyer (ESG Team)
*Operates from a corporate HQ.*
1. **Portfolio View:** Logs into their ESG Dashboard.
2. **Purchase/Retirement:** Selects 10,000 Verified Carbon Credits from a specific reforestation project in their supply chain geography. Clicks "Retire".
3. **Reporting:** Exports a compliant, cryptographically backed PDF certificate to attach to their annual Sustainability Report.

### 2.6 The Platform Administrator (Super Admin)
*Operates the CIOS Infrastructure.*
1. **Tenant Provisioning:** Reviews KYB documents for a newly applied Project Developer. Clicks "Provision Tenant".
2. **Registry Federation Health:** Monitors the background sync queues. Notices the Verra API is returning 500 errors; pauses the outbound queue to prevent thrashing.

## 3. Architecture Traceability
- **Dependent Documents:** `05-security-architecture/02-actors.md`, `08-ui-architecture/01-ui-layout.md`.
- **Primary Artifacts:** UX/UI Flows, Persona Definitions.
