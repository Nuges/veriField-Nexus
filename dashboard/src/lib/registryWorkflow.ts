import { normalizeRole } from "./roles";
import { resolveProjectMethodology } from "./projectMethodology";
import type { Project } from "./types";

export interface RegistryDocumentRequirement {
  document_id: string;
  official_name?: string;
  nexus_name?: string;
  document_class?: string;
  mandatory?: boolean;
  nexus_generated?: boolean;
  supported_formats?: string[];
  completeness_status?: string;
  blocking_requirements?: string[];
  missing_requirements?: string[];
}
export interface RegistryDocumentMatrix {
  version?: string;
  authorities?: { id: string; name: string; documents: RegistryDocumentRequirement[] }[];
}
export interface RegistryReadiness {
  project_id: string;
  target_standard: string;
  readiness_status: string;
  blocking_items?: string[];
  missing_requirements?: string[];
  document_readiness?: RegistryDocumentRequirement[];
  evaluated_at?: string;
}

// Mirrors existing backend registry:read permissions, without granting new access.
export function canReadRegistry(role?: string | null): boolean {
  return ["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "REGISTRY_ADMIN", "COMPLIANCE_ADMIN"].includes(normalizeRole(role));
}

export function registryExportBlockReason(project: Project, readiness: RegistryReadiness | null, standard: string, sector?: string | null): string | null {
  if (!resolveProjectMethodology(project).isAssigned) return "A methodology has not been assigned. This project remains Under Assessment.";
  const params = project.baseline_parameters || {};
  if (params.is_test === true || params.test_mode === true || ["TEST", "DEMO", "PILOT"].includes(String(params.data_classification).toUpperCase()) || /wokwi|simulation|telemetry pilot|local\/test/i.test(`${params.purpose || ""} ${params.environment || ""}`)) return "Pilot and test data are not eligible for registry exports.";
  if (/cook|mecd/i.test(`${project.sector || sector || ""} ${resolveProjectMethodology(project).code}`)) return "Cookstove registry exports remain gated while the pilot workflow is incomplete.";
  if (!readiness || readiness.project_id !== project.id || readiness.target_standard !== standard) return "Review readiness for this project and registry first.";
  if (readiness.readiness_status !== "SUBMISSION_READY" || !Array.isArray(readiness.blocking_items) || !Array.isArray(readiness.missing_requirements) || readiness.blocking_items.length || readiness.missing_requirements.length) return "Resolve the backend's missing requirements before generating an export.";
  return null;
}

export function registryPreparationLabel(readiness: RegistryReadiness | null): string {
  if (!readiness) return "Not Started";
  if (readiness.readiness_status === "BLOCKED" || readiness.blocking_items?.length || readiness.missing_requirements?.length) return "Missing Requirements";
  return readiness.readiness_status === "SUBMISSION_READY" ? "Ready for Review" : "In Preparation";
}
