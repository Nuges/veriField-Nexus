# Branching & Release Strategy

VeriField Nexus employs a strict Git Flow branching model and Semantic Versioning strategy to ensure stability across multiple environments (Development, Staging, Production).

## 1. Git Flow Topology

### `main` Branch
- **Purpose**: Represents the current, stable production state.
- **Rules**: 
  - Direct commits are **PROHIBITED**.
  - All merges to `main` must come from a `release/*` or `hotfix/*` branch via an approved Pull Request.
  - Every commit on `main` must be tagged with a Semantic Version.

### `develop` Branch
- **Purpose**: The integration branch for next-release features.
- **Rules**:
  - Direct commits are **PROHIBITED**.
  - All merges to `develop` must come from `feature/*` or `bugfix/*` branches via an approved Pull Request.
  - CI/CD must pass completely before merging.

### `feature/*` Branches
- **Purpose**: Active development of new capabilities or non-critical bug fixes.
- **Source**: Branched exclusively from `develop`.
- **Target**: Merged exclusively back into `develop`.
- **Naming**: `feature/JIRA-123-short-description`

### `release/*` Branches (Release Candidates)
- **Purpose**: Preparing for a production rollout. Allows for final regression testing, documentation, and version bumping.
- **Source**: Branched from `develop`.
- **Target**: Merged into `main` (and back-merged into `develop`).
- **Naming**: `release/v1.1.0`
- **Rules**: Only bug fixes related to the release are permitted here. No new features.

### `hotfix/*` Branches
- **Purpose**: Emergency fixes for critical production defects.
- **Source**: Branched exclusively from `main`.
- **Target**: Merged into both `main` and `develop`.
- **Naming**: `hotfix/JIRA-911-critical-auth-bug`

## 2. Semantic Versioning (SemVer)
Version numbers follow the `MAJOR.MINOR.PATCH` format:
- **MAJOR**: Incompatible API changes, major architectural shifts, or entirely new operational paradigms.
- **MINOR**: New functionality added in a backward-compatible manner (e.g., new domain, new universal component).
- **PATCH**: Backward-compatible bug fixes and security patches.

## 3. Release Process
1. **Feature Freeze**: Code is frozen on `develop` for the target version.
2. **Release Candidate**: A `release/vX.Y.Z` branch is cut.
3. **Validation**: The Release Candidate goes through Staging deployment, E2E testing, and QA validation.
4. **Approval**: The GO/NO-GO Executive Report is approved.
5. **Merge & Tag**: Merged into `main`, tagged `vX.Y.Z`, and back-merged into `develop`.
6. **Deployment**: CI/CD pipeline deploys the tagged release to Production.

## 4. Rollback Strategy
- **Application Level**: Kubernetes / Docker container deployments are rolled back to the previous known-good tag automatically if health checks fail.
- **Database Level**: Database migrations are strictly additive where possible. Destructive migrations (e.g., dropping a column) must be decoupled from the code deployment to allow code rollbacks without requiring a complex data restore. If a catastrophic schema failure occurs, point-in-time recovery (PITR) is initiated from the RDS/Supabase backups.
