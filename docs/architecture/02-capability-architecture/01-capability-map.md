# Enterprise Capability Map

This document outlines the core business capabilities of the VeriField Nexus CIOS. Capabilities represent *what* the platform does, agnostic of the specific software modules that implement them.

## 1. Governance & Policy Capabilities

### 1.1 Jurisdiction Management
- **Purpose:** Define and manage the legal and geographical boundaries where climate projects operate.
- **Owner:** National Regulators / Super Admin.
- **Dependencies:** Spatial Intelligence Capability.
- **Input:** GeoJSON boundaries, National Policy Definitions.
- **Output:** Jurisdiction Entity, Active Boundary Context.
- **Consumers:** Project Lifecycle Management, Compliance Engine.

### 1.2 Registry Federation
- **Purpose:** Standardize the communication and integration with external carbon registries (e.g., Verra, Gold Standard, Article 6 mechanisms).
- **Owner:** Platform Operator.
- **Dependencies:** API Gateway, Integration Architecture.
- **Input:** External Registry APIs, Authentication Keys.
- **Output:** Standardized Registry Interface, Synced Project Status.
- **Consumers:** Issuance Capability, Project Registration Capability.

### 1.3 Methodology Management
- **Purpose:** Digitalize and version-control the scientific methodologies used to calculate carbon reductions/removals.
- **Owner:** Registries / Standards Bodies.
- **Dependencies:** Governance Management.
- **Input:** PDF/Text Methodologies, Formula Strings, Data Requirements.
- **Output:** Executable Methodology Configuration.
- **Consumers:** Compliance Engine, Carbon Accounting Capability.

## 2. Operations Capabilities

### 2.1 Organization Onboarding & Management
- **Purpose:** Register and verify the legal entities operating on the platform (Developers, VVBs, etc.).
- **Owner:** Platform Administrator.
- **Dependencies:** Identity & Access Management.
- **Input:** KYB/KYC Documents, Organization Details.
- **Output:** Tenant Provisioning, Organization Role Assignment.
- **Consumers:** All Capabilities.

### 2.2 Project Lifecycle Management
- **Purpose:** Manage the end-to-end flow of a climate project from drafting to closure.
- **Owner:** Project Developers.
- **Dependencies:** Jurisdiction Management, Methodology Management.
- **Input:** Project Design Documents (PDD), Spatial Coordinates.
- **Output:** Registered Project Entity, Lifecycle State Changes.
- **Consumers:** Verification Capability, Compliance Capability.

### 2.3 Asset Lifecycle Management
- **Purpose:** Track physical assets (e.g., cookstoves, solar panels, biochar kilns) deployed under a project.
- **Owner:** Field Supervisors / Developers.
- **Dependencies:** Project Lifecycle Management.
- **Input:** Asset Serial Numbers, GPS Locations, Installation Dates.
- **Output:** Active Asset Inventory.
- **Consumers:** Monitoring Capability, IoT Integration.

## 3. MRV (Monitoring, Reporting, Verification) Capabilities

### 3.1 Monitoring & Evidence Collection
- **Purpose:** Gather empirical data proving the ongoing operation and impact of assets.
- **Owner:** Field Agents / IoT Devices.
- **Dependencies:** Asset Lifecycle Management, Document Management.
- **Input:** Photos, Surveys, Telemetry Data (IoT).
- **Output:** Raw Evidence Records, Timeseries Data.
- **Consumers:** Verification Capability, AI Analytics.

### 3.2 Verification
- **Purpose:** Assess collected evidence against the project's baseline and methodology requirements.
- **Owner:** Verifiers / Quality Assurance Teams.
- **Dependencies:** Monitoring Capability.
- **Input:** Raw Evidence, Project Baseline.
- **Output:** Verified Evidence, Verification Reports.
- **Consumers:** Audit Capability.

### 3.3 Independent Audit (Validation)
- **Purpose:** Provide third-party assurance that verified evidence translates to legitimate carbon impact.
- **Owner:** Independent Auditors (VVBs).
- **Dependencies:** Verification Capability, Methodology Management.
- **Input:** Verification Reports, Project Design Documents.
- **Output:** Audit Approval/Rejection, Validation Statement.
- **Consumers:** Carbon Accounting Capability.

## 4. Financial & Market Capabilities

### 4.1 Carbon Accounting
- **Purpose:** Execute the mathematical formulas defined in the methodology to calculate exact carbon tonnage based on audited evidence.
- **Owner:** Compliance Engine.
- **Dependencies:** Methodology Management, Independent Audit.
- **Input:** Audited Variables, Global Warming Potential (GWP) Constants.
- **Output:** Calculated Emission Reductions (tCO2e).
- **Consumers:** Issuance Capability.

### 4.2 Issuance & Credit Ledger
- **Purpose:** Mint the digital carbon credits and record them on an immutable ledger.
- **Owner:** Registry Operator.
- **Dependencies:** Carbon Accounting, Registry Federation.
- **Input:** Calculated tCO2e, Audit Approval.
- **Output:** Serialized Carbon Credits, Ledger Transaction Hash.
- **Consumers:** Marketplace Integrations, Reporting Capability.

## 5. Technical Capabilities

### 5.1 Identity & Access Management (IAM)
- **Purpose:** Authenticate users and authorize actions via RBAC/ABAC.
- **Owner:** Security Architecture.
- **Dependencies:** Organization Management.
- **Input:** Credentials, MFA Tokens.
- **Output:** JWT Sessions, Access Grants.
- **Consumers:** Entire Platform.

### 5.2 Workflow Engine
- **Purpose:** Orchestrate complex, multi-step business processes (e.g., the Audit Approval flow).
- **Owner:** Operational Architecture.
- **Dependencies:** IAM, Event Architecture.
- **Input:** State Change Triggers.
- **Output:** Task Assignments, State Transitions.
- **Consumers:** UI Architecture, Notification Engine.
