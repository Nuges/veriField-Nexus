# Climate Infrastructure Reference Model

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. The Climate Ecosystem Map

The global climate ecosystem is not a flat structure; it is a complex, multi-layered environment. VeriField Nexus operates across all of these layers, bridging the gap between physical reality and global finance.

### 1.1 Governance Layer
Sets the absolute rules of the global climate regime.
- **UNFCCC (United Nations Framework Convention on Climate Change):** The supreme global authority.
- **National Governments & Environment Ministries:** Set Nationally Determined Contributions (NDCs).
- **National Climate Authorities:** Oversee local climate action and enforce geographical policies.
- **Article 6 Authorities:** National bodies authorized to issue Letters of Authorization (LOA) for internationally transferred mitigation outcomes (ITMOs).

### 1.2 Standards Layer
Defines the scientific consensus and methodological rigor required to claim environmental impact.
- **Verra, Gold Standard, Climate Action Reserve (CAR), Puro.earth:** The major voluntary and compliance standard bodies.
- **ISO (International Organization for Standardization):** Provides overarching standards like ISO 14064 for GHG accounting.
- **GHG Protocol:** Defines global standardized frameworks for measuring emissions.

### 1.3 Verification Layer
Provides independent trust and validation to the ecosystem.
- **Validation and Verification Bodies (VVBs):** Accredited third-party auditors.
- **Monitoring Agencies:** Entities conducting specialized independent monitoring (e.g., continuous emissions monitoring).

### 1.4 Market & Ledger Layer
The financial recording and trading layer.
- **Carbon Registries:** The ultimate ledgers of record for carbon credits (National Registries or Standard-specific like the Verra Registry).
- **Carbon Exchanges & Marketplaces:** Platforms where credits are traded (e.g., Xpansiv CBL, AirCarbon Exchange).
- **Brokers & Traders:** Intermediaries facilitating complex climate finance transactions.

### 1.5 Finance Layer
The source of capital flowing into climate projects.
- **Development Finance Institutions (DFIs) & Multilateral Development Banks (MDBs):** e.g., World Bank, IFC, AfDB. Provide grant funding, concessional loans, and results-based financing.
- **Corporate ESG Investors:** Fortune 500 companies purchasing credits to meet Net-Zero targets.
- **Green Climate Fund (GCF) & Climate Venture Capital:** Early-stage and programmatic funding.

### 1.6 Delivery Layer
The boots on the ground executing the physical climate action.
- **Programme & Project Developers:** The organizations designing and managing the climate interventions.
- **Engineering, Procurement, and Construction (EPCs) & Installers:** Subcontractors deploying physical assets.
- **NGOs & Community Organizations:** Grassroots partners ensuring local benefit sharing.
- **Beneficiaries:** The end-users or communities receiving the climate intervention (e.g., a household receiving a clean cookstove).

### 1.7 Technology Layer
The digital and hardware infrastructure underpinning the entire ecosystem.
- **VeriField Nexus CIOS:** The central operating system coordinating all layers.
- **IoT & Sensor Networks:** Smart meters, inverters, and remote sensors providing raw telemetry.
- **Satellites & Earth Observation:** Providing spatial imagery for remote MRV.
- **GIS & Weather Providers:** Contextual data for baseline calculations and risk assessment.
- **AI Services:** Models for anomaly detection and predictive forecasting.
- **Enterprise ERPs & Utility Systems:** Corporate systems integrating with Nexus for automated ESG reporting.

## 2. Platform Positioning within the Ecosystem

VeriField Nexus does not seek to replace the UNFCCC, Verra, or the World Bank. Instead, it positions itself as the **interoperable trust layer** connecting them.

- **For the Governance Layer:** Nexus acts as the National Dashboard and compliance enforcer.
- **For the Standards Layer:** Nexus acts as the digital execution engine of their methodologies.
- **For the Finance Layer:** Nexus acts as the ultimate de-risking tool, providing cryptographic proof of impact before capital is released.
- **For the Delivery Layer:** Nexus acts as their core operational software, managing their daily field logistics and MRV.

## 3. Architecture Traceability
- **Dependent Documents:** `04-digital-mrv-architecture.md`, `05-registry-federation-architecture.md`, `08-climate-programme-architecture.md`, `12-enterprise-operational-model.md`
- **Primary Entities:** `Platform`, `Organization`
- **Related APIs:** Ecosystem Integration APIs (`/api/v1/federation/*`)
