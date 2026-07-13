# Enterprise Governance Architecture

Governance dictates the business rules, compliance requirements, and operational constraints applied to actors and entities within the CIOS.

## 1. Multidimensional Governance

Governance is not monolithic. It is applied through a hierarchy of intersecting scopes.

### 1.1 Global Governance
Policies enforced universally by the Platform Operator.
- *Examples:* Security baselines (MFA required), data retention minimums, immutable audit logging requirements.

### 1.2 National / Jurisdictional Governance
Policies enforced geographically. Any project physically located within a Jurisdiction inherits these rules.
- *Examples:* "Biochar projects are illegal in this region," or "All Cookstove projects must allocate 10% of issued credits to the National NDC buffer."

### 1.3 Registry & Methodology Governance
Policies enforced conceptually based on the chosen scientific standard.
- *Examples:* "Gold Standard requires 3 independent verification points per asset per year," or "The Baseline emission factor for this grid is 0.5 tCO2/MWh."

### 1.4 Organizational Governance
Internal operational policies set by the Project Developer.
- *Examples:* "All field evidence must be reviewed by a Senior Verifier before submission to the VVB."

## 2. Policy Resolution Engine

When multiple governance scopes intersect, the CIOS resolves conflicts using strict precedence rules to determine the effective runtime metadata or constraint.

**Precedence Order (Highest to Lowest):**
1. Global Policy
2. National Jurisdiction Policy
3. Registry / Methodology Policy
4. Organizational Policy

*Scenario:* An Organization sets a policy allowing Evidence to be uploaded offline. However, the Jurisdiction policy mandates Real-Time GPS stamping. The Policy Resolution Engine evaluates the `UploadEvidence` action and **DENIES** it if the real-time GPS stamp is missing, overriding the Organization's more lenient policy.

## 3. Architecture Governance

This documentation suite serves as the ultimate governance mechanism for the software development lifecycle itself.

- **No Implementation Before Architecture:** Engineers cannot create a new database table or API endpoint without an approved addition to the Bounded Contexts and Entity diagrams in this Enterprise Architecture Blueprint.
- **Architectural Decision Records (ADRs):** When diverging from a standard pattern (e.g., choosing a Graph DB instead of PostgreSQL for a specific new capability), an ADR must be submitted, reviewed by the Architecture Board, and merged into `docs/architecture/adr/`.
- **Blueprint Versioning:** The blueprint evolves via Pull Requests, ensuring architectural changes undergo the same rigorous peer review as application code.
