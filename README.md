# VeriField Nexus

> Verification Infrastructure for Real-World Climate Assets on Solana

VeriField Nexus is a decentralized Measurement, Reporting, and Verification (MRV) infrastructure framework. It enables climate projects, DePIN hardware networks, and environmental asset developers to standardise, trust-score, and cryptographically anchor real-world asset (RWA) data directly onto the Solana blockchain.

---

## 📣 Public Goods Declaration

**This project is partially open-source and designed as public infrastructure for Solana developers building real-world asset verification and environmental DePIN systems.**

To encourage collaborative ecosystem building while protecting proprietary operational intelligence, the codebase is structured as follows:

| Layer / Component | Licensing / Open-Source Status |
| :--- | :--- |
| **TypeScript SDK (`/sdk`)** | **Fully Open-Source (MIT)** — Integrations, captures, and client validation helpers. |
| **JSON Schemas (`/docs/schema.json`)** | **Public Domain** — Asset specifications for climate metrics. |
| **FastAPI REST API (`/backend/src`)** | **Open-Source Core (MIT)** — Payload validation routes and transaction builders. |
| **Anchor Program (`/contracts`)** | **Open-Source (MIT)** — On-chain state logs for environmental evidence. |
| *Scoring Rules Tuning* | *Proprietary* — Deep-learning anomaly weights and specific scoring thresholds. |
| *Operational Dashboards* | *Proprietary* — Local monitoring and alerting integration configs. |

---

## ❌ The Problem

Traditional MRV systems in voluntary carbon markets and green finance suffer from structural bottlenecks:
- **Opaque & Siloed Data**: Field data calculations are hidden inside proprietary databases, leading to double-counting and carbon credit trust issues.
- **Slow & Expensive**: Auditing verification records manually can take months and cost tens of thousands of dollars.
- **Incompatible with DeFi**: Climate tokens and green bonds cannot dynamically query verified evidence, preventing automated capital markets from scaling.

---

## 🚀 The Solution

VeriField Nexus solves this via a unified **Capture ➔ Validate ➔ Anchor** pipeline:
1. **Secure Capture**: Edge IoT devices and mobile field kits structure proof data locally.
2. **Deterministic Validation**: The Verification Engine scores the data based on location boundaries, timestamp continuity, and image uniqueness.
3. **Solana Anchoring**: Validated evidence hashes and trust scores are permanently written on-chain to Solana Program Derived Addresses (PDAs).

---

## ⚡ Why Solana?

VeriField Nexus is engineered to leverage Solana's high-performance blockchain network:

- **Sub-Second Finality**: Streaming telemetry from millions of DePIN IoT sensors requires sub-second processing and confirmation times to prevent network ingestion delays.
- **Ultra-Low Cost**: Logging hourly device heartbeats or clean cookstove sessions on-chain requires transaction costs to be fractions of a cent ($0.00025 avg), making micro-MRV operations economically viable.
- **Composability**: Storing RWA validation metrics directly in Solana accounts allows downstream DeFi applications (carbon offset pools, green lending protocol yield vaults) to read verification metrics instantly without trusting a centralized intermediary.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│                      1. SDK LAYER                      │
│      (Data Capture, GPS Logging & SHA-256 Hashing)     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   2. VERIFICATION LAYER                │
│       (FastAPI API, Anomaly Detection & Trust Scoring)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                    3. ON-CHAIN LAYER                   │
│         (Solana Program, Immutable Proof Anchor)       │
└────────────────────────────────────────────────────────┘
```

Detailed architectural blueprints are available in [docs/architecture.md](file:///Users/segun/Documents/Verifield%20nexus/docs/architecture.md).

---

## 📦 Use Cases

### 1. Solar Hybrid Energy Systems
Verifying solar output generation, grid usage ratios, and diesel backup displacement logs to issue clean energy offset tokens.
### 2. Clean Cookstoves (TPDDTEC & VMR0050)
Validating local microcontroller thermal readings from biomass stoves to confirm household emissions avoidance.
### 3. DePIN Hardware Networks
Securing a trust score layer for decentralised networks logging environmental factors (temperature, air quality, soil moisture).

---

## 🌍 Live Pilot
Our production deployment is currently running a live pilot verifying hybrid solar microgrid installations in **Port Harcourt, Nigeria**, processing real-time telemetry inputs and ensuring carbon avoidance logs match physical generator displacement.

---

## 🛠️ Quick Start

### 1. Installation
Install project dependencies at the root:
```bash
npm install
```

### 2. Run the Backend API
Start the FastAPI verification service (running on `http://localhost:8000`):
```bash
npm run backend:dev
```

### 3. Run the E2E Verification Demo
Execute the demo script to send a mock climate payload to the Verification Engine:
```bash
./scripts/demo.sh
```

---

## 🔗 Example verification Flow

The following example structures a payload using the SDK, validates it, and posts it to the verification ledger:

```typescript
import { createVerificationPayload, validatePayload } from "verifield-nexus-sdk";

// 1. Structure the evidence payload
const payload = createVerificationPayload(
  "hybrid_energy",
  { latitude: 4.8241, longitude: 7.0305, accuracy: 4.5 },
  Math.floor(Date.now() / 1000),
  "a855f7bacc153b82f6a855f7bacc153b82f6a855f7bacc153b82f6a855f7d2f4"
);

// 2. Validate format integrity
const { valid, errors } = validatePayload(payload);
if (!valid) {
  throw new Error(`Validation failed: ${errors?.join(", ")}`);
}

// 3. Dispatch to Ledger
// POST /api/v1/verify
```

---

## 🗺️ Roadmap & Grant Milestones

- [x] **Milestone 1**: 3-Layer MRV Architecture Specification & SDK Core.
- [x] **Milestone 2**: Ingestion engine with Trust Scoring and simulated Anchor transactions.
- [ ] **Milestone 3**: Anchor Rust program deployment on Solana Devnet.
- [ ] **Milestone 4**: Downstream DeFi token pool integration.
