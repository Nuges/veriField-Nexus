# Engineering Standards

These repository-wide engineering standards establish the baseline enterprise quality expectations for all contributors to VeriField Nexus.

## 1. Naming Conventions
- **Python**: PEP-8 compliant. `snake_case` for variables, functions, and modules. `PascalCase` for classes and types. `UPPER_SNAKE_CASE` for constants.
- **TypeScript**: `camelCase` for variables and functions. `PascalCase` for classes, interfaces, types, and React components.
- **Database**: `snake_case` for tables and columns. Plural nouns for table names (e.g., `organizations`, `projects`).
- **APIs**: Kebab-case for URL paths (e.g., `/api/v1/carbon-sinks`).

## 2. Project Structure
- **Backend**: Strict Domain-Driven Design layout under `app/domains/`. Each domain contains its own `models.py`, `schemas.py`, `service.py`, `repository.py`, and `api.py`.
- **Frontend**: Organized by universal/dynamic components under `src/components/dynamic/` and feature-specific logic mapped to metadata schemas.
- **Cross-Domain**: Shared utilities and core infrastructural code reside in `app/core/` and must not contain business logic.

## 3. Dependency Management
- **Python**: Dependencies are pinned using `requirements.txt` (or modern `pyproject.toml` / `uv` standards). Virtual environments are mandatory.
- **TypeScript**: Use `npm` or `yarn` with strict lockfiles (`package-lock.json`).
- **Security Audit**: Dependencies must be continually scanned using `pip-audit` and `npm audit` to prevent supply chain vulnerabilities.

## 4. Error Handling
- **Exceptions**: Use custom application exception classes that map to specific HTTP status codes globally.
- **No Silent Failures**: Never use bare `except:` or `except Exception: pass` unless strictly handling a benign operational fallback with explicit contextual logging.
- **User-Facing Errors**: API errors must return standardized JSON structures containing an `error_code`, `message`, and optional `details`. Internal stack traces must never leak to the client.

## 5. Logging
- **Structured Logging**: All logs must be structured JSON format for automated ingestion by aggregation tools (Datadog, ELK).
- **Contextual Awareness**: Logs must include tenant IDs, project IDs, trace IDs, and user IDs where applicable.
- **Severity Levels**:
  - `DEBUG`: Tracing algorithm steps and verbose SQL queries.
  - `INFO`: Normal operational milestones (e.g., entity creation, background job start).
  - `WARNING`: Recoverable anomalies or deprecated usage.
  - `ERROR`: Unrecoverable failures requiring SRE attention, including stack traces.
  - `CRITICAL`: Complete system failure, data loss, or security breach.

## 6. Configuration
- **Environment Variables**: All external bindings (DB, Redis, MQTT, APIs) must be injected via environment variables (`.env`).
- **Zero Code Configuration**: Hardcoding hostnames, ports, credentials, or toggle states in source code is strictly forbidden.
- **Validation**: Configurations must be loaded and validated on startup (e.g., using `pydantic-settings`).

## 7. Secrets Management
- **Never Commit Secrets**: Any commit containing plaintext credentials will trigger an immediate pipeline failure and credential revocation protocol.
- **Injection**: Secrets are provided to containers at runtime via secure orchestration (e.g., Kubernetes Secrets, AWS Secrets Manager, GitHub Actions Secrets).

## 8. Typing
- **Python Strictness**: `mypy` is enforced. All function signatures and complex variables must be annotated.
- **TypeScript Strictness**: `strict: true` in `tsconfig`. Avoid `any`; use `unknown` if the type is truly dynamic, followed by type narrowing or Zod validation.

## 9. Documentation
- **Docstrings**: Public functions, classes, and complex algorithms must include descriptive docstrings detailing arguments, return types, and side effects.
- **ADR**: Architecture Decision Records must be authored for any significant architectural shift or external dependency integration.
- **Runbooks**: Operational procedures for deploying, maintaining, and debugging the system must be documented in `operations_manual.md`.

## 10. Testing
- **Test-Driven Design**: Write tests alongside (or before) implementation.
- **Coverage**: Minimum 85% branch coverage is mandatory.
- **Mocking**: External services (APIs, hardware) must be mocked in unit tests, but real infrastructure (Postgres, Redis) should be used in Integration/E2E tests via Docker Compose.

## 11. Performance
- **Asynchronous Execution**: The backend is built on `asyncio`. Avoid blocking I/O on the main event loop. Use background workers (e.g., Celery/Redis) for CPU-bound or slow network tasks.
- **Database Optimization**: Utilize connection pooling (`PgBouncer`), proper indexing, and avoid N+1 query problems via eager loading (`joinedload`, `selectinload`).
- **Caching**: Aggregated data and static metadata definitions should leverage Redis caching to reduce database load.

## 12. Security
- **Least Privilege**: Services and users operate with the minimum permissions required.
- **Encryption**: Data at rest must be encrypted (database layer). Data in transit must use TLS 1.3 (HTTPS, MQTTS).
- **OWASP Top 10**: Code must proactively mitigate SQL Injection, XSS, CSRF, and broken access controls.

## 13. Review Expectations
- **Peer Review**: All PRs require at least one approving peer review before merging.
- **Automated Gates**: CI pipelines must pass before a human reviewer spends time analyzing the logic.
- **Constructive Feedback**: Reviewers evaluate architecture, readability, and edge cases, acting as gatekeepers of the Engineering Constitution.
