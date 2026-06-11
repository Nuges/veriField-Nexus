# VeriField Nexus

Measurement, Reporting, and Verification (MRV) system for tracking and validating real-world climate assets.

## Overview

VeriField Nexus provides a local database ledger and smart contract program to verify data payloads from physical cookstove and solar grid installations. The system uses a verification engine to score raw coordinates, device telemetry, and image hashes to check for duplicates and outliers, saving audit logs locally and anchoring proofs on-chain.

## Core Modules

### Cookstove Module
- Logs biomass utilization and usage rates.
- Validates household deployment and calculates emissions reductions.

### Hybrid Energy Module
- Logs solar generation telemetry (kWh) and battery capacities.
- Tracks and verifies diesel backup generator runtime to measure avoided fuel consumption.

## System Architecture

The codebase is split into three main parts:
1. **Capture (SDK / Clients)**: Packages data payloads locally on edge devices/mobile, computes SHA-256 image hashes, and records GPS coordinates.
2. **Validation (Backend API)**: Processes submissions, runs location accuracy algorithms, performs duplicate checks, and assigns trust scores.
3. **Storage (Ledger)**: Persists audit logs in the PostgreSQL database and writes proof anchors and scores to the Solana blockchain via Program Derived Addresses (PDAs).

## Project Structure

- `backend/`: FastAPI REST API service, SQLAlchemy database models, and local validation engine logic.
- `contracts/`: Anchor Rust workspace for deploying on-chain verification programs and running integration tests.
- `dashboard/`: Next.js web dashboard for auditing telemetry inputs and monitoring field agent uploads.
- `sdk/`: TypeScript client SDK containing helper libraries and payload validators.
- `mobile/`: Flutter field app code for offline captures.
- `scripts/`: Dev scripts for seeding data, clearing logs, and running local services.
- `examples/`: Sample JSON payloads for testing endpoint ingestion.

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- Solana CLI & Anchor CLI (Optional, only needed to compile/test smart contracts)

### Setup

To spin up the entire local dev environment (FastAPI backend and Next.js dashboard):

```bash
./scripts/dev/run-local-mrv.sh
```

This script will install npm packages, sync the python virtual environment, clear port conflicts, and start both uvicorn (port 8000) and the dashboard client (port 3000) in the background. Press `Ctrl+C` to cleanly shut down all services.

### Testing Contracts

To run the Solana Anchor integration tests (spins up local validator, builds, deploys, and verifies PDA anchors):

```bash
cd contracts
npm install
anchor test
```

## Example Usage

Create a new payload:

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

## License

MIT
