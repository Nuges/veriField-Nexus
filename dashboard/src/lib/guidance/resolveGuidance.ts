// =============================================================================
// VeriField Nexus — Contextual Page Guidance Resolver
// =============================================================================
// Resolves page metadata, sector terminology overlays, and RBAC permission checks
// into a coherent, truthful decision-support guidance object.
// =============================================================================

import { canPerformAction, normalizeRole, CANONICAL_ROLES } from "../roles";
import { BASE_PAGE_METADATA, FALLBACK_PAGE_METADATA } from "./pageMetadata";
import { getSectorOverlay } from "./sectorOverlays";
import {
  ContextualPageInsight,
  PageGuidanceContext,
  GuidanceAction,
  BasePageMetadata
} from "./types";

/**
 * Normalizes a raw pathname to match our page metadata registry keys.
 */
function normalizePath(pathname: string): string {
  if (!pathname) return "/dashboard";
  const clean = pathname.split("?")[0].replace(/\/+$/, "") || "/dashboard";

  // Exact match
  if (BASE_PAGE_METADATA[clean]) return clean;

  // Prefix matching for parameterized routes (e.g. /dashboard/activities/uuid -> /dashboard/activities)
  if (clean.startsWith("/dashboard/activities/")) return "/dashboard/activities";
  if (clean.startsWith("/dashboard/properties/")) return "/dashboard/properties";
  if (clean.startsWith("/dashboard/projects/")) return "/dashboard/projects";

  return clean;
}

/**
 * Resolves permissions and role boundaries for the page action.
 * Returns null if the user has no permission and no read-only fallback is suitable.
 */
function resolveAction(
  defaultAction?: GuidanceAction,
  role?: string | null
): GuidanceAction | undefined {
  if (!defaultAction) return undefined;

  const canonical = normalizeRole(role);

  // Super Admin can execute any action
  if (canonical === CANONICAL_ROLES.SUPER_ADMIN) {
    return defaultAction;
  }

  // Read-only roles must never receive mutation actions
  if (canonical === CANONICAL_ROLES.VIEWER || canonical === CANONICAL_ROLES.INVESTOR) {
    if (defaultAction.mutation) {
      // If the action was a mutation, convert to a read-only navigation action or omit
      if (defaultAction.href) {
        const readOnlyLabel = defaultAction.label
          .replace(/^(Manage|Create|Edit|Issue|Authorize|Resolve|Review)\s+/i, "View ")
          .replace(/Queue$/i, "Queue");
        return {
          label: readOnlyLabel.startsWith("View ") ? readOnlyLabel : `View ${readOnlyLabel}`,
          href: defaultAction.href,
          mutation: false
        };
      }
      return undefined;
    }
    return defaultAction;
  }

  // Check specific permission if configured
  if (defaultAction.permission) {
    const hasPerm = canPerformAction(defaultAction.permission, role);
    if (!hasPerm) {
      // Degrade to safe navigation action if possible, else omit
      if (defaultAction.href) {
        return {
          label: `View ${defaultAction.label.replace(/^(Manage|Edit|Create|Sign)\s+/i, "")}`,
          href: defaultAction.href,
          mutation: false
        };
      }
      return undefined;
    }
  }

  return defaultAction;
}

/**
 * Main resolver function. Produces page-aware, sector-aware, and role-aware guidance.
 */
export function resolveGuidance(context: PageGuidanceContext): ContextualPageInsight {
  const normalizedRoute = normalizePath(context.pathname);
  const baseMeta: BasePageMetadata = BASE_PAGE_METADATA[normalizedRoute] || FALLBACK_PAGE_METADATA;
  const sectorOverlay = getSectorOverlay(context.sector);
  const canonicalRole = normalizeRole(context.role);

  // 1. Resolve Next Action based on RBAC permissions
  let action = resolveAction(baseMeta.defaultAction, context.role);

  // Role-specific action tuning
  if (normalizedRoute === "/dashboard") {
    if (canonicalRole === CANONICAL_ROLES.VERIFIER || canonicalRole === CANONICAL_ROLES.AUDITOR) {
      action = {
        label: "View Verification Queue",
        href: "/dashboard/verifications",
        mutation: false
      };
    } else if (canonicalRole === CANONICAL_ROLES.FIELD_AGENT || canonicalRole === CANONICAL_ROLES.FIELD_SUPERVISOR) {
      action = {
        label: "View Field Operations",
        href: "/dashboard/operations",
        mutation: false
      };
    }
  }

  // 2. Resolve What To Do Next (truthful, runtime-aware if data provided)
  let whatToDoNext = baseMeta.baseWhatToDoNext;
  if (context.pageData) {
    if (typeof context.pageData.unresolvedFindingsCount === "number" && context.pageData.unresolvedFindingsCount > 0) {
      whatToDoNext = `Review ${context.pageData.unresolvedFindingsCount} open verification findings.`;
    } else if (typeof context.pageData.offlineSensorsCount === "number" && context.pageData.offlineSensorsCount > 0) {
      whatToDoNext = `Investigate ${context.pageData.offlineSensorsCount} monitoring devices currently offline.`;
    } else if (typeof context.pageData.pendingActivitiesCount === "number" && context.pageData.pendingActivitiesCount > 0) {
      whatToDoNext = `Review ${context.pageData.pendingActivitiesCount} field activity submissions in the queue.`;
    }
  }

  // 3. Resolve AI recommendation / Sector Overlay
  const sectorRec = sectorOverlay.recommendationOverlay?.[normalizedRoute];
  const aiRecommendation = sectorRec ||
    `Operational data and records for ${sectorOverlay.sectorName} are synchronized with VeriField digital MRV standards.`;

  // 4. Resolve Suggested Queries (merge sector queries if available, cap at 4)
  const sectorQueries = sectorOverlay.suggestedQueriesOverlay?.[normalizedRoute];
  const suggestedQueries = sectorQueries && sectorQueries.length > 0
    ? sectorQueries.slice(0, 4)
    : baseMeta.suggestedQueries.slice(0, 4);

  return {
    pageTitle: baseMeta.pageTitle,
    purpose: baseMeta.basePurpose,
    whyItMatters: baseMeta.baseWhyItMatters,
    whatToDoNext,
    aiRecommendation,
    nextActionLabel: action?.label || "",
    nextActionHref: action?.href || "",
    action,
    queryPlaceholder: baseMeta.queryPlaceholder,
    suggestedQueries
  };
}
