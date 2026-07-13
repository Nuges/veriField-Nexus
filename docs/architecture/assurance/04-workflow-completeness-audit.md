# 04 — Workflow Completeness Audit

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Audit Legend
- ✅ Defined & Implemented
- ⚠️ Partially defined or implemented
- ❌ Not defined or implemented

---

| Workflow | Actors | Inputs | Outputs | States | Events | Permissions | Jobs | Notifications | Audit | Error Handling | Recovery | Dependencies | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Organization Onboarding** | ⚠️ | ⚠️ | ⚠️ | ❌ | ✅ `org.created` | ✅ `MANAGE_ORG` | ❌ | ❌ | ⚠️ | ❌ | ❌ | Auth | ⚠️ Partial |
| **Jurisdiction Onboarding** | ✅ | ✅ | ✅ | ⚠️ | ❌ | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ❌ | Orgs, Spatial | ⚠️ Partial |
| **Programme Creation** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Jurisdictions | ❌ Missing |
| **Project Registration** | ✅ | ✅ | ✅ | ⚠️ | ✅ `project.created` | ✅ `CREATE_PROJECT` | ❌ | ❌ | ⚠️ | ⚠️ | ❌ | Programmes, Methodology | ⚠️ Partial |
| **Asset Registration** | ✅ | ✅ | ✅ | ⚠️ | ✅ `asset.created` | ✅ | ❌ | ❌ | ⚠️ | ⚠️ | ❌ | Projects | ⚠️ Partial |
| **Activity Submission** | ✅ | ✅ | ✅ | ✅ | ✅ `activity.*` | ✅ | ❌ | ❌ | ⚠️ | ✅ | ❌ | Assets | ✅ Mostly Complete |
| **Evidence Capture** | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Activities | ❌ Missing |
| **Monitoring** | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ✅ `sensor_processor` | ❌ | ❌ | ⚠️ | ❌ | IoT, Assets | ⚠️ Partial |
| **Internal Verification** | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ✅ `verification_worker` | ❌ | ❌ | ⚠️ | ❌ | Evidence | ⚠️ Partial |
| **VVB Validation** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Verification | ❌ Missing |
| **Compliance Check** | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | Governance | ⚠️ Partial |
| **Carbon Quantification** | ⚠️ | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | Methodology, Verification | ⚠️ Partial |
| **Registry Submission** | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Carbon Calc | ⚠️ Partial |
| **Issuance** | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Registry | ⚠️ Partial |
| **Transfer** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Ledger | ❌ Missing |
| **Retirement** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Ledger | ❌ Missing |
| **Reporting** | ⚠️ | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | Analytics | ⚠️ Partial |
| **Appeals** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Compliance | ❌ Missing |
| **Suspension** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | All | ❌ Missing |
| **Archiving** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | All | ❌ Missing |

---

## Summary

| Status | Count |
| :--- | :--- |
| ✅ Mostly Complete | 1 |
| ⚠️ Partial | 11 |
| ❌ Missing | 8 |

> [!WARNING]
> 8 out of 20 critical workflows are entirely missing from implementation. Only 1 workflow (Activity Submission) approaches completeness. No workflow currently creates audit records on every state change. No workflow sends notifications. No workflow has documented recovery procedures.
