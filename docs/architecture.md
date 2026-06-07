# VeriField Nexus — 3-Layer System Architecture

VeriField Nexus provides verification infrastructure for real-world climate assets (RWA) and Measurement, Reporting, and Verification (MRV) systems. The platform bridges physical environmental inputs with digital green ledgers via a robust, trust-scored pipeline anchored to the Solana blockchain.

## 🏛️ Three-Layer Architecture

The system is split into three clean layers to guarantee data integrity, cryptographic auditability, and decentralization:

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

---

### 1. SDK Layer (Data Capture & Standardization)
- **Role**: Installed on edge devices, mobile audit tools, or smart IoT gateways.
- **Function**: Standardizes input coordinates (GPS bounds), timestamps, and hashes the raw photographic proof or telemetry array.
- **Security**: The capture module locks device identifiers and generates local hashes, ensuring evidence is immutable before network transmission.

### 2. Verification Layer (REST API & Trust Scoring)
- **Role**: Managed REST API layer that aggregates inputs and runs the Trust scoring engine.
- **Function**: 
  - Validates formatting, checks timestamp sequences, and analyzes physical evidence hashes.
  - Generates a **Trust Score (0-100)** evaluating data quality, GPS consistency, and tamper signatures.
  - Prepares the transaction metadata package for the blockchain layer.

### 3. On-Chain Layer (Solana State Logging)
- **Role**: Decentralized consensus and anchoring layer.
- **Function**: Logs the validated verification record (Evidence Hash, Trust Score, Asset Type) onto the Solana blockchain, securing an immutable public audit trail.

---

## ⚡ Why Solana?

VeriField Nexus is purpose-built to leverage the Solana blockchain:

1. **Sub-Second Finality**: Real-time validation of streaming IoT data or field worker submissions requires rapid transaction feedback to prevent pipeline backlog.
2. **Ultra-Low Fees**: Frequently logging device heartbeats or clean cookstove usage events on-chain requires transaction costs to be fractions of a cent ($0.00025 avg), making DePIN and micro-MRV systems financially viable.
3. **Decentralized Composability**: Storing RWA validation metrics directly in Solana accounts allows downstream DeFi protocols (e.g., green bonds, carbon marketplaces, yield vaults) to automatically read and consume live verification scores without relying on centralized oracles.
