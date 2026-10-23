# Navigation, roles and field capture review

Date: 23 October 2026. Base: c59be19. Branch: fix/navigation-role-sector-cleanup.
Status: implementation checkpoint; GitHub/native/database checks pending.

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

The web collector chooses its form from the authorized project sector, not a cookstove default or a methodology guess. Five sector forms submit project-bound observations; agriculture uses the physical-sample collection endpoint. Missing project/sector and invalid quantities/coordinates are blocked. Zero latitude/longitude remain valid. GPS failure leaves coordinates empty. Optional photos must upload successfully before submission; no example proof URL or fabricated trust/verification score is created.

Offline records are scoped to user and organization. Explicit offline saves retain their client identifier and sync only under the matching account, project and sector. Authorization failures remain errors. The old unscoped browser queue is left intact and is not automatically attributed to another user.

Native changes: project-based entry routes to the existing four sector forms or the added soil collection screen, with account-scoped offline soil collections; role-aware navigation hides field submission from VVB/read-only users and hides audit mutations from admins. Generic native queues carry capture owner/organization and project; sync preserves mismatched/legacy records for reconciliation rather than submitting them as the current user. Removed seeded kiln/feedstock identifiers and guessed capacity defaults. Native execution is not claimed until the Flutter check runs.

## Validation at checkpoint

- Dashboard unit tests: 160 passed.
- TypeScript: no errors.
- Changed dashboard files: ESLint --quiet passed.
- Production dashboard build: passed, 41 routes.
- Chromium: 40 passed in 35.6s. Includes 116 sidebar destinations, five sector submissions, role action separation/direct denials, denied-write behavior, offline sync, GPS failure, mobile menu and five existing registry/download regressions. Backend responses are isolated fixtures; external requests are blocked. These tests do not assert live integrations or every possible mutation in every module.
- New backend boundary/authentication checks: 40 passed before broad regression.
- Independent opinion lifecycle: updated to reject super-admin opinion then authenticate a real verifier; 1 passed in 1.57s after fixing the test fixture's administrative auth override.
- Broad local backend run: 418 passed, 21 skipped, two failures and 11 errors. One failure was the outdated super-admin lifecycle expectation (corrected and rerun); the other failure and 11 errors require unavailable local PostgreSQL/PostGIS. A SQLite-only rerun before the final auth-fixture fix had 418 passed, 21 skipped, one deselected and that single lifecycle failure. Final isolated SQLite regression passed: 419 passed, 21 skipped, one deselected in 34.23s. Only the PostgreSQL-dependent telemetry file and the PostgreSQL-dependent sensor/community test were excluded locally; CI still runs them with PostGIS.
- Flutter/Dart are not installed locally. A GitHub workflow now runs Flutter analysis/tests and isolated browser workflows. Native and full PostgreSQL results are pending, not passed.

No production data/schema was modified. The known production agriculture schema gap remains: missing land_units/soil_samples tables and projects.methodology_id nullability require a separate controlled migration. A working collector UI does not prove that production agriculture persistence is ready. Publication, merge and deployment must be recorded separately in HANDOFF.md.
