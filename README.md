# VeriField Nexus

Private Measurement, Reporting, and Verification (MRV) SaaS Platform for tracking and validating environmental assets.

## Overview

VeriField Nexus is an enterprise-grade private SaaS platform designed for carbon developers and clean energy operators. The platform provides secure multi-tenant scoping, Super Admin governance, a closed approval-based onboarding flow, and a secure local database ledger to verify and audit coordinates, device telemetry, and image hashes from clean cookstove and solar grid installations.

## Core Modules

### Clean Cookstove Module
- Logs biomass utilization, coordinate distributions, and usage rates.
- Validates household deployment and calculates offset carbon credit metrics.

### Hybrid Energy Module
- Logs solar generation telemetry (kWh) and battery capacities.
- Tracks and verifies backup diesel generator runtime to quantify avoided fuel consumption.

## System Architecture

The codebase is organized as follows:
1. **Capture (Web PWA)**: Local-first edge capture client designed for field operations, featuring biometric coordinates locks, canvas-based image compression, and IndexedDB offline drafts caching.
2. **Verification (Backend API)**: Fast FastAPI verification engine that validates Coordinate accuracy, checks image hash similarity, calculates Trust Scores, and queues background quantification.
3. **Storage (Secure Ledger)**: PostgreSQL database with multi-tenant workspace isolation. Each verified asset is secured using SHA-256 state hashes and logged in the private audit ledger.

## Project Structure

- `backend/`: FastAPI REST API service, SQLAlchemy models, and trust engine logic.
- `dashboard/`: Next.js web application including the Field Capture PWA and tenant audit dashboards.
- `sdk/`: TypeScript client SDK containing helper libraries and payload validators.
- `mobile/`: Flutter field app client for offline-first operations.
- `scripts/`: Development utility scripts.
- `examples/`: Ingestion sample JSON payloads.

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.10+)

### Setup

To spin up the local development stack (FastAPI backend and Next.js dashboard):

```bash
./scripts/dev/run-local-mrv.sh
```

This script will install package dependencies, configure python virtual environments, and boot both the backend API (port 8000) and the Next.js web client (port 3000). Press `Ctrl+C` to stop all active services.

## License

Proprietary. Refer to the [LICENSE](file:///Users/segun/Documents/Verifield%20nexus/LICENSE) file for usage terms.
