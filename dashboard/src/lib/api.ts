// =============================================================================
// VeriField Nexus — Dashboard API Client
// =============================================================================
// Type-safe HTTP client for communicating with the FastAPI backend.
// =============================================================================

import type {
  Activity,
  ActivityListResponse,
  AnalyticsOverview,
  AnalyticsTrends,
  DailySubmission,
  Property,
  TrustDistribution,
  TrustScoreBreakdown,
} from "./types";

// Add types for cross verification
export interface SensorReading {
  id: string;
  asset_id: string;
  device_id: string;
  temperature: number | null;
  usage_flag: boolean;
  timestamp: string;
}

export interface CommunityValidation {
  id: string;
  asset_id: string;
  validator_id: string;
  response: string;
  timestamp: string;
}

export interface AuditTask {
  id: string;
  asset_id: string;
  assigned_agent: string;
  status: string;
  deadline: string | null;
  created_at: string;
}

// Base URL for the FastAPI backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://verifield-nexus.onrender.com";
const API_V1 = `${API_BASE}/api/v1`;

// Store the auth token in memory
let authToken: string | null = null;

/** Set the auth token for API requests. */
export function setAuthToken(token: string | null) {
  authToken = token;
}

/** Get stored auth token. */
export function getAuthToken(): string | null {
  if (!authToken && typeof window !== "undefined") {
    authToken = localStorage.getItem("vf_token");
  }
  return authToken;
}

// ---------------------------------------------------------------------------
// Generic Fetch Wrapper
// ---------------------------------------------------------------------------

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const currentToken = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
    ...(options.headers as Record<string, string> || {}),
  };

  const response = await fetch(`${API_V1}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      // Clear expired token and redirect to login
      localStorage.removeItem("vf_token");
      window.location.href = "/login";
    }

    const error = await response.json().catch(() => ({}));
    throw new Error(
      error.detail || `API error: ${response.status} ${response.statusText}`
    );
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export async function loginAdmin(email: string, password: string) {
  return apiFetch<{ user: any; access_token: string; expires_in: number }>(
    "/auth/login",
    {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }
  );
}

// ---------------------------------------------------------------------------
// Activities API
// ---------------------------------------------------------------------------

export async function fetchActivities(params?: {
  page?: number;
  per_page?: number;
  status?: string;
  activity_type?: string;
  min_trust?: number;
  max_trust?: number;
}): Promise<ActivityListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.status) searchParams.set("status", params.status);
  if (params?.activity_type) searchParams.set("activity_type", params.activity_type);
  if (params?.min_trust !== undefined) searchParams.set("min_trust", String(params.min_trust));
  if (params?.max_trust !== undefined) searchParams.set("max_trust", String(params.max_trust));

  const query = searchParams.toString();
  return apiFetch<ActivityListResponse>(
    `/activities${query ? `?${query}` : ""}`
  );
}

export async function fetchActivity(id: string): Promise<Activity> {
  return apiFetch<Activity>(`/activities/${id}`);
}

export async function fetchTrustScore(
  activityId: string
): Promise<TrustScoreBreakdown> {
  return apiFetch<TrustScoreBreakdown>(`/activities/${activityId}/trust`);
}

// ---------------------------------------------------------------------------
// Properties API
// ---------------------------------------------------------------------------

export async function fetchProperties(): Promise<{
  properties: Property[];
  total: number;
}> {
  return apiFetch(`/properties?per_page=100`);
}

export async function fetchProperty(id: string): Promise<Property & { total_activities?: number, avg_trust_score?: number, activity_breakdown?: any }> {
  return apiFetch<Property & { total_activities?: number, avg_trust_score?: number, activity_breakdown?: any }>(`/properties/${id}`);
}

export async function fetchPropertyActivities(id: string): Promise<Activity[]> {
  return apiFetch<Activity[]>(`/properties/${id}/activities?per_page=50`);
}

// ---------------------------------------------------------------------------
// Analytics API
// ---------------------------------------------------------------------------

export async function fetchAnalyticsOverview(): Promise<AnalyticsOverview> {
  return apiFetch<AnalyticsOverview>("/analytics/overview");
}

export async function fetchDailySubmissions(
  days = 30
): Promise<DailySubmission[]> {
  return apiFetch<DailySubmission[]>(`/analytics/daily?days=${days}`);
}

export async function fetchTrends(days = 30): Promise<AnalyticsTrends> {
  return apiFetch<AnalyticsTrends>(`/analytics/trends?days=${days}`);
}

export async function fetchTrustDistribution(): Promise<TrustDistribution> {
  return apiFetch<TrustDistribution>("/analytics/trust-distribution");
}

// ---------------------------------------------------------------------------
// Export API
// ---------------------------------------------------------------------------

export async function exportData(params: {
  format?: string;
  min_trust_score?: number;
  include_flagged?: boolean;
}) {
  return apiFetch("/export", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ---------------------------------------------------------------------------
// Cross Verification API
// ---------------------------------------------------------------------------

export async function fetchSensorReadings(assetId: string): Promise<SensorReading[]> {
  return apiFetch<SensorReading[]>(`/verification/sensors/${assetId}`);
}

export async function fetchCommunityValidations(assetId: string): Promise<CommunityValidation[]> {
  return apiFetch<CommunityValidation[]>(`/verification/community/${assetId}`);
}

export async function fetchMyAuditTasks(): Promise<AuditTask[]> {
  return apiFetch<AuditTask[]>("/verification/audits/my-tasks");
}

export async function createAuditTask(data: { asset_id: string; assigned_agent: string; deadline?: string }): Promise<AuditTask> {
  return apiFetch<AuditTask>("/verification/audits", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
