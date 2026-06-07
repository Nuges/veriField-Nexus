import { VerificationPayload } from "./types";

/**
 * Validates a verification payload for formatting and structural constraints.
 * 
 * @param payload VerificationPayload to evaluate
 * @returns An object containing `valid` (boolean) and an optional list of validation errors
 */
export function validatePayload(payload: VerificationPayload): {
  valid: boolean;
  errors?: string[];
} {
  const errors: string[] = [];

  // 1. Asset Type check
  if (payload.assetType !== "cookstove" && payload.assetType !== "hybrid_energy") {
    errors.push(`Invalid assetType: ${payload.assetType}. Must be 'cookstove' or 'hybrid_energy'.`);
  }

  // 2. GPS check
  if (!payload.gps || typeof payload.gps.latitude !== "number" || typeof payload.gps.longitude !== "number") {
    errors.push("Missing or malformed coordinates. GPS requires latitude and longitude numbers.");
  } else {
    const { latitude, longitude } = payload.gps;
    if (latitude < -90 || latitude > 90) {
      errors.push(`Latitude out of bounds: ${latitude}. Must be between -90 and 90.`);
    }
    if (longitude < -180 || longitude > 180) {
      errors.push(`Longitude out of bounds: ${longitude}. Must be between -180 and 180.`);
    }
  }

  // 3. Timestamp check
  if (!payload.timestamp || typeof payload.timestamp !== "number" || payload.timestamp <= 0) {
    errors.push(`Invalid timestamp: ${payload.timestamp}. Must be a positive Unix epoch integer.`);
  }

  // 4. Image Hash check
  const hashRegex = /^[a-fA-F0-9]{64}$/;
  if (!payload.imageHash || !hashRegex.test(payload.imageHash)) {
    errors.push("Invalid imageHash. Must be a 64-character SHA-256 hex string.");
  }

  return {
    valid: errors.length === 0,
    errors: errors.length > 0 ? errors : undefined,
  };
}
