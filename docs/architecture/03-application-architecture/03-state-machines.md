# Enterprise State Machines

Entities in the VeriField Nexus CIOS do not change state arbitrarily. They follow strict, mathematically sound state machines. State transitions are triggered by explicit actions or domain events, and each transition requires validation against the rules engine.

## 1. Project Lifecycle State Machine

The `Project` entity represents the core initiative generating climate impact.

```mermaid
stateDiagram-v2
    [*] --> DRAFT : Create PDD
    DRAFT --> SUBMITTED : Submit for Review
    SUBMITTED --> DRAFT : Reject (Requires Edits)
    SUBMITTED --> UNDER_VALIDATION : Assign VVB
    UNDER_VALIDATION --> REJECTED : Validation Failed
    UNDER_VALIDATION --> REGISTERED : Validation Passed
    
    REGISTERED --> MONITORING : Asset Deployed / Baseline Set
    MONITORING --> SUSPENDED : Compliance Violation
    SUSPENDED --> MONITORING : Remediation Accepted
    SUSPENDED --> REVOKED : Critical Failure
    
    MONITORING --> ARCHIVED : End of Crediting Period
    REGISTERED --> ARCHIVED : Abandoned
    REVOKED --> [*]
    ARCHIVED --> [*]
```

### Transition Constraints
- `SUBMITTED -> UNDER_VALIDATION`: Requires the Project to be fully contained within a valid `Jurisdiction`.
- `UNDER_VALIDATION -> REGISTERED`: Requires a cryptographically signed Validation Statement from an authorized `Organization (VVB)`.

## 2. Evidence Lifecycle State Machine

The `Evidence` entity represents a singular proof point (e.g., an IoT reading or a field photo).

```mermaid
stateDiagram-v2
    [*] --> RAW : Ingested via API
    RAW --> QUARANTINED : AI Flagged Anomaly
    QUARANTINED --> REJECTED : Verifier Confirms Invalid
    QUARANTINED --> VERIFIED : Verifier Overrides
    
    RAW --> PENDING_VERIFICATION : AI Passed
    PENDING_VERIFICATION --> VERIFIED : Verifier Approves
    PENDING_VERIFICATION --> REJECTED : Verifier Rejects
    
    VERIFIED --> AUDITED : Sampled & Passed by VVB
    VERIFIED --> REJECTED_BY_AUDITOR : Failed VVB Sampling
    
    AUDITED --> [*]
    REJECTED --> [*]
    REJECTED_BY_AUDITOR --> [*]
```

## 3. Carbon Credit Issuance State Machine

The `CarbonCredit` or `IssuanceBatch` entity.

```mermaid
stateDiagram-v2
    [*] --> CALCULATED : Accounting Engine Run
    CALCULATED --> PENDING_ISSUANCE : Sent to Registry Adapter
    PENDING_ISSUANCE --> FAILED_SYNC : Registry Error
    FAILED_SYNC --> PENDING_ISSUANCE : Retry Sync
    
    PENDING_ISSUANCE --> ISSUED : Confirmed by Registry
    ISSUED --> ON_HOLD : Regulatory Freeze
    ON_HOLD --> ISSUED : Unfrozen
    
    ISSUED --> LISTED : Synced to Marketplace
    LISTED --> SOLD : Executed Trade
    SOLD --> RETIRED : Beneficiary Claimed
    ISSUED --> RETIRED : Direct Retirement
    
    RETIRED --> [*]
```

## Soft Deletion Behavior

The state machines above do not include `DELETED`. 
- **Hard deletion (`DELETE FROM table`) is strictly prohibited** for business entities to ensure ledger immutability and auditability.
- Instead, records transition to an `ARCHIVED` state, or a generic `is_deleted = true` column is toggled. Soft-deleted records are filtered out of standard operational views but remain accessible via the Enterprise Audit API.
