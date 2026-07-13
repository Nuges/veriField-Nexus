# Climate Programme Architecture

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. The Role of Programmes

In global climate finance, individual localized "Projects" are rarely funded in isolation. Instead, capital is deployed at scale through "Programmes" or "Programmes of Activities (PoA)". 

A Programme is an umbrella framework that defines the financial, methodological, and governance structure under which multiple, physically distinct Projects are executed over time.

## 2. Programme Hierarchy & Governance

The platform explicitly distinguishes between a Programme and a Project.

- **Programme Level:** Defines the *rules of engagement*. 
  - *Example:* "The Sub-Saharan Solar Initiative" 
  - Sets the authorized methodology (e.g., AMS-I.L).
  - Sets the total capital committed.
  - Sets the target jurisdictions.
- **Project Level (CPA - Component Project Activity):** The *physical execution* within the Programme.
  - *Example:* "Solar Installation Phase 1: Kigali District".
  - Bounded by a specific timeframe and spatial polygon.
  - Inherits the rules of the parent Programme.

### 2.1 Programme Governance
Programmes are often jointly governed.
- **Coordinating/Managing Entity (CME):** The lead developer organization responsible for the overall Programme.
- **Implementing Partners:** Subcontractor organizations delegated to execute specific Projects under the Programme. 
- Nexus uses its Organization Architecture to handle this delegation, ensuring subcontractors can only see their specific CPAs, not the entire Programme financials.

## 3. Programme Financing & Distribution

Programmes act as the financial pooling vehicle.

- **Capital Inflow:** MDBs or Corporate Investors commit funds to the Programme (e.g., $50M for 5 million tCO2e over 10 years).
- **Tranching:** Funds are disbursed from the Programme to specific Projects based on milestones.
- **Results-Based Aggregation:** When a Project successfully issues carbon credits, the revenue or the credits themselves roll up to the Programme level for distribution to the overarching investors.

## 4. Programme Lifecycle & Closure

1. **Design & Submission:** The CME submits a Programme Design Document (PoA-DD).
2. **Approval:** The VVB and Registry approve the overarching framework.
3. **Inclusion:** Over several years, new Projects (CPAs) are "included" under the Programme. Each inclusion requires a lighter-weight validation, as the main methodology has already been approved at the Programme level.
4. **Closure/Termination:** The Programme reaches its end date. No new Projects can be included. Existing Projects finish their final crediting periods, and the Programme is officially archived.

## 5. Architecture Traceability
- **Dependent Documents:** `09-portfolio-architecture.md`, `03-climate-finance-architecture.md`.
- **Primary Actors:** CMEs, Investors, Regulators, Subcontractors.
- **Primary Entities:** `Programme`, `Project`.
