# 09 — UI Coverage Audit

**Architecture Version:** v2.0.0 | **Audit Date:** 2026-07-07

---

## Existing UI Pages (`dashboard/src/app/`)

| Page | Purpose | Business Process | APIs Called | Widgets/Tables | Filters | Actions | Permissions | Navigation | Loading | Errors | Empty States | Responsive | Offline | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `login/page.tsx` | Authentication | Sign In | ✅ Auth | ✅ Form | N/A | ✅ Submit | ✅ Public | ✅ | ⚠️ | ⚠️ | N/A | ⚠️ | ❌ | ✅ Functional |
| `signup/page.tsx` | Registration | Sign Up | ✅ Auth | ✅ Form | N/A | ✅ Submit | ✅ Public | ✅ | ⚠️ | ⚠️ | N/A | ⚠️ | ❌ | ✅ Functional |
| `dashboard/page.tsx` | Overview | Sector Dashboard | ✅ | ✅ StatCards | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/activities/page.tsx` | Activity Management | CRUD Activities | ✅ | ✅ Table | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/jurisdictions/page.tsx` | Jurisdiction Management | CRUD Jurisdictions | ✅ | ✅ Table + Map | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/compliance/page.tsx` | Compliance Overview | Compliance Status | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/carbon/page.tsx` | Carbon Dashboard | Carbon Metrics | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/registry/page.tsx` | Registry View | Registry Status | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/map/page.tsx` | Spatial Map | GIS Visualization | ⚠️ | ✅ Map | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/sensors/page.tsx` | Sensor Dashboard | IoT Monitoring | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/verifications/page.tsx` | Verification Queue | Verify Evidence | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/audits/page.tsx` | Audit Trail | View Audits | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/anomalies/page.tsx` | Anomaly View | Review AI Flags | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/trust-scores/page.tsx` | Trust Dashboard | Trust Metrics | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/community/page.tsx` | Community View | Community Validation | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/agents/page.tsx` | Agent Management | Field Agents | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/regulator/page.tsx` | Regulator Dashboard | Governance | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/executive/page.tsx` | Executive Dashboard | Analytics | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/properties/page.tsx` | Properties View | Asset Properties | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/settings/page.tsx` | Settings | Config | ⚠️ | ⚠️ | N/A | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `dashboard/poa/page.tsx` | Programmes (PoA) | Programme Mgmt | ❌ No API | ❌ | ❌ | ❌ | ❌ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ Placeholder |
| `super-admin/page.tsx` | Super Admin | Platform Admin | ⚠️ | ⚠️ | ❌ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |
| `capture/page.tsx` | Evidence Capture | Field MRV | ⚠️ | ✅ Form | N/A | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ Partial |

## Missing UI Screens (Required by Architecture)

| Screen | Architecture Source | Severity |
| :--- | :--- | :--- |
| **Project Management Page** | `09-portfolio` | 🔴 Critical |
| **Asset Management Page** | `09-portfolio` | 🔴 Critical |
| **Programme Management Page** (not placeholder) | `08-programme` | 🔴 Critical |
| **Portfolio Dashboard** | `09-portfolio` | 🔴 Critical |
| **VVB Audit Interface** | `04-digital-mrv` | 🔴 Critical |
| **Carbon Credit Ledger / Issuance** | `05-registry-fed` | 🔴 Critical |
| **Methodology Builder** | `06-methodology` | 🟠 High |
| **Notification Center** | `08-ui-architecture` | 🟠 High |
| **Workspace Switcher** | User request | 🟠 High |
| **NDC Reporting Dashboard** | `13-observability` | 🟡 Future |

## Cross-Cutting UI Concerns

| Concern | Status |
| :--- | :--- |
| Accessibility (a11y) | ❌ Not audited |
| Offline PWA Behaviour | ❌ Service worker route exists but no offline data sync |
| Responsive Design | ⚠️ Basic responsiveness only |
| Standardized Empty States | ❌ |
| Standardized Error Pages | ❌ |
| Loading Skeletons | ⚠️ Inconsistent |

> [!WARNING]
> 10 critical UI screens are missing. The PoA page is a non-functional placeholder. No page implements offline capability. No standardized empty states or error pages exist.
