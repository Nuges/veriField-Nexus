/**
 * =============================================================================
 * VeriField Nexus — Authoritative Role & Permission Engine (Frontend)
 * =============================================================================
 * Single source of truth for canonical roles, role aliases, permission sets,
 * route-level access rules, and Separation of Duties.
 * =============================================================================
 */

export const CANONICAL_ROLES = {
  SUPER_ADMIN: "SUPER_ADMIN",
  ORG_ADMIN: "ORG_ADMIN",
  PROJECT_MANAGER: "PROJECT_MANAGER",
  FIELD_SUPERVISOR: "FIELD_SUPERVISOR",
  FIELD_AGENT: "FIELD_AGENT",
  QA_OFFICER: "QA_OFFICER",
  VERIFIER: "VERIFIER",
  AUDITOR: "AUDITOR",
  COMPLIANCE_ADMIN: "COMPLIANCE_ADMIN",
  REGISTRY_ADMIN: "REGISTRY_ADMIN",
  FINANCE: "FINANCE",
  INVESTOR: "INVESTOR",
  VIEWER: "VIEWER",
} as const;

export type CanonicalRole = (typeof CANONICAL_ROLES)[keyof typeof CANONICAL_ROLES];

export const ROLE_ALIASES: Record<string, CanonicalRole> = {
  // Super Admin
  super_admin: "SUPER_ADMIN",
  superadmin: "SUPER_ADMIN",
  platform_super_admin: "SUPER_ADMIN",

  // Org Admin
  admin: "ORG_ADMIN",
  org_owner: "ORG_ADMIN",
  tenant_admin: "ORG_ADMIN",
  organization_admin: "ORG_ADMIN",

  // Project Manager
  project_developer: "PROJECT_MANAGER",
  developer: "PROJECT_MANAGER",
  portfolio_manager: "PROJECT_MANAGER",
  programme_manager: "PROJECT_MANAGER",

  // Field Operations
  field_agent: "FIELD_AGENT",
  operator: "FIELD_AGENT",
  technician: "FIELD_AGENT",
  surveyor: "FIELD_AGENT",

  // QA / MRV Officer
  mrv_officer: "QA_OFFICER",
  mrv_manager: "QA_OFFICER",
  iot_engineer: "QA_OFFICER",
  operations_engineer: "QA_OFFICER",

  // Verifier & Auditor
  vvb: "VERIFIER",
  vvb_verifier: "VERIFIER",
  vvb_auditor: "AUDITOR",
  third_party_auditor: "AUDITOR",

  // Compliance & Regulatory
  compliance_officer: "COMPLIANCE_ADMIN",
  regulator: "COMPLIANCE_ADMIN",
  jurisdiction_admin: "COMPLIANCE_ADMIN",

  // Registry
  registry_manager: "REGISTRY_ADMIN",
  registry_officer: "REGISTRY_ADMIN",

  // Finance
  finance_officer: "FINANCE",
  treasury: "FINANCE",
  billing_admin: "FINANCE",

  // Read-Only / Observers
  observer: "VIEWER",
  client: "VIEWER",
  platform_support: "VIEWER",
  executive: "INVESTOR",
};

/**
 * Resolves any raw or legacy role string into its canonical system role.
 */
export function normalizeRole(role?: string | null): CanonicalRole {
  if (!role) return CANONICAL_ROLES.VIEWER;
  const cleaned = role.trim().toUpperCase().replace(/\s+/g, "_");
  const cleanedLower = role.trim().toLowerCase().replace(/\s+/g, "_");

  if (ROLE_ALIASES[cleanedLower]) return ROLE_ALIASES[cleanedLower];
  if (ROLE_ALIASES[cleaned]) return ROLE_ALIASES[cleaned];
  if (Object.values(CANONICAL_ROLES).includes(cleaned as any)) {
    return cleaned as CanonicalRole;
  }

  return CANONICAL_ROLES.VIEWER;
}

export const ALLOWED_DASHBOARD_ROLES = Object.values(CANONICAL_ROLES);

export function isDashboardRoleAllowed(role?: string | null): boolean {
  if (!role) return false;
  const canonical = normalizeRole(role);
  return Boolean(canonical);
}

// ─── Route Access Control Map ────────────────────────────────────────────────
export interface RouteRule {
  pathPrefix: string;
  allowedRoles: CanonicalRole[];
  label: string;
}

export const ROUTE_ACCESS_RULES: RouteRule[] = [
  {
    pathPrefix: "/super-admin",
    allowedRoles: ["SUPER_ADMIN"],
    label: "Super Admin Infrastructure",
  },
  {
    pathPrefix: "/dashboard/people",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN"],
    label: "Team & User Access Control",
  },
  {
    pathPrefix: "/dashboard/access-control",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN"],
    label: "Access Control Matrix",
  },
  {
    pathPrefix: "/dashboard/settings",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN"],
    label: "Organization Settings & API Keys",
  },
  {
    pathPrefix: "/dashboard/verifications",
    allowedRoles: ["SUPER_ADMIN", "VERIFIER", "AUDITOR", "QA_OFFICER"],
    label: "Verification & Audit",
  },
  {
    pathPrefix: "/dashboard/audits",
    allowedRoles: ["SUPER_ADMIN", "VERIFIER", "AUDITOR", "QA_OFFICER"],
    label: "Audit Findings & Engagements",
  },
  {
    pathPrefix: "/dashboard/carbon",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "FINANCE", "PROJECT_MANAGER", "REGISTRY_ADMIN", "INVESTOR", "VIEWER"],
    label: "Carbon Credit Ledger",
  },
  {
    pathPrefix: "/dashboard/command-center",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "COMPLIANCE_ADMIN", "PROJECT_MANAGER"],
    label: "Article 6 Command Center",
  },
  {
    pathPrefix: "/dashboard/methodologies",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "QA_OFFICER", "COMPLIANCE_ADMIN", "VERIFIER", "AUDITOR", "INVESTOR", "VIEWER"],
    label: "Methodology & PDD Ingestion",
  },
  {
    pathPrefix: "/dashboard/registry",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "REGISTRY_ADMIN", "COMPLIANCE_ADMIN", "PROJECT_MANAGER", "INVESTOR", "VIEWER"],
    label: "Registry Operations & Submissions",
  },
  {
    pathPrefix: "/dashboard/projects",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "QA_OFFICER", "COMPLIANCE_ADMIN", "REGISTRY_ADMIN", "VERIFIER", "AUDITOR", "INVESTOR", "VIEWER"],
    label: "Projects & Mini-Grids",
  },
  {
    pathPrefix: "/dashboard/poa",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "QA_OFFICER", "COMPLIANCE_ADMIN", "REGISTRY_ADMIN", "VERIFIER", "AUDITOR", "INVESTOR", "VIEWER"],
    label: "Programmes of Activities (PoA)",
  },
  {
    pathPrefix: "/dashboard/operations",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "FIELD_SUPERVISOR", "FIELD_AGENT", "PROJECT_MANAGER", "QA_OFFICER", "INVESTOR", "VIEWER"],
    label: "Field Operations & Inspections",
  },
  {
    pathPrefix: "/dashboard/monitoring",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "FIELD_SUPERVISOR", "FIELD_AGENT", "QA_OFFICER", "PROJECT_MANAGER", "VERIFIER", "AUDITOR", "INVESTOR", "VIEWER"],
    label: "Live Telemetry & Sensor Monitoring",
  },
  {
    pathPrefix: "/dashboard/analytics",
    allowedRoles: ["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "QA_OFFICER", "COMPLIANCE_ADMIN", "REGISTRY_ADMIN", "FINANCE", "INVESTOR", "VIEWER"],
    label: "Sector Analytics & Reporting",
  },
];

/**
 * Checks whether a given role is authorized to visit a pathname.
 */
export function isRouteAuthorized(pathname: string, role?: string | null): boolean {
  const canonical = normalizeRole(role);

  // Super Admin can access everything
  if (canonical === CANONICAL_ROLES.SUPER_ADMIN) return true;

  // Root dashboard and universal guides are open to all valid roles
  if (pathname === "/dashboard" || pathname === "/dashboard/help" || pathname === "/dashboard/ai") {
    return true;
  }

  // Check matching route prefix
  for (const rule of ROUTE_ACCESS_RULES) {
    if (pathname === rule.pathPrefix || pathname.startsWith(`${rule.pathPrefix}/`)) {
      return rule.allowedRoles.includes(canonical);
    }
  }

  return true;
}

// ─── Mutation Action Permissions ─────────────────────────────────────────────
export type ActionPermission =
  | "project:create"
  | "project:edit"
  | "evidence:upload"
  | "activity:approve"
  | "activity:verify"
  | "audit:create"
  | "audit:sign"
  | "itmo:authorize"
  | "registry:submit"
  | "ledger:mint"
  | "users:manage"
  | "settings:edit";

export const ACTION_ROLE_MAP: Record<ActionPermission, CanonicalRole[]> = {
  "project:create": ["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER"],
  "project:edit": ["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER"],
  "evidence:upload": ["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "FIELD_SUPERVISOR", "FIELD_AGENT"],
  "activity:approve": ["SUPER_ADMIN", "ORG_ADMIN", "FIELD_SUPERVISOR", "QA_OFFICER"],
  "activity:verify": ["SUPER_ADMIN", "FIELD_SUPERVISOR", "QA_OFFICER", "VERIFIER"],
  "audit:create": ["SUPER_ADMIN", "VERIFIER", "AUDITOR"],
  "audit:sign": ["SUPER_ADMIN", "VERIFIER"],
  "itmo:authorize": ["SUPER_ADMIN", "COMPLIANCE_ADMIN"],
  "registry:submit": ["SUPER_ADMIN", "REGISTRY_ADMIN"],
  "ledger:mint": ["SUPER_ADMIN", "FINANCE"],
  "users:manage": ["SUPER_ADMIN", "ORG_ADMIN"],
  "settings:edit": ["SUPER_ADMIN", "ORG_ADMIN"],
};

export function canPerformAction(action: ActionPermission, role?: string | null): boolean {
  const canonical = normalizeRole(role);
  if (canonical === CANONICAL_ROLES.SUPER_ADMIN) return true;
  const allowed = ACTION_ROLE_MAP[action] || [];
  return allowed.includes(canonical);
}

// ─── Legacy Sorting and Filtering Helpers ────────────────────────────────────
export const ROLE_ORDER = [
  "SUPER_ADMIN",
  "ADMIN",
  "ORG_ADMIN",
  "PORTFOLIO_MANAGER",
  "PROJECT_MANAGER",
  "FIELD_AGENT",
  "AUDITOR",
  "VIEWER",
] as const;

export const STATUS_ORDER = [
  "PENDING",
  "IN_REVIEW",
  "APPROVED",
  "ACTIVE",
  "COMPLETED",
  "REJECTED",
  "ARCHIVED",
] as const;

export const DATE_FILTER_PRESETS = [
  { label: "Today", value: "today" },
  { label: "Yesterday", value: "yesterday" },
  { label: "Last 7 Days", value: "7days" },
  { label: "Last 30 Days", value: "30days" },
  { label: "This Month", value: "this_month" },
  { label: "Last Month", value: "last_month" },
  { label: "This Year", value: "this_year" },
  { label: "Custom Range", value: "custom" },
] as const;

export function getRolePriority(role?: string | null): number {
  const norm = normalizeRole(role);
  const idx = ROLE_ORDER.indexOf(norm as any);
  return idx !== -1 ? idx : 999;
}

export function getStatusPriority(status?: string | null): number {
  const norm = (status || "").trim().toUpperCase();
  const idx = STATUS_ORDER.indexOf(norm as any);
  return idx !== -1 ? idx : 999;
}

