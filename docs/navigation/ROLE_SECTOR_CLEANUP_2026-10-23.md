# Navigation, roles and field capture review

Date: 23 October 2026. Base: c59be19. Branch: fix/navigation-role-sector-cleanup.
Status: merged into main as 1f606c70f47e1399ae2e2a54772254a233c6941a via PR #3; frontend deployment succeeded and backend is live.

## Navigation and presentation

| Feature | Canonical home | Duplicate handling |
| --- | --- | --- |
| Project creation and project list | Projects | Assets only lists physical assets; project creation is permission gated. |
| Team accounts and privileges | People & access | Removed team roster from Projects and account mutations from Field performance. |
| Sensor devices and telemetry | Sensors | Old Operations telemetry tab redirects here. |
| Field observations and data submission | Field operations / Capture data | No embedded sensor, audit, or verification page; old tab links redirect. |
| Verification packages and independent review | Verification | Administrators prepare evidence; independent VVB actors review/sign. |
| Internal data quality | Data quality | Distinct from sensor device management and independent verification. |

Removed generic lifecycle timelines, example entity identifiers, confidence/verification banners, unsupported certified-offset summaries, static live badges, fake project metadata defaults and repeated role guidance. Existing functional callbacks, download paths and legacy URLs remain available. Project methods require an explicit selection; energy baseline inputs are limited to energy projects. Mobile navigation has a menu and no permanent desktop content offset.

## Role boundaries

| Role | Work and access |
| --- | --- |
| Super admin | Platform, organizations, users, all projects, field operations, sensors, assets, quality, field performance, reports, registry and verification oversight. No independent audit opinion/signing action. |
| Organization admin | Projects, team access, field oversight, internal approval, supporting documents and package preparation. No VVB verification. |
| Project manager | Project setup, evidence, programme/registry preparation and reporting. No independent signing or team administration. |
| Field supervisor | Field oversight, capture, internal approval and reporting. No independent signing. |
| Field agent | Project-bound capture and submitted field records. No administration or independent review. |
| QA officer | Internal quality/approval, supporting documents and review preparation. Project-edit-only agriculture mutations stay unavailable. |
| Verifier / VVB | Independent verification/review, evidence, findings and assurance decisions. No project creation, field submission or team administration. |
| Auditor | Independent package review/findings. No developer/field/team actions. |
| Compliance admin | Compliance, sovereign authorization and regulatory reporting. |
| Registry admin | Registry packages, submissions and issuance tracking. |
| Finance | Carbon ledger, settlement and financial reports. |
| Investor / viewer | Read-only project/report views. No project creation, field capture, lab import or quantification locking. |

Unknown roles and unknown non-admin dashboard routes fail closed. The same route rules filter sidebar links and direct URL access. There are 116 role/destination combinations across 13 roles. Backend enforcement distinguishes internal activity approval from independent verification. Both PUT activity update and PATCH status reject non-verifiers attempting verified status. Package/report separation of duties no longer grants a super-admin independent-review override. Soil QA uses internal approval permission.

Agriculture planning, laboratory imports, quantification and document uploads now check positive capabilities rather than treating all non-field-agent roles as writers.

## Field capture

The project API now exposes the stored sector ID/code and linked methodology code in list and detail responses. Legacy projects read their linked methodology family without changing stored assignments; projects with no sector/methodology stay unconfigured. API regression tests cover all five sectors, legacy linkage and no guessed sector.

The web collector chooses its form from the authorized project sector, not a cookstove default or a methodology guess. Five sector forms submit project-bound observations; agriculture uses the physical-sample collection endpoint. Missing project/sector and invalid quantities/coordinates are blocked. Zero latitude/longitude remain valid. GPS failure leaves coordinates empty. Optional photos must upload successfully before submission; no example proof URL or fabricated trust/verification score is created.

Offline records are scoped to user and organization. Explicit offline saves retain their client identifier and sync only under the matching account, project and sector. Authorization failures remain errors. The old unscoped browser queue is left intact and is not automatically attributed to another user.

Native changes: project-based entry routes to the existing four sector forms or the added soil collection screen, with account-scoped offline soil collections; role-aware navigation hides field submission from VVB/read-only users and hides audit mutations from admins. Generic native queues carry capture owner/organization and project; sync preserves mismatched/legacy records for reconciliation rather than submitting them as the current user. Removed seeded kiln/feedstock identifiers and guessed capacity defaults. Native analysis and all 10 Flutter tests passed in GitHub run 40002907984 (Flutter 3.47.7). The first analysis had five nonfatal style/nullability findings. The final analysis has one nonfatal style info (curly_braces_in_flow_control_structures at activity_form_screen.dart:129), with no errors or warnings. This is compilation/static analysis and unit/contract validation, not execution on a physical device.

## Validation at checkpoint

- Dashboard unit tests: 160 passed.
- TypeScript: no errors.
- Changed dashboard files: ESLint --quiet passed.
- Production dashboard build: passed, 41 routes.
- Chromium: 41 passed in 37.7s. Includes 116 sidebar destinations, five sector submissions, role action separation/direct denials, denied-write behavior, offline sync, GPS failure, mobile menu and five existing registry/download regressions. Backend responses are isolated fixtures; external requests are blocked. These tests do not assert live integrations or every possible mutation in every module.
- New backend boundary/authentication checks: 40 passed before broad regression.
- Independent opinion lifecycle: updated to reject super-admin opinion then authenticate a real verifier; 1 passed in 1.57s after fixing the test fixture's administrative auth override.
- Broad local backend run: 418 passed, 21 skipped, two failures and 11 errors. One failure was the outdated super-admin lifecycle expectation (corrected and rerun); the other failure and 11 errors require unavailable local PostgreSQL/PostGIS. A SQLite-only rerun before the final auth-fixture fix had 418 passed, 21 skipped, one deselected and that single lifecycle failure. Final isolated SQLite regression passed: 419 passed, 21 skipped, one deselected in 34.23s. Only the PostgreSQL-dependent telemetry file and the PostgreSQL-dependent sensor/community test were excluded locally; CI still runs them with PostGIS.
- Flutter/Dart are not installed locally. A GitHub workflow runs Flutter analysis/tests and isolated browser workflows. Initial browser CI: 40 passed in 30.6s; native: 10 passed. Initial full backend CI: 843 passed, 34 skipped, five deselected, two failures from legacy tests incorrectly expecting QA approval to be final verification. Those workflows now use internal validation approval; their targeted rerun and project response regressions passed: 37 passed in 4.38s. Final PR checks passed as recorded below.

Quality badges now describe the numerical score rather than claiming independent verification; field record labels are plain and project filtering is sent to the API before pagination. A browser regression also verifies real zero coordinates remain visible.

No production data/schema was modified. The known production agriculture schema gap remains: missing land_units/soil_samples tables and projects.methodology_id nullability require a separate controlled migration. A working collector UI does not prove that production agriculture persistence is ready. Publication, merge and deployment must be recorded separately in HANDOFF.md.

## Publication and final PR checks

- Application source: 589a3b286cd259d59a0aa1e7b81d4b7b87cc00fc. CI-only follow-up: 6b99fa2d2353713a0beb00b48a5c93cb300235d9. The follow-up reuses runner Chrome, times out a fallback install after five minutes and bounds the browser job at 15 minutes. It changes no application source.
- PR #3: https://github.com/Nuges/veriField-Nexus/pull/3. Final PR CI runs 40006720160 and 40006720149 both completed successfully.
- Required backend: 847 passed, 34 skipped, five deselected, one warning in 88.98s. Alembic migrations and authoritative PostGIS tests passed in CI. Dashboard typecheck/build, 160 unit tests, SDK and external STAC also passed.
- Final GitHub Chromium run: 41 passed in 1.3m. Flutter: 10 passed, with the single nonfatal analysis info described above. Local browser results remain separate from CI results.
- Merge commit: 1f606c70f47e1399ae2e2a54772254a233c6941a. Its tree 3cf92a5f2d5b1cd509b3135edec60c29f84148e9 exactly equals the final tested source tree.
- Vercel reports successful production deployment for the merge commit: https://vercel.com/nuges-projects-381ad4bc/veri-field-nexus/8GmQm1BvjzZjEnXxpFbMKDDFtTn9. This is the provider result, not a signed-in production journey. Main CI runs 40007250110 and 40007250112 also passed: 847 backend tests (34 skipped, five deselected, one warning, 88.53s), 41 Chromium scenarios (1.2m), 10 Flutter tests, and the same typecheck/build/migration/PostGIS/SDK/STAC gates. Native analysis retains one style info. Render deploy dep-dbdqshkipgvc739qum30 became LIVE on exact merge 1f606c7 at 2026-10-23T18:59:33.703952Z. One deploy was triggered after the automatic rollout did not appear; configuration was unchanged.

- Post-live HTTP checks: GET /health returned 200/healthy; GET /api/v1/health/ready returned 200/ready; unauthenticated GET /api/v1/registry/document-matrix returned 401. Error-level application logs from deployment start to 18:59:55Z contained no entries (short window only).
- Native code is committed and checked, but no native binary/app-store deployment or physical-device journey was performed. No signed-in production mutation was used to validate this release. The agriculture production schema blocker remains unchanged.
- Final handover is a two-file documentation-only commit with [skip ci] [skip render]; application/test source remains the exact deployed merge. Preserve Mac backups/stashes and verify branch/status before resuming in either tool.
