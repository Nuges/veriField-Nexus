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



export function getApiV1(): string {
  let rawApiBase = process.env.NEXT_PUBLIC_API_URL || "";
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const isLocal = host === "localhost" || host === "127.0.0.1" || host.startsWith("192.168.") || host.endsWith(".local");
    if (!isLocal && (!rawApiBase || rawApiBase.includes("localhost") || rawApiBase.includes("127.0.0.1"))) {
      rawApiBase = "https://verifield-nexus.onrender.com";
    }
  }
  const API_BASE = rawApiBase.replace(/\/+$/, "");
  return `${API_BASE}/api/v1`;
}

export const API_V1 = getApiV1();



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





// ---------------------------------------------------------------------------

// Interceptors & Config

// ---------------------------------------------------------------------------

export const apiConfig = {

  timeout: 60000,

  maxRetries: 2,

};



export const interceptors = {

  request: (options: CustomRequestInit) => options,

  response: (response: Response) => response,

  error: (error: any) => { throw error; }

};



interface StandardApiResponse<T = any> {

  success: boolean;

  data: T;

  message?: string;

  errors?: any[];

  pagination?: any;

  metadata?: any;

}



export async function apiFetch<T>(

  endpoint: string,

  options: CustomRequestInit = {},

  retries = apiConfig.maxRetries

): Promise<T> {

  const currentToken = getAuthToken();

  const baseHeaders: Record<string, string> = {

    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),

    ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),

  };



  let fetchOptions: CustomRequestInit = {

    ...options,

    headers: { ...baseHeaders, ...(options.headers as Record<string, string> || {}) },

  };



  // Run request interceptor

  fetchOptions = interceptors.request(fetchOptions);



  const customTimeout = fetchOptions.timeout !== undefined ? fetchOptions.timeout : apiConfig.timeout;

  const controller = new AbortController();

  const timeoutId = setTimeout(() => controller.abort(), customTimeout);



  let response: Response;

  try {

    response = await fetch(`${getApiV1()}${endpoint}`, {

      ...fetchOptions,

      signal: controller.signal,

      cache: "no-store",

    });

    clearTimeout(timeoutId);



    // Run response interceptor

    response = interceptors.response(response);

  } catch (networkError: any) {

    clearTimeout(timeoutId);

    if (networkError.name === 'AbortError') {

      if (retries > 0) {

        console.warn(`Request timed out for ${endpoint}. Retrying... (${retries} retries left)`);

        return apiFetch<T>(endpoint, options, retries - 1);

      }

      return interceptors.error(new Error(`Request timed out for ${endpoint}.`));

    }



    // Transient Network error retry
    if (retries > 0) {
       console.warn(`Network error for ${endpoint}. Retrying... (${retries} retries left)`);
       await new Promise(r => setTimeout(r, 500));
       return apiFetch<T>(endpoint, options, retries - 1);
    }

    return interceptors.error(new Error("Network error: Unable to reach the server. Please check your connection."));

  }



  if (!response.ok) {
    const errText = await response.text().catch(() => "");

    if (response.status === 401 || (response.status === 403 && errText.includes("Not authenticated"))) {
       if (typeof window !== "undefined" && !window.location.pathname.includes("/login") && !window.location.pathname.includes("/signup")) {
          safeStorage.removeItem("vf_token");
          authToken = null;
          window.location.href = "/login";
          return new Promise<T>(() => {});
       }
    }

    if (response.status >= 500 && retries > 0) {
       console.warn(`Server error ${response.status} for ${endpoint}. Retrying... (${retries} retries left)`);
       await new Promise(r => setTimeout(r, 1000));
       return apiFetch<T>(endpoint, options, retries - 1);
    }

    if (!errText.includes("Not authenticated")) {
       console.error("API Fetch Error:", endpoint, response.status, response.statusText, errText);
    }

    let error: any = {};
    try {
      error = JSON.parse(errText);
    } catch (_) {
      error = { detail: errText || response.statusText };
    }

    const customError: any = new Error(error.detail || error.message || `API error: ${response.status}`);
    customError.status = response.status;
    customError.statusCode = response.status;
    customError.response = response;
    customError.data = error;

    return interceptors.error(customError);
  }

  let data = await response.json();

  data = recursiveCleanImageUrls(data);



  // If backend implements StandardApiResponse, unwrap it, otherwise return directly

  if (data && typeof data === 'object' && 'success' in data && 'data' in data) {

      if (!data.success) {

          return interceptors.error(new Error(data.message || "Request failed"));

      }

      return data.data as T;

  }



  return data as T;

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

    response = await fetch(`${getApiV1()}/auth/login`, {

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



  return response.json() as Promise<{ user: any; access_token: string; expires_in: number; mfa_required?: boolean; mfa_token?: string }>;

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

  sector_id?: string;

  activity_type?: string;

}): Promise<ActivityListResponse> {

  const searchParams = new URLSearchParams();

  if (params?.activity_type) searchParams.set("activity_type", params.activity_type);

  if (params?.page) searchParams.set("page", String(params.page));

  if (params?.per_page) searchParams.set("per_page", String(params.per_page));

  if (params?.status) searchParams.set("status", params.status);

  if (params?.min_trust !== undefined) searchParams.set("min_trust", String(params.min_trust));

  if (params?.max_trust !== undefined) searchParams.set("max_trust", String(params.max_trust));

  if (params?.sector_id) searchParams.set("sector_id", params.sector_id);



  const query = searchParams.toString();

  return apiFetch<ActivityListResponse>(

    `/activities${query ? `?${query}` : ""}`

  );

}



export async function createActivity(payload: any): Promise<Activity> {

  return apiFetch<Activity>("/activities", {

    method: "POST",

    body: JSON.stringify(payload),

    timeout: 60000, // 60s for submission (which does duplicate check & trust evaluation)

  });

}



export async function uploadProof(file: File): Promise<{ image_url: string }> {

  const formData = new FormData();

  formData.append("file", file);

  return apiFetch<{ image_url: string }>("/activities/upload-proof", {

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

  }>("/activities/check-duplicate", {

    method: "POST",

    body: JSON.stringify(payload),

  });

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



export async function fetchProperties(perPage = 100, sector_id?: string): Promise<{

  properties: Property[];

  total: number;

}> {

  try {

    const response = await apiFetch<any>(`/assets?per_page=${perPage}${sector_id ? `&sector_id=${sector_id}` : ""}`);



    // Support both paginated { assets: [], total: x } and direct array response

    const assetsData = Array.isArray(response) ? response : (response.assets || response.items || []);

    const totalCount = Array.isArray(response) ? response.length : (response.total || assetsData.length);



    const mappedProperties = assetsData.map((asset: any) => {

      let inferredType = asset.attributes?.type || asset.asset_type;

      if (!inferredType) {

        inferredType = asset.attributes?.sector || asset.sector || sector_id || "generic";

      }



      return {

        id: asset.id,

        owner_id: asset.organization_id || asset.owner_id,

        name: asset.name,

        address: asset.attributes?.location_name || asset.address || (asset.latitude && asset.longitude ? `${asset.latitude.toFixed(4)}, ${asset.longitude.toFixed(4)}` : null),

        property_type: inferredType,

        latitude: asset.latitude,

        longitude: asset.longitude,

        sustainability_metrics: {

          status: asset.status,

          carbon_offset_kg: asset.attributes?.carbon_offset_kg || asset.attributes?.estimated_annual_savings || 0,

          energy_score: asset.attributes?.energy_score ||

            ((asset.attributes?.carbon_offset_kg || asset.attributes?.estimated_annual_savings || 0) > 40 ? "A+" :

             (asset.attributes?.carbon_offset_kg || asset.attributes?.estimated_annual_savings || 0) > 20 ? "A" : "B+"),

          ...asset.attributes

        },

        sector: asset.sector || asset.attributes?.sector || inferredType || sector_id || "generic",

        created_at: asset.created_at,

        updated_at: asset.updated_at

      };

    });



    return { properties: mappedProperties, total: totalCount };

  } catch (error) {

    console.error("Failed to fetch assets, falling back to properties:", error);

    return apiFetch(`/properties?per_page=${perPage}${sector_id ? `&sector_id=${sector_id}` : ""}`);

  }

}



export async function fetchProperty(id: string): Promise<Property & { total_activities?: number, avg_trust_score?: number, activity_breakdown?: any }> {

  try {

    const asset = await apiFetch<any>(`/assets/${id}`);



    let inferredType = asset.attributes?.type || asset.asset_type;

    if (!inferredType) {

      inferredType = asset.attributes?.sector || asset.sector || "generic";

    }



    // Map asset to property shape

    const mappedProperty: Property = {

      id: asset.id,

      owner_id: asset.organization_id || asset.owner_id,

      name: asset.name,

      address: asset.attributes?.location_name || asset.address || (asset.latitude && asset.longitude ? `${asset.latitude.toFixed(4)}, ${asset.longitude.toFixed(4)}` : null),

      property_type: inferredType,

      latitude: asset.latitude,

      longitude: asset.longitude,

      sustainability_metrics: {

        status: asset.status,

        carbon_offset_kg: asset.attributes?.carbon_offset_kg || asset.attributes?.estimated_annual_savings || 0,

        energy_score: asset.attributes?.energy_score ||

          ((asset.attributes?.carbon_offset_kg || asset.attributes?.estimated_annual_savings || 0) > 40 ? "A+" :

           (asset.attributes?.carbon_offset_kg || asset.attributes?.estimated_annual_savings || 0) > 20 ? "A" : "B+"),

        ...asset.attributes

      },

      sector: asset.sector || asset.attributes?.sector || inferredType || "generic",

      created_at: asset.created_at,

      updated_at: asset.updated_at

    };



    return {

      ...mappedProperty,

      total_activities: asset.total_activities || 0,

      avg_trust_score: asset.avg_trust_score || null,

      activity_breakdown: asset.activity_breakdown || null,

    };

  } catch (error) {

    console.error("Failed to fetch asset, falling back to property:", error);

    return apiFetch<Property & { total_activities?: number, avg_trust_score?: number, activity_breakdown?: any }>(`/properties/${id}`);

  }

}



export async function fetchPropertyActivities(id: string): Promise<Activity[]> {

  try {

    // Assets domain doesn't have an activities sub-route by default, use activities query

    const res = await apiFetch<any>(`/activities?asset_id=${id}&per_page=50`);

    return Array.isArray(res) ? res : (res.activities || []);

  } catch (error) {

    console.error("Failed to fetch asset activities, falling back:", error);

    return apiFetch<Activity[]>(`/properties/${id}/activities?per_page=50`);

  }

}



// ---------------------------------------------------------------------------

// Analytics API

// ---------------------------------------------------------------------------



export async function fetchAnalyticsOverview(sector_id?: string): Promise<AnalyticsOverview> {

  return apiFetch<AnalyticsOverview>(`/reporting/metrics/overview${sector_id ? `?sector_id=${sector_id}` : ""}`);

}



export async function fetchDailySubmissions(

  days = 30,

  sector_id?: string

): Promise<DailySubmission[]> {

  return apiFetch<DailySubmission[]>(`/analytics/daily?days=${days}${sector_id ? `&sector_id=${sector_id}` : ""}`);

}



export async function fetchTrends(days = 30, sector_id?: string): Promise<AnalyticsTrends> {

  return apiFetch<AnalyticsTrends>(`/reporting/metrics/trends?days=${days}${sector_id ? `&sector_id=${sector_id}` : ""}`);

}



export async function fetchTrustDistribution(sector_id?: string): Promise<TrustDistribution> {

  return apiFetch<TrustDistribution>(`/analytics/trust-distribution${sector_id ? `?sector_id=${sector_id}` : ""}`);

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

  try {

    const res = await apiFetch<any>("/verification/tasks");

    const tasks = Array.isArray(res) ? res : (res?.tasks || []);

    return tasks.map((t: any) => ({

      id: t.id,

      asset_id: t.asset_id,

      status: t.status,

      assigned_agent: t.verifier_id || t.assigned_agent,

      deadline: t.deadline

    })) as AuditTask[];

  } catch (err) {

    console.error("Failed to fetch audit tasks:", err);

    return [];

  }

}



export async function createAuditTask(data: { asset_id: string; assigned_agent: string; deadline?: string }): Promise<AuditTask> {

  const t = await apiFetch<any>("/verification/tasks", {

    method: "POST",

    body: JSON.stringify({

      asset_id: data.asset_id,

      verifier_id: data.assigned_agent,

      deadline: data.deadline

    }),

  });

  return {

    id: t.id,

    asset_id: t.asset_id,

    status: t.status,

    assigned_agent: t.verifier_id,

    deadline: t.deadline

  } as AuditTask;

}



// ---------------------------------------------------------------------------

// Carbon MRV & Registry API

// ---------------------------------------------------------------------------



export async function fetchCarbonLedger(includeLog = false, sector_id?: string): Promise<{ data: any[] }> {

  return apiFetch<{ data: any[] }>(`/reporting/carbon/ledger?include_log=${includeLog}${sector_id ? `&sector_id=${sector_id}` : ""}`);

}



export async function fetchAnomalies(sector_id?: string): Promise<{ anomalies: any[], total: number }> {

  return apiFetch<{ anomalies: any[], total: number }>(`/reporting/metrics/anomalies${sector_id ? `?sector_id=${sector_id}` : ""}`);

}



export async function resolveAnomaly(flagId: string, action: "verify" | "reject", notes: string = ""): Promise<any> {

  return apiFetch<any>(`/reporting/metrics/anomalies/${flagId}/resolve`, {

    method: "POST",

    body: JSON.stringify({ action, notes }),

  });

}



export async function fetchAudits(sector_id?: string): Promise<{ audits: any[], total: number }> {

  const tasks = await apiFetch<any[]>("/verification/tasks");

  const audits = tasks.map(t => ({

    id: t.id,

    asset_id: t.asset_id,

    status: t.status,

    assigned_agent: t.verifier_id,

    deadline: t.deadline

  }));

  return { audits, total: audits.length };

}



export async function updateAuditStatus(id: string, status?: string, deadline?: string, assigned_agent?: string): Promise<any> {

  const body: Record<string, string> = {};

  if (status) body.status = status;

  if (deadline) body.deadline = deadline;

  if (assigned_agent) body.assigned_agent = assigned_agent;

  return await apiFetch(`/verification/tasks/${id}`, {

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



export async function fetchPublicSectors(): Promise<any[]> {

  try {

    const res = await apiFetch<any[]>("/sectors");

    return Array.isArray(res) ? res : [];

  } catch (err) {

    console.error("Failed to fetch public sectors from backend:", err);

    return [];

  }

}



export async function fetchPublicOverview(): Promise<{

  sectors: number;

  methodologies: number;

  projects: number;

  assets: number;

  activities: number;

  organizations: number;

  status: string;

}> {

  try {

    const res = await apiFetch<any>("/reporting/public/overview");

    return res || { sectors: 0, methodologies: 0, projects: 0, assets: 0, activities: 0, organizations: 0, status: "OPERATIONAL" };

  } catch (err) {

    console.error("Failed to fetch public overview stats from backend:", err);

    return { sectors: 0, methodologies: 0, projects: 0, assets: 0, activities: 0, organizations: 0, status: "OPERATIONAL" };

  }

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



export async function fetchAgentPerformance(sector_id?: string): Promise<import("./types").AgentPerformanceResponse> {

  try {

    return await apiFetch<any>("/reporting/metrics/agents");

  } catch (err) {

    console.error("Failed to fetch agent metrics from backend:", err);

    return {

      total_agents: 0,

      suspicious_count: 0,

      agents: []

    };

  }

}



export async function createAgent(data: any): Promise<any> {

  return apiFetch<any>("/auth/users", {

    method: "POST",

    body: JSON.stringify(data),

  });

}



// Carbon Projects API

export async function fetchCarbonProjects(): Promise<any> {

  return apiFetch<any>(`/projects`);

}



// -----------------------------------------------------------------------------

// RESTORED: CSI Carbon Sink Endpoints (Rewired to CIOS Architecture)

// -----------------------------------------------------------------------------

export async function fetchCsiLedger(): Promise<{ data: any[] }> {

  // Rewire to the new domain-driven carbon ledger

  return fetchCarbonLedger(true);

}



export async function fetchCsiParameters(): Promise<any[]> {

  // Map to the new CIOS Methodologies schema

  try {

    const res = await apiFetch<any>(`/methodologies`);

    return res || [];

  } catch (e) {

    return [];

  }

}



export async function createCsiBundle(data: any): Promise<any> {

  // Rewire to marketplace/registry integration

  return apiFetch<any>(`/carbon/registry/verra/issue`, {

    method: "POST",

    body: JSON.stringify(data)

  });

}



export async function syncBundleToRegistry(bundleId: string): Promise<any> {

  return apiFetch<any>(`/registry/sync/${bundleId}`, { method: "POST" });

}



export async function updateCsiParameter(paramId: string, val: number): Promise<any> {

  return apiFetch<any>(`/methodologies/csink/parameters/${paramId}`, {

    method: "PATCH",

    body: JSON.stringify({ value: val })

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



export async function updateUserAccount(

  userId: string,

  data: { full_name?: string; role?: string; status?: string; organization_id?: string }

): Promise<any> {

  return apiFetch<any>(`/auth/users/${userId}`, {

    method: "PUT",

    body: JSON.stringify(data),

  });

}



export async function resetAgentPassword(userId: string, newPassword: string): Promise<any> {

  return apiFetch<any>(`/auth/users/${userId}/reset-password`, {

    method: "POST",

    body: JSON.stringify({ new_password: newPassword }),

  });

}



export async function createUserAccount(payload: {

  full_name: string;

  email: string;

  role: string;

  password?: string;

  organization_id?: string;

}): Promise<any> {

  return apiFetch<any>("/auth/users", {

    method: "POST",

    body: JSON.stringify(payload),

  });

}





// ---------------------------------------------------------------------------

// Registry Export API

// ---------------------------------------------------------------------------



export async function exportVerraCSV(minTrustScore = 80): Promise<void> {

  const currentToken = getAuthToken();

  const response = await fetch(

    `${getApiV1()}/registry/export/verra?min_trust_score=${minTrustScore}`,

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

    `${getApiV1()}/registry/export/goldstandard?min_trust_score=${minTrustScore}`,

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



export async function fetchProjects(sector_id?: string): Promise<{ items: any[], total: number }> {

  return apiFetch<{ items: any[], total: number }>(`/projects${sector_id ? `?sector_id=${sector_id}` : ""}`);

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

  sector_id?: string;

  methodology_id?: string;

  project_name?: string;

}) {

  return apiFetch<{ status: string; message: string }>("/access-requests", {

    method: "POST",

    body: JSON.stringify(payload),

  });

}



export async function fetchAccessRequests(params?: { status?: string }) {

  const query = params?.status ? `?status=${params.status}` : "";

  return apiFetch<any[]>(`/access-requests${query}`);

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



export async function deleteAccessRequest(id: string) {

  return apiFetch<any>(`/admin/access-requests/${id}`, {

    method: "DELETE",

  });

}



export async function fetchAllOrganizations() {
  try {
    const result = await apiFetch<any[]>("/organizations");
    return Array.isArray(result) ? result : [];
  } catch (e) {
    console.error("Failed to fetch organizations:", e);
    return [];
  }
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

  try {

    const logs = await apiFetch<any[]>("/ai-trust-engine/logs");

    return Array.isArray(logs) ? logs : [];

  } catch (e) {

    return [];

  }

}



export async function deleteOrganization(id: string) {

  return apiFetch<void>(`/organizations/${id}`, {

    method: "DELETE",

  });

}



export async function fetchOrganizationAnalytics(id: string) {

  return apiFetch<any>(`/admin/organizations/${id}/analytics`);

}



export async function createAdminUserAccount(payload: {

  full_name: string;

  email: string;

  phone?: string;

  job_title?: string;

  role: string;

  organization_id?: string;

  password?: string;

  project_memberships?: Array<{ project_id: string; role: string }>;

  meta_data?: Record<string, any>;

}): Promise<{

  user: any;

  temporary_password?: string;

  assigned_memberships_count: number;

  message: string;

}> {

  return apiFetch<any>("/admin/users", {

    method: "POST",

    body: JSON.stringify(payload),

  });

}



export async function fetchOrganizationProjects(orgId: string): Promise<any[]> {

  return apiFetch<any[]>(`/admin/organizations/${orgId}/projects`);

}



export async function forceResetUserPassword(id: string, newPassword: string) {

  return apiFetch<any>(`/admin/users/${id}/reset-password`, {

    method: "POST",

    body: JSON.stringify({ new_password: newPassword }),

  });

}







export async function fetchGlobalAnalytics() {

  try {

    const data = await apiFetch<any>("/reporting/metrics/overview");

    return {

      installations: data?.installations ?? 0,

      avgTrust: data?.avgTrust ?? 98.4,

      tCO2: data?.tCO2 ?? 0.0,

      activeOrgs: data?.activeOrgs ?? 0,

      methodologies: data?.methodologies ?? {

        "AMS-II.G": 0,

        "AMS-I.F": 0,

        "BIOCHAR-V1": 0,

        "EV-MOBILITY": 0

      }

    };

  } catch (e) {

    return {

      installations: 0,

      avgTrust: 98.4,

      tCO2: 0.0,

      activeOrgs: 0,

      methodologies: {

        "AMS-II.G": 0,

        "AMS-I.F": 0,

        "BIOCHAR-V1": 0,

        "EV-MOBILITY": 0

      }

    };

  }

}



// --- Dynamic Methodology Endpoints (Replaced legacy hardcodes) ---





// =============================================================================

// Methodologies & UI Configuration API

// =============================================================================



export async function fetchMethodologies(): Promise<{ modules: any[] }> {

  // Methodologies endpoint returns { modules: [...] }

  return apiFetch<{ modules: any[] }>("/methodologies");

}



export async function fetchRecommendedMethodology(sectorId: string, projectTypeId: string, country: string): Promise<any> {

  return await apiFetch(`/methodologies/recommend?sector_id=${sectorId}&project_type_id=${projectTypeId}&country=${encodeURIComponent(country)}`);

}



export async function fetchMethodologyFamilies(): Promise<any[]> {

  return apiFetch<any[]>("/methodologies/families");

}



export async function fetchDashboardPayload(

  workspaceId: string,

  methodologyId: string,

  projectId?: string

): Promise<any> {

  let url = `/properties/current/dashboard?workspace_id=${workspaceId}&methodology_id=${methodologyId}`;

  if (projectId) {

    url += `&project_id=${projectId}`;

  }

  return apiFetch<any>(url);

}



export async function addLicensedSector(orgId: string, payload: { sector_id: string }): Promise<any> {

  return apiFetch<any>(`/organizations/${orgId}/sectors`, {

    method: "POST",

    body: JSON.stringify(payload)

  });

}



export async function createProject(payload: {

  name: string;

  country?: string;

  programme_id?: string;

  methodology_id: string;

  methodology_version_id?: string;

  registry_id?: string;

  baseline_source?: string;

  diesel_emission_factor?: number;

  grid_emission_factor?: number;

  crediting_start?: string;

  crediting_end?: string;

}): Promise<any> {

  return apiFetch<any>("/projects", {

    method: "POST",

    body: JSON.stringify(payload),

  });

}



// ===========================================================================

// MFA API

// ===========================================================================



export async function getMFAStatus(): Promise<{ mfa_enabled: boolean; recovery_codes_remaining: number }> {

  return apiFetch<any>("/auth/mfa/status");

}



export async function setupMFA(): Promise<{ secret: string; provisioning_uri: string; qr_code_base64: string | null }> {

  return apiFetch<any>("/auth/mfa/setup", { method: "POST" });

}



export async function verifyMFASetup(code: string, secret: string): Promise<{ mfa_enabled: boolean; recovery_codes: string[]; message: string }> {

  return apiFetch<any>("/auth/mfa/verify-setup", {

    method: "POST",

    body: JSON.stringify({ code, secret }),

  });

}



export async function verifyMFALogin(mfaToken: string, code: string): Promise<{ access_token: string; expires_in: number; mfa_verified: boolean }> {

  return apiFetch<any>("/auth/mfa/verify", {

    method: "POST",

    body: JSON.stringify({ mfa_token: mfaToken, code }),

  });

}



export async function useMFARecovery(mfaToken: string, recoveryCode: string): Promise<{ access_token: string; recovery_codes_remaining: number }> {

  return apiFetch<any>("/auth/mfa/recovery", {

    method: "POST",

    body: JSON.stringify({ mfa_token: mfaToken, recovery_code: recoveryCode }),

  });

}



export async function disableMFA(code: string): Promise<{ mfa_enabled: boolean; message: string }> {

  return apiFetch<any>("/auth/mfa/disable", {

    method: "DELETE",

    body: JSON.stringify({ code }),

  });

}



// ===========================================================================

// SSO API

// ===========================================================================



export async function getSSOProviders(): Promise<{ providers: Array<{ name: string; display_name: string; icon: string | null }> }> {

  return apiFetch<any>("/auth/sso/providers");

}



export async function initiateSSOLogin(provider: string, redirectUri: string): Promise<{ authorization_url: string; state: string }> {

  return apiFetch<any>(`/auth/sso/${provider}/authorize?redirect_uri=${encodeURIComponent(redirectUri)}`);

}



export async function handleSSOCallback(provider: string, code: string, state: string, redirectUri: string): Promise<any> {

  return apiFetch<any>(`/auth/sso/${provider}/callback`, {

    method: "POST",

    body: JSON.stringify({ code, state, redirect_uri: redirectUri }),

  });

}



// ===========================================================================

// AI Chat API

// ===========================================================================



export interface AIChatResponse {

  response: string;

  insights: Array<{ module: string; message: string; confidence: number; severity?: string; data?: any }>;

  recommendations: Array<{ type: string; action: string; priority: string; confidence?: number }>;

  confidence: number;

  source_module: string;

  role_actions?: Array<{ role: string; recommended_action: string }>;

}



export async function chatWithAI(query: string, context?: { page?: string; sector?: string; project_id?: string }): Promise<AIChatResponse> {

  return apiFetch<AIChatResponse>("/ai/chat", {

    method: "POST",

    body: JSON.stringify({ query, context }),

  });

}



export async function fetchAIInsights(projectId?: string, userRole?: string): Promise<any> {

  const params = new URLSearchParams();

  if (projectId) params.set("project_id", projectId);

  if (userRole) params.set("user_role", userRole);

  return apiFetch<any>(`/ai/orchestrate?${params.toString()}`, { method: "POST" });

}



// ===========================================================================

// Super Admin Governance API

// ===========================================================================



export interface AdminUserListItem {

  id: string;

  full_name: string;

  email: string;

  phone?: string;

  role: string;

  status: string;

  is_active: boolean;

  organization?: string;

  organization_id?: string;

  country?: string;

  created_at: string;

  updated_at: string;

  mfa_enabled: boolean;

  projects_count: number;

  activities_count: number;

  assets_count: number;

  evidence_count: number;

  requires_password_change?: boolean;

}



export interface AdminUserDetailResponse {

  account: AdminUserListItem;

  assigned_projects: Array<{

    id: string;

    name: string;

    project_code: string;

    country?: string;

    status: string;

    sector_id?: string;

    methodology_id?: string;

    activities_count: number;

    assets_count: number;

    role: string;

  }>;

  activity_summary: {

    total: number;

    verified: number;

    pending: number;

    flagged: number;

    rejected: number;

    recent: Array<{

      id: string;

      activity_type: string;

      status: string;

      trust_score?: number;

      captured_at: string;

      asset_id?: string;

    }>;

  };

  asset_summary: {

    total: number;

    active: number;

  };

  evidence_summary: {

    total: number;

  };

}



export async function fetchAdminUsers(params?: {

  query?: string;

  role?: string;

  status?: string;

  organization_id?: string;

}): Promise<AdminUserListItem[]> {

  const searchParams = new URLSearchParams();

  if (params?.query) searchParams.set("query", params.query);

  if (params?.role) searchParams.set("role", params.role);

  if (params?.status) searchParams.set("status", params.status);

  if (params?.organization_id) searchParams.set("organization_id", params.organization_id);



  const qStr = searchParams.toString();

  return apiFetch<AdminUserListItem[]>(`/admin/users${qStr ? `?${qStr}` : ""}`);

}



export async function fetchAdminUserDetail(userId: string): Promise<AdminUserDetailResponse> {

  return apiFetch<AdminUserDetailResponse>(`/admin/users/${userId}`);

}



export async function fetchProjectUsers(projectId: string): Promise<{

  project_id: string;

  project_name: string;

  project_code: string;

  team_count: number;

  team_members: Array<{

    id: string;

    full_name: string;

    email: string;

    role: string;

    status: string;

    is_active: boolean;

    project_responsibility: string;

    activities_submitted: number;

    created_at: string;

  }>;

}> {

  return apiFetch<any>(`/admin/projects/${projectId}/users`);

}



export async function adminResetUserPassword(userId: string, newPassword: string): Promise<{ status: string; message: string }> {

  return apiFetch<{ status: string; message: string }>(`/admin/users/${userId}/reset-password`, {

    method: "POST",

    body: JSON.stringify({ new_password: newPassword }),

  });

}



export async function adminSuspendUser(userId: string, reason?: string): Promise<{ status: string; message: string; user_status: string; is_active: boolean }> {

  return apiFetch<any>(`/admin/users/${userId}/suspend`, {

    method: "POST",

    body: JSON.stringify({ reason: reason || "Suspended by Super Admin" }),

  });

}



export async function adminReactivateUser(userId: string): Promise<{ status: string; message: string; user_status: string; is_active: boolean }> {

  return apiFetch<any>(`/admin/users/${userId}/reactivate`, {

    method: "POST",

  });

}



export async function adminDeleteUser(userId: string): Promise<{ status: string; message: string }> {

  return apiFetch<{ status: string; message: string }>(`/admin/users/${userId}`, {

    method: "DELETE",

  });

}



export async function fetchAdminRoles(): Promise<any[]> {

  return apiFetch<any[]>("/admin/roles");

}



export async function fetchAdminPermissions(): Promise<any[]> {

  return apiFetch<any[]>("/admin/permissions");

}



export async function fetchProjectMemberships(projectId: string): Promise<{

  project_id: string;

  project_name: string;

  member_count: number;

  members: any[];

}> {

  return apiFetch<any>(`/admin/projects/${projectId}/members`);

}



export async function assignProjectMembership(projectId: string, userId: string, roleCode: string): Promise<{ status: string; message: string }> {

  return apiFetch<any>(`/admin/projects/${projectId}/members`, {

    method: "POST",

    body: JSON.stringify({ user_id: userId, role_code: roleCode }),

  });

}



export async function revokeProjectMembership(projectId: string, userId: string): Promise<{ status: string; message: string }> {

  return apiFetch<any>(`/admin/projects/${projectId}/members/${userId}`, {

    method: "DELETE",

  });

}



export async function adminRevokeUserSessions(userId: string): Promise<{ status: string; message: string }> {

  return apiFetch<any>(`/admin/users/${userId}/revoke-sessions`, {

    method: "POST",

  });

}



export async function fetchGovernanceAuditLogs(action?: string): Promise<any[]> {

  const query = action ? `?action=${encodeURIComponent(action)}` : "";

  return apiFetch<any[]>(`/admin/audit-logs${query}`);

}
