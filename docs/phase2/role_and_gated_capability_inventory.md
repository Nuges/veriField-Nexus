# Phase 2 roles and gated capabilities

Existing role definitions, aliases, permission maps and sidebar categories are unchanged.
The table records existing route policy and the existing backend `registry:read` policy,
which the touched workflow now enforces. It does not grant access to project records:
project ABAC independently requires the user's organization, except SUPER_ADMIN.

| Role | Registry preparation/read/download | Existing verification route | Existing project route |
|---|---|---|---|
| SUPER_ADMIN | Yes | Yes | Yes |
| ORG_ADMIN | Yes | Yes | Yes |
| PROJECT_MANAGER | Yes | Yes | Yes |
| FIELD_SUPERVISOR | No | No | Yes |
| FIELD_AGENT | No | No | No |
| QA_OFFICER | No | Yes | Yes |
| VERIFIER | No | Yes | Yes |
| AUDITOR | No | Yes | Yes |
| COMPLIANCE_ADMIN | Yes | No | Yes |
| REGISTRY_ADMIN | Yes | No | Yes |
| FINANCE | No | No | No |
| INVESTOR | No | No | Yes |
| VIEWER | No | No | Yes |

The existing global registry route map includes INVESTOR and VIEWER. Their page now
explains lack of registry-read permission and sends no readiness/download request.
Changing that global map is outside this task. Verification links and the project
verification tab use the existing route policy. All 13 registry role decisions are
covered on both API prefixes using isolated fixtures. Subsequent Mac mock browser
tests passed, including VIEWER denial and permitted project preparation/downloads.
Broader navigation across all roles remains unverified in a browser.

| Capability | Classification and decision | Reason / remaining contract |
|---|---|---|
| Cookstove calculations and issuance | Gated/pilot; backend retained, no new issuance/submission controls | Heuristic baselines and incomplete metering; new preparation exports stay disabled for cookstove/MECD projects. |
| Unassigned methodology | Gated | Display `Under Assessment`; no automatic methodology, sequestration estimate or export eligibility. |
| Test/demo/pilot datasets | Gated in new preparation UI | Explicit classification/environment flags reject export, independent of backend ready status. |
| Aggregate registry CSV/JSON | Legacy; retained without launchers in touched Registry/PoA screens | No project input; historical fixed baseline/asset-derived values. Other legacy callers remain and require review before deprecation. |
| Legacy JSON package | Legacy; no new exposure | Heuristic/default fields and weaker post-build tenancy checks. Retain compatibility, audit before wider use. |
| Official authority forms and records | External evidence required | Requirement list is visible; UI does not manufacture official records. Existing document upload remains the intake workflow. |
| ITMO/Article 6 authorization | Specialist; not expanded | Existing compliance permission retained. Generated metadata is not independent regulatory evidence. No live write performed. |
| Cryptographic lineage investigation | Advanced; retained | Shared activity scoping fixed; advanced endpoint permission/unowned-project handling still needs review. |
| Registry configs/plugins/synchronization | Internal/specialist; not expanded | Credentials, role/tenant checks and provider contracts require separate review. No provider called. |
| Biochar/Puro and other future adapters | Existing specialist/gated consumers retained | No claim of validation from endpoint presence; inspect individual contracts before broad exposure. |
| Direct automated Verra/Gold Standard issuance | Unsupported/incomplete stubs retained | No new issuance UI; missing external credentials are not a submission or credit record. |
| Laboratory template/upload and device enrollment | Existing operational flows retained | Authenticated templates and existing validation feedback reused; no new ingestion engine or fake accepted status. |

The full exported-function inventory is in `api_capability_inventory.md` and its JSON
companion. It searches source, tests and supporting scripts. No literal reference is
not proof of dead code; dynamic consumers remain possible. No exports were deleted.
