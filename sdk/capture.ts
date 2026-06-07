import { VerificationPayload, AssetType, GPSCoordinates, DeviceSignature } from "./types";

/**
 * Constructs a standardized verification payload for climate RWA logging.
 *
 * @param assetType Type of the verified asset ("cookstove" | "hybrid_energy")
 * @param gps GPS coordinates (latitude, longitude, accuracy)
 * @param timestamp Unix epoch timestamp in seconds
 * @param imageHash SHA-256 hash of the evidence files
 * @param deviceSignature Optional signature metadata from the capture device
 * @returns A structured VerificationPayload object
 */
export function createVerificationPayload(
  assetType: AssetType,
  gps: GPSCoordinates,
  timestamp: number,
  imageHash: string,
  deviceSignature?: DeviceSignature
): VerificationPayload {
  return {
    assetType,
    gps: {
      latitude: Number(gps.latitude),
      longitude: Number(gps.longitude),
      accuracy: gps.accuracy !== undefined ? Number(gps.accuracy) : undefined,
    },
    timestamp: Math.floor(timestamp),
    imageHash: imageHash.trim(),
    deviceSignature,
  };
}
