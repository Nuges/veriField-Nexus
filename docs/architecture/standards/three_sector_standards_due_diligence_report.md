# VeriField Nexus — Three-Sector Standards Due-Diligence & Acceptance Report
**Scope:** Cookstoves (`AMS-II.G`), Hybrid Energy (`AMS-I.F`), EV Mobility (`AMS-III.C` & `VM0038`)  
**Status:** Completed Standards Evidence Due-Diligence  
**Date:** October 2026  

---

## 1. Environment Separation & Data Integrity

- **Supabase Production Database**: PostGIS **3.3.7** (`UNTOUCHED`; 0 mutations, 0 schema changes, 0 data modifications).
- **Local Test Database (`test_ci_db`)**: PostGIS **3.6.1** (**TEST ENVIRONMENT ONLY**; strictly isolated for local concurrency and persistence verification).
- **No Production Database Operations**: Zero destructive migrations, table drops, or production seeds executed.

---

## 2. Sector Standards Due-Diligence & Gating Determinations

### A. Clean Cookstoves — CDM AMS-II.G

1. **Current Official Normative Source**:
   - **Methodology**: UNFCCC CDM Small-Scale Methodology AMS-II.G (*Energy efficiency measures in thermal applications of non-renewable biomass*).
   - **Version**: **Version 14.0 (CDM EB 125)**.
2. **fNRB Determination / TOOL30 Status (CORRECTED)**:
   - Under AMS-II.G v14, the former TOOL30 fNRB determination option is **removed** from the operative fNRB parameter tables.
   - Applicable **TOOL33 v3.0** defaults may be used, or stakeholders may submit a new methodological approach for consideration by the CDM Executive Board.
   - TOOL30 is not universally mandatory for fNRB determination.
3. **TOOL33 Role (CORRECTED)**:
   - Current TOOL33 v3.0 (*Default values for calculating emission reductions for small-scale project activities*) provides authorized national/regional fNRB and other common default parameters.
   - It is an alternative source for eligible fNRB defaults, but it is **not** the source of the AMS-II.G projected fossil-fuel substitution factors.
4. **Fossil-Fuel Substitution Factor (CORRECTED)**:
   - Current AMS-II.G v14 uses applicable regional projected fossil-fuel factors or a calculated fuel mix under **Equation (3)** ($EF_{projected\_fossilfuel}$).
   - $81.6\text{ tCO}_2\text{/TJ}$ is **not** a current universal default factor. Proponents must apply applicable regional defaults or calculate the projected substitution mix pursuant to Equation (3).
   - VeriField's prototype used $1.68\text{ tCO}_2/\text{t}$ ($112\text{ t/TJ}$), representing biogenic wood combustion carbon content rather than Equation (3) projected fossil substitution.
5. **Leakage Treatment (CORRECTED)**:
   - Leakage may be assessed ex post or addressed using the $0.95$ default adjustment factor ($L_y = 0.05$).
   - Stove decommissioning relates to continued-use adjustment evidence (mitigating stove stacking / baseline stove continued operation) and does **not** establish an automatic zero-leakage rule.
6. **Sampling Requirements (CORRECTED WITH QUALIFICATION)**:
   - Sampling precision and frequency are parameter-specific under the CDM Sampling Standard and AMS-II.G v14.
   - Both **annual** and **biennial** (two-year) monitoring routes exist depending on the specific parameter.
7. **Production Gating Status**: **GATED (`[]`)**.
   - Current implementation remains a prototype with hardcoded parameters and omitted leakage; cannot be exposed on production onboarding until aligned with operative AMS-II.G v14 equations.

---

### B. Hybrid Energy & Mini-Grids — CDM AMS-I.F

1. **Current Official Normative Source**:
   - **Methodology**: UNFCCC CDM Small-Scale Methodology AMS-I.F (*Renewable electricity generation for captive use and mini-grid systems*).
   - **Version**: **Version 5.0 (CDM EB 115)**.
2. **Meter Requirements (CORRECTED)**:
   - TOOL05 does **not** establish a generic $\pm 2\% / \pm 1\%$ fallback hierarchy.
   - Applicable regulatory/supplier requirements govern first and foremost (statutory legal metrology or supplier/grid codes), with TOOL05 fallback calibration and meter accuracy-class requirements where needed.
3. **Uncertainty Deductions (CORRECTED)**:
   - No generic additional mathematical uncertainty deduction is required for qualifying calibrated meters. Meter accuracy and calibration are qualification and instrumentation standards, not a formula discount deducted from metered gross generation.
4. **On-Site Fossil Fuel Treatment (CORRECTED)**:
   - On-site fossil-fuel consumption emissions must be calculated using **TOOL03 pursuant to AMS-I.F paragraph 27** ($PE_{FF,y} = \sum FC_{i,y} \times NCV_i \times EF_{CO2,i}$).
5. **Real Gaps Keeping AMS-I.F Gated**:
   - Mathematical double-counting of battery storage (`clean_kwh = solar_generation_kwh + battery_discharge_kwh`).
   - Complete omission of backup diesel project emissions ($PE_{FF,y}$ under TOOL03 / paragraph 27).
6. **Production Gating Status**: **GATED (`[]`)**.

---

### C. EV Mobility — CDM AMS-III.C & Verra VM0038

1. **Current Official Normative Source (AMS-III.C)**:
   - **Methodology**: UNFCCC CDM Small-Scale Methodology AMS-III.C (*Emission reductions by electric and hybrid vehicles*).
   - **Version**: **Version 16.0 (CDM EB 115)**.
2. **Applicability Scope (CORRECTED WITH QUALIFICATION)**:
   - Charging service providers may participate in AMS-III.C project activities.
   - **Qualification**: While charging service providers are eligible to participate, methodology compliance still requires appropriate project EV identification, vehicle-category classification ($i$), baseline specific fuel consumption ($SFC_{BL,i}$), vehicle-category electricity/distance monitoring ($EC_{PJ,i,y}$ / $DD_{i,y}$), displacement evidence, and grid transmission & distribution losses ($TD_y$).
3. **Verra VM0038 & VMD0049 Status**:
   - **VM0038 Version**: **1.1**
   - **VM0038 Status**: **ACTIVE** (Active since 19 August 2026 under Verra VCS).
   - **VMD0049 Version**: **1.1**
   - **VMD0049 Status**: **ACTIVE** (Active since 19 August 2026 under Verra VCS).
   - **VMD0049 Title**: ***Positive List for Electric Vehicle Charging Systems***.
   - **VM0038 Implementation**: **NO** (Internal VeriField assertion; designated future methodology candidate for VeriField's charging infrastructure product, subject to separate implementation and acceptance).
4. **Real Gaps Keeping EV Mobility Gated**:
   - VeriField's charger-only architecture lacks structured vehicle category registration, verified fleet telematics/odometers, and grid T&D loss calculation.
5. **Production Gating Status**: **GATED (`[]`)**.

---

## 3. Authoritative Production Onboarding Matrix

Production onboarding remains strictly restricted to methodologies proven production-ready:

| Canonical Sector | Production-Enabled Methodologies | Current Status |
| :--- | :--- | :--- |
| **AGRICULTURE_LAND_USE** | `[VM0042]` | PRODUCTION_READY / FROZEN |
| **BIOCHAR** | `[VM0044, PURO_BIOCHAR_2025]` | PRODUCTION_READY / FROZEN |
| **COOKSTOVES** | `[]` | GATED (Unconfigured in onboarding) |
| **HYBRID_ENERGY** | `[]` | GATED (Unconfigured in onboarding) |
| **EV_MOBILITY** | `[]` | GATED (Unconfigured in onboarding) |

---

## 4. Acceptance Test Summary

- **Backend Acceptance Suite**:
  - `tests/domains/test_three_sector_acceptance_standards_and_postgres.py`: **22 passed**
- **Frontend Scoping Suite**:
  - `dashboard/tests/onboarding_methodology_scoping.test.ts`: **5 passed, 0 failed**
- **Frontend Type Checking**:
  - `npx tsc --noEmit`: **0 errors**
