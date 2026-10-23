# Registry contracts and compatibility — Phase 2

Inspected locally on 23 October 2026. Canonical prefix: `/api/v1/registry`.
The same router is also mounted at `/api/v1/registry-integrations`; both remain.
Runtime inspection found 15 operations per prefix, not 26 distinct unused capabilities.
No external registry was contacted. This table describes implementation, not regulatory acceptance.

| Method and suffix | Inputs and output | Access and Phase 2 decision |
|---|---|---|
| GET `/document-matrix` | No project input; shared requirement catalog with `version`, `authorities`, and documents | Existing `registry:read` dependency now enforced. Used in project preparation; catalog is not evidence. |
| GET `/readiness/{project_id}` | UUID project; `target_standard=VERRA`, `target_stage=verification`; JSON includes project/standard, blocking and missing items, document assessments | Existing `registry:read` plus project ABAC before evaluation. UI uses internal preparation labels, not approval scores. |
| GET `/dossier/{standard}/{project_id}` | UUID project; `stage=monitoring`, optional `version`; generated JSON dossier | Existing `registry:read` plus project ABAC. Client consolidated; no new dossier/authorization screen. |
| GET `/package-download/{standard}/{project_id}` | UUID project; `stage=verification`, optional `version`; ZIP bytes and attachment filename | Existing `registry:read` plus project ABAC before builder. Selected-project UI enables only assigned, nonpilot/noncookstove projects with matching, explicitly ready assessment and no reported blockers. |
| GET `/documents/{standard}/{project_id}/{document_id}` | UUID project, document identifier, `format=pdf` (also docx/json); rendered bytes | Existing `registry:read` plus project ABAC before rendering. UI exposes supported internal drafts; official authority forms/records are not generated from this screen. |
| GET `/export/{registry_type}` | `min_trust_score=80`; aggregate JSON from asset attributes; **no project parameter** | Existing explicit role check retained. Tenant aggregate and fixed fuel baseline make this unsuitable for the selected-project workflow. Removed its launchers from Registry and PoA; clients/backend retained. |
| GET `/package/{registry_type}/{project_id}` | UUID project, `min_trust_score=80`; legacy JSON manifest | Legacy service and clients retained. Post-generation tenant check is weaker than the new read workflow; no new UI exposure. Requires a separate hardening/deprecation decision. |
| GET `/configs` | Config list | Existing authentication; conditional organization filtering in controller. Retained specialist/internal API, not newly exposed. Review model-backed tenancy before wider use. |
| POST `/configs` | `RegistryConfigCreate`; saved config response | Existing SUPER_ADMIN/COMPLIANCE_ADMIN check retained. No configuration writes executed. |
| GET `/plugins` | Adapter metadata and pending-credentials states | Existing authentication retained; no ordinary-operator plugin controls added. |
| POST `/{registry_id}/sync` | UUID config; `SyncActionRequest`; sync log | Existing controller/service retained; stronger explicit permission and tenant checks need separate review before expansion. Not executed. |
| POST `/sync/{bundle_id}` | Bundle string, `provider_name=local`; provider synchronization response | Existing behavior can create config/log records and call providers. No new control added; not executed. Permission, ownership and external-evidence contracts need review. |
| GET `/status/{sync_id}` | Sync string, `provider_name=local`; provider result | Existing behavior retained; not executed against a live provider. |
| GET `/lineage/{project_id}` | UUID project; lineage JSON graph and summary | Existing authentication/organization checks retained. Shared activity scoping corrected. Advanced investigation, not a new operator action. Unowned-project and role checks need follow-up. |
| POST `/itmo/authorize` | Existing `ITMOAuthorizationRequest`; authorization/dossier response | Existing `compliance:authorize` and organization check retained. Client signature and POST compatibility retained; tested with fetch mocks only. No authorization recorded. Existing default references require substantive regulatory review. |

## Frontend consumers and fallback

`dashboard/src/lib/api.ts` remains the shared API boundary. Readiness, document matrix,
dossier, package ZIP, document downloads and the existing ITMO client now share
canonical-prefix handling. Only HTTP 404 permits the legacy-prefix fallback.
HTTP 401, 403 and 500 remain failures. Tokens survive fallback; no denied download
creates success feedback. `downloadArticle6PackageZip` delegates to the new generic
package function and remains exported for compatibility.

`RegistryModule` serves the registry page, project tab, and existing Enterprise dashboard.
The portfolio screen reuses the registry page. Project Documents, Ingestion Center,
Verification and PoA link to this preparation workflow instead of duplicating exports.
Legacy export/package helpers and AI/reporting consumers remain in the capability
inventory; they were not deleted or certified as operationally ready by this change.

## Evidence boundary

Registry readiness, package builder, dossier, document generation and reporting lineage
now share one activity query: explicit project records, plus legacy records without a
project on that project's assets, always within its organization. An organization-wide
fallback is no longer a project relationship. A conflicting explicit project ID wins
over an asset link and excludes the record.

Existing assessment engines still use heuristic completeness and regulatory metadata.
The new UI calls these internal assessments. UI export eligibility is **not** a new
backend authorization policy: legacy/direct API callers can still request draft
packages without this frontend readiness gate. Server-side readiness policy,
authoritative evidence validation and remaining advanced-route hardening are Phase 3
work; no submission or issuance is enabled by the new screen.
