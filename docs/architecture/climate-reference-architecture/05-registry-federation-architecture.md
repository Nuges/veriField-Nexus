# Enterprise Registry Federation Architecture

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. The Need for Federation

There is no single "Global Carbon Registry." The market is fragmented across National Registries (for compliance and Article 6 transfers) and Independent Standards Registries (Verra, Gold Standard, CAR) for the Voluntary Carbon Market. 
VeriField Nexus does not attempt to usurp these authorities. Instead, it acts as a meta-registry, federating data across them to provide developers with a single operational view while maintaining strict synchronization with the ultimate ledgers of record.

## 2. Supported Federation Targets
- **Independent Standard Registries:** APIs for Verra, Gold Standard, Puro.earth.
- **National Carbon Registries:** e.g., the Rwanda Carbon Registry, Singapore's Climate Impact X (CIX).
- **Meta-Ledgers & Climate Data Hubs:** e.g., The World Bank's Climate Warehouse (CAD Trust).
- **Corporate Internal Registries:** Private ledgers tracking internal supply chain (Scope 3) emissions.

## 3. The Federation Lifecycle

### 3.1 Registration Sync
When a Project is registered in Nexus, the Federation Engine securely pushes the PDD and spatial boundaries to the target external registry. Nexus stores the external `registry_project_id` to establish the mapping.

### 3.2 Duplicate Prevention & Conflict Resolution
Before syncing, Nexus queries the CAD Trust or the target registry to ensure the spatial boundaries or asset serial numbers do not already exist on another ledger.
- **Conflict:** If a jurisdiction overlap is detected, the `Project` state transitions to `SUSPENDED` locally and a conflict resolution workflow is initiated for human review.

### 3.3 Issuance & Retirement Sync
Nexus does not mint the final carbon credit on the external market.
1. Nexus generates the `AuditApproved` event with the verified `tCO2e` volume.
2. The Federation Adapter calls the target registry's Issuance API.
3. The registry mints the credits and returns an array of Serial Numbers.
4. Nexus stores these serial numbers locally to track inventory.
5. If an asset is retired on Nexus, an API call is made to the registry to burn the serial numbers.

### 3.4 Interoperability & Offline Recovery
- **Idempotency:** All calls to external registries carry a unique idempotency key (derived from the Nexus Event ID). This ensures that if a network partition occurs and Nexus retries the sync, the external registry does not double-issue credits.
- **Offline Recovery:** If an external registry is down, the Nexus Adapter queues the sync requests in a durable Dead Letter Queue (DLQ). A background worker continuously attempts recovery using an exponential backoff strategy.

## 4. Adapter Lifecycle

The Federation Architecture uses a plugin model. New registries can be added without changing the core Ledger module.
- Each Adapter implements a standard interface: `registerProject()`, `issueCredits()`, `retireCredits()`, `getHealthStatus()`.

## 5. Architecture Traceability
- **Dependent Documents:** `05-security-architecture/01-auth-rbac.md` (for storing API keys), `07-integration-architecture/01-integration-catalogue.md`.
- **Primary Actors:** Registry Operators, Platform Operators.
- **Consumed Events:** `ProjectApproved`, `AuditApproved`, `RetirementRequested`.
