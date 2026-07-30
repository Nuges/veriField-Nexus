# 08 — API Catalogue & Endpoint Route Mapping



## Complete FastAPI Route Mapping



All backend endpoints are prefixed with `/api/v1` and enforce JWT authentication and multi-tenant ABAC controls.



| Domain Tag | HTTP Method | Endpoint Route | Description | RBAC Role |

| :--- | :--- | :--- | :--- | :--- |

| **Auth** | `POST` | `/api/v1/auth/login` | JWT Login & Token Generation | Public |

| **Auth** | `GET` | `/api/v1/auth/me` | Current User & Licensed Sectors Profile | Authenticated |

| **Auth** | `POST` | `/api/v1/auth/agents` | Provision New Field Agent Credentials | Org Admin |

| **Organizations**| `GET` | `/api/v1/organizations/{id}` | Tenant Organization Details | Org Admin |

| **Organizations**| `POST` | `/api/v1/organizations/{id}/sectors` | Provision Additional Licensed Sector | Super / Org Admin |

| **Projects** | `POST` | `/api/v1/projects` | Register Project & Bind Methodology | Org Admin |

| **Projects** | `GET` | `/api/v1/projects` | List Organization Projects | Authenticated |

| **Properties** | `GET` | `/api/v1/properties` | List Monitored Assets & Properties | Authenticated |

| **Dashboard** | `GET` | `/api/v1/properties/current/dashboard` | Resolve Level 5 CIOS Dashboard Payload | Authenticated |

| **Activities** | `GET` | `/api/v1/activities` | List Field Submissions & Telemetry Logs | Authenticated |

| **Activities** | `POST` | `/api/v1/activities` | Submit New Field Activity / Revisit Log | Field Agent |

| **Verification** | `GET` | `/api/v1/verification/tasks` | List Audit & Revisit Tasks | Auditor / Admin |

| **Verification** | `POST` | `/api/v1/verification/tasks` | Dispatch Audit Task to Asset | Org Admin |

| **Verification** | `POST` | `/api/v1/verification/tasks/{id}/status`| Sign & Update Audit Task Status | Auditor / Admin |

| **Sensors** | `GET` | `/api/v1/sensors/devices` | IoT Hardware Fleet Telemetry Stream | Hardware Eng / Admin |

| **Programmes** | `GET` | `/api/v1/programmes` | List Programme of Activities (PoA) | Authenticated |

| **Reporting** | `GET` | `/api/v1/reporting/carbon-ledger` | Fetch Verified Carbon Credit Ledger | Auditor / Admin |

| **Registry** | `POST` | `/api/v1/registry/export` | Export Verra VCS CSV / Gold Standard JSON | Auditor / Admin |

| **Trust Engine** | `GET` | `/api/v1/ai-trust-engine/metrics` | AI Trust Index Scores & Anomaly Engine | System Auditor |

| **Settings** | `GET/PUT`| `/api/v1/settings` | Global System Weights & Parameters | Org Admin |
