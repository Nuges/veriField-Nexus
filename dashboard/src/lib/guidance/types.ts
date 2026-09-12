// =============================================================================
// VeriField Nexus — Page Guidance & Decision Support Types
// =============================================================================
// Modular, role-aware, sector-aware, and permission-gated guidance architecture.
// =============================================================================

import { ActionPermission } from "../roles";

export interface GuidanceAction {
  label: string;
  href?: string;
  permission?: ActionPermission;
  mutation?: boolean;
}

export interface ContextualPageInsight {
  pageTitle: string;
  purpose: string;
  whyItMatters: string;
  whatToDoNext: string;
  aiRecommendation: string;
  nextActionLabel?: string;
  nextActionHref?: string;
  action?: GuidanceAction;
  queryPlaceholder: string;
  suggestedQueries: string[];
}

export interface PageGuidanceContext {
  pathname: string;
  sector?: string | null;
  role?: string | null;
  projectId?: string | null;
  pageData?: Record<string, unknown>;
}

export interface BasePageMetadata {
  pageTitle: string;
  basePurpose: string;
  baseWhyItMatters: string;
  baseWhatToDoNext: string;
  defaultAction?: GuidanceAction;
  queryPlaceholder: string;
  suggestedQueries: string[];
}

export interface SectorGuidanceOverlay {
  sectorName: string;
  protocol?: string;
  contextTerminology: string;
  recommendationOverlay?: Record<string, string>;
  suggestedQueriesOverlay?: Record<string, string[]>;
}
