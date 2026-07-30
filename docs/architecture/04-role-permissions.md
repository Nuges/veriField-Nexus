# 04 — Role-Based Access Control (RBAC) Matrix



## Permission Matrix Across Application Roles



| System Role | Dashboard Access | Project Creation | Agent Provisioning | Field Capture | Verification Sign-off | Registry Exports | Sector Licensing | System Settings |

| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |

| **SUPER_ADMIN** | Full (Global) | Yes | Yes | Read-Only | Read-Only | Read-Only | Full Control | Full Control |

| **ORG_ADMIN** | Tenant Workspace | Yes | Yes | Read-Only | Read-Only | Yes | Request Add | Tenant Settings |

| **FIELD_AGENT** | Mobile / Capture | No | No | Full Capture | No | No | No | Profile Only |

| **VERIFIER / AUDITOR** | Audit Hub | No | No | Read-Only | Full Approval | Full Export | No | Profile Only |

| **VIEWER** | Read-Only | No | No | Read-Only | No | No | No | Profile Only |



---



## Attribute-Based Access Control (ABAC) Rules



1. **Tenant Isolation Enforcer**:

   - `WHERE organization_id = current_user.organization_id` is automatically injected into all SQLAlchemy queries unless `current_user.role == 'SUPER_ADMIN'`.

2. **Sector Permission Guard**:

   - Users can only view or query sectors listed in `organization.licensed_sectors`.

3. **Password Reset Guard**:

   - Password resets for agents can only be triggered by an `ORG_ADMIN` of the same organization or a `SUPER_ADMIN`.
