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

export const ALLOWED_DASHBOARD_ROLES = [
  "SUPER_ADMIN",
  "ORG_ADMIN",
  "ORG_OWNER",
  "ADMIN",
  "AUDITOR",
  "VVB",
  "VERIFIER",
  "FIELD_AGENT",
  "QA_OFFICER",
  "REGISTRY_ADMIN",
  "REGISTRY_MANAGER",
  "PORTFOLIO_MANAGER",
  "IOT_ENGINEER",
  "PROGRAMME_MANAGER",
  "PROJECT_MANAGER",
  "EXECUTIVE",
  "INVESTOR",
  "CLIENT",
  "OPERATIONS_ENGINEER",
  "JURISDICTION_ADMIN",
  "COMPLIANCE_ADMIN",
  "FIELD_SUPERVISOR",
  "PLATFORM_SUPPORT",
  "OBSERVER",
  "VIEWER",
] as const;

export function normalizeRole(role?: string | null): string {
  if (!role) return "";
  return role.trim().toUpperCase().replace(/\s+/g, "_");
}

export function isDashboardRoleAllowed(role?: string | null): boolean {
  const normalized = normalizeRole(role);
  if (!normalized) return false;
  return (
    ALLOWED_DASHBOARD_ROLES.includes(normalized as any) ||
    ALLOWED_DASHBOARD_ROLES.includes(role as any)
  );
}

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
