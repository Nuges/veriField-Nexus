# Controlled agriculture schema repair

Date: 23 October 2026. Application base: 897ce81 (application source 1f606c7).
Branch: fix/agriculture-schema-repair. Status: prepared; production not changed.

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
