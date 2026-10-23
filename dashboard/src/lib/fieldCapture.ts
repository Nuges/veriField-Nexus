import { normalizeToCanonicalSectorCode, type CanonicalSectorCode } from "./sectors";
import type { Project } from "./types";

export const CAPTURE_FIELDS: Record<CanonicalSectorCode, { label: string; metric: string; key: string; type: string }> = {
  COOKSTOVES: { label: "Clean cooking", metric: "Cooking time (hours)", key: "project_cooking_duration", type: "CLEAN_COOKING" },
  HYBRID_ENERGY: { label: "Hybrid energy", metric: "Energy delivered (kWh)", key: "energy_generated_kwh", type: "HYBRID_ENERGY" },
  BIOCHAR: { label: "Biochar", metric: "Biochar produced (kg)", key: "biochar_weight_kg", type: "BIOCHAR_PRODUCTION" },
  EV_MOBILITY: { label: "Electric mobility", metric: "Distance travelled (km)", key: "distance_km", type: "EV_TRIP" },
  AGRICULTURE_LAND_USE: { label: "Agriculture & land use", metric: "Sample depth (cm)", key: "actual_depth_to_cm", type: "soil_sample_collection" },
};

export function projectCaptureSector(project?: Project | null): CanonicalSectorCode | null {
  if (!project) return null;
  return normalizeToCanonicalSectorCode(project.sector) || normalizeToCanonicalSectorCode(project.sector_id)
    || normalizeToCanonicalSectorCode(project.baseline_parameters?.sector)
    || normalizeToCanonicalSectorCode(project.baseline_parameters?.sector_code);
}

export function validateCapture(project: Project | undefined, allowedSectors: string[], metric: string, latitude: number | null, longitude: number | null): string | null {
  const sector = projectCaptureSector(project);
  if (!project || !sector) return "Select a project with a configured operating sector.";
  if (!allowedSectors.some(s => normalizeToCanonicalSectorCode(s) === sector)) return "This project's sector is outside your workspace access.";
  if (!Number.isFinite(Number(metric)) || Number(metric) <= 0) return "Enter a quantity greater than zero.";
  if (latitude === null || longitude === null || !Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return "Provide the actual location before submitting.";
  if (sector === "COOKSTOVES" && Number(metric) > 24) return "Cooking time cannot exceed 24 hours per day.";
  return null;
}

export const captureQueueKey = (userId: string, orgId?: string | null) => `verifield_capture_queue:${orgId || "platform"}:${userId}`;
