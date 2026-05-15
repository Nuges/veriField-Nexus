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

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  let response: Response;
  try {
    response = await fetch(`${API_V1}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
      cache: "no-store", // Prevents Next.js aggressive caching for dashboard live data
    });
    clearTimeout(timeoutId);
  } catch (networkError: any) {
    clearTimeout(timeoutId);
    if (networkError.name === 'AbortError') {
      throw new Error("Request timed out. The server is taking too long to respond. Please try again.");
    }
    // Network error — backend unreachable, don't logout
    throw new Error("Network error: Unable to reach the server. Please check your connection.");
  }

  if (!response.ok) {
    // Only redirect to login on 401 for non-auth endpoints
    // This prevents the login → dashboard → 401 → login loop
    if (
      response.status === 401 &&
      typeof window !== "undefined" &&
      !endpoint.startsWith("/auth/") &&
      !window.location.pathname.includes("/login")
    ) {
      localStorage.removeItem("vf_token");
      authToken = null;
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
  const res = await apiFetch<any>(
    `/activities${query ? `?${query}` : ""}`
  );
  
  // Map backend's 'data' key to the dashboard's expected 'activities' key
  return {
    ...res,
    activities: res.data || [],
  } as ActivityListResponse;
}

export async function fetchActivity(id: string): Promise<Activity> {
  return apiFetch<Activity>(`/activities/${id}`);
}

export async function updateActivityStatus(id: string, status: string): Promise<Activity> {
  return apiFetch<Activity>(`/activities/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
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
  return apiFetch<AnalyticsOverview>("/metrics/overview");
}

export async function fetchDailySubmissions(
  days = 30
): Promise<DailySubmission[]> {
  return apiFetch<DailySubmission[]>(`/analytics/daily?days=${days}`);
}

export async function fetchTrends(days = 30): Promise<AnalyticsTrends> {
  return apiFetch<AnalyticsTrends>(`/metrics/trends?days=${days}`);
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

// ---------------------------------------------------------------------------
// Carbon MRV & Registry API
// ---------------------------------------------------------------------------

export async function fetchCarbonLedger(): Promise<{ data: any[] }> {
  return apiFetch<{ data: any[] }>(`/carbon/ledger`);
}

export async function fetchAnomalies(): Promise<{ anomalies: any[], total: number }> {
  return apiFetch<{ anomalies: any[], total: number }>("/metrics/anomalies");
}

export async function resolveAnomaly(flagId: string, action: "verify" | "reject", notes: string = ""): Promise<any> {
  return apiFetch<any>(`/metrics/anomalies/${flagId}/resolve`, {
    method: "PATCH",
    body: JSON.stringify({ action, notes }),
  });
}

export async function fetchAudits(): Promise<{ audits: any[], total: number }> {
  return apiFetch<{ audits: any[], total: number }>("/audits");
}

export async function updateAuditStatus(id: string, status: string, deadline?: string): Promise<any> {
  const body: Record<string, string> = { status };
  if (deadline) body.deadline = deadline;
  return apiFetch<any>(`/audits/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function issueVerraCredits(): Promise<any> {
  return apiFetch<any>(`/carbon/registry/verra/issue`, {
    method: "POST",
  });
}

export async function issueGoldStandardCredits(): Promise<any> {
  return apiFetch<any>(`/carbon/registry/goldstandard/issue`, {
    method: "POST",
  });
}

export async function quantifyActivity(id: string, projectId?: string): Promise<any> {
  return apiFetch<any>(`/carbon/calculate/${id}`, {
    method: "POST",
    body: projectId ? JSON.stringify({ project_id: projectId }) : undefined,
  });
}

// ---------------------------------------------------------------------------
// Agent Performance API
// ---------------------------------------------------------------------------

export async function fetchAgentPerformance(): Promise<import("./types").AgentPerformanceResponse> {
  return apiFetch<import("./types").AgentPerformanceResponse>("/metrics/agents");
}

export async function createAgent(data: any): Promise<any> {
  return apiFetch<any>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateAgentStatus(userId: string, status: "active" | "suspended" | "revoked"): Promise<any> {
  return apiFetch<any>(`/auth/users/${userId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// ---------------------------------------------------------------------------
// Registry Export API
// ---------------------------------------------------------------------------

export async function exportVerraCSV(minTrustScore = 80): Promise<void> {
  const currentToken = getAuthToken();
  const response = await fetch(
    `${API_V1}/registry/export/verra?min_trust_score=${minTrustScore}`,
    {
      headers: {
        ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
      },
    }
  );
  if (!response.ok) throw new Error("Export failed");
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = response.headers.get("Content-Disposition")?.split("filename=")[1] || "verra_export.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function exportGoldStandardJSON(minTrustScore = 80): Promise<any> {
  return apiFetch<any>(`/registry/export/goldstandard?min_trust_score=${minTrustScore}`);
}

// ---------------------------------------------------------------------------
// Satellite NDVI API
// ---------------------------------------------------------------------------

export async function fetchNdvi(assetId: string, month?: string): Promise<any> {
  const params = month ? `?month=${month}` : "";
  return apiFetch<any>(`/satellite/ndvi/${assetId}${params}`, { method: "POST" });
}

export async function fetchNdviHistory(assetId: string): Promise<import("./types").NdviHistoryResponse> {
  return apiFetch<import("./types").NdviHistoryResponse>(`/satellite/ndvi/${assetId}/history`);
}

// ---------------------------------------------------------------------------
// Sensor Devices API
// ---------------------------------------------------------------------------

export async function fetchSensorDevices(): Promise<{ devices: any[]; total: number }> {
  return apiFetch<{ devices: any[]; total: number }>("/sensors/devices");
}

// ---------------------------------------------------------------------------
// Carbon Projects API
// ---------------------------------------------------------------------------

export async function fetchProjectTotal(projectId: string): Promise<any> {
  return apiFetch<any>(`/carbon/projects/${projectId}/total`);
}

export async function createCarbonProject(data: {
  name: string;
  methodology_id: string;
  baseline_parameters: Record<string, any>;
}): Promise<any> {
  return apiFetch<any>("/carbon/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// System Settings API
// ---------------------------------------------------------------------------

export async function fetchSettings(): Promise<{ gps_weight: number; image_weight: number; frequency_weight: number }> {
  return apiFetch<{ gps_weight: number; image_weight: number; frequency_weight: number }>("/settings");
}

export async function updateSettings(data: { gps_weight: number; image_weight: number; frequency_weight: number }): Promise<any> {
  return apiFetch<any>("/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

