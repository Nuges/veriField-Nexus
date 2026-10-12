// =============================================================================
// VeriField Nexus — Project Methodology Resolution & Presentation Logic
// =============================================================================

import { STALE_METHODOLOGY_UUID_ALIASES } from "./sectors";

export interface ResolvedProjectMethodology {
  code: string;
  isAssigned: boolean;
  version?: string;
}

/**
 * Resolves project methodology presentation with strict fallback protection:
 * 1. Checks persisted project.methodology_code or project.methodology?.code.
 * 2. Checks contract baseline_parameters.methodology_code.
 * 3. Checks methodology_id against canonical methodology catalog / aliases.
 * 4. If no methodology is assigned, returns "Under Assessment" (NO fake VM0042 fallback).
 */
export function resolveProjectMethodology(project: any): ResolvedProjectMethodology {
  if (!project) {
    return { code: "Under Assessment", isAssigned: false, version: undefined };
  }

  // 1. Direct methodology_code on project record / API response
  const directCode =
    project.methodology_code ||
    project.methodology?.code ||
    project.methodology?.methodology_code;
  if (typeof directCode === "string" && directCode.trim()) {
    return {
      code: directCode.trim().replace(/_/g, "-"),
      isAssigned: true,
      version:
        project.methodology_version ||
        project.methodology?.version ||
        project.baseline_parameters?.methodology_version ||
        undefined,
    };
  }

  // 2. Baseline parameters methodology_code per data contract
  const baselineCode = project.baseline_parameters?.methodology_code;
  if (typeof baselineCode === "string" && baselineCode.trim()) {
    return {
      code: baselineCode.trim().replace(/_/g, "-"),
      isAssigned: true,
      version:
        project.baseline_parameters?.methodology_version ||
        project.methodology_version ||
        undefined,
    };
  }

  // 3. methodology_id mapped through canonical aliases
  const methodologyId = project.methodology_id;
  if (methodologyId && typeof methodologyId === "string") {
    const aliasCode = STALE_METHODOLOGY_UUID_ALIASES[methodologyId];
    if (aliasCode) {
      return {
        code: aliasCode,
        isAssigned: true,
        version:
          project.methodology_version ||
          project.baseline_parameters?.methodology_version ||
          undefined,
      };
    }
  }

  // 4. No methodology assigned -> "Under Assessment"
  return {
    code: "Under Assessment",
    isAssigned: false,
    version: undefined,
  };
}
