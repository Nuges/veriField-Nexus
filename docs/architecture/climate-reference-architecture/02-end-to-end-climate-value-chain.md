# End-to-End Climate Value Chain

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. The Value Chain Architecture

The climate value chain extends far beyond the simple issuance of a carbon credit. It encompasses the entire lifecycle from macro-level national policy down to community-level impact measurement and global reporting. VeriField Nexus tracks, governs, or facilitates every single step of this 20+ stage lifecycle.

## 2. The Complete Lifecycle

### Phase 1: Origination & Governance
1. **Policy Development:** National governments establish climate policies and NDCs.
2. **Climate Strategy:** DFIs and Corporate Investors define capital deployment strategies.
3. **Programme Design:** Developers group massive scale initiatives (e.g., "National Clean Cooking Programme").
4. **Methodology Selection:** The scientific standard (e.g., Gold Standard) is selected to quantify the impact.
5. **Funding & Blended Finance Alignment:** Capital is committed based on projected impact (Results-Based Financing).
6. **Jurisdiction Configuration:** The Regulator defines the spatial boundaries and specific rules in VeriField Nexus.
7. **Registry Configuration:** The federated connection to the ultimate ledger is established.

### Phase 2: Execution & Deployment
8. **Programme Approval:** The overarching programme is approved by the host country and registry.
9. **Project Design (PDD):** Specific instances of the programme (Projects) are drafted.
10. **Project Registration:** The VVB validates the PDD, and it is officially registered on the platform.
11. **Implementation & Procurement:** Physical hardware is sourced.
12. **Asset Registration & Installation:** Field Agents deploy physical assets (e.g., Solar panels, trees) and register them in the CIOS with GPS and cryptographic signatures.

### Phase 3: Digital MRV (Monitoring, Reporting, Verification)
13. **Continuous Monitoring:** IoT devices, satellites, and periodic field surveys generate raw data streams.
14. **Evidence Collection:** Mobile apps and edge devices capture hashed, time-stamped evidence.
15. **Internal Verification:** The Developer's QA team uses the Nexus Trust Engine to scrub anomalies.
16. **Validation & Audit:** The VVB independently samples and audits the verified data on the platform.
17. **Compliance Evaluation:** The Nexus Policy Engine runs final checks against National and Registry rules.

### Phase 4: Financialization & Market
18. **Carbon Quantification:** The Methodology Engine mathematically calculates the exact emission reductions (tCO2e).
19. **Registry Synchronisation:** Nexus communicates with the external Registry (e.g., Verra) to request issuance.
20. **Issuance:** Digital carbon assets are minted on the ledger.
21. **Trading & Marketplace:** Assets are transferred to buyers via integrated marketplaces or OTC (Over-the-Counter) networks.
22. **Settlement:** Escrow is released; financial compensation flows to the developer.

### Phase 5: Retirement & Impact
23. **Retirement:** The corporate buyer claims the credit against their carbon footprint, permanently burning it from the ledger.
24. **Impact Measurement & Benefit Sharing:** Nexus calculates and distributes community revenue shares or tracks co-benefits (e.g., health improvements, job creation).
25. **National Reporting:** The host country's Environment Ministry views the real-time dashboard to adjust their national inventory.
26. **NDC & Global Reporting:** Final aggregated data flows up to the UNFCCC.
27. **Continuous Improvement:** AI analytics feed data back to Phase 1 for adjusting future policy and methodologies.

## 3. Architecture Traceability
- **Dependent Documents:** `03-climate-finance-architecture.md`
- **Primary Actors:** Entire Ecosystem
- **Produced Events:** Lifecycle stage transition events (e.g., `ProgrammeApproved`, `AssetRegistered`, `AuditCompleted`).
