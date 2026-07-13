# Code Review Checklist

This checklist is mandatory for all Pull Request (PR) reviewers. Reviewers are the gatekeepers of the VeriField Nexus Engineering Constitution. A PR must not be approved unless every item on this checklist is either verified or deemed explicitly non-applicable.

## 1. Architecture & Design
- [ ] Does this PR strictly adhere to the defined Domain-Driven Design (DDD) boundaries?
- [ ] Does this PR adhere to the Event-Driven Architecture (EDA) principles?
- [ ] Is the implementation overly complex, or could it be simplified?
- [ ] Have universal, reusable components been utilized instead of creating bespoke implementations?

## 2. Metadata Compliance
- [ ] **CRITICAL**: Does this code introduce any hardcoded methodologies, sectors, workflows, or roles? (If yes, REJECT immediately).
- [ ] Is all application behavior driven dynamically by the metadata configurations?
- [ ] Are new configuration schemas backward compatible with existing generic engines?

## 3. Security & Access Control
- [ ] Are RBAC and ABAC checks explicitly implemented and correct for any new endpoints or data mutations?
- [ ] Is user input strictly validated and sanitized (e.g., Pydantic parsing, Zod validation) to prevent injection attacks?
- [ ] Are secrets, passwords, or tokens inadvertently exposed or logged?
- [ ] Does the PR conform to the principle of least privilege?

## 4. Performance & Scalability
- [ ] Are database queries optimized? (e.g., appropriate indexing, avoiding N+1 queries via eager loading).
- [ ] Are heavy CPU or I/O bound tasks offloaded to asynchronous background workers/queues?
- [ ] Does this PR risk introducing memory leaks or unbounded memory growth?
- [ ] Is caching (Redis) utilized appropriately for high-read data?

## 5. Testing
- [ ] Does the PR include adequate Unit Tests covering both happy paths and edge cases?
- [ ] Are Integration Tests provided for database migrations and inter-domain communications?
- [ ] If applicable, are there End-to-End (E2E) or API Contract tests?
- [ ] Does the overall test coverage remain above the mandatory 85% threshold?

## 6. Documentation
- [ ] Are complex algorithms, public APIs, and classes documented with clear, standardized docstrings?
- [ ] Has the OpenAPI (Swagger) schema been validated for clarity and completeness?
- [ ] Have the relevant architecture diagrams, ADRs, or user manuals been updated to reflect this change?
- [ ] Are SRE runbooks updated if this change alters operational procedures?

## 7. Maintainability & Code Quality
- [ ] Does the code comply with the SOLID principles?
- [ ] Is the code "Clean" and self-documenting (clear variable/function naming)?
- [ ] Are there any remaining `TODO`, `FIXME`, or `pass` placeholders in the execution path?
- [ ] Is there duplicated business logic that should be abstracted?

## 8. Readability
- [ ] Is the code formatted correctly according to standard tools (`black`, `prettier`)?
- [ ] Is the logic easy to follow without requiring extensive cognitive overhead?
- [ ] Are comments used to explain *why* something is done, rather than just *what* is done?

## 9. Backward Compatibility
- [ ] Will this change break existing client integrations, mobile apps, or external APIs (e.g., v1 contract breakage)?
- [ ] Will this database migration lock critical tables in production or corrupt existing operational data?

## 10. Deployment & Rollback Impact
- [ ] Is the deployment process straightforward and entirely automated via CI/CD?
- [ ] Can this change be safely rolled back in production without catastrophic data loss or downtime?
- [ ] Does this change require coordinated, synchronized deployments of multiple separate services? (If yes, flag for release management).
