# 01 — Architecture Coverage Matrix

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Coverage Matrix

The following matrix maps every identified platform capability to its coverage across the architectural layers. A capability is "Covered" if it is explicitly referenced in the named architectural document; "Partial" if mentioned tangentially; "Missing" if no reference exists.

### Legend
- ✅ Covered (explicitly documented)
- ⚠️ Partial (referenced but lacks detail)
- ❌ Missing (no reference found)

---

| Capability | Climate Ref Arch | Enterprise Arch | Business Domain | Module (Backend) | Service Layer | API (Route) | Entity (Model) | Workflow | UI (Page) | Permission | Events | Coverage % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Identity & Auth** | ✅ `01-ref-model` | ✅ `05-security` | ✅ `02-domains` | ✅ `authentication` | ✅ `identity_provider` | ✅ `auth.py` | ✅ `user.py` | ✅ | ✅ `login` | ✅ | ✅ `user.created` | 100% |
| **Organizations** | ✅ `01-ref-model` | ✅ `01-business` | ✅ `02-domains` | ✅ `organizations` | ✅ | ✅ `organizations/api` | ✅ `organization.py` | ⚠️ | ⚠️ | ✅ `MANAGE_ORG` | ✅ `organization.created` | 90% |
| **Jurisdictions** | ✅ `07-spatial` | ✅ `06-governance` | ✅ `02-domains` | ✅ `jurisdictions` | ✅ | ✅ `jurisdictions.py` | ✅ `jurisdiction.py` | ⚠️ | ✅ `jurisdictions/page` | ⚠️ | ❌ | 75% |
| **Projects** | ✅ `09-portfolio` | ✅ `01-business` | ✅ `02-domains` | ✅ `projects` | ✅ | ✅ `projects.py` | ✅ `project.py` | ✅ | ❌ dedicated page | ✅ `CREATE_PROJECT` | ✅ `project.created` | 85% |
| **Assets** | ✅ `09-portfolio` | ✅ `04-info` | ✅ `02-domains` | ✅ `assets` | ✅ | ✅ `assets.py` | ✅ `asset.py` | ⚠️ | ❌ | ✅ | ✅ `asset.created` | 75% |
| **Activities** | ✅ `09-portfolio` | ✅ `04-info` | ✅ `02-domains` | ✅ `activities` | ✅ | ✅ `activities.py` | ✅ `activity.py` | ⚠️ | ✅ `activities/page` | ✅ | ✅ `activity.created` | 85% |
| **Programmes (PoA)** | ✅ `08-programme` | ✅ `01-business` | ✅ `02-domains` | ❌ No domain module | ❌ | ❌ | ❌ | ❌ | ✅ `poa/page` | ❌ | ❌ | 30% |
| **Portfolios** | ✅ `09-portfolio` | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 15% |
| **Methodologies** | ✅ `06-methodology` | ✅ `07-integration` | ✅ `02-domains` | ✅ `methodology_registry` | ✅ | ✅ `methodology.py` | ✅ `base_registry.py` | ⚠️ | ❌ | ❌ | ❌ | 60% |
| **Registry Federation** | ✅ `05-registry-fed` | ✅ `07-integration` | ✅ `02-domains` | ✅ `registry_integrations` | ✅ `registry_provider` | ✅ `registry.py` | ❌ No dedicated model | ⚠️ | ✅ `registry/page` | ❌ | ❌ | 55% |
| **Compliance** | ✅ `04-mrv` | ✅ `06-governance` | ✅ `02-domains` | ✅ `compliance_engine` | ✅ `compliance_engine` | ✅ `compliance.py` | ✅ `compliance.py` | ⚠️ | ✅ `compliance/page` | ❌ | ❌ | 65% |
| **Verification** | ✅ `04-mrv` | ✅ `10-operational` | ✅ `02-domains` | ❌ No domain | ✅ `verification_worker` | ✅ `cross_verification.py` | ❌ | ⚠️ | ✅ `verifications/page` | ❌ | ❌ | 45% |
| **Validation (VVB)** | ✅ `04-mrv` | ✅ `10-operational` | ✅ `02-domains` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 15% |
| **Evidence / MRV** | ✅ `04-mrv` | ✅ `04-info` | ✅ `02-domains` | ⚠️ (via activities) | ⚠️ | ⚠️ | ❌ No `evidence` model | ⚠️ | ✅ `capture/page` | ❌ | ❌ | 35% |
| **Carbon Accounting** | ✅ `02-value-chain` | ✅ `01-business` | ✅ `02-domains` | ⚠️ `quantification_engine` | ✅ | ✅ `carbon.py` | ✅ `carbon_calculation.py` | ⚠️ | ✅ `carbon/page` | ❌ | ❌ | 55% |
| **Issuance & Ledger** | ✅ `05-registry-fed` | ✅ `03-application` | ✅ `02-domains` | ✅ `ledger` | ✅ | ✅ `ledger/api` | ✅ `ledger/models` | ⚠️ | ❌ | ✅ | ✅ | 65% |
| **Marketplace / Trading** | ✅ `14-roadmap` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 5% |
| **Climate Finance** | ✅ `03-finance` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 5% |
| **Spatial / GIS** | ✅ `07-spatial` | ✅ `04-info` | ✅ | ⚠️ (in jurisdictions) | ✅ `gps_validator` | ⚠️ | ⚠️ | ⚠️ | ✅ `map/page` | ❌ | ❌ | 45% |
| **IoT / Sensors** | ✅ `11-data` | ✅ `07-integration` | ✅ | ⚠️ | ✅ `sensor_processor` | ✅ `sensors.py` | ✅ `sensor_reading.py` | ⚠️ | ✅ `sensors/page` | ❌ | ❌ | 55% |
| **AI / Trust Engine** | ✅ `10-intelligence` | ✅ `03-application` | ✅ | ✅ `ai_trust_engine` | ✅ `trust_engine`, `ai_detector` | ✅ `ai_trust/api` | ✅ `trust_log.py`, `anomaly_flag.py` | ⚠️ | ✅ `trust-scores`, `anomalies` | ✅ | ❌ | 70% |
| **Reporting / Analytics** | ✅ `13-observability` | ✅ `04-info` | ✅ | ✅ `reporting` | ✅ | ✅ `analytics.py`, `export.py` | ⚠️ | ⚠️ | ✅ `executive/page` | ❌ | ✅ | 60% |
| **Notifications** | ⚠️ `12-ops-model` | ✅ `08-ui` | ✅ | ✅ `notifications` | ✅ | ✅ `notifications/api` | ✅ `notifications/models` | ⚠️ | ❌ | ✅ | ✅ | 65% |
| **Audit Trail** | ✅ `12-ops-model` | ✅ `05-security` | ✅ | ⚠️ (model only) | ❌ | ✅ `audits.py` | ✅ `audit_trail.py`, `audit_task.py` | ⚠️ | ✅ `audits/page` | ❌ | ❌ | 50% |
| **Workspaces** | ⚠️ | ✅ `01-business` | ✅ | ✅ `workspaces` | ✅ | ✅ `workspaces/api` | ✅ `workspaces/models` | ⚠️ | ❌ | ✅ | ✅ `workspace.created` | 65% |
| **Plugin Runtime** | ⚠️ `06-methodology` | ✅ `03-application` | ✅ | ✅ `plugin_runtime` | ✅ | ✅ `plugin_runtime/api` | ✅ | ⚠️ | ❌ | ✅ | ✅ | 65% |
| **Accreditation (VVBs)** | ✅ `01-ref-model` | ✅ `05-security` | ✅ | ❌ (model only) | ❌ | ✅ `accreditations.py` | ✅ `accreditation.py` | ❌ | ❌ | ❌ | ❌ | 30% |
| **Community Validation** | ⚠️ | ⚠️ | ⚠️ | ❌ (model only) | ❌ | ✅ `community.py` | ✅ `community_validation.py` | ❌ | ✅ `community/page` | ❌ | ❌ | 25% |
| **Settings / Config** | ⚠️ | ✅ `08-ui` | ⚠️ | ❌ (model only) | ❌ | ✅ `settings.py` | ✅ `system_setting.py` | ❌ | ✅ `settings/page` | ❌ | ❌ | 30% |
| **Job Execution** | ✅ `13-observability` | ✅ `09-infra` | ✅ | ✅ `job_scheduler` | ✅ | ❌ | ✅ `job.py` | ⚠️ | ⚠️ `JobPollingWidget` | ❌ | ❌ | 50% |
| **Developer Platform** | ✅ `14-roadmap` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 5% |
| **Digital Twins** | ✅ `14-roadmap` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 5% |

---

## Summary

| Coverage Level | Count | Percentage |
| :--- | :--- | :--- |
| Full Coverage (≥ 80%) | 4 | 12.5% |
| Substantial (60-79%) | 10 | 31.3% |
| Partial (30-59%) | 10 | 31.3% |
| Minimal (< 30%) | 8 | 25.0% |

**Overall Architecture Coverage: ~48%**

> [!WARNING]
> The architecture is well-articulated at the Climate Reference and Enterprise layers, but significant implementation gaps remain. 8 capabilities have minimal or no implementation coverage.
