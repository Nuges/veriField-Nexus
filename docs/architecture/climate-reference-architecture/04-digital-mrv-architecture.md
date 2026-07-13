# Enterprise Digital MRV Architecture

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. Overview of Digital MRV

Monitoring, Reporting, and Verification (MRV) is traditionally the most expensive and error-prone phase of the climate value chain. VeriField Nexus digitizes this entirely, shifting from paper-based, sampling-heavy audits to continuous, population-level cryptographic verification.

## 2. The MRV Engine Subsystems

The Enterprise Digital MRV Architecture is composed of several interdependent engines that process reality into verified data.

### 2.1 The Evidence & Monitoring Engine
- **IoT Integration:** Direct ingestion of telemetry (e.g., thermal sensor logs from a biochar kiln).
- **Remote Sensing & Satellite:** Ingests geospatial raster data (e.g., NDVI indexes for deforestation tracking) via integration with providers like Planet or Sentinel-2.
- **Edge Data Collection:** Field Agents use offline-first mobile applications to capture structured survey data, GPS polygons, and photos. 
- **Cryptographic Hashing:** All data is hashed immediately upon creation (`SHA-256`) to guarantee provenance and immutability.

### 2.2 The Trust Engine (Data Integrity)
Before any data reaches a human verifier, the Trust Engine evaluates its physical impossibility.
- Checks if GPS coordinates jump thousands of miles in minutes.
- Checks for EXIF data manipulation or stripped metadata.
- Validates that the device timestamp was derived from a secure NTP server, not locally altered.

### 2.3 The Risk Engine (Anomaly Detection)
Uses statistical models and AI to score the likelihood of fraud or human error.
- Compares the uploaded photo against a database of known stock images or previously uploaded project photos to detect duplicates.
- Evaluates statistical variance in sensor data (e.g., a cookstove registering usage 24 hours a day).
- Flags high-risk evidence for mandatory manual review, while auto-verifying low-risk evidence.

### 2.4 The Verification Engine (Internal QA)
The developer's internal quality assurance workflow.
- Verifiers are presented with a dashboard prioritizing `QUARANTINED` or high-risk evidence.
- Verifiers can request rework from the field agent or definitively approve the evidence, attaching their digital signature.

### 2.5 The Sampling & Audit Engine (External VVB)
- **Methodological Sampling:** Instead of reviewing 100,000 cookstoves, the registry methodology dictates a statistically significant sample size (e.g., 90/10 confidence/precision).
- The Audit Engine automatically generates a randomized, un-biasable sample set from the verified population.
- The external VVB uses this engine to review the sample, leaving immutable audit notes.

### 2.6 The Carbon Quantification Engine
- Translates verified facts into carbon reality.
- Executes the parameterized formulas (defined in the Methodology Architecture) against the audited evidence dataset to calculate the precise `tCO2e` emission reductions or removals.

## 3. Architecture Traceability
- **Dependent Documents:** `10-climate-intelligence-architecture.md`, `11-climate-data-architecture.md`
- **Primary Actors:** Field Agents, Verifiers, Auditors (VVBs).
- **Primary Entities:** `Evidence`, `TelemetryData`, `AuditStatement`.
- **Produced Events:** `EvidenceUploaded`, `AnomalyDetected`, `VerificationCompleted`, `AuditApproved`.
