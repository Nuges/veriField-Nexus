# Business Domains

The VeriField Nexus CIOS is partitioned into distinct Business Domains. Each domain represents a major functional area of the platform, encapsulating the capabilities required to manage specific aspects of the climate infrastructure lifecycle.

## 1. Identity & Organization Domain
**Purpose:** Manages the identities of all actors interacting with the platform, the organizations they belong to, and the complex hierarchical relationships between those organizations.
- **Key Capabilities:** Identity Management, Organization Management, Tenant Provisioning, Role-Based Access Control (RBAC), Attribute-Based Access Control (ABAC), Machine Identity Management.
- **Core Entities:** `User`, `Organization`, `ServiceAccount`, `Role`, `Policy`.

## 2. Governance & Policy Domain
**Purpose:** Defines the rules of engagement. This domain acts as the global policy engine, determining what is permissible within the platform based on geographical, methodological, and regulatory constraints.
- **Key Capabilities:** Jurisdiction Management, Registry Federation, Methodology Management, Compliance Rule Definition.
- **Core Entities:** `Jurisdiction`, `RegistryAdapter`, `Methodology`, `ComplianceRule`, `SpatialBoundary`.

## 3. Operations & Asset Domain
**Purpose:** The core execution engine for developers and operators managing physical climate assets on the ground.
- **Key Capabilities:** Programme Management, Project Lifecycle Management, Asset Registration, Activity Tracking.
- **Core Entities:** `Programme`, `Project`, `Asset`, `Installation`, `Activity`.

## 4. Monitoring, Reporting, and Verification (MRV) Domain
**Purpose:** Responsible for the collection of empirical data and the rigorous processes used to verify and validate that data against established methodologies.
- **Key Capabilities:** Evidence Collection, Continuous Monitoring, IoT Integration, Field Verification, Independent Audit, Validation.
- **Core Entities:** `Evidence`, `TelemetryData`, `VerificationTask`, `Audit`, `ValidationResult`.

## 5. Carbon Ledger & Issuance Domain
**Purpose:** The financial and accounting engine of the platform. It translates verified environmental impact into tradable, traceable digital assets.
- **Key Capabilities:** Carbon Accounting, Credit Issuance, Registry Synchronization, Ledger Management, Retirement Tracking.
- **Core Entities:** `CarbonCredit`, `LedgerTransaction`, `IssuanceBatch`, `RetirementCertificate`.

## 6. Enterprise Analytics & Intelligence Domain
**Purpose:** Provides macroscopic visibility into the health, compliance, and impact of the platform across all jurisdictions and programmes.
- **Key Capabilities:** Executive Dashboards, National Reporting, Spatial Analytics, AI Forecasting, NDC Tracking.
- **Core Entities:** `DashboardConfig`, `ReportDefinition`, `AnalyticSnapshot`.

## Domain Interaction

These domains do not operate in isolation. They communicate via explicit interfaces and domain events. For example, when the MRV Domain publishes an `AuditApproved` event, the Carbon Ledger Domain reacts by initiating an `IssuanceBatch`.
