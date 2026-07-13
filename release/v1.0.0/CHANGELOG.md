# VeriField Nexus Changelog

## [v1.0.0] - 2026-07-13

### Added
- Complete integration of Dynamic Metadata execution using `asteval`.
- Missing Hardware Device telemetry lifecycle hooks.
- Operations runbook and CI/CD validation.
- Missing Alembic definitions in Base metadata array mapping.

### Removed
- Deprecated RC experimental features.
- Hardcoded string variables bypassing methodology definitions.
- `TODO`, `FIXME`, and `NotImplementedError` stubs from production codebase.

### Fixed
- Missing Verification tasks table generation issue across integration boundary.
- Hardware model property mapping bug (`hardware_type` vs `device_type`).
