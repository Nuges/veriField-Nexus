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
  User,
} from "./types";
import { safeStorage } from "./storage";

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
  property_name?: string | null;
  property_address?: string | null;
  property_type?: string | null;
  agent_name?: string | null;
}

// Base URL for the FastAPI backend
// Always use relative paths so requests go through the Next.js rewrite proxy.
// Only use an explicit URL if NEXT_PUBLIC_API_URL is set and non-empty.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
export const API_V1 = `${API_BASE}/api/v1`;

// Store the auth token in memory
let authToken: string | null = null;

/** Set the auth token for API requests. */
export function setAuthToken(token: string | null) {
  authToken = token;
}

/** Get stored auth token. */
export function getAuthToken(): string | null {
  if (!authToken && typeof window !== "undefined") {
    authToken = safeStorage.getItem("vf_token");
  }
  return authToken;
}

// ---------------------------------------------------------------------------
// Generic Fetch Wrapper
// ---------------------------------------------------------------------------

interface CustomRequestInit extends RequestInit {
  timeout?: number;
}

function cleanImageUrl(url: string): string {
  if (typeof url === "string" && url.includes("/static/")) {
    const parts = url.split("/static/");
    return "/static/" + parts[parts.length - 1];
  }
  return url;
}

function recursiveCleanImageUrls(obj: any): any {
  if (obj === null || obj === undefined) return obj;
  if (typeof obj === "string") {
    return cleanImageUrl(obj);
  }
  if (Array.isArray(obj)) {
    return obj.map(recursiveCleanImageUrls);
  }
  if (typeof obj === "object") {
    const cleaned: any = {};
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        cleaned[key] = recursiveCleanImageUrls(obj[key]);
      }
    }
    return cleaned;
  }
  return obj;
}

export async function apiFetch<T>(
  endpoint: string,
  options: CustomRequestInit = {}
): Promise<T> {
  const { timeout, ...fetchOptions } = options;
  const currentToken = getAuthToken();
  const headers: Record<string, string> = {
    ...(fetchOptions.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
    ...(fetchOptions.headers as Record<string, string> || {}),
  };

  const customTimeout = timeout !== undefined ? timeout : 30000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), customTimeout); // default 30s — accounts for ngrok/tunnel latency

  let response: Response;
  try {
    response = await fetch(`${API_V1}${endpoint}`, {
      ...fetchOptions,
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
    // Never redirect on 503 (service unavailable) or 500 (server error)
    if (
      response.status === 401 &&
      typeof window !== "undefined" &&
      !endpoint.startsWith("/auth/") &&
      !window.location.pathname.includes("/login")
    ) {
      safeStorage.removeItem("vf_token");
      authToken = null;
      window.location.href = "/login";
      return new Promise<T>(() => {});
    }

    const error = await response.json().catch(() => ({}));
    let errorMessage = `API error: ${response.status} ${response.statusText}`;
    if (error.detail) {
      if (typeof error.detail === "string") {
        errorMessage = error.detail;
      } else if (Array.isArray(error.detail)) {
        errorMessage = error.detail.map((err: any) => {
          const locStr = err.loc ? err.loc.join(".") : "";
          return locStr ? `${locStr}: ${err.msg}` : err.msg;
        }).join("; ");
      } else if (typeof error.detail === "object") {
        if (Array.isArray(error.detail.errors) && error.detail.errors.length > 0) {
          errorMessage = error.detail.errors.join("; ");
        } else if (error.detail.message) {
          errorMessage = String(error.detail.message);
        } else {
          errorMessage = JSON.stringify(error.detail);
        }
      }
    }
    throw new Error(errorMessage);
  }

  const data = await response.json();
  return recursiveCleanImageUrls(data) as T;
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export async function loginAdmin(email: string, password: string) {
  // Use direct fetch — login must NEVER send a stale Authorization header
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s for login — ngrok adds 7-10s latency

  let response: Response;
  try {
    response = await fetch(`${API_V1}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timeoutId);
  } catch (networkError: any) {
    clearTimeout(timeoutId);
    if (networkError.name === "AbortError") {
      throw new Error("Login timed out. The server is taking too long to respond. Please try again.");
    }
    throw new Error("Network error: Unable to reach the server. Please check your connection.");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Login failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<{ user: any; access_token: string; expires_in: number }>;
}

export async function onboardDeveloper(payload: {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
  sector: string;
  country?: string;
  project_type?: string;
}) {
  return apiFetch<{ user: any; access_token: string; expires_in: number }>(
    "/auth/onboard",
    {
      method: "POST",
      body: JSON.stringify(payload),
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
  min_trust?: number;
  max_trust?: number;
  sector?: string;
}): Promise<ActivityListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.status) searchParams.set("status", params.status);
  if (params?.min_trust !== undefined) searchParams.set("min_trust", String(params.min_trust));
  if (params?.max_trust !== undefined) searchParams.set("max_trust", String(params.max_trust));
  if (params?.sector) searchParams.set("sector", params.sector);

  const query = searchParams.toString();
  return apiFetch<ActivityListResponse>(
    `/installations${query ? `?${query}` : ""}`
  );
}

export async function createActivity(payload: any): Promise<Activity> {
  return apiFetch<Activity>("/installations", {
    method: "POST",
    body: JSON.stringify(payload),
    timeout: 60000, // 60s for submission (which does duplicate check & trust evaluation)
  });
}

export async function uploadProof(file: File): Promise<{ image_url: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<{ image_url: string }>("/installations/upload-proof", {
    method: "POST",
    body: formData,
    timeout: 90000, // 90s for image upload on mobile networks
  });
}

export async function checkDuplicate(payload: {
  latitude: number;
  longitude: number;
  activity_type: string;
}): Promise<{
  duplicate_flag: boolean;
  environment_type: string;
  radius_used_m: number;
  nearby_installations: any[];
}> {
  return apiFetch<{
    duplicate_flag: boolean;
    environment_type: string;
    radius_used_m: number;
    nearby_installations: any[];
  }>("/installations/check-duplicate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchActivity(id: string): Promise<Activity> {
  return apiFetch<Activity>(`/installations/${id}`);
}

export async function updateActivityStatus(id: string, status: string): Promise<Activity> {
  return apiFetch<Activity>(`/installations/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function fetchTrustScore(
  activityId: string
): Promise<TrustScoreBreakdown> {
  return apiFetch<TrustScoreBreakdown>(`/installations/${activityId}/trust`);
}

// ---------------------------------------------------------------------------
// Properties API
// ---------------------------------------------------------------------------

export async function fetchProperties(perPage = 100, sector?: string): Promise<{
  properties: Property[];
  total: number;
}> {
  return apiFetch(`/properties?per_page=${perPage}${sector ? `&sector=${sector}` : ""}`);
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

export async function fetchAnalyticsOverview(sector?: string): Promise<AnalyticsOverview> {
  return apiFetch<AnalyticsOverview>(`/metrics/overview${sector ? `?sector=${sector}` : ""}`);
}

export async function fetchDailySubmissions(
  days = 30,
  sector?: string
): Promise<DailySubmission[]> {
  return apiFetch<DailySubmission[]>(`/analytics/daily?days=${days}${sector ? `&sector=${sector}` : ""}`);
}

export async function fetchTrends(days = 30, sector?: string): Promise<AnalyticsTrends> {
  return apiFetch<AnalyticsTrends>(`/metrics/trends?days=${days}${sector ? `&sector=${sector}` : ""}`);
}

export async function fetchTrustDistribution(sector?: string): Promise<TrustDistribution> {
  return apiFetch<TrustDistribution>(`/analytics/trust-distribution${sector ? `?sector=${sector}` : ""}`);
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
  return apiFetch<AuditTask[]>("/audits/my-tasks");
}

export async function createAuditTask(data: { asset_id: string; assigned_agent: string; deadline?: string }): Promise<AuditTask> {
  return apiFetch<AuditTask>("/audits", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Carbon MRV & Registry API
// ---------------------------------------------------------------------------

export async function fetchCarbonLedger(includeLog = false, sector?: string): Promise<{ data: any[] }> {
  return apiFetch<{ data: any[] }>(`/carbon/ledger?include_log=${includeLog}${sector ? `&sector=${sector}` : ""}`);
}

export async function fetchAnomalies(sector?: string): Promise<{ anomalies: any[], total: number }> {
  return apiFetch<{ anomalies: any[], total: number }>(`/metrics/anomalies${sector ? `?sector=${sector}` : ""}`);
}

export async function resolveAnomaly(flagId: string, action: "verify" | "reject", notes: string = ""): Promise<any> {
  return apiFetch<any>(`/metrics/anomalies/${flagId}/resolve`, {
    method: "PATCH",
    body: JSON.stringify({ action, notes }),
  });
}

export async function fetchAudits(sector?: string): Promise<{ audits: any[], total: number }> {
  return apiFetch<{ audits: any[], total: number }>(`/audits${sector ? `?sector=${sector}` : ""}`);
}

export async function updateAuditStatus(id: string, status?: string, deadline?: string, assigned_agent?: string): Promise<any> {
  const body: Record<string, string> = {};
  if (status) body.status = status;
  if (deadline) body.deadline = deadline;
  if (assigned_agent) body.assigned_agent = assigned_agent;
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
    body: JSON.stringify(projectId ? { project_id: projectId } : {}),
  });
}

// ---------------------------------------------------------------------------
// Agent Performance API
// ---------------------------------------------------------------------------

export async function fetchAgentPerformance(sector?: string): Promise<import("./types").AgentPerformanceResponse> {
  return apiFetch<import("./types").AgentPerformanceResponse>(`/metrics/agents${sector ? `?sector=${sector}` : ""}`);
}

export async function createAgent(data: any): Promise<any> {
  return apiFetch<any>("/auth/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchUsers(): Promise<any[]> {
  return apiFetch<any[]>("/auth/users");
}

export async function updateAgentStatus(userId: string, status: "active" | "suspended" | "revoked"): Promise<any> {
  return apiFetch<any>(`/auth/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

export async function resetAgentPassword(userId: string, newPassword: string): Promise<any> {
  return apiFetch<any>(`/auth/users/${userId}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword }),
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

export async function exportGoldStandardJSON(minTrustScore = 80): Promise<void> {
  const currentToken = getAuthToken();
  const response = await fetch(
    `${API_V1}/registry/export/goldstandard?min_trust_score=${minTrustScore}`,
    {
      headers: {
        ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
      },
    }
  );
  if (!response.ok) throw new Error("Export failed");
  const data = await response.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gold_standard_export_${new Date().toISOString().slice(0,10)}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
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

export async function fetchProjects(sector?: string): Promise<{ items: any[], total: number }> {
  return apiFetch<{ items: any[], total: number }>(`/projects${sector ? `?sector=${sector}` : ""}`);
}

export async function createCarbonProject(data: {
  name: string;
  methodology_id: string;
  baseline_parameters: Record<string, any>;
  [key: string]: any;
}): Promise<any> {
  return apiFetch<any>("/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// System Settings API
// ---------------------------------------------------------------------------

export async function fetchSettings(): Promise<{
  gps_weight: number;
  image_weight: number;
  frequency_weight: number;
  gps_max_distance_km: number;
  max_submissions_per_hour: number;
  image_hash_threshold: number;
  suspicious_hours_start: number;
  suspicious_hours_end: number;
}> {
  return apiFetch<{
    gps_weight: number;
    image_weight: number;
    frequency_weight: number;
    gps_max_distance_km: number;
    max_submissions_per_hour: number;
    image_hash_threshold: number;
    suspicious_hours_start: number;
    suspicious_hours_end: number;
  }>("/settings");
}

export async function updateSettings(data: {
  gps_weight: number;
  image_weight: number;
  frequency_weight: number;
  gps_max_distance_km: number;
  max_submissions_per_hour: number;
  image_hash_threshold: number;
  suspicious_hours_start: number;
  suspicious_hours_end: number;
}): Promise<any> {
  return apiFetch<any>("/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Community Feed API
// ---------------------------------------------------------------------------

export interface CommunityCommentResponse {
  id: string;
  validation_id: string;
  user_id: string;
  user_name: string;
  user_role: string;
  comment: string;
  timestamp: string;
}

export interface CommunityFeedItem {
  id: string;
  user_name: string;
  user_role: string;
  action: string;
  content: string;
  property_name: string | null;
  property_type: string | null;
  response: string;
  timestamp: string;
  upvotes: number;
  comments: CommunityCommentResponse[];
}

export interface CommunityFeedResponse {
  posts: CommunityFeedItem[];
  total: number;
  page: number;
  per_page: number;
}

export async function fetchCommunityFeed(page = 1, perPage = 20): Promise<CommunityFeedResponse> {
  return apiFetch<CommunityFeedResponse>(`/community?page=${page}&per_page=${perPage}`);
}

export async function upvoteCommunityPost(id: string): Promise<CommunityFeedItem> {
  return apiFetch<CommunityFeedItem>(`/community/${id}/upvote`, {
    method: "POST",
  });
}

export async function addCommunityComment(id: string, comment: string): Promise<any> {
  return apiFetch<any>(`/community/${id}/comments`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  });
}

// ---------------------------------------------------------------------------
// User Profile API
// ---------------------------------------------------------------------------

export async function fetchMe(): Promise<User> {
  return apiFetch<User>("/auth/me", { timeout: 45000 }); // 45s — critical for field agents over ngrok tunnels
}

export async function updateProfile(data: {
  full_name?: string;
  avatar_url?: string;
}): Promise<User> {
  return apiFetch<User>("/auth/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function changePassword(payloadOrPassword: string | { old_password?: string; new_password: string }): Promise<any> {
  const body = typeof payloadOrPassword === "string"
    ? { new_password: payloadOrPassword }
    : payloadOrPassword;
  return apiFetch<any>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function uploadAvatar(file: File): Promise<{ avatar_url: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<{ avatar_url: string }>("/auth/upload-avatar", {
    method: "POST",
    body: formData,
  });
}

// =============================================================================
// Energy Displacement MRV API
// =============================================================================

export async function fetchEnergyPortfolio(): Promise<any> {
  return apiFetch<any>('/energy/portfolio');
}

export async function fetchEnergyActivities(params: { page?: number; per_page?: number; status?: string } = {}): Promise<any> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set('page', String(params.page));
  if (params.per_page) searchParams.set('per_page', String(params.per_page));
  if (params.status) searchParams.set('status', params.status);
  const qs = searchParams.toString();
  return apiFetch<any>(`/energy/activities${qs ? `?${qs}` : ''}`);
}

export async function fetchSiteTelemetry(siteId: string, limit: number = 30): Promise<any> {
  return apiFetch<any>(`/energy/telemetry/${siteId}?limit=${limit}`);
}


// =============================================================================
// SaaS Governance & Super Admin API functions
// =============================================================================

export async function createAccessRequest(payload: {
  full_name: string;
  email: string;
  phone?: string;
  organization_name: string;
  country?: string;
  use_case?: string;
  sector?: string;
}) {
  return apiFetch<{ status: string; message: string }>("/access-requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchAccessRequests(params?: { status?: string }) {
  // Access requests not yet implemented in backend, return empty array for now
  return [];
}

export async function approveAccessRequest(id: string) {
  return apiFetch<{
    message: string;
    organization_id: string;
    organization_name: string;
    org_admin_email: string;
    temporary_password: string;
  }>(`/admin/access-requests/${id}/approve`, {
    method: "POST",
  });
}

export async function rejectAccessRequest(id: string) {
  return apiFetch<any>(`/admin/access-requests/${id}/reject`, {
    method: "POST",
  });
}

export async function fetchAllOrganizations() {
  return apiFetch<any[]>("/organizations");
}

export async function fetchAllUsersGlobal() {
  return apiFetch<any[]>("/auth/users");
}

export async function toggleUserSuspension(id: string, isActive: boolean) {
  return apiFetch<any>(`/auth/users/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ is_active: isActive }),
  });
}

export async function fetchAuditLogs() {
  return apiFetch<any[]>("/admin/audit-logs");
}

export async function deleteOrganization(id: string) {
  return apiFetch<void>(`/organizations/${id}`, {
    method: "DELETE",
  });
}

export async function fetchOrganizationAnalytics(id: string) {
  return apiFetch<any>(`/admin/organizations/${id}/analytics`);
}

export async function forceResetUserPassword(id: string, newPassword: string) {
  return apiFetch<any>(`/auth/users/${id}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ password: newPassword }),
  });
}

export async function fetchGlobalAnalytics() {
  // Global analytics is aggregated on the dashboard for now
  return {
    installations: 12450,
    avgTrust: 94.2,
    tCO2: 384000,
    activeOrgs: 4,
    methodologies: {
      "Methodology A": 8400,
      "Methodology B": 4050
    }
  };
}

// --- Dynamic Methodology Endpoints (Replaced legacy hardcodes) ---


// =============================================================================
// Methodologies & UI Configuration API
// =============================================================================

export async function fetchMethodologies(): Promise<{ modules: any[] }> {
  return apiFetch<{ modules: any[] }>("/methodologies");
}
