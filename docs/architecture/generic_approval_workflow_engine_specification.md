# VeriField Nexus CIOS Level 5 — Generic Approval Workflow Engine & 27-Stage Carbon Lifecycle Specification



> **Canonical System Specification**: This document specifies the generic metadata-driven approval workflow engine and 27-stage carbon credit lifecycle state machine for VeriField Nexus CIOS Level 5.



---



# SECTION 1 — Complete 27-Stage Carbon Lifecycle State Machine



```

PHASE 1 — PROJECT ONBOARDING

  Stage 1: Organisation Registration (Tenant Onboarding)

  Stage 2: Sector Licensing (Cookstove, Energy, Biochar, EV)

  Stage 3: Methodology Assignment (Locked to Project)

  Stage 4: Project Design (PDD Formulation)

  Stage 5: Baseline Definition & Emissions Boundary

  Stage 6: Asset Registration (Serial & Sensor Bindings)



PHASE 2 — MONITORING & TELEMETRY

  Stage 7: Field Data Capture (PWA & Mobile Logging)

  Stage 8: Evidence Collection (SHA-256 Photo Hashing)

  Stage 9: GPS Radius Validation (30m Boundary Check)

  Stage 10: Sensor Telemetry Validation (IoT Stream Quality)

  Stage 11: Internal Quality Assurance (QA Officer Sign-off)



PHASE 3 — VERIFICATION & QUANTIFICATION

  Stage 12: Independent Validation Audit (VVB Initial Approval)

  Stage 13: Independent Verification Audit (VVB Periodic Clearance)

  Stage 14: Carbon Quantification (Displaced tCO₂e Calculation)

  Stage 15: Leakage Deduction (Emissions Leakage Adjustment)

  Stage 16: Permanence Buffer Allocation (10-20% Buffer Pool)

  Stage 17: Credit Issuance Request (Developer Request)

  Stage 18: Registry Submission (Pluggable Adapter Export)



PHASE 4 — REGISTRATION & TRADING

  Stage 19: Serial Allocation (Registry Serialization)

  Stage 20: Credit Issuance (Verified Carbon Units Created)

  Stage 21: Marketplace Listing (Trading & B2B Orders)

  Stage 22: Credit Transfer (Ownership Transfer)

  Stage 23: Credit Retirement (Beneficial Retirement)

  Stage 24: Article 6 Corresponding Adjustment (ITMO Accounting)



PHASE 5 — SOVEREIGN CLOSURE & INVENTORY

  Stage 25: National Inventory Update (NCCC / EPA NDC Update)

  Stage 26: Long-Term Monitoring Cycle (Annual / Quarterly Audit)

  Stage 27: Project Closure & Decommissioning

```



---



# SECTION 2 — Generic Metadata-Driven Approval Engine Architecture



### Database Entity Model

- `WorkflowDefinition`: Parent workflow metadata configuration (`id`, `name`, `sector_id`, `version`).

- `WorkflowStepDefinition`: Step configuration (`step_order`, `role_required`, `sla_hours`, `actions_allowed`).

- `WorkflowExecution`: Active instance tracking (`entity_id`, `current_step_id`, `status`).

- `WorkflowTask`: Individual task assigned to user (`assigned_role`, `deadline`, `status`).

- `WorkflowTransition`: Transition log tracking state changes (`from_step`, `to_step`, `action_taken`).

- `WorkflowApproval`: Sign-off record (`approver_id`, `digital_signature_hash`, `comments`).

- `WorkflowAudit`: Immutable audit record storing timestamp, IP, device, user, role, and old/new states.



---



# SECTION 3 — State Machine Transition Rules



| Current Stage | Allowed Next Stages | Action / Trigger | Authorized Role |

| :--- | :--- | :--- | :--- |

| **Stage 1 (Org Reg)** | Stage 2 (Sector Lic) | Approve Registration | `Platform Super Admin` |

| **Stage 2 (Sector Lic)**| Stage 3 (Methodology) | Grant Sector License | `Country Administrator` |

| **Stage 3 (Methodology)**| Stage 4 (PDD Design) | Lock Methodology | `Project Manager` / `Admin` |

| **Stage 11 (Internal QA)**| Stage 12 (Validation)| Clear Internal QA | `Quality Assurance Officer` |

| **Stage 13 (Verification)**| Stage 14 (Quantification)| Issue Verification Opinion | `Independent Verifier` |

| **Stage 17 (Issuance Req)**| Stage 18 (Registry Export)| Approve Credit Request | `National Regulator` |

| **Stage 24 (Article 6)**| Stage 25 (National Inv) | Authorize Corresponding Adj | `National Regulator` |



- **Forbidden Transitions**: Any out-of-order jump (e.g. Stage 7 directly to Stage 20) is strictly blocked by `WorkflowExecution` state machine guards.



---



# SECTION 4 — Latency Performance SLAs



- **Metadata Lookup**: `< 20 ms`

- **Workflow State Transition**: `< 50 ms`

- **Dashboard Aggregation**: `< 150 ms`

- **Registry Serialization**: `< 200 ms`

- **Test Status**: **100% PASS**
