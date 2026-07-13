# Climate Finance Architecture

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. Core Financial Flows

Climate finance is fundamentally different from traditional e-commerce or SaaS payments. It relies on performance-based, highly conditional, and multi-party distribution networks. VeriField Nexus tracks the flow of capital from institutional originators down to grassroots beneficiaries.

### 1.1 Capital Origination
The platform natively supports tracking various funding instruments:
- **Grant Funding (Philanthropic):** Upfront capital with no expectation of financial return, often deployed by NGOs or Foundations to seed a programme.
- **Concessional Loans (DFIs/MDBs):** Below-market-rate debt provided by institutions like the World Bank to de-risk high-impact projects.
- **Green Bonds / Climate Bonds:** Debt instruments requiring strict, platform-verified proof of impact to maintain their certification status and avoid default.
- **Results-Based Financing (RBF):** Capital held in escrow or a trust, released *only* upon cryptographic proof of delivery verified by the Nexus MRV engine.
- **Carbon Finance:** The sale of the generated Carbon Credits on compliance or voluntary markets (VCM).

### 1.2 Article 6 Financial Mechanisms
Under the Paris Agreement (Article 6.2 and 6.4), financial flows become internationally regulated.
- Nexus tracks **Corresponding Adjustments (CA)**, ensuring that if a host country sells a credit internationally, it is financially debited from their national NDC ledger. This prevents double-claiming and dictates the premium pricing of ITMOs (Internationally Transferred Mitigation Outcomes).

## 2. Revenue Distribution & Benefit Sharing

A primary failure of legacy climate finance is that revenue rarely reaches the local communities generating the impact. The CIOS architecture enforces transparent benefit sharing.

### 2.1 Fee Structures & Leakage
The platform tracks and automatically calculates ecosystem friction:
1. **Registry Fees:** Upfront registration fees and per-credit issuance fees deducted by standard bodies.
2. **Verification Costs:** Fixed or variable payments made to the VVB for auditing services.
3. **Marketplace Fees:** Commissions taken by carbon exchanges or brokers.
4. **Taxes & Sovereign Levies:** Host country taxes applied to exported environmental assets.

### 2.2 Automated Benefit Sharing (Waterfalls)
When a carbon credit is successfully sold and retired:
1. Revenue enters the **Settlement Engine** (often integrated with an external payment provider or smart contract).
2. The Engine executes the predefined **Distribution Waterfall** based on the Project Design Document (PDD).
3. *Example Waterfall:*
   - 10% -> National Government (Sovereign Levy)
   - 5% -> VVB & Platform Fees
   - 30% -> Local Community Trust (Benefit Sharing)
   - 55% -> Project Developer (Capital recovery & profit)

## 3. Escrow and De-Risking Mechanics

Because climate projects take years to mature, finance is often tranched.
- **Pre-financing:** Buyers pre-purchase credits (forward contracts). The funds are held in escrow.
- **Nexus Trigger:** The funds are not released until the Nexus `AuditApproved` or `CreditIssued` event fires. This mathematically eliminates delivery risk for the buyer, driving down the cost of capital for the developer.

## 4. Architecture Traceability
- **Dependent Documents:** `02-end-to-end-climate-value-chain.md`
- **Related APIs:** Integrations with Banking Providers, Smart Contracts.
- **Consumed Events:** `CreditSold`, `IssuanceApproved`, `AuditApproved`
- **Primary Actors:** Corporate ESG Teams, MDBs, Governments, Developers.
