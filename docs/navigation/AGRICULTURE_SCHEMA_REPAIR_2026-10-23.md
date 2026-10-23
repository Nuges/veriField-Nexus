# Controlled agriculture schema repair

Date: 23 October 2026. Application base: 897ce81 (application source 1f606c7).
Branch: fix/agriculture-schema-repair. Status: PR #4 merged; controlled production schema repair applied and verified.

## Observed production state

Read-only inspection of Supabase project rxlfxrbyhagyofzfwzoa found 111 public
tables/partitions. None of the 28 agriculture ORM tables or their boundary-version
dependency exists. projects.methodology_id is UUID NOT NULL, while the deployed
ORM and optional-methodology onboarding permit NULL. Its foreign key is valid.
Alembic records 3307d715f0e7; Supabase migration history is empty. Application
startup has separately added other objects, so that old marker is not a reliable
instruction to replay the remaining historical chain.

Production has six projects and one activity; the affected organization still
has zero projects. Existing project values and methodology assignments must remain
unchanged. No production row data is copied into tests. The fixture contains only
the inspected column definitions of ten existing dependency tables, plus synthetic
rows and a small activity sentinel; it does not reproduce activity partitioning.

## Exact change

New Alembic revision 615d2865c464 contains frozen REPAIR_SQL. The controlled SQL is
a single DO statement, with a three-second lock timeout, 60-second statement
timeout and advisory transaction lock. It requires existing PostGIS; it does not
install or move extensions. Geometry resolves with the existing extensions schema.
Target relations are explicitly qualified in public.

It checks that every target table is absent and required UUID dependencies exist
before modifying anything. Any partial schema aborts for inspection. It widens
projects.methodology_id to nullable, retaining the foreign key and every stored
value. It creates exactly these 29 new tables:

| Area | New tables |
| --- | --- |
| Foundation | land_units, project_boundary_versions, agriculture_strata, agriculture_stratum_memberships, agriculture_management_records |
| Legacy observations | soil_samples, tree_observations, satellite_observations, agriculture_model_runs |
| Ground sampling | sampling_campaigns, sampling_plan_versions, sampling_points, physical_samples, sample_collection_events, chain_of_custody_events |
| Laboratory | laboratory_receipts, laboratory_analyses, laboratory_results, sample_qa_reviews, laboratory_import_batches, laboratory_import_rows |
| Quantification | quantification_input_snapshots, agriculture_prerequisite_assessments, agriculture_soc_stock_snapshots, agriculture_soc_stock_results, agriculture_soc_layer_results, agriculture_soc_change_results, agriculture_net_ghg_results, agriculture_vintage_ghg_results |

Columns, foreign keys, unique constraints, spatial indexes and declared indexes are
frozen from the deployed ORM; additional leading-column foreign-key indexes cover
optional evidence/actor links. Cyclic foreign keys are added after table creation.
RLS is enabled on each new table, and all privileges are revoked from PUBLIC and
the existing anon/authenticated/service_role client roles. No JWT policy is guessed:
the application uses its existing SQL owner connection plus FastAPI tenant/RBAC
checks. No new direct Supabase Data API path is introduced.

The SQL does not insert/update/delete projects, users, organizations, activity
records, methodology assignments or entitlements. It does not create a farm
project, import the 183-acre boundary, interpret soil results, select a methodology,
or mark any carbon result verified. Other missing EO/biochar tables are outside
this repair; this is agriculture persistence, not a full-database reconciliation.

## Migration histories

The Alembic revision follows the current repository head c7d8e9f0a1b2, so normal
clean installations can continue using the established chain. If all target
tables already exist, that path only ensures nullable methodology; it does not
rewrite their policies, grants or columns. The inspected historical chain also omits four legacy tables (agriculture_model_runs, satellite_observations, soil_samples and tree_observations). An explicit completion path creates only those four when exactly the other 25 exist. Every other partial schema is rejected; the controlled production SQL still requires all 29 absent.

For the drifted live database, apply only the reviewed frozen REPAIR_SQL through
Supabase apply_migration, with its own descriptive history entry. Do not invoke
alembic upgrade head, manually advance alembic_version, or stamp old migrations as
applied. Reconcile the older Alembic history separately before adopting automatic
full-chain upgrades in production. Reapplying the standalone SQL intentionally
aborts when tables exist; check history and schema rather than retry blindly.

## Verification and execution order

1. Publish the repair in a draft PR and run the new disposable PostGIS CI step.
   The test guard accepts only localhost:5432/test_db with test_user, creates
   separately named vf_agri_repair_* databases, and never falls back to a real DB.
2. Build those fixture schemas from the inspected columns, not ORM create_all or
   historical upgrades. Test nullable unassigned agriculture projects, foundation
   and real land-unit persistence, all 29 column contracts, client privilege/RLS
   denial, preservation of existing records/FKs and Alembic marker, partial schema
   rejection, injected-failure rollback and the existing physical sample/custody
   collection contract against PostGIS. CI destroys its disposable service; the
   tests issue no DROP DATABASE or DROP TABLE.
3. Require the normal full CI/migration checks to pass as well. Recheck production
   target-table absence, dependency keys and protected-record fingerprints.
4. Apply the one atomic migration, then verify all target tables, columns, RLS,
   client grants, methodology nullability/FK and unchanged protected fingerprints.
   Run Supabase advisors and live API readiness checks. No protected operational
   pilot or real field sample is used for a write test.
5. Record the exact SQL hash, source/PR/CI and Supabase history entry in HANDOFF.md.
   Any later farm project recovery must use actual approved request details and
   the application's checks, rather than inventing project data or entitlements.

## Recovery

If any statement fails, the single DO statement rolls back the entire repair,
including the nullability change. A lock timeout leaves the old schema intact.
Fix the cause and inspect state before a deliberate retry.

After a successful commit, preserve all additive tables and records. The existing
application can continue with nullable methodology. If a workflow must be stopped,
stop its writes and revert the relevant application change while retaining data;
do not run historical destructive downgrades or delete new samples. Restoring NOT
NULL would require proving that no unassigned project exists, and any physical
schema removal requires a separately reviewed, explicitly approved recovery plan.
The new downgrade refuses destructive reversal.

## Results at preparation checkpoint

Local command (isolated SQLite import context, no network DB):
python -m pytest schema_tests/test_agriculture_schema_repair.py -q --tb=short
Result: 6 passed, 6 skipped in 0.27s (after the historical-gap regression was added). The skips require disposable PostGIS and are
not claimed passed. A local PostgreSQL installation was unavailable because the
workspace cannot change the required OS user IDs; no production database was used
as a substitute. Initial GitHub run 40010251070 passed all 11 repair tests in 7.85s, including actual PostGIS writes and rollback. The subsequent normal Alembic chain failed because it omitted four legacy models; the new explicit completion path and its regression address that. Final PostGIS/full CI results remain pending.

Supabase security advisor returned only the pre-existing Auth leaked-password
protection warning; this repair does not change authentication configuration.
Supabase guidance checked: https://supabase.com/docs/guides/api/securing-your-api
and https://supabase.com/docs/guides/database/postgres/row-level-security.

Read-only protected-data baseline before any production change: six projects
(hash 04df95945cc53de6428ce9fbf36b133c), one activity
(hash c4338c5a56a1fdf95cc17d0567fcdc09), affected organization hash
c40074f3275d76d136a5f5db88934b5b, and zero projects in that organization.
Recompute these after approval and immediately before/after execution; concurrent
legitimate writes require reviewing changed fingerprints rather than overwriting.

## Applied production checkpoint

- Tested source: 6fb5c973198f9be0fe95bfadd4888417fbeded88. PR #4
  https://github.com/Nuges/veriField-Nexus/pull/4 merged as
  22dab9dfb9b9f0d9213297a2fcfc7e482d18afd8. Merge tree
  ef43f0fc7ffb1c67ae5d07a4e2fb7504a4164276 exactly matches the tested source.
- Final PR runs 40010798243 and 40010798282 passed: 12 independent repair tests
  in 9.44s, normal Alembic and authoritative PostGIS, 847 backend tests (34 skipped,
  five deselected, one warning in 61.83s), 160 frontend unit tests/typecheck/build,
  SDK/STAC, 41 Chromium scenarios (1.3m), 10 Flutter tests. Native analysis retains
  one nonfatal style info; it is not a physical-device run.
- Supabase migration name: restore_agriculture_schema_20261023; version:
  20261023192615. Applied only frozen REPAIR_SQL with SHA-256
  c3edd50fcacaae7ea042ac25a0d1ccf83971b9ad4a64e3a2418529e5d4bedba5.
  Live PostgreSQL reports 17.6; PostGIS is 3.3.7 in extensions. CI used its
  disposable PostgreSQL 15/PostGIS 3.4 service, not an exact production clone.
- Immediate preflight confirmed all 29 target relations absent, methodology still
  NOT NULL, unchanged protected hashes, old Alembic marker and no Supabase entries.
  The application was checked out at the identical merged/tested tree before apply.
- Post-apply: 29 tables owned by postgres, all expected column names/nullability
  match the deployed ORM; RLS enabled on all 29; no PUBLIC/anon/authenticated/
  service_role grants; zero invalid foreign keys; zero unindexed new foreign keys.
  projects.methodology_id is nullable with its original RESTRICT foreign key intact.
- The six project records, one activity and affected organization have exactly the
  same hashes as the baseline above. Affected organization project count remains 0.
  The 29 new tables contain 0 rows total. No farm/project/methodology selection,
  sample, boundary, result or entitlement was fabricated or provisioned.
- Alembic remains 3307d715f0e7 deliberately. Only Supabase history records this
  controlled bridge; do not stamp or replay the older chain.
- Supabase advisor now reports 29 informational rls_enabled_no_policy notices.
  This is intentional for private backend-only tables without client grants;
  adding public JWT policies to silence the notice would change the access model.
  Reference: https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy.
  The earlier Auth leaked-password warning remains unchanged:
  https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection.
- Live HTTP: /health 200/healthy, /api/v1/health/ready 200/ready,
  unauthenticated /api/v1/agriculture/land-units 401. Error-level app log query
  from 19:26:00Z through 19:28:16Z returned no entries (short window only).
- Vercel provider status is success for merge 22dab9d:
  https://vercel.com/nuges-projects-381ad4bc/veri-field-nexus/DfsVGWW4YGjCYB2sWMBrEaGqCkFb.
  Render remains on live dep-dbdqshkipgvc739qum30/application source 1f606c7.
  This PR changes migrations/tests/CI/docs only; it does not change API/dashboard/
  mobile runtime code. No additional Render rollout was needed or triggered.
- Main CI runs 40011329098 and 40011329245 also completed successfully: 12 repair tests in 13.34s, 847 backend tests in 88.63s (34 skipped, five deselected, one warning), 41 browser scenarios in 1.3m, 10 Flutter tests, and the migration/typecheck/build/SDK/STAC gates.
  No signed-in production write or actual farm workflow has been run. The user can
  now create an unassigned agriculture project through Projects; selecting a
  methodology remains an explicit project decision. Other missing EO/biochar
  objects and broader migration-history reconciliation remain separate work.

- Final checkpoint is documentation-only with [skip ci] [skip render]; runtime,
  migration and test source remain identical to merge 22dab9d. Main and the shared
  continuation branch are synchronized. Preserve existing Mac stashes; do not
  reapply old patches or re-execute the applied SQL over this now-present schema.
