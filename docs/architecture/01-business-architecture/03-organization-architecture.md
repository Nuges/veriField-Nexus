# Organization Architecture

Organizations are the foundational multi-tenant unit of the VeriField Nexus CIOS. Every action, asset, and project is scoped to an Organization.

## Organization Concept

The platform is designed around a B2B2C and G2B (Government-to-Business) model. An Organization is any legal entity operating within the platform. Users belong to Organizations. Permissions are derived from the intersection of a User's Role and their Organization's Role in the ecosystem.

## Organization Typology

1. **Platform Operator (Super Admin):** The entity managing the CIOS infrastructure (e.g., VeriField Nexus itself).
2. **National Regulator / Government Body:** An organization holding jurisdictional authority (e.g., Ministry of Environment).
3. **Registry / Standards Body:** An organization defining methodologies and holding the master ledger (e.g., Verra, Gold Standard, National Carbon Registry).
4. **Project Developer:** An organization funding, managing, and executing climate projects.
5. **Validation & Verification Body (VVB):** An independent auditing organization authorized to validate projects and verify evidence.
6. **Corporate / Financier:** An organization purchasing credits or funding programmes for ESG compliance.
7. **Service Provider / Subcontractor:** An organization hired by a developer to perform field activities (e.g., local installation crews).

## Organization Hierarchy & Relationships

Organizations can form complex relationships:
- **Parent/Child (Subsidiaries):** A multinational developer may have country-specific subsidiaries. Policies and branding inherit downward.
- **Regulator/Subject:** A National Regulator has oversight over all Project Developers operating within its defined Jurisdiction.
- **Client/Contractor:** A Project Developer grants restricted, scoped access to a Subcontractor organization for specific projects.

## Organization Lifecycle

1. **Onboarding / Registration:** Initiated via self-service or invitation. Requires KYC/KYB validation.
2. **Provisioning:** The platform provisions an isolated logical tenant space, ensuring data separation via Row-Level Security (RLS).
3. **Active (Operational):** The organization configures its settings, branding, and invites users.
4. **Suspended:** The organization violates compliance rules. Access is revoked, and all active projects are frozen. Data remains intact.
5. **Archived (Soft Delete):** The organization ceases operations. Data is retained for auditability but removed from active queries. Hard deletion is strictly prohibited.

## Organization Configuration & Metadata

Instead of hardcoding features per organization type, behavior is driven by metadata configurations:
- **Capabilities Matrix:** A bitmask or JSON configuration determining which modules the organization can access (e.g., VVBs get the Audit Module, Regulators get the Governance Module).
- **Custom Branding:** Whitelabeling settings (logos, colors) that propagate to all child entities and user interfaces.
- **Policy Overrides:** Organizations can define internal policies (e.g., "All field data requires secondary approval") that strictly add to, but never weaken, global or jurisdictional policies.

## Organization Isolation

Data isolation is guaranteed through the Tenant ID (`organization_id`). Every operational database table includes an `organization_id` column. Access layers (e.g., ORMs, API endpoints) automatically append `WHERE organization_id = ?` to all queries based on the authenticated user's context. Cross-organization visibility (e.g., an Auditor viewing a Developer's project) requires explicit, cryptographically verifiable Access Grants.
