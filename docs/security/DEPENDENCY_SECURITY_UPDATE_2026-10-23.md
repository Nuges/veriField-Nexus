# VeriField dependency security update

Date: 23 October 2026 (Africa/Lagos).
Status: **READY_FOR_MERGE**. The user authorized commit/push and merging into main
after passing validation. The exact existing Render service has been verified;
hosted deployment will follow the authorized merge.
Base: `a234ab7` on `work/continue-antigravity`; isolated implementation branch:
`work/security-dependencies-2026-10-23`.

## Result and scope

Updated Next.js, its matching compiler packages and ESLint configuration from 16.2.4
to 16.4.2. Updated compatible affected indirect dependencies through the existing npm
resolver without `--force`, custom forks, overrides or audit suppression. React and
React DOM remain 19.2.4. No product source, backend, RBAC, API, migration, deployment
configuration or protected operational record changed.

The production dependency audit now reports **zero vulnerabilities**, exit 0. The full
audit reports **five high-severity package entries and zero critical entries**, exit 1,
down from 16 affected packages (1 low, 1 moderate, 13 high, 1 critical). The remaining
five entries form one development-tool dependency chain, detailed below. This is not
a claim that the full npm audit returned zero or that the entire platform is secure.

## Exact direct changes and affected dependencies

| Dependency | Before | After | Purpose |
|---|---|---|---|
| next | 16.2.4 | 16.4.2 | Supported 16.x update beyond the published critical security fixes |
| eslint-config-next | 16.2.4 | 16.4.2 | Keep lint tooling aligned with Next.js; no major downgrade |
| All six explicitly declared @next/swc-* entries across root/dashboard manifests | 16.2.4 | 16.4.2 | Preserve matching native compilers for Mac and Linux |
| sharp | 0.34.5 | 0.35.5 | Patched image-processing dependency selected by Next.js |
| postcss | 8.4.31 / 8.5.12 | 8.5.23 / 8.5.31 | Patched runtime/build dependency branches |
| nanoid | 3.3.11 | 3.3.20 | Compatible patched 3.x resolution |
| ws | 8.20.0 | 8.22.0 | Compatible patched 8.x resolution |
| @babel/core | 7.29.0 | 7.29.7 | Patched development dependency |
| brace-expansion | 1.1.14 / 5.0.5 | 1.1.21 / 5.0.12 | Compatible fixes in both existing dependency branches |
| browserslist | 4.28.2 | 4.29.4 | Compatible patched 4.x resolution |
| js-yaml | 4.1.1 | 4.3.2 | Compatible patched 4.x resolution |
| source-map-js | 1.2.1 | 1.2.2 | Patched 1.x resolution |
| baseline-browser-mapping | 2.10.24 | 2.11.31 | Compatible patched 2.x resolution |

Full transitive version changes, including necessary platform image binaries and
supporting dependency changes, are recorded in `dependency-validation-2026-10-23.json`.
The lock was generated using the nested install strategy to retain its existing
workspace placement and avoid the larger unrelated refresh from default hoisting.
`npm ci` consumes the checked-in lock without requiring a repository config change.
Both Darwin compiler variants are locked at 16.4.2 under the root optional dependencies;
Linux x64 compiler 16.4.2 was actually loaded by the successful build. Next.js and
sharp require Node >=20.9.0; the previous Next.js version already had that minimum.

## Remaining full-audit entries

`eslint-config-next -> @next/eslint-plugin-next -> fast-glob -> micromatch -> braces`.
All five installed paths are marked development-only in the final lockfile. They
propagate one advisory: GHSA-vfj7-8cjw-p6xm / CVE-2026-93687, affecting braces <=3.0.3.
The latest published braces release remains 3.0.3. The GitHub Advisory Database withdrew
this advisory on 23 October 2026, stating it is not practically exploitable. npm still
returned it during this validation. The discrepancy is recorded rather than hidden.

npm proposes downgrading eslint-config-next to 14.2.35 to alter that chain. That would
mismatch the active Next.js 16 tooling and was not applied. No scanner ignore list,
false clean-audit claim, third-party fork or unsupported dependency replacement was
introduced. Recheck the advisory feed and raw audit on the Mac; counts may change as
upstream withdrawal metadata propagates.

Primary sources reviewed:

- https://github.com/vercel/next.js/releases/tag/v16.4.2
- https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw
- https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr
- https://github.com/advisories/GHSA-vfj7-8cjw-p6xm
- https://github.com/micromatch/braces/issues/73
- Official npm registry metadata for Next.js 16.4.2, eslint-config-next 16.4.2,
  @next/swc-darwin-arm64 16.4.2, sharp 0.35.5, postcss 8.5.23 and braces latest.

## Executed verification

Commands ran from the isolated repository root on Linux x64, Node 24.19.0/npm 11.9.0.
Exact command flags, counts, audit results and package versions are in the JSON companion.

| Check | Result | Exit |
|---|---|---|
| Clean npm ci with lifecycle scripts disabled | 442 packages installed | 0 |
| Frontend unit tests | 138 passed, 0 failed | 0 |
| Independent TypeScript check | Passed | 0 |
| Production webpack build with explicit dead loopback API/backend URLs and telemetry disabled | Next.js 16.4.2, 41 pages generated | 0 |
| Existing lint script | 0 errors, 329 warnings | 0 |
| Baseline lint comparison | 0 errors, 324 warnings | 0 |
| Normal lifecycle-enabled npm ci | 442 packages installed; lock unchanged | 0 |
| Installed dependency tree | Next/compiler/lint versions aligned; React unchanged | 0 |
| Full npm audit (lockfile) | 5 high, 0 critical, all from withdrawn development advisory | 1 |
| Production npm audit (lockfile) | 0 vulnerabilities | 0 |
| Production-server HTTP smoke | /login, registry, verifications and project laboratory shells each returned HTTP 200 with expected HTML | 0 |
| Whitespace/diff check | Passed | 0 |

The five added lint warnings come from the new Next.js
`no-location-assign-relative-destination` rule on existing assets, methodologies,
settings, login and API-client navigation code. No warning suppression or unrelated
navigation refactor was added. Full lint deltas are recorded in the JSON companion.

HTTP smoke checks prove server startup and HTML delivery only. They do not prove
browser interaction, authentication or backend integration. The local server used
explicit dead-loopback backend settings and was stopped after the checks.

## Browser verification and other limits

**PASS ON MAC:** after applying the security patch, the user confirmed all five
Chromium scenarios passed in 2.5 seconds, exit 0. The user also supplied successful
Mac npm ci output (440 packages added, 442 audited), 138 unit passes, independent
TypeScript, quiet lint, the Next.js 16.4.2 build (41 pages), production audit with
zero vulnerabilities, and git diff --check. The silent steps returned successfully
in an &&-chained command. Mac Node/npm versions and a full lint warning count were
not present in the output and are not inferred.

Browser command from the Mac dashboard directory:

`BASE_URL=http://127.0.0.1:3001 npx playwright test tests/phase2_registry_workflow.spec.ts --project=chromium`

The scenarios cover unassigned-pilot export blocking, selected-project readiness and
download success, viewer access, a denied download without legacy fallback, and the
laboratory template download. Backend responses are mocked; non-loopback browser
requests are aborted by the existing test. These results validate the targeted mock
workflows after the dependency update, not real authentication or operational data.

Linux browser downloads remained BLOCKED — ENVIRONMENT because both full Chromium
and headless-shell downloads were truncated, and system installation was unavailable.
That local limitation is retained in the record; the required mock browser run was
completed separately on the user's Mac.

Backend tests were not repeated because no backend or application source changed.
No security exploit test, production access, live-registry call, protected operational
data read/write, migration or deployment occurred during implementation/validation.
After the successful Mac checks, the user separately authorized committing/pushing
this security checkpoint and merging the accumulated work into main for deployment.
The earlier a234ab7 Phase 2 checkpoint and successful CI remain intact on GitHub.

## Changed files and next action

The root and dashboard package manifests, root lockfile and HANDOFF.md are modified.
This report, a validation JSON companion, and three raw npm audit snapshots are added
under docs/security/. They retain the before/after evidence and upstream discrepancy.

All targeted dependency-update checks now pass on the Mac and the available Linux
checks pass as recorded. The raw full audit still returns five high development-tool
entries derived from the withdrawn advisory; it is not reported as a zero-findings
full audit. This is a tested source checkpoint, not production-release approval.

The user confirmed that the closing documentation patch applied cleanly and the
expected nine files are modified/new. The latest instruction authorizes committing
and pushing this tested checkpoint, then merging the accumulated recovered work into
main for Render deployment. Only HANDOFF.md and security report/results changed after
the successful tests; dependency files and application source have not changed.
Keep both earlier stashes and preserve current Mac copies before synchronizing.

Read the current PR checks before merge. The user supplied the exact Render service
URL; read-only discovery verified srv-d7r4an3t6lks73fnffm0 (veriField-Nexus) in Eddi,
linked to this repository/main with auto-deploy enabled on commit. The current live
deploy before merge is dep-db6a2bd9fdbs73fd49n0 at 3585531. Monitor the new automatic
deploy after merge; no new deploy has yet been triggered or verified by this
checkpoint. See HANDOFF.md for the active release instruction and next step.
