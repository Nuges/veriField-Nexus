# Contribution Guidelines

We welcome contributions to VeriField Nexus! To maintain the enterprise-grade stability and architectural integrity of the platform, all engineers must follow this contribution process.

## 1. Development Lifecycle
1. **Issue Assignment**: Ensure your work is tracked against a registered issue or JIRA ticket.
2. **Branching**: Create a `feature/*` or `bugfix/*` branch from the latest `develop` branch.
3. **Implementation**: Write code adhering to the [Engineering Standards](engineering_standards.md) and [Architecture Principles](architecture_principles.md).
4. **Testing**: Implement required Unit, Integration, or E2E tests. Ensure local execution of the test suite passes (`pytest`, `npm test`).
5. **Commits**: Write descriptive, imperative commit messages (e.g., `Add generic metadata ingestion route`).

## 2. Coding Expectations
- **Zero Hardcoding**: Ensure your feature works globally across all methodologies. Do not hardcode configurations.
- **Type Safety**: Fully type your Python and TypeScript code.
- **Formatting**: Run `black`, `ruff`, and `prettier` before committing.
- **Documentation**: Document complex logic inline and update architecture documents if required.

## 3. Pull Request Process
1. **Draft PR**: Open a Draft PR if you need early feedback.
2. **Ready for Review**: When complete, open the PR against the `develop` branch.
3. **CI/CD Checks**: Ensure all automated GitHub Actions pipelines pass (Linting, Tests, Security Scans). A failed pipeline blocks the review process.
4. **Self-Review**: Complete the mandatory [Definition of Done](definition_of_done.md) checklist in your PR description.
5. **Peer Review**: Assign at least one code reviewer. The reviewer will use the [Code Review Checklist](code_review_checklist.md).
6. **Revisions**: Address reviewer comments promptly. Do not argue against the core Architecture Principles.

## 4. Merge Requirements
A Pull Request may only be merged if it satisfies ALL of the following:
- Passes the strict Definition of Done.
- Receives at least one Approved status from a senior reviewer or code owner.
- Passes all automated CI/CD checks (Zero failed tests, coverage >= 85%, no security vulnerabilities).
- Has no outstanding unresolved review comments.
- Is up-to-date with the base branch (rebasing may be required).

## 5. Deployment Post-Merge
- Once merged into `develop`, your code will be automatically deployed to the **Development / Staging** environment.
- Monitor the observability stack (logs, metrics) for any regressions introduced by your feature.
- Your code will be bundled into the next Release Candidate according to the [Branching & Release Strategy](branching_release_strategy.md).
