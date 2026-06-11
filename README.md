# VeriField Nexus

VeriField Nexus is a Measurement, Reporting, and Verification (MRV) system for tracking and validating real-world climate assets.

## Overview

VeriField Nexus provides a structured, automated framework to verify climate payloads from real-world installations. By validating physical parameters—such as GPS coordinates, proof photos, and hardware telemetry—the system mitigates risks of double-counting and inaccurate reporting in climate projects, replacing manual audits with automated, trust-scored digital ledger records.

## Core Modules

### Cookstove Module
- Tracks biomass utilization and usage rates.
- Validates household deployment and associated emissions reduction.

### Hybrid Energy Module
- Tracks solar PV capacity, inverter telemetry, and backup diesel generator runtimes.
- Validates clean energy generation and avoided diesel fuel displacement.

## System Architecture

The system consists of three layers:

- **Capture**: Client-side SDK and IoT devices capture field data, record GPS coordinates, and compute perceptual hashes of proof images.
- **Validation**: REST API services execute the verification engine rules to detect duplicates, validate location ranges, and assign a trust score (0-100).
- **Storage**: Verified logs and trust scores are permanently recorded in a database or anchored on-chain for immutable auditability.

## Project Structure

- `/sdk`: TypeScript SDK containing verification schemas, validation helpers, and client integration utilities.
- `/backend`: FastAPI service that processes submissions, scores integrity, and executes verification algorithms.
- `/contracts`: Rust smart contracts for logging verified evidence and anchoring proof hashes.
- `/dashboard`: Next.js web application for monitoring telemetry feeds, viewing trust metrics, and auditing installations.
- `/docs`: Technical schemas and system configuration documentation.

## Getting Started

### Prerequisites

- Node.js (v18+)
- Python (3.10+)

### Setup

Install the workspace dependencies:

```bash
npm install
```

Start the FastAPI backend service:

```bash
npm run backend:dev
```

## Example Usage

The following example structures a validation payload using the SDK:

```typescript
import { createVerificationPayload, validatePayload } from "verifield-nexus-sdk";

const payload = createVerificationPayload(
  "hybrid_energy",
  { latitude: 4.8241, longitude: 7.0305, accuracy: 4.5 },
  Math.floor(Date.now() / 1000),
  "a855f7bacc153b82f6a855f7bacc153b82f6a855f7bacc153b82f6a855f7d2f4"
);

const { valid, errors } = validatePayload(payload);
if (!valid) {
  throw new Error(`Validation failed: ${errors?.join(", ")}`);
}
```

## Use Cases

### Cookstove MRV
Validating local microcontroller and usage survey data from biomass stoves to verify household emission reductions under methodology templates like GS TPDDTEC or Verra VMR0050.

### Hybrid Energy MRV
Monitoring real-time telemetry inputs from solar microgrids to verify grid/diesel displacement and issue verified displacement metrics under methodology templates like Verra AMS-I.F.

## Contributing

Contributions are welcome. Please open an issue first to discuss the changes you would like to make.

## License

MIT
