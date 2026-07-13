# Methodology Architecture

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. The Problem with Hardcoded Methodologies

A carbon methodology (e.g., Gold Standard's *Technologies and Practices to Displace Decentralized Thermal Energy Consumption*) is a 50+ page scientific document dictating exactly how to calculate emission reductions. 
Historically, software platforms hardcoded these mathematical formulas into their application logic. When the standard body released a new version (e.g., v3.1 to v4.0), it required a massive software engineering rewrite and redeployment, causing immense technical debt and downtime.

VeriField Nexus solves this by separating the *calculation logic* from the *application code*.

## 2. Parameterization and Runtime Resolution

In the CIOS, a Methodology is treated as configuration data, not application code.

### 2.1 The Methodology Package
A Methodology is ingested as a structured JSON/YAML package. It contains:
- **Metadata:** Name, Version, Standard Body, Sector Applicability.
- **Parameter Libraries:** The list of variables required (e.g., $N_{days}$, $FC_{baseline}$, $EF_{fuel}$).
- **Emission Factors:** Global or regional constants (e.g., The carbon intensity of the Rwandan electrical grid).
- **Calculation Engines:** The algebraic formulas represented as Abstract Syntax Trees (ASTs) or safe, sandboxed expression strings (e.g., `(FC_baseline - FC_project) * EF_fuel * N_days`).
- **Validation Rules:** Constraints to check before calculating (e.g., `FC_project` must be > 0).

### 2.2 Methodology Authoring & Deployment
1. A Registry Administrator or Platform Engineer uses a visual "Methodology Builder" UI to author a new package.
2. The package is reviewed and mathematically simulated using historical test data.
3. Upon approval, it is published to the `methodologies` table in the database.
4. *Zero code deployment is required.*

### 2.3 Runtime Execution
When an Audit is approved:
1. The Carbon Engine loads the specific Methodology Package linked to the Project.
2. It fetches the required parameters from the verified Evidence records.
3. It passes the formulas and the parameters into an isolated mathematical expression evaluator.
4. The output `tCO2e` is returned and logged.

## 3. Versioning, Inheritance, and Overrides

- **Versioning:** Methodologies are strictly versioned. A project registers under a specific version (e.g., v3.0). When v4.0 is published, existing projects continue using v3.0 until their crediting period expires, while new projects use v4.0.
- **Inheritance:** A National Regulator can take a global methodology (e.g., CDM AMS-II.G) and inherit it, creating a national variant with customized Emission Factors specific to their country.
- **Overrides:** During Project Registration, a Developer can provide localized, lab-tested parameter overrides (e.g., proving their specific stove is 5% more efficient than the default parameter). These overrides require explicit VVB validation before the Carbon Engine will accept them.

## 4. Architecture Traceability
- **Dependent Documents:** `04-digital-mrv-architecture.md` (which feeds the parameters).
- **Primary Actors:** Registry Administrators, Regulators, Developers, Auditors.
- **Primary Entities:** `MethodologyTemplate`, `CalculationResult`.
