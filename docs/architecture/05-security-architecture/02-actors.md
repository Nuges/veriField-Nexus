# Enterprise User Role & Actor Architecture

An Actor is any entity capable of performing an action within the CIOS. Actors include human personas, organizations (when acting collectively), and system service accounts.

## 1. Actor Typology

### 1.1 Human Actors
- **Super Admin:** Platform operators managing the global infrastructure, cross-tenant policies, and system-wide overrides.
- **National Regulator:** Government officials defining jurisdictions, NDCs, and national climate policies.
- **Registry Operator:** Administrators from standard bodies (e.g., Verra) managing methodology updates and credit issuance approval.
- **Programme Manager (Developer):** Designs and submits Projects for validation, oversees portfolio performance.
- **Field Agent (Developer/Subcontractor):** Ground personnel using mobile apps to register assets and capture evidence.
- **Verifier (Developer/3rd Party):** Desktop QA analysts reviewing evidence uploaded by Field Agents against baseline expectations.
- **Auditor (VVB):** Independent third-party reviewers validating Project Design Documents (PDDs) and verifying emission reduction claims.
- **Corporate ESG Buyer:** End consumers purchasing or retiring credits to offset emissions.

### 1.2 System Actors (Machine Identities)
- **IoT Ingestion Gateway:** Service accounts authenticating smart meters or sensors pushing continuous telemetry data.
- **Registry Sync Worker:** Background jobs authenticating against external registries (via API Gateway) to synchronize ledger states.
- **AI Analytics Engine:** Internal services with read-only access to specific Data Products for forecasting.

## 2. Delegation & Approval Authority

- **Delegation:** A Programme Manager can delegate specific `Project` access to a Subcontractor organization. The delegated Field Agents operate under the permissions granted by the Developer, bounded by the Developer's tenant context.
- **Approval Chains:** Certain high-stakes actions require multi-signature approvals. For example, a VVB issuing a positive Audit requires two distinct Auditors within the VVB organization to digitally sign the transaction.

## 3. The Access Matrix Concept

Instead of hardcoding "If role == Field Agent", the application evaluates the Matrix:

`Can [Actor] perform [Action] on [Resource] given [Context]?`

- Actor: `User:123` (Role: Field Agent, Org: SolarCorp)
- Action: `UPDATE`
- Resource: `Asset:456`
- Context: `Asset:456 belongs to Project:789, owned by SolarCorp`.

Result: `ALLOW`.
