/**
 * Supported climate asset types in the VeriField Nexus MRV ecosystem.
 */
export type AssetType = "cookstove" | "hybrid_energy";

/**
 * Geospatial coordinates captured at the asset site.
 */
export interface GPSCoordinates {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

/**
 * Metadata parameters describing the capture device.
 */
export interface DeviceSignature {
  deviceId: string;
  os?: string;
  appVersion?: string;
}

/**
 * Raw input payload structured at the capture source.
 */
export interface VerificationPayload {
  assetType: AssetType;
  gps: GPSCoordinates;
  timestamp: number;
  imageHash: string;
  deviceSignature?: DeviceSignature;
}

/**
 * Final scored verification record anchored on-chain.
 */
export interface VerificationRecord {
  id: string;
  assetType: AssetType;
  gps: GPSCoordinates;
  timestamp: number;
  imageHash: string;
  verificationScore: number;
  solanaSignature?: string;
  anchoredAt?: string;
}
