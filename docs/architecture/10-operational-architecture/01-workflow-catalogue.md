# Enterprise Workflow Catalogue

Workflows define how state transitions are orchestrated across multiple actors over time. The CIOS classifies workflows by their business objective.

## 1. Compliance & Approval Workflows

These workflows are characterized by strict multi-step gates, often requiring cryptographic signatures and spanning multiple organizations.

### 1.1 Project Validation Workflow
**Purpose:** Ensure a newly drafted Project complies with National and Registry policies before it can issue credits.
- **Initiator:** Developer (Programme Manager).
- **Steps:**
  1. Developer submits Draft PDD.
  2. Platform automatically cross-checks Spatial Boundaries against Jurisdiction rules (Spatial Query Service).
  3. PDD is assigned to an independent VVB organization.
  4. VVB Auditor 1 reviews and drafts Validation Statement.
  5. VVB Auditor 2 performs QA and digitally signs Approval.
  6. Platform promotes Project to `REGISTERED`.

### 1.2 Verification & Issuance Workflow
**Purpose:** Transform raw field evidence into issued carbon credits.
- **Initiator:** Field Agent.
- **Steps:**
  1. Agent uploads evidence (photo + GPS).
  2. AI Analytics scans for anomalies (e.g., duplicate image).
  3. Internal Verifier approves evidence batch.
  4. External VVB Auditor samples batch and approves.
  5. Compliance Engine runs Carbon Calculation formula based on methodology.
  6. Ledger Module initiates Sync to Verra/National Registry.
  7. Upon Registry confirmation, Platform mints local Carbon Credits.

## 2. Operational Workflows

These govern the day-to-day interactions within the platform.

### 2.1 Organization Onboarding Workflow
**Purpose:** Securely provision a new tenant workspace.
- **Steps:**
  1. User submits Registration Form + KYB Docs.
  2. Super Admin receives Task.
  3. Super Admin approves; Platform creates Tenant, isolates DB rows, configures branding.
  4. Platform emails Org Admin with temporary credentials.

### 2.2 Asset Deployment Workflow
**Purpose:** Install and register a physical asset in the field.
- **Steps:**
  1. Offline Mobile App scans Asset QR/Serial.
  2. Captures GPS and Timestamp.
  3. When back online, Sync Engine pushes to Asset Module.
  4. Triggers `AssetCreated` event.

## 3. Background Workflows (Asynchronous)

These run without human intervention.

### 3.1 Registry Sync Engine
- **Trigger:** Nightly cron job (`0 0 * * *`).
- **Steps:** Pulls status of all `PENDING_ISSUANCE` batches from external Registries. Updates local DB. Emits `CreditIssued` events for successful syncs.

### 3.2 Automated Anomaly Detection
- **Trigger:** `EvidenceUploaded` event.
- **Steps:** AI models scan photos for EXIF tampering, incorrect geographical bounding boxes, or statistical anomalies in IoT telemetry compared to historical baselines. Flags are added to the Auditor Dashboard.
