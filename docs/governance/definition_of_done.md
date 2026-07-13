# Definition of Done (DoD)

The Definition of Done is a mandatory, non-negotiable checklist that governs all development for VeriField Nexus. No pull request, feature, methodology, workflow, integration, hardware driver, API, frontend component, or infrastructure change may be merged unless it strictly satisfies every applicable criterion below.

## 1. Architecture Compliance
- [ ] **Architecture is Law**: The implementation adheres strictly to the defined Domain-Driven Design (DDD) and Event-Driven Architecture (EDA).
- [ ] **Metadata-Driven**: The architecture remains entirely metadata-driven.
- [ ] **Zero Hardcoding**:
  - [ ] No hardcoded methodologies.
  - [ ] No hardcoded sectors.
  - [ ] No hardcoded workflows.
  - [ ] No hardcoded roles.
- [ ] **Configuration over Code**: Application logic relies on configuration and metadata rather than imperative branching.
- [ ] **DRY Principle**: No duplicated business logic across domains or components.

## 2. Backend (Python)
- [ ] **SOLID Principles**: Code follows SOLID design principles.
- [ ] **Domain-Driven Design (DDD)**: Logic is correctly encapsulated within the appropriate domain boundary.
- [ ] **Clean Architecture**: Separation of concerns is maintained (API -> Service -> Repository).
- [ ] **Fully Typed**: All functions, methods, variables, and returns have strict Python type hints.
- [ ] **mypy Passes**: `mypy` static type checking passes with zero errors on the codebase.
- [ ] **Ruff Passes**: `ruff` static linting passes with zero errors.
- [ ] **Black Formatted**: Code is formatted using `black` in compliance with PEP8 enterprise standards.
- [ ] **No Dead Code**: All unused variables, imports, and functions are removed.
- [ ] **No TODO / FIXME**: All `TODO`, `FIXME`, or `pass` blocks have been resolved.
- [ ] **No Placeholders**: No mock, scaffold, or placeholder implementations remain in production paths.

## 3. Frontend (TypeScript/React)
- [ ] **Strict TypeScript**: `tsconfig` strict mode passes.
- [ ] **No `any` Types**: No unnecessary use of the `any` keyword.
- [ ] **Reusable Components**: UI leverages reusable, metadata-driven universal components.
- [ ] **Accessibility (a11y)**: Components are fully accessibility compliant (ARIA labels, keyboard navigation, contrast).
- [ ] **Responsive Design**: UI adapts flawlessly to mobile, tablet, and desktop viewports.
- [ ] **No Duplicated Logic**: Shared state and UI logic are extracted to custom hooks or context providers.

## 4. Database (PostgreSQL/SQLAlchemy)
- [ ] **Alembic Migrations**: All schema changes are accompanied by an automatic/manual Alembic migration script.
- [ ] **Referential Integrity**: Foreign keys and constraints are maintained.
- [ ] **Indexes Reviewed**: Proper indexing is applied to queryable fields for performance optimization.
- [ ] **No Legacy Anti-Patterns**: No deprecated column types, unstructured JSON dumps (unless strictly necessary for metadata payload abstraction), or legacy schema designs are introduced.

## 5. API (FastAPI)
- [ ] **OpenAPI Documentation**: API routes accurately reflect models in the automatically generated OpenAPI (Swagger) schema.
- [ ] **Input Validation**: Comprehensive Pydantic schema validation is applied to all request payloads.
- [ ] **Standardized Error Handling**: Errors utilize the standardized enterprise HTTP exception schemas.
- [ ] **Version Compatibility**: Changes maintain backward compatibility (e.g., `v1` API contract is not broken).

## 6. Security
- [ ] **RBAC Verified**: Role-Based Access Control logic is correctly mapped and tested.
- [ ] **ABAC Verified**: Attribute-Based Access Control correctly isolates tenant metadata and assets.
- [ ] **Authorization Tested**: Explicit unit/integration tests assert that unauthorized access is blocked.
- [ ] **Input Sanitization**: All external inputs are validated and sanitized to prevent injection attacks.
- [ ] **Secrets Protected**: No secrets, tokens, keys, or passwords are hardcoded or logged in plaintext.
- [ ] **No Sensitive Commits**: `.env` and sensitive configurations are ignored by git.

## 7. Testing
The test suite must meet the following mandatory thresholds:
- [ ] **Coverage Threshold**: Minimum 85% branch coverage required for new code.
- [ ] **Unit Tests**: Granular logic is thoroughly tested.
- [ ] **Integration Tests**: Database, cache, and inter-domain communication paths are tested.
- [ ] **End-to-End Tests**: Complete user workflows are simulated.
- [ ] **API Contract Tests**: Endpoint requests and responses match defined schemas.
- [ ] **Metadata Validation Tests**: Dynamic schema generation is tested against invalid configuration states.
- [ ] **Hardware Simulation Tests**: MQTT, OTA, and edge interactions are mocked and tested (where applicable).
- [ ] **Regression Tests**: Any previously identified defects have explicit tests preventing regression.

## 8. Documentation
Every feature or significant change must include:
- [ ] **Developer Documentation**: Inline docstrings and architecture decision records (ADRs) if applicable.
- [ ] **Architecture Documentation**: High-level component diagrams and interaction models updated.
- [ ] **API Documentation**: Pydantic models contain human-readable `description` metadata.
- [ ] **User Documentation**: If applicable, end-user manuals and UI tooltips updated.
- [ ] **Operational Documentation**: Runbooks and SRE response plans updated if the change affects production observability or deployment.

## 9. Performance
- [ ] **Performance Impact Assessed**: High-load operations (e.g., telemetry ingestion, large queries) have been benchmarked.
- [ ] **No Significant Regressions**: API response times (P95) and database latencies remain within enterprise thresholds.
- [ ] **Monitoring Hooks Added**: Where required, new business metrics are pushed to the observability stack.

## 10. Observability
- [ ] **Logging Implemented**: Structured, contextual JSON logging is applied at appropriate severity levels.
- [ ] **Metrics Exposed**: Prometheus/Grafana metrics capture throughput and latency for the new feature.
- [ ] **Tracing Maintained**: OpenTelemetry tracing contexts are preserved across async queues and event buses.
- [ ] **Errors Actionable**: Error logs contain sufficient context (IDs, stack traces) for SRE resolution.

## 11. CI/CD Pipeline
- [ ] **All Pipelines Pass**: GitHub Actions (or equivalent CI runner) exhibit a green status.
- [ ] **No Failed Checks**: No individual step in the verification matrix failed.
- [ ] **No Skipped Validation**: No mandatory validation gate was intentionally bypassed without explicit executive approval.
