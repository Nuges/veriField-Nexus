# Data Flow Lifecycle

This document describes the end-to-end data lifecycle in the VeriField Nexus infrastructure, mapping how data transitions from raw field inputs to secure, trust-scored blockchain records.

## Sequence Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. Capture  │────▶│ 2. Validate  │────▶│   3. Hash    │────▶│    4. API    │
│ (Field/IoT)  │     │  (Local SDK) │     │ (Crypto Proof)     │ (TrustEngine)│
└──────────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                      │
                                                                      ▼
┌──────────────┐     ┌──────────────┐                         ┌──────┴───────┐
│   Ledger     │◀────│  6. Anchor   │◀────────────────────────│   5. Score   │
│  (Solana)    │     │  (On-Chain)  │                         │(Metadata Pkg)│
└──────────────┘     └──────────────┘                         └──────────────┘
```

---

### Step 1: Capture (Field / IoT Devices)
- **Action**: A physical field installation occurs (e.g., a solar hybrid setup or clean cookstove delivery).
- **Inputs**: Raw sensors capture GPS coordinates, Unix epoch timestamp, device serial, and proof images.

### Step 2: Validate (Local SDK)
- **Action**: The VeriField TS/JS SDK parses the inputs to verify format integrity.
- **Rule**: Rejects malformed payload formats locally before initiating any costly network requests.

### Step 3: Hash (Evidence Hashing)
- **Action**: The SDK hashes the verification proof (photo or raw telemetry array) using the `SHA-256` hashing standard.
- **Outcome**: Converts large raw inputs into a lightweight, fixed-size 32-byte cryptographic identifier (`imageHash`).

### Step 4: API (Ingest & Process)
- **Action**: The verification payload is securely POSTed to the backend API (`/api/v1/verify`).
- **Function**: Re-verifies constraints and queries historic ledger inputs to check for duplicate entry submissions.

### Step 5: Score (Trust Engine)
- **Action**: The scoring service analyzes indicators:
  - GPS boundaries versus target project scope.
  - Timestamp continuity.
  - Image hash collision/uniqueness.
- **Outcome**: Assigns a numeric **Trust Score (0-100)** to the payload.

### Step 6: Anchor (Solana Logging)
- **Action**: The verification record (Asset Type, Trust Score, and cryptographic Evidence Hash) is submitted to the Solana smart contract.
- **On-chain State**: Writes to a Solana PDA (Program Derived Address), producing an immutable on-chain confirmation signature.
