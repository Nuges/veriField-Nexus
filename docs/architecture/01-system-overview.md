# 01 — Sovereign System Overview & Architecture (Level 5 CIOS)



## Executive Summary

VeriField Nexus is a sovereign-grade Digital Monitoring, Reporting, and Verification (dMRV) Climate Information Operating System (CIOS). It is designed to be deployable by federal governments (Federal Government of Nigeria, Ghana, Kenya, Rwanda, Brazil, Indonesia), UN agencies, multilateral development banks, carbon project developers, and independent verifiers without modifying the underlying codebase.



---



## Sovereign Domain Hierarchy



```

GLOBAL (Multi-Region Platform Infrastructure)

  └── COUNTRY (e.g. Nigeria, Ghana, Kenya, Rwanda, Brazil, Indonesia)

       └── JURISDICTION (Sub-national / Regional Carbon Authority)

            └── REGULATOR (National Environmental Protection Agency)

                 └── CARBON FRAMEWORK (Article 6.2, Article 6.4, Voluntary Carbon Market)

                      └── ORGANISATION (Project Developer / Utility / Enterprise)

                           └── WORKSPACE (Level 5 CIOS Workspace)

                                └── SECTOR (Clean Cookstoves, Hybrid Energy, Biochar, EV Mobility)

                                     └── METHODOLOGY (AMS-II.G, AMS-I.F, VM0044, AMS-III.C - Locked)

                                          └── PROGRAMME OF ACTIVITIES (PoA / National Umbrella Programme)

                                               └── PROJECT / CPA (e.g. Kano Solar Mini-Grid)

                                                    └── ASSETS / PROPERTIES (Devices / Inverters)

                                                         └── ACTIVITIES (Field Logs & Sensor Streams)

                                                              └── EVIDENCE (SHA-256 Hashed Photos)

                                                                   └── VERIFICATION (Auditor Sign-off)

                                                                        └── CARBON ACCOUNTING (Quantification)

                                                                             └── ISSUANCE (Regulator Approval)

                                                                                  └── PLUGGABLE REGISTRY (National / Verra / GS / Article 6)

                                                                                       └── REPORTING & PORTFOLIO (National Inventory)

```



---



## Core Sovereign Principles



1. **Configuration Over Code**:

   - Countries, jurisdictions, regulators, carbon frameworks, and registries are metadata-driven objects.

2. **Pluggable Registry Integration**:

   - Verified credits can be routed to National Carbon Registries, Article 6.2 ITMO mechanisms, or voluntary registries (Verra, Gold Standard, Puro.earth) based on configurable governance rules.

3. **22-Stage Carbon Credit Lifecycle**:

   - Implements a complete 22-stage production state machine from Sector Licensing through Carbon Quantification, Risk Assessment, Registry Submission, and Retirement.

4. **20 Professional Carbon Issuance Roles**:

   - Dedicated access levels for National Regulators, Jurisdiction Admins, Registry Officers, Technical Reviewers, Carbon Accountants, Independent Verifiers, and Field Agents.

5. **Absolute Tenant & Country Isolation**:

   - Scopes all queries through `country_id`, `jurisdiction_id`, and `organization_id`.
