# 02 — Requirements Traceability Matrix

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Traceability Legend
- ✅ Traceable (explicit linkage exists)
- ⚠️ Implicit (can be inferred but not explicitly documented)
- ❌ Broken (no trace exists at this layer)

## Full Hierarchy Trace

| Capability | Climate Operating Model | Climate Ref Arch | Enterprise Arch | Domain Arch (Module) | API | Database Entity | UI Screen | Workflow | Events | Jobs | Audit | Lineage % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Identity & Auth | ✅ §3.4 Trust | ✅ `01` | ✅ `05-security` | ✅ `authentication` | ✅ `auth.py` | ✅ `user` | ✅ `login` | ✅ | ✅ `user.created` | ❌ | ⚠️ | 82% |
| Organizations | ✅ §3.1 | ✅ `01` | ✅ `01-business` | ✅ `organizations` | ✅ | ✅ `organization` | ⚠️ | ⚠️ | ✅ `org.created` | ❌ | ⚠️ | 73% |
| Jurisdictions | ✅ §3.5 Gov | ✅ `07` | ✅ `06-governance` | ✅ `jurisdictions` | ✅ | ✅ `jurisdiction` | ✅ | ⚠️ | ❌ | ⚠️ | ⚠️ | 64% |
| Projects | ✅ §2 Value | ✅ `09` | ✅ `01-business` | ✅ `projects` | ✅ | ✅ `project` | ❌ | ⚠️ | ✅ `project.created` | ❌ | ⚠️ | 64% |
| Assets | ✅ §2 Value | ✅ `09` | ✅ `04-info` | ✅ `assets` | ✅ | ✅ `asset` | ❌ | ⚠️ | ✅ `asset.created` | ❌ | ❌ | 55% |
| Activities | ✅ §2 Value | ✅ `09` | ✅ `04-info` | ✅ `activities` | ✅ | ✅ `activity` | ✅ | ⚠️ | ✅ `activity.*` | ❌ | ⚠️ | 73% |
| Programmes (PoA) | ✅ §2 | ✅ `08` | ✅ `01-business` | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | 27% |
| Portfolios | ✅ §2 | ✅ `09` | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 18% |
| Methodologies | ✅ §3.6 | ✅ `06` | ✅ `07-integration` | ✅ `methodology_registry` | ✅ | ✅ | ❌ | ⚠️ | ❌ | ❌ | ❌ | 45% |
| Registry Federation | ✅ §3.6 | ✅ `05` | ✅ `07-integration` | ✅ `registry_integrations` | ✅ | ❌ | ✅ | ⚠️ | ❌ | ❌ | ❌ | 45% |
| Compliance | ✅ §3.5 | ✅ `04` | ✅ `06-governance` | ✅ `compliance_engine` | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ❌ | 55% |
| Verification | ✅ §3.4 | ✅ `04` | ✅ `10-operational` | ❌ | ⚠️ | ❌ | ✅ | ⚠️ | ❌ | ✅ `verification_worker` | ❌ | 36% |
| Validation (VVB) | ✅ §3.4 | ✅ `04` | ✅ `10-operational` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 18% |
| Evidence / MRV | ✅ §3.4 | ✅ `04` | ✅ `04-info` | ⚠️ | ⚠️ | ❌ | ✅ `capture` | ⚠️ | ❌ | ❌ | ❌ | 36% |
| Carbon Accounting | ✅ §3.6 | ✅ `02` | ✅ `01-business` | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ❌ | 45% |
| Issuance & Ledger | ✅ §3.6 | ✅ `05` | ✅ `03-app` | ✅ `ledger` | ✅ | ✅ | ❌ | ⚠️ | ❌ | ❌ | ❌ | 45% |
| Marketplace | ✅ §2 | ✅ `14` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 9% |
| Climate Finance | ✅ §2 | ✅ `03` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 9% |
| Spatial / GIS | ✅ §3.5 | ✅ `07` | ✅ `04-info` | ⚠️ | ⚠️ | ⚠️ | ✅ `map` | ⚠️ | ❌ | ❌ | ❌ | 36% |
| IoT / Sensors | ✅ §3.4 | ✅ `11` | ✅ `07-integration` | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ✅ `sensor_processor` | ❌ | 55% |
| AI / Trust Engine | ✅ §3.4 | ✅ `10` | ✅ `03-app` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ⚠️ | 64% |
| Notifications | ⚠️ | ⚠️ | ✅ `08-ui` | ✅ | ✅ | ✅ | ❌ | ⚠️ | ✅ | ❌ | ❌ | 45% |
| Audit Trail | ✅ §3.4 | ✅ `12` | ✅ `05-security` | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ✅ | 55% |

---

## Summary

**Average Lineage Coverage: ~43%**

> [!CAUTION]
> Several critical capabilities (Programmes, Portfolios, Validation, Marketplace, Climate Finance) have broken traceability below 30%. These capabilities exist in the Climate Reference Architecture but have no backend domain module, API, or database entity to support them.
