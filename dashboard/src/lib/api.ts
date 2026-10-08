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
  Project,
  Organization,
  AuditFinding,
  LedgerTransaction,
  CarbonMintResponse,
  StandardApiResponse,
  VerificationTask,
  VerificationTasksResponse,
} from "./types";

export type { CarbonMintResponse, LedgerTransaction, Project, VerificationTask, VerificationTasksResponse };

import { safeStorage } from "./storage";
import { resolveCanonicalSectorLabel } from "./sectors";



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
  if (!rawApiBase) {
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      const isLocal = host === "localhost" || host === "127.0.0.1" || host.startsWith("192.168.") || host.endsWith(".local");
      if (isLocal) {
        rawApiBase = "http://localhost:8000";
      } else {
        rawApiBase = "https://verifield-nexus.onrender.com";
      }
    } else {
      rawApiBase = process.env.BACKEND_API_URL || "http://localhost:8000";
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



function recursiveCleanImageUrls<T>(obj: T): T {
  if (obj === null || obj === undefined) return obj;
  if (typeof obj === "string") {
    return cleanImageUrl(obj) as unknown as T;
  }
  if (Array.isArray(obj)) {
    return obj.map((item) => recursiveCleanImageUrls(item)) as unknown as T;
  }
  if (typeof obj === "object") {
    const record = obj as Record<string, unknown>;
    const cleaned: Record<string, unknown> = {};
    for (const key in record) {
      if (Object.prototype.hasOwnProperty.call(record, key)) {
        cleaned[key] = recursiveCleanImageUrls(record[key]);
      }
    }
    return cleaned as unknown as T;
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
  error: (error: unknown) => { throw error; }
};



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

    let errorDetailMsg = "";
    if (typeof error.detail === "string") {
      errorDetailMsg = error.detail;
    } else if (Array.isArray(error.detail)) {
      errorDetailMsg = error.detail.map((e: any) => e.msg || e.detail || (typeof e === "string" ? e : JSON.stringify(e))).join("; ");
    } else if (error.detail && typeof error.detail === "object") {
      errorDetailMsg = error.detail.message || error.detail.msg || JSON.stringify(error.detail);
    } else if (typeof error.message === "string") {
      errorDetailMsg = error.message;
    }

    const customError: any = new Error(errorDetailMsg || `API error: ${response.status}`);
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
  password?: string;
  full_name: string;
  organization_name?: string;
  sector?: string;
  country?: string;
  project_type?: string;
}) {
  return apiFetch<{ user: any; access_token: string; expires_in: number }>(
    "/auth/signup",
    {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        password: payload.password,
        full_name: payload.full_name,
        organization: payload.organization_name,
        country: payload.country,
      }),
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
  project_id?: string;
}): Promise<ActivityListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.activity_type) searchParams.set("activity_type", params.activity_type);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.status) searchParams.set("status", params.status);
  if (params?.min_trust !== undefined) searchParams.set("min_trust", String(params.min_trust));
  if (params?.max_trust !== undefined) searchParams.set("max_trust", String(params.max_trust));
  if (params?.sector_id) searchParams.set("sector_id", params.sector_id);
  if (params?.project_id) searchParams.set("project_id", params.project_id);

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

        organization_id: asset.organization_id || null,

        project_id: asset.project_id || null,

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

      organization_id: asset.organization_id || null,

      project_id: asset.project_id || null,

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
    const res = await apiFetch<any>(`/activities?property_id=${id}&per_page=50`);
    if (Array.isArray(res)) return res;
    if (res && Array.isArray(res.activities)) return res.activities;
    // Fallback query with asset_id if no property_id match
    const assetRes = await apiFetch<any>(`/activities?asset_id=${id}&per_page=50`);
    return Array.isArray(assetRes) ? assetRes : (assetRes?.activities || []);
  } catch (error) {
    console.error("Failed to fetch property activities:", error);
    return [];
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
  const registryType = params.format === "json" ? "goldstandard" : "verra";
  return apiFetch(`/registry/export/${registryType}?min_trust_score=${params.min_trust_score || 80}`);
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



export async function fetchVerificationTasks(params?: {
  status?: string;
  page?: number;
  per_page?: number;
}): Promise<VerificationTasksResponse> {
  try {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    const qs = q.toString() ? `?${q.toString()}` : "";
    const res = await apiFetch<VerificationTasksResponse | VerificationTask[]>(`/verification/tasks${qs}`);
    if (Array.isArray(res)) {
      return {
        tasks: res,
        audits: res,
        total: res.length,
        page: 1,
        per_page: res.length,
      };
    }
    const taskList = Array.isArray(res?.tasks) ? res.tasks : (Array.isArray(res?.audits) ? res.audits : []);
    return {
      tasks: taskList,
      audits: taskList,
      total: typeof res?.total === "number" ? res.total : taskList.length,
      page: res?.page ?? 1,
      per_page: res?.per_page ?? 50,
    };
  } catch (err) {
    console.error("Failed to fetch verification tasks:", err);
    return { tasks: [], audits: [], total: 0, page: 1, per_page: 50 };
  }
}

export async function fetchMyAuditTasks(): Promise<AuditTask[]> {
  try {
    const res = await fetchVerificationTasks();
    return res.tasks.map((t: any) => ({
      id: t.id,
      asset_id: t.asset_id,
      status: t.status,
      assigned_agent: t.verifier_id || t.assigned_agent,
      deadline: t.deadline,
      created_at: t.created_at || "",
      property_name: t.property_name,
      property_address: t.property_address,
      property_type: t.property_type,
      agent_name: t.agent_name,
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
  try {
    const res = await fetchVerificationTasks();
    const audits = res.tasks.map((t: any) => ({
      id: t.id,
      asset_id: t.asset_id,
      status: t.status,
      assigned_agent: t.verifier_id || t.assigned_agent,
      deadline: t.deadline,
      created_at: t.created_at || "",
      property_name: t.property_name,
      property_address: t.property_address,
      property_type: t.property_type,
      agent_name: t.agent_name,
    }));
    return { audits, total: res.total };
  } catch (err) {
    console.error("Failed to fetch audits:", err);
    return { audits: [], total: 0 };
  }
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
  return {
    status: "pending",
    detail: "Verra VCS direct automated API issuance is pending external credential configuration. Please download the certified CSV export for registry portal deposit."
  };
}

export async function issueGoldStandardCredits(): Promise<any> {
  return {
    status: "pending",
    detail: "Gold Standard direct automated API issuance is pending external credential configuration. Please download the certified JSON export for registry portal deposit."
  };
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
  return updateActivityStatus(id, "verified");
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
  return apiFetch<any>(`/marketplace/listings`, {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export async function syncBundleToRegistry(bundleId: string): Promise<any> {
  return apiFetch<any>(`/registry/sync/${bundleId}`, { method: "POST" });
}

export async function updateCsiParameter(paramId: string, val: number): Promise<any> {
  return apiFetch<any>(`/csink/parameters/${paramId}`, {
    method: "PATCH",
    body: JSON.stringify({ value: val })
  });
}



export async function fetchUsers(): Promise<User[]> {
  return apiFetch<User[]>("/auth/users");
}

export async function updateAgentStatus(userId: string, status: "active" | "suspended" | "revoked"): Promise<User> {
  return apiFetch<User>(`/auth/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

export async function updateUserAccount(
  userId: string,
  data: { full_name?: string; role?: string; status?: string; organization_id?: string }
): Promise<User> {
  return apiFetch<User>(`/auth/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function resetAgentPassword(userId: string, newPassword: string): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>(`/auth/users/${userId}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ password: newPassword, new_password: newPassword }),
  });
}

export async function createUserAccount(payload: {
  full_name: string;
  email: string;
  role: string;
  password?: string;
  organization_id?: string;
}): Promise<User> {
  return apiFetch<User>("/auth/users", {
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
// Document Intelligence & PDD API
// ---------------------------------------------------------------------------

export async function uploadProjectDocument(
  projectId: string,
  formData: FormData
): Promise<{ document: any; message: string; processing_status: string }> {
  const currentToken = getAuthToken();
  const response = await fetch(`${getApiV1()}/projects/${projectId}/documents`, {
    method: "POST",
    headers: {
      ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
    },
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchProjectDocuments(projectId: string): Promise<any[]> {
  return apiFetch<any[]>(`/projects/${projectId}/documents`);
}

export async function fetchDocumentDetails(documentId: string): Promise<any> {
  return apiFetch<any>(`/documents/${documentId}`);
}

export async function fetchDocumentFraudFlags(documentId: string): Promise<any[]> {
  return apiFetch<any[]>(`/documents/${documentId}/fraud-flags`);
}

export async function downloadDocument(documentId: string, customFilename?: string): Promise<void> {
  const currentToken = getAuthToken();
  const response = await fetch(`${getApiV1()}/documents/${documentId}/download`, {
    headers: {
      ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
    },
  });

  if (!response.ok) throw new Error("Document download failed");

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = customFilename || "document.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function generateAndDownloadReport(orgId: string, projectId?: string, title?: string): Promise<void> {
  // 1. Create Report
  const report = await apiFetch<any>("/reporting/", {
    method: "POST",
    body: JSON.stringify({
      org_id: orgId,
      title: title || "Verified Project Carbon Ledger & MRV Report",
      report_type: "MRV_CARBON_LEDGER",
      parameters: { project_id: projectId },
    }),
  });

  if (!report || !report.id) {
    throw new Error("Failed to initialize report generation.");
  }

  // 2. Poll for completion
  let attempts = 0;
  while (attempts < 15) {
    await new Promise((r) => setTimeout(r, 600));
    const updated = await apiFetch<any>(`/reporting/?org_id=${orgId}`);
    const found = Array.isArray(updated) ? updated.find((r: any) => r.id === report.id) : null;
    if (found && found.status === "COMPLETED") {
      // 3. Download physical PDF
      const currentToken = getAuthToken();
      const res = await fetch(`${getApiV1()}/reporting/${report.id}/download`, {
        headers: { ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}) },
      });
      if (!res.ok) throw new Error("Report download failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const cleanTitle = (title || "mrv_report").toLowerCase().replace(/[^a-z0-9]+/g, "_");
      a.download = `${cleanTitle}_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      return;
    }
    if (found && found.status === "FAILED") {
      throw new Error("Report generation failed on backend.");
    }
    attempts++;
  }
  throw new Error("Report generation timed out. Please try again.");
}

export async function fetchRegistryPackage(registryType: string, projectId: string): Promise<any> {
  return apiFetch<any>(`/registry/package/${registryType}/${projectId}`);
}


// Sensor Devices API

// ---------------------------------------------------------------------------



export async function fetchSensorDevices(): Promise<{ devices: any[]; total: number }> {

  return apiFetch<{ devices: any[]; total: number }>("/sensors/devices");

}



// ---------------------------------------------------------------------------

// Carbon Projects API

// ---------------------------------------------------------------------------



export async function fetchProjectTotal(projectId: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${projectId}`);
}

export async function fetchProjects(sector_id?: string): Promise<{ items: Project[], total: number }> {
  return apiFetch<{ items: Project[], total: number }>(`/projects${sector_id ? `?sector_id=${sector_id}` : ""}`);
}

export async function createCarbonProject(data: {
  name: string;
  methodology_id: string;
  baseline_parameters: Record<string, unknown>;
  [key: string]: unknown;
}): Promise<Project> {
  return apiFetch<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}



// ---------------------------------------------------------------------------

// System Settings API

// ---------------------------------------------------------------------------



export async function fetchSettings(sectorId?: string): Promise<{
  gps_weight: number;
  image_weight: number;
  frequency_weight: number;
  gps_max_distance_km: number;
  max_submissions_per_hour: number;
  image_hash_threshold: number;
  suspicious_hours_start: number;
  suspicious_hours_end: number;
  organization_id?: string;
  sector_id?: string;
}> {
  const query = sectorId ? `?sector_id=${encodeURIComponent(sectorId)}` : "";
  return apiFetch<{
    gps_weight: number;
    image_weight: number;
    frequency_weight: number;
    gps_max_distance_km: number;
    max_submissions_per_hour: number;
    image_hash_threshold: number;
    suspicious_hours_start: number;
    suspicious_hours_end: number;
    organization_id?: string;
    sector_id?: string;
  }>(`/settings${query}`);
}

export async function updateSettings(data: {
  gps_weight?: number;
  image_weight?: number;
  frequency_weight?: number;
  gps_max_distance_km?: number;
  max_submissions_per_hour?: number;
  image_hash_threshold?: number;
  suspicious_hours_start?: number;
  suspicious_hours_end?: number;
  sector_id?: string;
}, sectorId?: string): Promise<any> {
  const query = sectorId ? `?sector_id=${encodeURIComponent(sectorId)}` : "";
  return apiFetch<any>(`/settings${query}`, {
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
  return fetchActivities({
    ...params,
    activity_type: "SOLAR_GENERATION",
  });
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
  const list = await apiFetch<any[]>(`/access-requests${query}`);
  if (Array.isArray(list)) {
    return list.map((req) => ({
      ...req,
      sector_name: resolveCanonicalSectorLabel(req),
    }));
  }
  return list;
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



export async function deleteAccessRequest(id: string): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>(`/admin/access-requests/${id}`, {
    method: "DELETE",
  });
}

export async function fetchAllOrganizations(): Promise<Organization[]> {
  try {
    const result = await apiFetch<Organization[]>("/organizations");
    return Array.isArray(result) ? result : [];
  } catch (e) {
    console.error("Failed to fetch organizations:", e);
    return [];
  }
}

export async function fetchAllUsersGlobal(): Promise<User[]> {
  return apiFetch<User[]>("/auth/users");
}

export async function toggleUserSuspension(id: string, isActive: boolean) {
  if (isActive) {
    return adminReactivateUser(id);
  } else {
    return adminSuspendUser(id);
  }
}

export async function fetchAuditLogs(): Promise<Record<string, unknown>[]> {
  try {
    const logs = await apiFetch<Record<string, unknown>[]>("/ai-trust-engine/logs");
    return Array.isArray(logs) ? logs : [];
  } catch {
    return [];
  }
}

export async function deleteOrganization(id: string): Promise<void> {
  return apiFetch<void>(`/organizations/${id}`, {
    method: "DELETE",
  });
}

export async function fetchOrganizationAnalytics(id: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/admin/organizations/${id}/analytics`);
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
  meta_data?: Record<string, unknown>;
}): Promise<{
  user: User;
  temporary_password?: string;
  assigned_memberships_count: number;
  message: string;
}> {
  return apiFetch<{
    user: User;
    temporary_password?: string;
    assigned_memberships_count: number;
    message: string;
  }>("/admin/users", {
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

      avgTrust: data?.avgTrust ?? null,

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

      avgTrust: null,

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



export async function fetchMethodologies(sector?: string): Promise<{ modules: any[] }> {
  const query = sector ? `?sector=${encodeURIComponent(sector)}` : "";
  return apiFetch<{ modules: any[] }>(`/methodologies${query}`);
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



export async function chatWithAI(
  query: string,
  context?: { page?: string; sector?: string; project_id?: string; user_role?: string; [key: string]: unknown }
): Promise<AIChatResponse> {
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
  return apiFetch<{ status: string; message: string; user_status: string; is_active: boolean }>(`/admin/users/${userId}/suspend`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || "Suspended by Super Admin" }),
  });
}

export async function adminReactivateUser(userId: string): Promise<{ status: string; message: string; user_status: string; is_active: boolean }> {
  return apiFetch<{ status: string; message: string; user_status: string; is_active: boolean }>(`/admin/users/${userId}/reactivate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function adminDeleteUser(userId: string): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>(`/admin/users/${userId}`, {
    method: "DELETE",
  });
}

export interface AdminRole {
  id: string;
  name: string;
  code: string;
  description?: string;
  permissions?: string[];
}

export interface AdminPermission {
  id: string;
  code: string;
  name: string;
  module?: string;
}

export interface ProjectMember {
  user_id: string;
  full_name?: string;
  email?: string | null;
  role?: string;
  role_code?: string;
  joined_at?: string;
}

export async function fetchAdminRoles(): Promise<AdminRole[]> {
  return apiFetch<AdminRole[]>("/admin/roles");
}

export async function fetchAdminPermissions(): Promise<AdminPermission[]> {
  return apiFetch<AdminPermission[]>("/admin/permissions");
}

export async function fetchProjectMemberships(projectId: string): Promise<{
  project_id: string;
  project_name: string;
  member_count: number;
  members: ProjectMember[];
}> {
  return apiFetch<{
    project_id: string;
    project_name: string;
    member_count: number;
    members: ProjectMember[];
  }>(`/admin/projects/${projectId}/members`);
}

export async function assignProjectMembership(projectId: string, userId: string, roleCode: string): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>(`/admin/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, role_code: roleCode }),
  });
}

export async function revokeProjectMembership(projectId: string, userId: string): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>(`/admin/projects/${projectId}/members/${userId}`, {
    method: "DELETE",
  });
}

export async function adminRevokeUserSessions(userId: string): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>(`/admin/users/${userId}/revoke-sessions`, {
    method: "POST",
  });
}

export async function fetchGovernanceAuditLogs(action?: string): Promise<Record<string, unknown>[]> {
  const query = action ? `?action=${encodeURIComponent(action)}` : "";
  return apiFetch<Record<string, unknown>[]>(`/admin/audit-logs${query}`);
}

export async function submitITMOAuthorization(data: {
  project_id: string;
  acquiring_party?: string;
  authorized_use_scope?: string;
  cooperative_approach_id?: string;
}): Promise<{
  status: string;
  message: string;
  project_id: string;
  project_name: string;
  serial_number: string;
  cumulative_itmos_tco2e: number;
  cooperative_approach_id: string;
  acquiring_party: string;
  dossier_sha256: string;
  authorized_at: string;
  dossier: Record<string, unknown>;
}> {
  try {
    return await apiFetch<{
      status: string;
      message: string;
      project_id: string;
      project_name: string;
      serial_number: string;
      cumulative_itmos_tco2e: number;
      cooperative_approach_id: string;
      acquiring_party: string;
      dossier_sha256: string;
      authorized_at: string;
      dossier: Record<string, unknown>;
    }>("/registry/itmo/authorize", {
      method: "POST",
      body: JSON.stringify(data),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    if (errorMsg.includes("404") || errorMsg.includes("Not Found")) {
      return await apiFetch<{
        status: string;
        message: string;
        project_id: string;
        project_name: string;
        serial_number: string;
        cumulative_itmos_tco2e: number;
        cooperative_approach_id: string;
        acquiring_party: string;
        dossier_sha256: string;
        authorized_at: string;
        dossier: Record<string, unknown>;
      }>("/registry-integrations/itmo/authorize", {
        method: "POST",
        body: JSON.stringify(data),
      });
    }
    throw err;
  }
}

export async function fetchComplianceDossier(standard: string, projectId: string): Promise<Record<string, unknown>> {
  try {
    return await apiFetch<Record<string, unknown>>(`/registry/dossier/${standard}/${projectId}`);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    if (errorMsg.includes("404") || errorMsg.includes("Not Found")) {
      return await apiFetch<Record<string, unknown>>(`/registry-integrations/dossier/${standard}/${projectId}`);
    }
    throw err;
  }
}

export async function fetchRegistryReadiness(projectId: string, standard: string = "VERRA"): Promise<Record<string, unknown>> {
  try {
    return await apiFetch<Record<string, unknown>>(`/registry/readiness/${projectId}?target_standard=${standard}`);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    if (errorMsg.includes("404") || errorMsg.includes("Not Found")) {
      return await apiFetch<Record<string, unknown>>(`/registry-integrations/readiness/${projectId}?target_standard=${standard}`);
    }
    throw err;
  }
}

export async function downloadArticle6PackageZip(standard: string, projectId: string): Promise<void> {
  const currentToken = getAuthToken();
  const headers: Record<string, string> = {};
  if (currentToken) {
    headers["Authorization"] = `Bearer ${currentToken}`;
  }

  let res = await fetch(`${getApiV1()}/registry/package-download/${standard}/${projectId}`, {
    headers,
  });

  if (!res.ok) {
    res = await fetch(`${getApiV1()}/registry-integrations/package-download/${standard}/${projectId}`, {
      headers,
    });
  }

  if (!res.ok) {
    throw new Error(`Failed to download package (HTTP ${res.status})`);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${standard}_${projectId.slice(0, 8)}_package.zip`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function executeCarbonMinting(data: {
  project_id?: string;
  target_chain?: string;
  recipient_wallet?: string;
  volume_tco2e?: number;
}): Promise<CarbonMintResponse> {
  return apiFetch<CarbonMintResponse>("/ledger/mint", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchLedgerTransactions(): Promise<LedgerTransaction[]> {
  return apiFetch<LedgerTransaction[]>("/ledger/transactions");
}

export async function fetchRegistryDocumentMatrix(): Promise<Record<string, unknown>> {
  try {
    return await apiFetch<Record<string, unknown>>("/registry/document-matrix");
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    if (errorMsg.includes("404") || errorMsg.includes("Not Found")) {
      return await apiFetch<Record<string, unknown>>("/registry-integrations/document-matrix");
    }
    throw err;
  }
}

export async function downloadRegistryDocument(
  standard: string,
  projectId: string,
  documentId: string,
  format: "pdf" | "docx" | "json" = "pdf"
): Promise<void> {
  const currentToken = getAuthToken();
  const headers: Record<string, string> = {};
  if (currentToken) {
    headers["Authorization"] = `Bearer ${currentToken}`;
  }

  let res = await fetch(`${getApiV1()}/registry/documents/${standard}/${projectId}/${documentId}?format=${format}`, {
    headers,
  });

  if (!res.ok) {
    res = await fetch(`${getApiV1()}/registry-integrations/documents/${standard}/${projectId}/${documentId}?format=${format}`, {
      headers,
    });
  }

  if (!res.ok) {
    throw new Error(`Failed to download ${documentId} (HTTP ${res.status})`);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const ext = format.toLowerCase();
  a.download = `${documentId}_${projectId.slice(0, 8)}.${ext}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

// =============================================================================
// Biochar Carbon Removal Value-Chain API
// =============================================================================

export interface BiocharBatchRecord {
  id: string;
  organization_id?: string;
  project_id: string;
  batch_number: string;
  facility_name: string;
  kiln_id: string;
  production_run_id?: string;
  feedstock_type: string;
  feedstock_weight_tonnes: number;
  biochar_yield_tonnes: number;
  dry_mass_tonnes?: number;
  pyrolysis_temp_celsius?: number;
  residence_time_minutes?: number;
  fixed_carbon_pct: number;
  molar_h_c_ratio: number;
  carbon_permanence_factor: number;
  net_co2e_removed_tonnes: number;
  quality_grade: string;
  status: string;
  has_anomaly: boolean;
  anomaly_reason?: string;
  carbon_claim_project_id?: string;
  carbon_claim_registry?: string;
  carbon_claim_methodology?: string;
  mass_balance_allocated_tonnes: number;
  mass_balance_status: string;
  created_at: string;
}

export interface BiocharSummary {
  total_batches: number;
  total_feedstock_tonnes: number;
  total_biochar_produced_tonnes: number;
  total_net_co2e_removed_tonnes: number;
  grade_a_percentage: number;
  detected_anomalies_count: number;
}

export interface BiocharMassBalance {
  batch_id: string;
  batch_number: string;
  original_produced_mass_tonnes: number;
  current_inventory_tonnes: number;
  terminal_end_use_tonnes: number;
  documented_losses_tonnes: number;
  rejected_tonnes: number;
  total_reconciled_tonnes: number;
  discrepancy_tonnes: number;
  status: string;
  is_valid: boolean;
  tolerated_variance: number;
  notes?: string;
}

export interface BiocharMethodologyConflict {
  has_conflict: boolean;
  conflict_code?: string;
  severity?: string;
  biochar_project_id?: string;
  agriculture_project_id?: string;
  affected_land_unit_id?: string;
  affected_land_unit_name?: string;
  biochar_methodology?: string;
  agriculture_methodology?: string;
  carbon_pool?: string;
  message?: string;
  resolution_requirement?: string;
  accounting_blocked: boolean;
}

export interface BiocharEligibility {
  project_id: string;
  target_standard: string;
  target_methodology: string;
  methodology_version: string;
  eligibility_status: string;
  facility_criteria_met: boolean;
  feedstock_criteria_met: boolean;
  additionality_status: string;
  requirements_complete: string[];
  requirements_missing: string[];
  blocking_findings: string[];
  review_findings: string[];
  source_references: string[];
  evaluated_at: string;
}

export interface BiocharChainOfCustody {
  batch_id: string;
  batch_number: string;
  traceability_complete: boolean;
  nodes: Array<{
    node_type: string;
    node_id: string;
    title: string;
    details: Record<string, unknown>;
    hash?: string;
  }>;
  upstream_chain: string[];
  downstream_chain: string[];
  evidence_hashes: string[];
}

export async function fetchBiocharBatches(projectId?: string): Promise<BiocharBatchRecord[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<BiocharBatchRecord[]>(`/biochar/batches${query}`);
}

export async function fetchBiocharBatch(batchId: string): Promise<BiocharBatchRecord> {
  return apiFetch<BiocharBatchRecord>(`/biochar/batches/${batchId}`);
}

export async function fetchBiocharSummary(projectId?: string): Promise<BiocharSummary> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<BiocharSummary>(`/biochar/summary${query}`);
}

export async function fetchBiocharMassBalance(batchId: string): Promise<BiocharMassBalance> {
  return apiFetch<BiocharMassBalance>(`/biochar/batches/${batchId}/mass-balance`);
}

export async function fetchBiocharLineage(batchId: string): Promise<BiocharChainOfCustody> {
  return apiFetch<BiocharChainOfCustody>(`/biochar/batches/${batchId}/lineage`);
}

export async function fetchBiocharLandUnitConflict(
  landUnitId: string,
  biocharMethodology = "VM0044",
  biocharProjectId?: string
): Promise<BiocharMethodologyConflict> {
  const pidQuery = biocharProjectId ? `&biochar_project_id=${biocharProjectId}` : "";
  return apiFetch<BiocharMethodologyConflict>(
    `/biochar/conflicts/land-units/${landUnitId}?biochar_methodology=${biocharMethodology}${pidQuery}`
  );
}

export async function fetchBiocharEligibility(
  projectId: string,
  targetStandard = "VERRA",
  targetMethodology = "VM0044",
  methodologyVersion = "v1.2"
): Promise<BiocharEligibility> {
  return apiFetch<BiocharEligibility>(
    `/biochar/projects/${projectId}/eligibility?target_standard=${targetStandard}&target_methodology=${targetMethodology}&methodology_version=${methodologyVersion}`
  );
}

export interface FeedstockSourceRecord {
  id: string;
  source_code: string;
  source_name: string;
  source_type: string;
  biomass_type: string;
  origin_location?: string;
  supplier_name?: string;
  waste_status: string;
  baseline_fate: string;
  sustainability_status: string;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface FeedstockLotRecord {
  id: string;
  lot_number: string;
  feedstock_type: string;
  mass_received_tonnes: number;
  moisture_content_pct: number;
  dry_mass_tonnes: number;
  available_mass_tonnes: number;
  allocated_mass_tonnes: number;
  dry_basis_derivation_method?: string;
  storage_location?: string;
  receipt_date: string;
  created_at: string;
}

export interface ProductionFacilityRecord {
  id: string;
  facility_code: string;
  facility_name: string;
  location: string;
  facility_status: string;
  technology_type: string;
  production_capacity_tpy?: number;
  permits_json?: Record<string, any>;
  created_at: string;
}

export interface ProductionRunRecord {
  id: string;
  run_number: string;
  start_time: string;
  end_time?: string;
  total_feedstock_input_tonnes: number;
  total_feedstock_dry_tonnes: number;
  avg_pyrolysis_temp_celsius: number;
  residence_time_minutes: number;
  output_biochar_mass_tonnes: number;
  qa_status: string;
  created_at: string;
}

export interface BiocharEndUseItem {
  id: string;
  batch_id: string;
  end_use_type: string;
  applied_quantity_tonnes: number;
  event_date: string;
  source_land_unit_id?: string;
  application_rate_tonnes_per_ha?: number;
  area_hectares?: number;
  application_method?: string;
  gps_coordinates?: string;
  crop_type?: string;
  product_category?: string;
  recipient_organization?: string;
  durability_classification?: string;
  verification_status: string;
  created_at: string;
}

export async function fetchFeedstockSources(projectId?: string): Promise<FeedstockSourceRecord[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<FeedstockSourceRecord[]>(`/biochar/sources${query}`);
}

export const fetchBiocharSources = fetchFeedstockSources;

export async function fetchFeedstockLots(projectId?: string): Promise<FeedstockLotRecord[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<FeedstockLotRecord[]>(`/biochar/lots${query}`);
}

export async function fetchProductionFacilities(projectId?: string): Promise<ProductionFacilityRecord[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<ProductionFacilityRecord[]>(`/biochar/facilities${query}`);
}

export async function fetchProductionRuns(projectId?: string): Promise<ProductionRunRecord[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<ProductionRunRecord[]>(`/biochar/runs${query}`);
}

export async function fetchBiocharEndUses(projectId?: string): Promise<BiocharEndUseItem[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<BiocharEndUseItem[]>(`/biochar/end-uses${query}`);
}

// ─── Puro.earth Biochar Edition 2025 V2 Endpoints ──────────────────────────

export interface PuroRuleDefinitionRecord {
  id: string;
  section_number: number;
  section_title: string;
  rule_number: string;
  rule_title: string;
  applicability_condition?: string;
  requirement_type: string;
  implementation_handler: string;
  required_evidence_types: string[];
  is_blocking: boolean;
}

export interface PuroNormativeDependencyRecord {
  id: string;
  code: string;
  title: string;
  version: string;
  document_type: string;
  status: string;
  effective_date: string;
  source_reference?: string;
  required_by_rules: string[];
  implementation_state: string;
  checksum_hash?: string;
  last_reviewed_at?: string;
}

export interface PuroEndUseCategoryRecord {
  id: string;
  category_code: string;
  category_name: string;
  sector: string;
  product_type: string;
  application_type?: string;
  pure_or_mixed: string;
  min_environmental_quality?: string;
  is_corc_eligible: boolean;
  default_durability_years: number;
  persistence_factor_non_soil?: number;
  reversal_rules?: Record<string, any>;
  cascading_conditions?: Record<string, any>;
  reversal_discount_factor_required?: boolean;
  required_evidence_types: string[];
  rule_references: string[];
}

export interface PuroSupplierProfileRecord {
  id: string;
  organization_id: string;
  project_id: string;
  facility_id: string;
  supplier_legal_name: string;
  registration_number?: string;
  jurisdiction_country: string;
  supplier_role: string;
  claim_rights_status: string;
  authorization_agreement_ref?: string;
  rights_declaration_doc_hash?: string;
  contract_effective_date?: string;
  contract_expiry_date?: string;
  validation_state: string;
  created_at: string;
}

export interface PuroFacilityProfileRecord {
  id: string;
  organization_id: string;
  facility_id: string;
  facility_classification: string;
  host_country: string;
  reference_coordinates?: string;
  spatial_extent_geojson?: Record<string, any>;
  receiving_location?: string;
  pretreatment_location?: string;
  conversion_location?: string;
  packaging_location?: string;
  technology_similarity_verified: boolean;
  commissioned_status: string;
  operating_status: string;
  created_at: string;
}

export interface PuroCreditingPeriodRecord {
  id: string;
  organization_id: string;
  facility_id: string;
  sequence_number: number;
  start_date: string;
  end_date: string;
  crediting_duration_years: number;
  status: string;
  renewal_type?: string;
  renewal_eligibility: boolean;
  previous_period_id?: string;
  created_at: string;
}

export interface PuroQuantificationRequest {
  batch_id: string;
  soil_temperature_celsius?: number;
  dry_mass_override_tonnes?: number;
  impurity_pct?: number;
  eligible_feedstock_fraction?: number;
  e_project_transport_tco2e?: number;
  e_project_processing_tco2e?: number;
  e_project_application_tco2e?: number;
  e_project_auxiliary_fuel_tco2e?: number;
  e_project_methane_storage_tco2e?: number;
  e_leakage_tco2e?: number;
  dry_mass_determination_method?: string;
}

export interface PuroSimulationRequest {
  batch_id?: string;
  dry_mass_tonnes: number;
  c_org_pct: number;
  molar_h_c: number;
  soil_temperature_celsius: number;
  baseline_scenario?: string;
  historical_baseline_tco2e?: number;
  end_use_category_code?: string;
  reversal_discount_factor?: number;
  is_non_soil_durable?: boolean;
  e_biomass?: number;
  e_production?: number;
  e_use?: number;
  e_infra?: number;
  e_dluc?: number;
  crediting_years?: number;
  is_leakage_mitigated?: boolean;
  ecological_leakage_tco2e?: number;
  market_activity_shifting_tco2e?: number;
  iluc_feedstock_category?: string;
  feedstock_quantity_dry_tonnes?: number;
}

export interface PuroQuantificationBreakdown {
  eligible_dry_biochar_mass_tonnes: number;
  organic_carbon_pct: number;
  molar_h_c: number;
  soil_temperature_celsius: number;
  persistence_fraction_pf: number;
  regression_m?: number | null;
  regression_a?: number | null;
  durability_class: string;

  c_stored_tco2e: number;
  c_baseline_tco2e: number;
  c_loss_tco2e: number;
  e_project_tco2e: number;
  e_ops_biomass_tco2e?: number;
  e_ops_production_tco2e?: number;
  e_ops_use_tco2e?: number;
  e_ops_total_tco2e?: number;
  e_emb_infra_tco2e?: number;
  e_emb_dluc_tco2e?: number;
  e_emb_annualized_tco2e?: number;

  leakage_eco_tco2e?: number;
  leakage_ma_tco2e?: number;
  leakage_iluc_tco2e?: number;
  e_leakage_tco2e: number;

  net_corcs_calculated: number;
  combined_uncertainty_pct: number;
  deductible_uncertainty_pct: number;
  final_corcs_issuable: number;
  reported_uncertainty_text?: string | null;

  calculation_mode?: string;
  calculation_status: string;
  corc_point_status: string;
  calculation_hash: string;
  methodology_version: string;
  coefficient_version: string;
  engine_version: string;
  timestamp: string;
  execution_id?: string | null;
  superseded_at?: string | null;
  replacement_engine_version?: string | null;
  rule_references: string[];
  warnings: string[];
  notes?: string | null;
}

export interface PuroAuditWorkflowRecord {
  id: string;
  organization_id: string;
  facility_id: string;
  monitoring_period_id?: string;
  audit_type: string;
  auditor_organization: string;
  lead_auditor_name?: string;
  audit_status: string;
  scheduled_date?: string;
  completion_date?: string;
  audit_dossier_hash?: string;
  certificate_number?: string;
  created_at: string;
}

export interface PuroOutputReportRecord {
  id: string;
  organization_id: string;
  facility_id: string;
  monitoring_period_id: string;
  report_number: string;
  report_version: number;
  report_status: string;
  total_eligible_biochar_mass_tonnes: number;
  total_net_corcs: number;
  manifest_hash: string;
  ledger_signature_id?: string;
  generated_at: string;
}

export interface PuroRegistryReadiness {
  project_id: string;
  facility_id?: string;
  methodology_code: string;
  readiness_state: string;
  overall_capability_status: string;
  active_blockers: string[];
  unresolved_dependencies: string[];
  audit_readiness_status: string;
  quantification_status: string;
  issuance_status: string;
  corc_point_verified_batches_count: number;
  total_eligible_batches_count: number;
  evaluated_at: string;
}

export async function fetchPuroRules(): Promise<PuroRuleDefinitionRecord[]> {
  return apiFetch<PuroRuleDefinitionRecord[]>("/biochar/puro/rules");
}

export async function fetchPuroDependencies(): Promise<PuroNormativeDependencyRecord[]> {
  return apiFetch<PuroNormativeDependencyRecord[]>("/biochar/puro/dependencies");
}

export async function fetchPuroEndUseCategories(): Promise<PuroEndUseCategoryRecord[]> {
  return apiFetch<PuroEndUseCategoryRecord[]>("/biochar/puro/categories");
}

export async function fetchPuroSupplierProfile(projectId: string): Promise<PuroSupplierProfileRecord | null> {
  return apiFetch<PuroSupplierProfileRecord | null>(`/biochar/puro/projects/${projectId}/supplier`);
}

export async function fetchPuroFacilityProfile(facilityId: string): Promise<PuroFacilityProfileRecord | null> {
  return apiFetch<PuroFacilityProfileRecord | null>(`/biochar/puro/facilities/${facilityId}/profile`);
}

export async function fetchPuroCreditingPeriods(facilityId: string): Promise<PuroCreditingPeriodRecord[]> {
  return apiFetch<PuroCreditingPeriodRecord[]>(`/biochar/puro/facilities/${facilityId}/crediting-periods`);
}

export async function executePuroQuantification(
  batchId: string,
  payload?: PuroQuantificationRequest
): Promise<PuroQuantificationBreakdown> {
  return apiFetch<PuroQuantificationBreakdown>(`/biochar/puro/batches/${batchId}/quantification`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ batch_id: batchId, ...(payload || {}) }),
  });
}

export async function simulatePuroQuantification(
  payload: PuroSimulationRequest,
  batchId?: string
): Promise<PuroQuantificationBreakdown> {
  const url = batchId
    ? `/biochar/puro/batches/${batchId}/simulate-quantification`
    : "/biochar/puro/simulate-quantification";
  return apiFetch<PuroQuantificationBreakdown>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function fetchPuroAudits(facilityId: string): Promise<PuroAuditWorkflowRecord[]> {
  return apiFetch<PuroAuditWorkflowRecord[]>(`/biochar/puro/facilities/${facilityId}/audits`);
}

export async function fetchPuroOutputReports(facilityId: string): Promise<PuroOutputReportRecord[]> {
  return apiFetch<PuroOutputReportRecord[]>(`/biochar/puro/facilities/${facilityId}/output-reports`);
}

export async function fetchPuroRegistryReadiness(
  projectId: string,
  facilityId?: string
): Promise<PuroRegistryReadiness> {
  const q = facilityId ? `?facility_id=${facilityId}` : "";
  return apiFetch<PuroRegistryReadiness>(`/biochar/puro/projects/${projectId}/readiness${q}`);
}

// ─── Verra VM0044 v1.2 Biochar Quantification Engine Endpoints ───────────────

export interface VM0044MethodologyVersionRecord {
  id: string;
  code: string;
  name: string;
  version: string;
  status: string;
  sectoral_scope: string;
  activity_type: string;
  release_date: string;
  ccp_eligible: boolean;
  ccp_approval_date?: string;
  is_active: boolean;
  created_at: string;
}

export interface VM0044RuleDefinitionRecord {
  id: string;
  rule_id: string;
  section: string;
  title: string;
  requirement_type: string;
  summary: string;
  mandatory: boolean;
  fail_closed_condition: string;
}

export interface VM0044NormativeDependencyRecord {
  id: string;
  dependency_code: string;
  title: string;
  normative_role: string;
  mandatory: boolean;
  active_version: string;
}

export interface VM0044ApplicabilityEvaluateRequest {
  project_id: string;
  facility_id?: string;
  feedstock_source_ids?: string[];
  batch_id?: string;
  end_use_record_ids?: string[];
}

export interface VM0044ApplicabilityResponse {
  status: "ELIGIBLE" | "INELIGIBLE";
  facility_check: { passed: boolean; details: string[] };
  feedstock_check: { passed: boolean; details: string[] };
  process_check: { passed: boolean; details: string[] };
  end_use_check: { passed: boolean; details: string[] };
  blocking_findings: string[];
  evaluated_at: string;
}

export interface VM0044AdditionalityEvaluateRequest {
  project_id: string;
  regulatory_surplus_demonstrated: boolean;
  analysis_option: "OPTION_1_INVESTMENT_COMPARISON" | "OPTION_2_BENCHMARK_ANALYSIS";
  project_irr_pct?: number;
  benchmark_irr_pct?: number;
  benchmark_source?: string;
  financial_model_hash?: string;
}

export interface VM0044AdditionalityResponse {
  status: "COMPLETE" | "NOT_ADDITIONAL";
  step1_regulatory_surplus: boolean;
  step2_positive_list: boolean;
  step3_investment_analysis: boolean;
  findings: string[];
  evaluated_at: string;
}

export interface VM0044SnapshotRequest {
  project_id: string;
  batch_id: string;
  end_use_record_id?: string;
  technology_class?: "HIGH_TECHNOLOGY" | "LOW_TECHNOLOGY";
  grid_electricity_kwh?: number;
  fossil_fuel_litres?: number;
  biomass_transport_distance_km?: number;
  biochar_transport_distance_km?: number;
  uncertainty_pct?: number;
}

export interface VM0044SnapshotResponse {
  snapshot_id: string;
  snapshot_hash: string;
  batch_id: string;
  project_id: string;
  technology_class: string;
  created_at: string;
}

export interface VM0044CalculationRequest {
  project_id: string;
  batch_id: string;
  end_use_record_id?: string;
  technology_class?: "HIGH_TECHNOLOGY" | "LOW_TECHNOLOGY";
  grid_electricity_kwh?: number;
  fossil_fuel_litres?: number;
  biomass_transport_distance_km?: number;
  biochar_transport_distance_km?: number;
  uncertainty_pct?: number;
  preview?: boolean;
}

export interface VM0044EquationBreakdown {
  biochar_dry_mass_tonnes: number;
  c_org_fraction: number;
  permanence_factor_pr_de: number;
  organic_carbon_stored_cc_tonnes: number;
  gross_co2e_stored_tonnes: number;
  er_ss_tonnes: number;
  pe_d_tonnes: number;
  pe_p_tonnes: number;
  pe_c_tonnes: number;
  pe_ps_total_tonnes: number;
  er_ps_tonnes: number;
  pe_as_tonnes: number;
  e_p_tonnes: number;
  le_ts_tonnes: number;
  le_tap_tonnes: number;
  le_total_tonnes: number;
  er_gross_removals_tonnes: number;
  uncertainty_pct: number;
  uncertainty_deduction_tonnes: number;
  er_net_removals_tonnes: number;
}

export interface VM0044CalculationResponse {
  calculation_id: string;
  project_id: string;
  batch_id: string;
  end_use_record_id: string;
  status: "CALCULATED" | "PREVIEW" | "FAILED";
  methodology_version: string;
  technology_class: string;
  equation_breakdown: VM0044EquationBreakdown;
  net_removal_tco2e: number;
  is_issuable: boolean;
  snapshot_hash: string;
  calculation_hash: string;
  calculated_at: string;
}

export interface VM0044CalculationExecutionRecord {
  id: string;
  project_id: string;
  batch_id: string;
  end_use_record_id: string;
  status: string;
  engine_version: string;
  technology_class: string;
  net_removal_tco2e: number;
  is_issuable: boolean;
  snapshot_hash: string;
  calculation_hash: string;
  created_at: string;
}

export async function fetchVM0044Version(): Promise<VM0044MethodologyVersionRecord> {
  return apiFetch<VM0044MethodologyVersionRecord>("/biochar/vm0044/version");
}

export async function fetchVM0044Rules(): Promise<VM0044RuleDefinitionRecord[]> {
  return apiFetch<VM0044RuleDefinitionRecord[]>("/biochar/vm0044/rules");
}

export async function fetchVM0044Dependencies(): Promise<VM0044NormativeDependencyRecord[]> {
  return apiFetch<VM0044NormativeDependencyRecord[]>("/biochar/vm0044/dependencies");
}

export async function evaluateVM0044Applicability(
  req: VM0044ApplicabilityEvaluateRequest
): Promise<VM0044ApplicabilityResponse> {
  return apiFetch<VM0044ApplicabilityResponse>("/biochar/vm0044/applicability/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function evaluateVM0044Additionality(
  req: VM0044AdditionalityEvaluateRequest
): Promise<VM0044AdditionalityResponse> {
  return apiFetch<VM0044AdditionalityResponse>("/biochar/vm0044/additionality/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function createVM0044Snapshot(
  req: VM0044SnapshotRequest
): Promise<VM0044SnapshotResponse> {
  return apiFetch<VM0044SnapshotResponse>("/biochar/vm0044/snapshots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function executeVM0044Calculation(
  req: VM0044CalculationRequest
): Promise<VM0044CalculationResponse> {
  return apiFetch<VM0044CalculationResponse>("/biochar/vm0044/calculate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function fetchVM0044Executions(
  projectId?: string,
  batchId?: string
): Promise<VM0044CalculationExecutionRecord[]> {
  const query = new URLSearchParams();
  if (projectId) query.set("project_id", projectId);
  if (batchId) query.set("batch_id", batchId);
  const qs = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<VM0044CalculationExecutionRecord[]>(`/biochar/vm0044/executions${qs}`);
}

// ─── Earth Observation & Agriculture Spatial Endpoints ──────────────────────

export interface SatelliteObservationRecord {
  id: string;
  organization_id: string;
  project_id: string;
  land_unit_id?: string | null;
  provider: string;
  scene_id: string;
  acquisition_timestamp: string;
  cloud_coverage_pct?: number | null;
  spatial_resolution_m: number;
  observation_type: string;
  raw_band_uris: Record<string, any>;
  derived_indices: Record<string, any>;
  provenance_hash: string;
  processing_level: string;
  lineage_manifest?: Record<string, any>;
  created_at: string;
}

export interface LandUnitRecord {
  id: string;
  organization_id: string;
  project_id: string;
  parent_id?: string | null;
  name: string;
  code?: string | null;
  unit_type: string;
  area_ha: number;
  perimeter_m?: number;
  boundary_geojson: any;
  boundary_source?: string;
  centroid_lat?: number;
  centroid_lon?: number;
  land_use_category?: string | null;
  soil_type?: string | null;
  slope_pct?: number | null;
  is_active: boolean;
  stratum_id?: string | null;
  properties?: Record<string, any>;
}

export interface SoilSampleRecord {
  id: string;
  organization_id: string;
  project_id: string;
  land_unit_id: string;
  sample_code: string;
  latitude: number;
  longitude: number;
  collection_date: string;
  depth_top_cm: number;
  depth_bottom_cm: number;
  organic_carbon_pct?: number | null;
  bulk_density_g_cm3?: number | null;
  lab_sample_id?: string | null;
}

export interface TreeObservationRecord {
  id: string;
  organization_id: string;
  project_id: string;
  land_unit_id: string;
  tree_tag: string;
  latitude: number;
  longitude: number;
  dbh_cm: number;
  height_m?: number | null;
  species_name?: string | null;
  observation_timestamp: string;
}

export async function fetchSatelliteObservations(projectId?: string): Promise<SatelliteObservationRecord[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<SatelliteObservationRecord[]>(`/agriculture/satellite-observations${query}`).catch(() => []);
}

export async function fetchLandUnits(projectId?: string): Promise<LandUnitRecord[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<LandUnitRecord[]>(`/agriculture/land-units${query}`).catch(() => []);
}

export async function fetchSoilSamples(projectId?: string, landUnitId?: string): Promise<SoilSampleRecord[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (landUnitId) params.set("land_unit_id", landUnitId);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<SoilSampleRecord[]>(`/agriculture/soil-samples${qs}`).catch(() => []);
}

export async function fetchTreeObservations(projectId?: string, landUnitId?: string): Promise<TreeObservationRecord[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (landUnitId) params.set("land_unit_id", landUnitId);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<TreeObservationRecord[]>(`/agriculture/tree-observations${qs}`).catch(() => []);
}

// ─── Agriculture MRV Phase 1: Foundation, Strata, Management History & Readiness ───

export interface StratumRecord {
  id: string;
  organization_id: string;
  project_id: string;
  code: string;
  name: string;
  description?: string | null;
  stratum_type: string;
  area_ha: number;
  is_active: boolean;
  properties?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  member_count: number;
  land_unit_ids: string[];
}

export interface ManagementRecordItem {
  id: string;
  organization_id: string;
  project_id: string;
  land_unit_id?: string | null;
  record_type: string;
  practice_category: string;
  event_date: string;
  end_date?: string | null;
  data_source: string;
  details: Record<string, unknown>;
  evidence_id?: string | null;
  entered_by_id?: string | null;
  qa_status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectFoundationData {
  project_id: string;
  project_name: string;
  project_code?: string | null;
  sector: { id?: string; code: string; name: string };
  methodology: { id?: string; code?: string; name?: string; version_id?: string; version?: string };
  methodology_lock_status: string;
  locked_methodology_snapshot?: Record<string, unknown> | null;
  crediting_period: { start?: string | null; end?: string | null };
  baseline_parameters: Record<string, unknown>;
  authoritative_boundary?: {
    id: string;
    version_number: number;
    effective_date: string;
    area_ha: number;
    perimeter_m?: number | null;
    source: string;
    crs: string;
    boundary_geojson: Record<string, unknown>;
  } | null;
  land_units_count: number;
  strata_count: number;
  management_records_count: number;
}

export interface ComponentReadinessItem {
  status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED";
  message: string;
  details: Record<string, unknown>;
}

export interface FoundationReadinessData {
  project_id: string;
  overall_status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED";
  components: {
    project_configuration: ComponentReadinessItem;
    methodology_lock: ComponentReadinessItem;
    authoritative_boundary: ComponentReadinessItem;
    land_units: ComponentReadinessItem;
    stratification: ComponentReadinessItem;
    management_baseline: ComponentReadinessItem;
  };
  evaluated_at: string;
}

export async function fetchProjectFoundation(projectId: string): Promise<ProjectFoundationData | null> {
  return apiFetch<ProjectFoundationData>(`/agriculture/projects/${projectId}/foundation`).catch(() => null);
}

export async function lockProjectMethodology(projectId: string, notes?: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/agriculture/projects/${projectId}/lock-methodology`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export async function linkProjectBoundary(
  projectId: string,
  payload: { boundary_geojson: Record<string, unknown>; source?: string; reason?: string; effective_date?: string }
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/agriculture/projects/${projectId}/link-boundary`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchProjectStrata(projectId: string, asOfDate?: string): Promise<StratumRecord[]> {
  const query = asOfDate ? `?as_of_date=${asOfDate}` : "";
  return apiFetch<StratumRecord[]>(`/agriculture/projects/${projectId}/strata${query}`).catch(() => []);
}

export async function createProjectStratum(
  projectId: string,
  payload: { code: string; name: string; description?: string; stratum_type?: string; area_ha?: number }
): Promise<StratumRecord> {
  return apiFetch<StratumRecord>(`/agriculture/projects/${projectId}/strata`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addStratumMemberships(
  projectId: string,
  stratumId: string,
  memberships: Array<{ land_unit_id: string; valid_from: string; valid_to?: string; status?: string }>
): Promise<StratumRecord> {
  return apiFetch<StratumRecord>(`/agriculture/projects/${projectId}/strata/${stratumId}/members`, {
    method: "POST",
    body: JSON.stringify({ memberships }),
  });
}

export async function fetchProjectManagementRecords(
  projectId: string,
  params?: { landUnitId?: string; practiceCategory?: string; recordType?: string }
): Promise<ManagementRecordItem[]> {
  const q = new URLSearchParams();
  if (params?.landUnitId) q.set("land_unit_id", params.landUnitId);
  if (params?.practiceCategory) q.set("practice_category", params.practiceCategory);
  if (params?.recordType) q.set("record_type", params.recordType);
  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch<ManagementRecordItem[]>(`/agriculture/projects/${projectId}/management-records${qs}`).catch(() => []);
}

export async function createProjectManagementRecord(
  projectId: string,
  payload: {
    record_type: string;
    practice_category?: string;
    event_date: string;
    end_date?: string;
    data_source?: string;
    corroboration?: string;
    details?: Record<string, unknown>;
    land_unit_id?: string;
    qa_status?: string;
  }
): Promise<ManagementRecordItem> {
  return apiFetch<ManagementRecordItem>(`/agriculture/projects/${projectId}/management-records`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchFoundationReadiness(projectId: string): Promise<FoundationReadinessData | null> {
  return apiFetch<FoundationReadinessData>(`/agriculture/projects/${projectId}/foundation-readiness`).catch(() => null);
}

// ─── Agriculture MRV Phase 2: Ground Sampling, Field Collection, Chain of Custody & Lab Assays ───

export interface SamplingCampaignRecord {
  id: string;
  project_id: string;
  organization_id: string;
  campaign_code: string;
  name: string;
  description?: string;
  planned_start_date: string;
  planned_end_date?: string;
  actual_start_date?: string;
  actual_end_date?: string;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface SamplingPlanVersionRecord {
  id: string;
  campaign_id: string;
  project_id: string;
  organization_id: string;
  version_number: number;
  effective_as_of_date: string;
  is_locked: boolean;
  locked_at?: string;
  locked_by_id?: string;
  stratification_snapshot: Record<string, unknown>;
  allocation_parameters: Record<string, unknown>;
  notes?: string;
  created_at: string;
}

export interface SamplingPointRecord {
  id: string;
  campaign_id: string;
  plan_version_id: string;
  project_id: string;
  organization_id: string;
  land_unit_id: string;
  stratum_id?: string;
  point_code: string;
  planned_lat: number;
  planned_lon: number;
  target_depth_from_cm: number;
  target_depth_to_cm: number;
  is_composite: boolean;
  subsample_count: number;
  notes?: string;
  status: string;
  created_at: string;
}

export interface SampleCollectionEventRecord {
  id: string;
  physical_sample_id: string;
  sampling_point_id: string;
  actual_lat: number;
  actual_lon: number;
  deviation_distance_m: number;
  deviation_reason?: string;
  collection_timestamp: string;
  collector_id?: string;
  collector_name: string;
  actual_depth_from_cm: number;
  actual_depth_to_cm: number;
  sample_condition: string;
  notes?: string;
  photo_evidence_id?: string;
  photo_hash?: string;
  device_metadata: Record<string, unknown>;
  idempotency_key?: string;
  sync_timestamp?: string;
  created_at: string;
}

export interface ChainOfCustodyEventRecord {
  id: string;
  physical_sample_id: string;
  event_type: string;
  event_timestamp: string;
  custodian_id?: string;
  custodian_name: string;
  custodian_organization: string;
  from_location?: string;
  to_location?: string;
  condition: string;
  seal_intact: boolean;
  seal_identifier?: string;
  notes?: string;
  evidence_id?: string;
  created_at: string;
}

export interface LaboratoryReceiptRecord {
  id: string;
  physical_sample_id: string;
  laboratory_name: string;
  laboratory_id_ref?: string;
  received_at: string;
  received_by_name: string;
  condition_on_receipt: string;
  seal_status: string;
  intake_status: string;
  rejection_reason?: string;
  receipt_evidence_id?: string;
  notes?: string;
  created_at: string;
}

export interface LaboratoryResultRecord {
  id: string;
  analysis_id: string;
  physical_sample_id: string;
  analyte: string;
  raw_value: number | string;
  raw_unit: string;
  normalized_value?: number | string;
  normalized_unit?: string;
  normalization_method?: string;
  detection_limit?: number | string;
  uncertainty_pct?: number | string;
  qualifier: string;
  is_superseded: boolean;
  superseded_by_id?: string;
  revision_reason?: string;
  created_at: string;
}

export interface LaboratoryAnalysisRecord {
  id: string;
  physical_sample_id: string;
  laboratory_name: string;
  laboratory_accreditation?: string;
  analysis_batch_id?: string;
  analytical_method: string;
  method_standard_code?: string;
  analysis_date: string;
  report_reference_number?: string;
  analyst_name?: string;
  qa_status: string;
  evidence_id?: string;
  created_at: string;
  results: LaboratoryResultRecord[];
}

export interface SampleQAReviewRecord {
  id: string;
  physical_sample_id: string;
  reviewer_id?: string;
  reviewer_name: string;
  review_date: string;
  overall_qa_status: string;
  location_verified: boolean;
  deviation_acceptable: boolean;
  depth_valid: boolean;
  custody_complete: boolean;
  lab_receipt_verified: boolean;
  required_assays_present: boolean;
  notes?: string;
  created_at: string;
}

export interface PhysicalSampleRecord {
  id: string;
  sample_code: string;
  project_id: string;
  campaign_id: string;
  plan_version_id: string;
  sampling_point_id: string;
  organization_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  sampling_point?: SamplingPointRecord;
  collection_event?: SampleCollectionEventRecord;
  custody_events?: ChainOfCustodyEventRecord[];
  laboratory_receipt?: LaboratoryReceiptRecord;
  laboratory_analyses?: LaboratoryAnalysisRecord[];
  qa_review?: SampleQAReviewRecord;
}

export interface GroundEvidenceReadinessComponent {
  status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED";
  message: string;
  details: Record<string, unknown>;
}

export interface GroundEvidenceReadinessData {
  project_id: string;
  overall_status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED";
  components: {
    sampling_campaign: GroundEvidenceReadinessComponent;
    sampling_plan: GroundEvidenceReadinessComponent;
    stratum_coverage: GroundEvidenceReadinessComponent;
    sampling_points: GroundEvidenceReadinessComponent;
    field_collection: GroundEvidenceReadinessComponent;
    chain_of_custody: GroundEvidenceReadinessComponent;
    lab_receipt: GroundEvidenceReadinessComponent;
    required_assays: GroundEvidenceReadinessComponent;
    qa_review: GroundEvidenceReadinessComponent;
  };
  evaluated_at: string;
}

export async function fetchSamplingCampaigns(
  projectId: string,
  status?: string
): Promise<SamplingCampaignRecord[]> {
  const query = status ? `?status=${status}` : "";
  return apiFetch<SamplingCampaignRecord[]>(`/agriculture/projects/${projectId}/sampling-campaigns${query}`).catch(() => []);
}

export async function createSamplingCampaign(
  projectId: string,
  payload: {
    campaign_code: string;
    name: string;
    description?: string;
    planned_start_date: string;
    planned_end_date?: string;
    notes?: string;
  }
): Promise<SamplingCampaignRecord> {
  return apiFetch<SamplingCampaignRecord>(`/agriculture/projects/${projectId}/sampling-campaigns`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchSamplingPlanVersions(
  projectId: string,
  campaignId: string
): Promise<SamplingPlanVersionRecord[]> {
  return apiFetch<SamplingPlanVersionRecord[]>(
    `/agriculture/projects/${projectId}/sampling-campaigns/${campaignId}/plan-versions`
  ).catch(() => []);
}

export async function createSamplingPlanVersion(
  projectId: string,
  campaignId: string,
  payload: {
    effective_as_of_date: string;
    allocation_parameters?: Record<string, unknown>;
    notes?: string;
  }
): Promise<SamplingPlanVersionRecord> {
  return apiFetch<SamplingPlanVersionRecord>(
    `/agriculture/projects/${projectId}/sampling-campaigns/${campaignId}/plan-versions`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function lockSamplingPlanVersion(
  projectId: string,
  campaignId: string,
  versionId: string,
  payload?: { notes?: string }
): Promise<SamplingPlanVersionRecord> {
  return apiFetch<SamplingPlanVersionRecord>(
    `/agriculture/projects/${projectId}/sampling-campaigns/${campaignId}/plan-versions/${versionId}/lock`,
    {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function fetchSamplingPoints(
  projectId: string,
  campaignId: string,
  planVersionId?: string
): Promise<SamplingPointRecord[]> {
  const query = planVersionId ? `?plan_version_id=${planVersionId}` : "";
  return apiFetch<SamplingPointRecord[]>(
    `/agriculture/projects/${projectId}/sampling-campaigns/${campaignId}/points${query}`
  ).catch(() => []);
}

export async function createSamplingPoints(
  projectId: string,
  campaignId: string,
  versionId: string,
  payload: {
    points: Array<{
      point_code: string;
      land_unit_id: string;
      stratum_id?: string;
      planned_lat: number;
      planned_lon: number;
      depth_from_cm?: number;
      depth_to_cm?: number;
      target_depth_from_cm?: number;
      target_depth_to_cm?: number;
      is_composite?: boolean;
      subsample_count?: number;
      notes?: string;
    }>;
  }
): Promise<SamplingPointRecord[]> {
  return apiFetch<SamplingPointRecord[]>(
    `/agriculture/projects/${projectId}/sampling-campaigns/${campaignId}/plan-versions/${versionId}/points`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchPhysicalSamples(
  projectId: string,
  params?: { campaignId?: string; status?: string }
): Promise<PhysicalSampleRecord[]> {
  const q = new URLSearchParams();
  if (params?.campaignId) q.set("campaign_id", params.campaignId);
  if (params?.status) q.set("status", params.status);
  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch<PhysicalSampleRecord[]>(`/agriculture/projects/${projectId}/physical-samples${qs}`).catch(() => []);
}

export async function fetchPhysicalSample(
  projectId: string,
  sampleId: string
): Promise<PhysicalSampleRecord | null> {
  return apiFetch<PhysicalSampleRecord>(`/agriculture/projects/${projectId}/physical-samples/${sampleId}`).catch(() => null);
}

export async function recordSampleCollection(
  projectId: string,
  sampleId: string,
  payload: {
    actual_lat: number;
    actual_lon: number;
    deviation_reason?: string;
    collection_timestamp: string;
    collector_name: string;
    actual_depth_from_cm?: number;
    actual_depth_to_cm?: number;
    sample_condition?: string;
    notes?: string;
    photo_evidence_id?: string;
    photo_hash?: string;
    device_metadata?: Record<string, unknown>;
    idempotency_key?: string;
  }
): Promise<SampleCollectionEventRecord> {
  return apiFetch<SampleCollectionEventRecord>(
    `/agriculture/projects/${projectId}/physical-samples/${sampleId}/collection`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function recordSampleCustodyEvent(
  projectId: string,
  sampleId: string,
  payload: {
    event_type: string;
    event_timestamp: string;
    custodian_name: string;
    custodian_organization: string;
    from_location?: string;
    to_location?: string;
    condition?: string;
    seal_intact?: boolean;
    seal_identifier?: string;
    notes?: string;
    evidence_id?: string;
  }
): Promise<ChainOfCustodyEventRecord> {
  return apiFetch<ChainOfCustodyEventRecord>(
    `/agriculture/projects/${projectId}/physical-samples/${sampleId}/custody-events`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function recordSampleLaboratoryReceipt(
  projectId: string,
  sampleId: string,
  payload: {
    laboratory_name: string;
    laboratory_id_ref?: string;
    received_at: string;
    received_by_name: string;
    condition_on_receipt?: string;
    seal_status?: string;
    intake_status?: string;
    rejection_reason?: string;
    receipt_evidence_id?: string;
    notes?: string;
  }
): Promise<LaboratoryReceiptRecord> {
  return apiFetch<LaboratoryReceiptRecord>(
    `/agriculture/projects/${projectId}/physical-samples/${sampleId}/lab-receipt`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function recordSampleLaboratoryAnalysis(
  projectId: string,
  sampleId: string,
  payload: {
    laboratory_name: string;
    laboratory_accreditation?: string;
    analysis_batch_id?: string;
    analytical_method?: string;
    method_standard_code?: string;
    analysis_date: string;
    report_reference_number?: string;
    analyst_name?: string;
    evidence_id?: string;
    results: Array<{
      analyte: string;
      raw_value: number;
      raw_unit: string;
      normalized_value?: number;
      normalized_unit?: string;
      normalization_method?: string;
      detection_limit?: number;
      uncertainty_pct?: number;
      qualifier?: string;
    }>;
  }
): Promise<LaboratoryAnalysisRecord> {
  return apiFetch<LaboratoryAnalysisRecord>(
    `/agriculture/projects/${projectId}/physical-samples/${sampleId}/lab-analyses`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function reviseLaboratoryResult(
  projectId: string,
  resultId: string,
  payload: {
    new_raw_value: number;
    new_raw_unit: string;
    revision_reason: string;
    new_normalized_value?: number;
    new_normalized_unit?: string;
    normalization_method?: string;
    detection_limit?: number;
    uncertainty_pct?: number;
    qualifier?: string;
  }
): Promise<LaboratoryResultRecord> {
  return apiFetch<LaboratoryResultRecord>(
    `/agriculture/projects/${projectId}/laboratory-results/${resultId}/revise`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function recordSampleQAReview(
  projectId: string,
  sampleId: string,
  payload: {
    reviewer_name: string;
    review_date?: string;
    overall_qa_status: string;
    location_verified?: boolean;
    deviation_acceptable?: boolean;
    depth_valid?: boolean;
    custody_complete?: boolean;
    lab_receipt_verified?: boolean;
    required_assays_present?: boolean;
    notes?: string;
  }
): Promise<SampleQAReviewRecord> {
  return apiFetch<SampleQAReviewRecord>(
    `/agriculture/projects/${projectId}/physical-samples/${sampleId}/qa-review`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchGroundEvidenceReadiness(
  projectId: string
): Promise<GroundEvidenceReadinessData | null> {
  return apiFetch<GroundEvidenceReadinessData>(
    `/agriculture/projects/${projectId}/ground-evidence-readiness`
  ).catch(() => null);
}

// ---------------------------------------------------------------------------
// Phase 3A: Quantification Readiness & Calculation Input Contract Types & APIs
// ---------------------------------------------------------------------------

export interface QuantificationReadinessDimension {
  dimension: string;
  status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED" | "NOT_APPLICABLE";
  message: string;
  evaluated_at?: string;
  details?: Record<string, unknown>;
}

export interface QuantificationReadinessData {
  project_id: string;
  overall_status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED";
  dimensions: Record<string, QuantificationReadinessDimension>;
  evaluated_at: string;
}

export interface QuantificationMeasurementItem {
  physical_sample_id: string;
  sample_code: string;
  sampling_point_id: string;
  point_code: string;
  land_unit_id: string;
  land_unit_code: string;
  stratum_id?: string | null;
  stratum_code?: string | null;
  laboratory_result_id: string;
  analyte: string;
  raw_value: number;
  raw_unit: string;
  normalized_value: number;
  normalized_unit: string;
  provenance_class: string;
  sampling_date: string;
  sample_depth_from_cm: number;
  sample_depth_to_cm: number;
  standard_depth_from_cm: number;
  standard_depth_to_cm: number;
  depth_alignment_status: "MATCH" | "PARTIAL_COVERAGE" | "OVERLAPPING_INTERVAL" | "OUT_OF_SCOPE" | "NEEDS_REVIEW";
  bulk_density_status: "PRESENT" | "MISSING" | "NOT_APPLICABLE";
  bulk_density_normalized_value?: number | null;
  bulk_density_normalized_unit?: string | null;
  coarse_fragments_status: "MEASURED_ZERO" | "MEASURED" | "NOT_MEASURED" | "NOT_APPLICABLE";
  coarse_fragments_fraction?: number | null;
  measurement_uncertainty?: number | null;
}

export interface ExcludedMeasurementItem {
  physical_sample_id: string;
  sample_code: string;
  sampling_point_id?: string | null;
  point_code?: string | null;
  land_unit_id?: string | null;
  land_unit_code?: string | null;
  exclusion_reasons: string[];
  rejection_details: Record<string, unknown>;
}

export interface EligibleMeasurementSetData {
  project_id: string;
  total_candidates: number;
  total_eligible: number;
  total_excluded: number;
  baseline_measurements: QuantificationMeasurementItem[];
  project_measurements: QuantificationMeasurementItem[];
  excluded_measurements: ExcludedMeasurementItem[];
  rule_set_version: string;
  methodology_code: string;
  methodology_version: string;
  boundary_version_id?: string | null;
  evaluated_at: string;
}

export interface QuantificationSnapshotItem {
  id: string;
  organization_id: string;
  project_id: string;
  snapshot_code: string;
  status: string;
  context: "BASELINE" | "MONITORING";
  period_start?: string | null;
  period_end?: string | null;
  methodology_code: string;
  methodology_version: string;
  rule_set_version: string;
  snapshot_hash: string;
  is_locked: boolean;
  locked_at?: string | null;
  locked_by_id?: string | null;
  created_by_id?: string | null;
  total_eligible_measurements: number;
  total_excluded_measurements: number;
  readiness_summary: Record<string, unknown>;
  input_package: Record<string, unknown>;
  source_evidence_ids: string[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export async function fetchQuantificationReadiness(
  projectId: string
): Promise<QuantificationReadinessData | null> {
  return apiFetch<QuantificationReadinessData>(
    `/agriculture/projects/${projectId}/quantification-readiness`
  ).catch(() => null);
}

export async function fetchEligibleMeasurements(
  projectId: string,
  campaignId?: string
): Promise<EligibleMeasurementSetData | null> {
  const query = campaignId ? `?campaign_id=${encodeURIComponent(campaignId)}` : "";
  return apiFetch<EligibleMeasurementSetData>(
    `/agriculture/projects/${projectId}/eligible-measurements${query}`
  ).catch(() => null);
}

export async function createQuantificationSnapshot(
  projectId: string,
  payload: {
    context: "BASELINE" | "MONITORING";
    period_start?: string;
    period_end?: string;
    campaign_id?: string;
    notes?: string;
  }
): Promise<QuantificationSnapshotItem> {
  return apiFetch<QuantificationSnapshotItem>(
    `/agriculture/projects/${projectId}/quantification-input-snapshots`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchQuantificationSnapshots(
  projectId: string
): Promise<QuantificationSnapshotItem[]> {
  return apiFetch<QuantificationSnapshotItem[]>(
    `/agriculture/projects/${projectId}/quantification-input-snapshots`
  ).catch(() => []);
}

export async function fetchQuantificationSnapshotDetail(
  projectId: string,
  snapshotId: string
): Promise<QuantificationSnapshotItem | null> {
  return apiFetch<QuantificationSnapshotItem>(
    `/agriculture/projects/${projectId}/quantification-input-snapshots/${snapshotId}`
  ).catch(() => null);
}

// ---------------------------------------------------------------------------
// Agriculture Phase 3B-0 Methodology Prerequisite Types & Client APIs
// ---------------------------------------------------------------------------

export interface PrerequisiteDimensionItem {
  status: "READY" | "INCOMPLETE" | "BLOCKED" | "NOT_APPLICABLE" | "NOT_CONFIGURED";
  requirement: "REQUIRED" | "OPTIONAL" | "CONDITIONAL";
  blocking: boolean;
  finding_type: "BLOCKING" | "NON_BLOCKING_ADVISORY" | "NOT_APPLICABLE";
  reason_code: string;
  message: string;
  details: Record<string, any>;
}

export interface PrerequisiteEvaluationData {
  project_id: string;
  overall_status: "READY" | "READY_WITH_ADVISORY" | "INCOMPLETE" | "BLOCKED";
  methodology_code: string;
  methodology_version: string;
  corrections_clarifications_version: string;
  rule_set_version: string;
  vcs_standard_version: string;
  governing_vcs_standard?: string;
  v5_template_variant?: string;
  project_description_template?: string;
  dimensions: Record<string, PrerequisiteDimensionItem>;
  blocking_reasons: string[];
  advisory_notes: string[];
  total_dimensions: number;
  evaluated_at: string;
  evaluation_hash: string;
}

export interface PrerequisiteAssessmentItem {
  id: string;
  organization_id: string;
  project_id: string;
  snapshot_id?: string | null;
  assessment_code: string;
  version: number;
  status: "PREVIEW" | "LOCKED" | "ARCHIVED" | "SUPERSEDED";
  overall_readiness: "READY" | "READY_WITH_ADVISORY" | "INCOMPLETE" | "BLOCKED";
  methodology_code: string;
  methodology_version: string;
  corrections_clarifications_version: string;
  rule_set_version: string;
  vcs_standard_version: string;
  governing_vcs_standard?: string;
  v5_template_variant?: string;
  project_description_template?: string;
  vcs_resolution_metadata: Record<string, any>;
  quantification_route_map: Record<string, any>;
  esm_input_dossier: Record<string, any>;
  sampling_design_assessment: Record<string, any>;
  uncertainty_input_readiness: Record<string, any>;
  baseline_monitoring_pairing: Record<string, any>;
  dimensions: Record<string, any>;
  blocking_reasons: string[];
  advisory_notes: string[];
  assessment_hash: string;
  is_locked: boolean;
  locked_at?: string | null;
  locked_by_id?: string | null;
  created_by_id?: string | null;
  superseded_by_id?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export async function fetchPrerequisiteReadiness(
  projectId: string,
  runPowerAnalysis: boolean = false,
  targetMdd?: number
): Promise<PrerequisiteEvaluationData | null> {
  const params = new URLSearchParams();
  if (runPowerAnalysis) params.append("run_power_analysis", "true");
  if (targetMdd !== undefined) params.append("target_mdd", String(targetMdd));
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<PrerequisiteEvaluationData>(
    `/agriculture/projects/${projectId}/prerequisites/readiness${query}`
  ).catch(() => null);
}

export async function evaluatePrerequisites(
  projectId: string,
  payload?: { run_power_analysis?: boolean; target_mdd?: number }
): Promise<PrerequisiteEvaluationData> {
  return apiFetch<PrerequisiteEvaluationData>(
    `/agriculture/projects/${projectId}/prerequisites/evaluate`,
    {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function lockPrerequisiteAssessment(
  projectId: string,
  payload: {
    snapshot_id?: string;
    notes?: string;
    run_power_analysis?: boolean;
    target_mdd?: number;
  }
): Promise<PrerequisiteAssessmentItem> {
  return apiFetch<PrerequisiteAssessmentItem>(
    `/agriculture/projects/${projectId}/prerequisites/lock`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchPrerequisiteAssessments(
  projectId: string
): Promise<PrerequisiteAssessmentItem[]> {
  return apiFetch<PrerequisiteAssessmentItem[]>(
    `/agriculture/projects/${projectId}/prerequisites/assessments`
  ).catch(() => []);
}

export async function fetchPrerequisiteAssessmentDetail(
  projectId: string,
  assessmentId: string
): Promise<PrerequisiteAssessmentItem | null> {
  return apiFetch<PrerequisiteAssessmentItem>(
    `/agriculture/projects/${projectId}/prerequisites/assessments/${assessmentId}`
  ).catch(() => null);
}

// ---------------------------------------------------------------------------
// Agriculture Phase 3B-1 SOC Stock & Equivalent Soil Mass Engine Types & APIs
// ---------------------------------------------------------------------------

export interface SOCLayerResultItem {
  id: string;
  stock_result_id: string;
  sample_id?: string | null;
  layer_index: number;
  depth_upper_cm: number | string;
  depth_lower_cm: number | string;
  layer_thickness_cm: number | string;
  bulk_density_g_cm3?: number | string | null;
  bulk_density_provenance: string;
  coarse_fragment_fraction?: number | string | null;
  coarse_fragment_provenance: string;
  soc_concentration_g_kg: number | string;
  laboratory_result_id?: string | null;
  layer_soil_mass_t_ha: number | string;
  layer_soc_mass_t_c_ha: number | string;
  cumulative_soil_mass_t_ha: number | string;
  cumulative_soc_mass_t_c_ha: number | string;
  fraction_in_reference_mass?: number | string | null;
  included_soil_mass_t_ha?: number | string | null;
  included_soc_mass_t_c_ha?: number | string | null;
  created_at: string;
}

export interface SOCStockResultItem {
  id: string;
  organization_id: string;
  project_id: string;
  quantification_unit_id?: string | null;
  stratum_id?: string | null;
  sampling_point_id?: string | null;
  campaign_id?: string | null;
  prerequisite_assessment_id: string;
  input_snapshot_id?: string | null;
  stock_snapshot_id?: string | null;
  result_code: string;
  measurement_period_type: "BASELINE" | "MONITORING";
  aggregation_level: "SAMPLE_POINT" | "STRATUM" | "QUANTIFICATION_UNIT" | "PROJECT";
  methodology_version: string;
  corrections_clarifications_version: string;
  calculation_engine_version: string;
  esm_algorithm: string;
  reference_soil_mass_t_ha: number | string;
  reference_depth_cm: number | string;
  equivalent_depth_cm?: number | string | null;
  total_sampled_soil_mass_t_ha?: number | string | null;
  max_sampled_depth_cm?: number | string | null;
  soc_stock_t_c_per_ha: number | string;
  unadjusted_stock_t_c_per_ha?: number | string | null;
  shallow_soil_exception_applied: boolean;
  depth_sufficiency_status: string;
  area_ha?: number | string | null;
  sample_count: number;
  strata_weights: Record<string, any>;
  component_breakdown: Record<string, any>;
  result_status: string;
  calculation_hash: string;
  input_snapshot_hash: string;
  created_by_id?: string | null;
  superseded_by_id?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  layers?: SOCLayerResultItem[];
}

export interface SOCStockEvaluationData {
  project_id: string;
  prerequisite_assessment_id: string;
  measurement_period_type: "BASELINE" | "MONITORING";
  status: "EVALUATED" | "BLOCKED";
  esm_algorithm: string;
  reference_soil_mass_t_ha: number | string;
  reference_depth_cm: number | string;
  sample_point_results: any[];
  stratum_results: any[];
  project_soc_stock_t_c_per_ha?: number | string | null;
  total_area_ha?: number | string | null;
  carbon_accounting_status: string;
  net_tco2e_removals: null;
  blocking_reasons: string[];
  advisory_notes: string[];
  evaluation_hash: string;
}

export async function evaluateSOCStock(
  projectId: string,
  payload: {
    prerequisite_assessment_id?: string;
    snapshot_id?: string;
    measurement_period_type?: "BASELINE" | "MONITORING";
    reference_depth_cm?: number;
    reference_soil_mass_t_ha?: number;
    esm_algorithm?: string;
  }
): Promise<SOCStockEvaluationData> {
  return apiFetch<SOCStockEvaluationData>(
    `/agriculture/projects/${projectId}/soc-stock/evaluate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function calculateSOCStock(
  projectId: string,
  payload: {
    prerequisite_assessment_id: string;
    snapshot_id?: string;
    measurement_period_type?: "BASELINE" | "MONITORING";
    reference_depth_cm?: number;
    reference_soil_mass_t_ha?: number;
    esm_algorithm?: string;
    notes?: string;
  }
): Promise<SOCStockResultItem> {
  return apiFetch<SOCStockResultItem>(
    `/agriculture/projects/${projectId}/soc-stock/calculate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchSOCStockResults(
  projectId: string,
  periodType?: "BASELINE" | "MONITORING",
  aggregationLevel?: string
): Promise<SOCStockResultItem[]> {
  const params = new URLSearchParams();
  if (periodType) params.append("measurement_period_type", periodType);
  if (aggregationLevel) params.append("aggregation_level", aggregationLevel);
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<SOCStockResultItem[]>(
    `/agriculture/projects/${projectId}/soc-stock/results${q}`
  ).catch(() => []);
}

export async function fetchSOCStockResultDetail(
  projectId: string,
  resultId: string
): Promise<SOCStockResultItem | null> {
  return apiFetch<SOCStockResultItem>(
    `/agriculture/projects/${projectId}/soc-stock/results/${resultId}`
  ).catch(() => null);
}

export async function fetchSOCStockResultComponents(
  projectId: string,
  resultId: string
): Promise<Record<string, any> | null> {
  return apiFetch<Record<string, any>>(
    `/agriculture/projects/${projectId}/soc-stock/results/${resultId}/components`
  ).catch(() => null);
}

// ---------------------------------------------------------------------------
// Phase 3B-2: SOC Stock Change & Uncertainty Quantification Types & API
// ---------------------------------------------------------------------------

export interface SOCChangeResultItem {
  id: string;
  organization_id: string;
  project_id: string;
  baseline_stock_result_id: string;
  monitoring_stock_result_id: string;
  prerequisite_assessment_id: string;
  result_code: string;
  methodology_version: string;
  corrections_clarifications_version: string;
  calculation_engine_version: string;
  quantification_approach: string;
  t_start: string;
  t_final: string;
  elapsed_years: number | string;
  esm_algorithm: string;
  reference_soil_mass_t_ha: number | string;
  reference_depth_cm: number | string;
  total_project_area_ha: number | string;
  baseline_mean_soc_t_c_per_ha: number | string;
  monitoring_mean_soc_t_c_per_ha: number | string;
  delta_soc_project_t_c_ha_yr: number | string;
  delta_soc_baseline_t_c_ha_yr: number | string;
  delta_soc_net_t_c_ha_yr: number | string;
  delta_co2_project_tco2e_ha_yr: number | string;
  delta_co2_baseline_tco2e_ha_yr: number | string;
  delta_co2_net_tco2e_ha_yr: number | string;
  total_project_delta_co2_tco2e_yr: number | string;
  total_baseline_delta_co2_tco2e_yr: number | string;
  total_net_delta_co2_tco2e_yr: number | string;
  baseline_soc_change_tco2e_yr: number | string;
  project_soc_change_tco2e_yr: number | string;
  qa2_net_soc_effect_tco2e_yr: number | string;
  uncertainty_adjusted_soc_effect_tco2e_yr: number | string;
  sign_indicator: number;
  eq44_eq45_status: string;
  df_estimator: string;
  co2_to_c_ratio: number | string;
  variance_delta_soc_project: number | string;
  variance_delta_soc_baseline: number | string;
  total_variance_delta_soc: number | string;
  standard_error_delta_soc_t_c_ha_yr: number | string;
  standard_error_tco2e_yr: number | string;
  degrees_of_freedom: number;
  student_t_value_0667: number | string;
  relative_uncertainty_pct: number | string;
  allowable_uncertainty_pct: number | string;
  uncertainty_deduction_pct: number | string;
  uncertainty_deduction_fraction: number | string;
  adjusted_net_delta_co2_tco2e_yr: number | string;
  measurement_error_status: string;
  measurement_error_router: string;
  strata_results: any[];
  component_breakdown: Record<string, any>;
  carbon_accounting_status: string;
  ledger_status: string;
  result_status: string;
  calculation_hash: string;
  input_snapshot_hash: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface SOCChangeEvaluationData {
  project_id: string;
  status: "EVALUATED" | "BLOCKED";
  baseline_stock_result_id: string;
  monitoring_stock_result_id: string;
  elapsed_years: number | string;
  t_start: string;
  t_final: string;
  total_project_area_ha: number | string;
  delta_soc_project_t_c_ha_yr: number | string;
  delta_soc_baseline_t_c_ha_yr: number | string;
  delta_soc_net_t_c_ha_yr: number | string;
  delta_co2_net_tco2e_ha_yr: number | string;
  total_net_delta_co2_tco2e_yr: number | string;
  baseline_soc_change_tco2e_yr?: number | string;
  project_soc_change_tco2e_yr?: number | string;
  qa2_net_soc_effect_tco2e_yr?: number | string;
  uncertainty_adjusted_soc_effect_tco2e_yr?: number | string;
  sign_indicator?: number;
  eq44_eq45_status?: string;
  df_estimator?: string;
  adjusted_net_delta_co2_tco2e_yr: number | string;
  degrees_of_freedom: number;
  student_t_value_0667: number | string;
  relative_uncertainty_pct: number | string;
  uncertainty_deduction_pct: number | string;
  uncertainty_deduction_fraction: number | string;
  uncertainty_status: string;
  measurement_error_status: string;
  strata_results: any[];
  blocking_reasons: string[];
  evaluation_hash: string;
}

export async function evaluateSOCChange(
  projectId: string,
  payload: {
    baseline_stock_result_id: string;
    monitoring_stock_result_id: string;
    prerequisite_assessment_id?: string;
    laboratory_method?: string;
    lab_qa_verified?: boolean;
    active_lab_proficiency?: boolean;
    notes?: string;
  }
): Promise<SOCChangeEvaluationData> {
  return apiFetch<SOCChangeEvaluationData>(
    `/agriculture/projects/${projectId}/soc-change/evaluate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function finalizeSOCChange(
  projectId: string,
  payload: {
    baseline_stock_result_id: string;
    monitoring_stock_result_id: string;
    prerequisite_assessment_id: string;
    laboratory_method?: string;
    lab_qa_verified?: boolean;
    active_lab_proficiency?: boolean;
    notes?: string;
  }
): Promise<SOCChangeResultItem> {
  return apiFetch<SOCChangeResultItem>(
    `/agriculture/projects/${projectId}/soc-change/finalize`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchSOCChangeResults(
  projectId: string
): Promise<SOCChangeResultItem[]> {
  return apiFetch<SOCChangeResultItem[]>(
    `/agriculture/projects/${projectId}/soc-change/results`
  ).catch(() => []);
}

export async function fetchSOCChangeResultDetail(
  projectId: string,
  resultId: string
): Promise<SOCChangeResultItem | null> {
  return apiFetch<SOCChangeResultItem>(
    `/agriculture/projects/${projectId}/soc-change/results/${resultId}`
  ).catch(() => null);
}

export async function fetchSOCChangeResultComponents(
  projectId: string,
  resultId: string
): Promise<Record<string, any> | null> {
  return apiFetch<Record<string, any>>(
    `/agriculture/projects/${projectId}/soc-change/results/${resultId}/components`
  ).catch(() => null);
}

// ---------------------------------------------------------------------------
// Phase 3B-3: Net GHG Reductions & Removals & Section 8.7 VCU Readiness Types & API
// ---------------------------------------------------------------------------

export interface AgricultureVintageGHGResultItem {
  id: string;
  net_ghg_result_id: string;
  vintage_year: number;
  gross_reductions_er_tco2e: number | string;
  gross_removals_cr_tco2e: number | string;
  leakage_tco2e: number | string;
  leakage_er_lker_tco2e: number | string;
  leakage_cr_lkcr_tco2e: number | string;
  net_reductions_ernet_tco2e: number | string;
  net_removals_crnet_tco2e: number | string;
  total_net_ghg_errnet_tco2e: number | string;
  buffer_deduction_reductions_tco2e?: number | string | null;
  buffer_deduction_removals_tco2e?: number | string | null;
  total_buffer_deduction_tco2e?: number | string | null;
  internal_vcu_eligible_reductions_tco2e?: number | string | null;
  internal_vcu_eligible_removals_tco2e?: number | string | null;
  internal_vcu_eligible_total_tco2e?: number | string | null;
  vcu_readiness_status: string;
  vintage_details?: Record<string, any>;
  created_at: string;
}

export interface AgricultureNetGHGResultItem {
  id: string;
  organization_id: string;
  project_id: string;
  soc_change_result_id?: string | null;
  prerequisite_assessment_id: string;
  result_code: string;
  methodology_version: string;
  corrections_clarifications_version: string;
  calculation_engine_version: string;
  ruleset_version: string;
  verification_period_start: string;
  verification_period_end: string;
  elapsed_years: number | string;
  applicability_matrix: Record<string, any>;
  total_baseline_emissions_tco2e: number | string;
  total_project_emissions_tco2e: number | string;
  total_emission_reductions_from_sources_tco2e: number | string;
  eq44_baseline_total_carbon_stock_change_tco2e: number | string;
  eq45_project_total_carbon_stock_change_tco2e: number | string;
  eq44_eq45_status: string;
  gross_reductions_er_tco2e: number | string;
  gross_removals_cr_tco2e: number | string;
  total_leakage_tco2e: number | string;
  leakage_allocation_er_lker_tco2e: number | string;
  leakage_allocation_cr_lkcr_tco2e: number | string;
  net_reductions_ernet_tco2e: number | string;
  net_removals_crnet_tco2e: number | string;
  total_net_ghg_errnet_tco2e: number | string;
  npr_rating_pct?: number | string | null;
  risk_assessment_id?: string | null;
  buffer_deduction_reductions_tco2e?: number | string | null;
  buffer_deduction_removals_tco2e?: number | string | null;
  total_buffer_deduction_tco2e?: number | string | null;
  internal_vcu_eligible_reductions_tco2e?: number | string | null;
  internal_vcu_eligible_removals_tco2e?: number | string | null;
  internal_vcu_eligible_total_tco2e?: number | string | null;
  vcu_readiness_status: string;
  internal_mrv_status: string;
  vvb_status: string;
  registry_status: string;
  ledger_status: string;
  result_status: string;
  calculation_hash: string;
  input_snapshot_hash: string;
  created_by_id?: string | null;
  superseded_by_id?: string | null;
  notes?: string | null;
  component_breakdown: Record<string, any>;
  vintages: AgricultureVintageGHGResultItem[];
  created_at: string;
  updated_at: string;
}

export interface NetGHGEvaluationData {
  project_id: string;
  status: "EVALUATED" | "BLOCKED";
  verification_period_start: string;
  verification_period_end: string;
  elapsed_years: number | string;
  applicability_matrix: Record<string, any>;
  total_baseline_emissions_tco2e: number | string;
  total_project_emissions_tco2e: number | string;
  total_emission_reductions_from_sources_tco2e: number | string;
  eq44_baseline_total_carbon_stock_change_tco2e: number | string;
  eq45_project_total_carbon_stock_change_tco2e: number | string;
  gross_reductions_er_tco2e: number | string;
  gross_removals_cr_tco2e: number | string;
  total_leakage_tco2e: number | string;
  leakage_allocation_er_lker_tco2e: number | string;
  leakage_allocation_cr_lkcr_tco2e: number | string;
  net_reductions_ernet_tco2e: number | string;
  net_removals_crnet_tco2e: number | string;
  total_net_ghg_errnet_tco2e: number | string;
  npr_rating_pct?: number | string | null;
  buffer_deduction_reductions_tco2e?: number | string | null;
  buffer_deduction_removals_tco2e?: number | string | null;
  total_buffer_deduction_tco2e?: number | string | null;
  internal_vcu_eligible_reductions_tco2e?: number | string | null;
  internal_vcu_eligible_removals_tco2e?: number | string | null;
  internal_vcu_eligible_total_tco2e?: number | string | null;
  vcu_readiness_status: string;
  vintages: any[];
  blocking_reasons: string[];
  evaluation_hash: string;
  component_breakdown?: Record<string, any>;
}

export async function evaluateNetGHG(
  projectId: string,
  payload: Record<string, any>
): Promise<NetGHGEvaluationData> {
  return apiFetch<NetGHGEvaluationData>(
    `/agriculture/projects/${projectId}/net-ghg/evaluate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function finalizeNetGHG(
  projectId: string,
  payload: Record<string, any>
): Promise<AgricultureNetGHGResultItem> {
  return apiFetch<AgricultureNetGHGResultItem>(
    `/agriculture/projects/${projectId}/net-ghg/finalize`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchNetGHGResults(
  projectId: string
): Promise<AgricultureNetGHGResultItem[]> {
  return apiFetch<AgricultureNetGHGResultItem[]>(
    `/agriculture/projects/${projectId}/net-ghg/results`
  ).catch(() => []);
}

export async function fetchNetGHGResultDetail(
  projectId: string,
  resultId: string
): Promise<AgricultureNetGHGResultItem | null> {
  return apiFetch<AgricultureNetGHGResultItem>(
    `/agriculture/projects/${projectId}/net-ghg/results/${resultId}`
  ).catch(() => null);
}

export async function fetchNetGHGResultComponents(
  projectId: string,
  resultId: string
): Promise<Record<string, any> | null> {
  return apiFetch<Record<string, any>>(
    `/agriculture/projects/${projectId}/net-ghg/results/${resultId}/components`
  ).catch(() => null);
}



// ---------------------------------------------------------------------------
// Agriculture Laboratory Bulk Data Import Types & Client APIs
// ---------------------------------------------------------------------------

export interface LaboratoryImportRowItem {
  id: string;
  import_batch_id: string;
  organization_id: string;
  project_id: string;
  source_sheet_name?: string;
  source_row_number: number;
  raw_row_payload: Record<string, any>;
  mapped_payload: Record<string, any>;
  validation_status: "VALID" | "WARNING" | "ERROR" | "SKIPPED";
  validation_messages: Array<{ severity: "ERROR" | "WARNING"; code: string; message: string }>;
  matched_sample_id?: string;
  matched_sample_code?: string;
  canonical_analyte?: string;
  raw_value?: number;
  raw_unit?: string;
  normalized_value?: number;
  normalized_unit?: string;
  resulting_lab_result_id?: string;
  created_at: string;
  updated_at: string;
}

export interface LaboratoryImportBatchItem {
  id: string;
  organization_id: string;
  project_id: string;
  sampling_campaign_id?: string;
  laboratory_name?: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  file_sha256: string;
  evidence_id?: string;
  status: "UPLOADED" | "MAPPED" | "VALIDATED" | "VALIDATED_WITH_ERRORS" | "IMPORTED" | "PARTIALLY_IMPORTED" | "FAILED";
  source_type: string;
  uploaded_by?: string;
  uploaded_at: string;
  mapping_version: string;
  mapping_config: Record<string, any>;
  total_rows: number;
  valid_rows: number;
  warning_rows: number;
  error_rows: number;
  imported_rows: number;
  skipped_rows: number;
  error_summary: Array<{ row: number; sample_code: string; code: string; message: string }>;
  created_at: string;
  updated_at: string;
}

export interface LaboratoryImportValidationResult {
  batch_id: string;
  status: string;
  total_rows: number;
  valid_rows: number;
  warning_rows: number;
  error_rows: number;
  can_commit: boolean;
  preview_rows: LaboratoryImportRowItem[];
  error_summary: Array<{ row: number; sample_code: string; code: string; message: string }>;
}

export interface LaboratoryImportCommitResult {
  batch_id: string;
  status: string;
  imported_rows: number;
  skipped_rows: number;
  analyses_created: number;
  results_created: number;
  samples_analyzed: number;
  message: string;
}

export async function fetchLaboratoryImportBatches(
  projectId: string
): Promise<LaboratoryImportBatchItem[]> {
  return apiFetch<LaboratoryImportBatchItem[]>(
    `/agriculture/projects/${projectId}/laboratory-import/batches`
  ).catch(() => []);
}

export async function fetchLaboratoryImportBatch(
  projectId: string,
  batchId: string
): Promise<LaboratoryImportBatchItem | null> {
  return apiFetch<LaboratoryImportBatchItem>(
    `/agriculture/projects/${projectId}/laboratory-import/batches/${batchId}`
  ).catch(() => null);
}

export async function fetchLaboratoryImportRows(
  projectId: string,
  batchId: string,
  validationStatus?: string
): Promise<LaboratoryImportRowItem[]> {
  const query = validationStatus ? `?validation_status=${encodeURIComponent(validationStatus)}` : "";
  return apiFetch<LaboratoryImportRowItem[]>(
    `/agriculture/projects/${projectId}/laboratory-import/batches/${batchId}/rows${query}`
  ).catch(() => []);
}

export async function uploadLaboratoryBulkFile(
  projectId: string,
  file: File,
  laboratoryName?: string,
  campaignId?: string
): Promise<LaboratoryImportBatchItem> {
  const formData = new FormData();
  formData.append("file", file);

  const params = new URLSearchParams();
  if (laboratoryName) params.append("laboratory_name", laboratoryName);
  if (campaignId) params.append("sampling_campaign_id", campaignId);
  const qStr = params.toString() ? `?${params.toString()}` : "";

  return apiFetch<LaboratoryImportBatchItem>(
    `/agriculture/projects/${projectId}/laboratory-import/upload${qStr}`,
    {
      method: "POST",
      body: formData,
    }
  );
}

export async function validateLaboratoryImportBatch(
  projectId: string,
  batchId: string,
  payload: {
    mapping_config?: Record<string, any>;
    laboratory_name?: string;
    sampling_campaign_id?: string;
  }
): Promise<LaboratoryImportValidationResult> {
  return apiFetch<LaboratoryImportValidationResult>(
    `/agriculture/projects/${projectId}/laboratory-import/batches/${batchId}/validate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function commitLaboratoryImportBatch(
  projectId: string,
  batchId: string,
  payload: {
    import_valid_only?: boolean;
    laboratory_name?: string;
    notes?: string;
    import_as_revision?: boolean;
    revision_reason?: string;
  }
): Promise<LaboratoryImportCommitResult> {
  return apiFetch<LaboratoryImportCommitResult>(
    `/agriculture/projects/${projectId}/laboratory-import/batches/${batchId}/commit`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export function getLaboratoryImportTemplateUrl(projectId: string, format: "csv" | "xlsx" = "csv"): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  return `${base}/api/v1/agriculture/projects/${projectId}/laboratory-import/template?format=${format}`;
}

export function getLaboratoryImportErrorsUrl(projectId: string, batchId: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  return `${base}/api/v1/agriculture/projects/${projectId}/laboratory-import/batches/${batchId}/errors.csv`;
}


// ---------------------------------------------------------------------------
// Verification Packages & Auditor Workspace Types & Client APIs
// ---------------------------------------------------------------------------

export interface VerificationPackageSummary {
  id: string;
  project_id: string;
  organization_id: string;
  monitoring_period_start: string;
  monitoring_period_end: string;
  package_name: string;
  package_version: number;
  parent_package_id?: string | null;
  package_status: string;
  registry_target: string;
  audit_type: string;
  manifest_hash: string;
  ledger_signature_id?: string | null;
  sealed_at?: string | null;
  completeness_score: number;
  blocker_reasons: string[];
  created_at: string;
  updated_at: string;
}

export interface VerificationPackageDetail extends VerificationPackageSummary {
  manifest_json: Record<string, unknown>;
  diff_summary_json: Record<string, unknown>;
  sealed_by_user_id?: string | null;
}

export interface VerificationPackageFindingItem {
  id: string;
  package_id: string;
  finding_number: string;
  finding_type: "CAR" | "CL" | "FAR" | "NCR";
  severity: "CRITICAL" | "MAJOR" | "MINOR" | "OBSERVATION";
  title: string;
  description: string;
  target_domain: string;
  target_record_id?: string | null;
  target_field?: string | null;
  status: "OPEN" | "RESPONSE_SUBMITTED" | "RESOLVED" | "CLOSED";
  auditor_user_id?: string | null;
  auditor_organization?: string | null;
  project_response?: string | null;
  response_submitted_at?: string | null;
  resolved_at?: string | null;
  resolution_notes?: string | null;
  resolution_package_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface VerificationPackageEvidenceItem {
  id: string;
  package_id: string;
  evidence_category: string;
  reference_domain: string;
  reference_id: string;
  title: string;
  file_name: string;
  file_uri: string;
  file_size_bytes: number;
  sha256_hash: string;
  verified_hash?: string | null;
  integrity_status: "VERIFIED" | "INTEGRITY_MISMATCH" | "UNVERIFIED";
  uploaded_at?: string | null;
  created_at: string;
}

export interface VerificationAccessGrantItem {
  id: string;
  package_id: string;
  auditor_user_id?: string | null;
  auditor_email: string;
  auditor_organization: string;
  grantee_role: string;
  is_active: boolean;
  expires_at?: string | null;
  last_accessed_at?: string | null;
  created_at: string;
}

export interface MultiBiomassBlendComponent {
  lot_id: string;
  lot_number: string;
  source_id: string;
  source_code: string;
  source_name: string;
  biomass_type: string;
  waste_status: string;
  baseline_fate: string;
  sustainability_status: string;
  allocated_wet_mass_tonnes: number;
  allocated_dry_mass_tonnes: number;
  blend_pct_wet_basis: number;
  blend_pct_dry_basis: number;
  moisture_content_pct: number;
}

export interface MultiBiomassBlendBreakdown {
  production_run_id: string;
  run_number: string;
  total_wet_mass_tonnes: number;
  total_dry_mass_tonnes: number;
  component_count: number;
  components: MultiBiomassBlendComponent[];
}

export interface BiocharProductFormulationItem {
  id: string;
  organization_id: string;
  project_id?: string | null;
  product_name: string;
  product_code: string;
  target_sector: string;
  description?: string | null;
  biochar_target_ratio: number;
  is_active: boolean;
  created_at: string;
}

export interface BiocharProductBatchItem {
  id: string;
  organization_id: string;
  project_id?: string | null;
  formulation_id: string;
  batch_number: string;
  production_date: string;
  total_product_mass_tonnes: number;
  biochar_mass_tonnes: number;
  non_biochar_mass_tonnes: number;
  packaging_type?: string | null;
  storage_location?: string | null;
  created_at: string;
}

export async function fetchVerificationPackages(
  projectId?: string,
  packageStatus?: string
): Promise<VerificationPackageSummary[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (packageStatus) params.set("package_status", packageStatus);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<VerificationPackageSummary[]>(`/verification/packages${qs}`).catch(() => []);
}

export async function fetchVerificationPackage(packageId: string): Promise<VerificationPackageDetail> {
  return apiFetch<VerificationPackageDetail>(`/verification/packages/${packageId}`);
}

export async function compileVerificationPackage(data: {
  project_id: string;
  monitoring_period_start: string;
  monitoring_period_end: string;
  package_name: string;
  registry_target?: string;
  audit_type?: string;
}): Promise<VerificationPackageDetail> {
  return apiFetch<VerificationPackageDetail>("/verification/packages/compile", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function sealVerificationPackage(packageId: string): Promise<VerificationPackageDetail> {
  return apiFetch<VerificationPackageDetail>(`/verification/packages/${packageId}/seal`, {
    method: "POST",
  });
}

export async function fetchPackageEvidence(packageId: string): Promise<VerificationPackageEvidenceItem[]> {
  return apiFetch<VerificationPackageEvidenceItem[]>(`/verification/packages/${packageId}/evidence`).catch(() => []);
}

export async function verifyEvidenceIntegrity(
  packageId: string,
  evidenceId: string
): Promise<VerificationPackageEvidenceItem> {
  return apiFetch<VerificationPackageEvidenceItem>(
    `/verification/packages/${packageId}/evidence/${evidenceId}/verify`,
    {
      method: "POST",
    }
  );
}

export async function verifyAllEvidenceIntegrity(packageId: string): Promise<{
  total_evidence_items: number;
  verified_count: number;
  mismatch_count: number;
  unverified_count: number;
  all_passed: boolean;
}> {
  return apiFetch<{
    total_evidence_items: number;
    verified_count: number;
    mismatch_count: number;
    unverified_count: number;
    all_passed: boolean;
  }>(`/verification/packages/${packageId}/evidence/verify-all`, {
    method: "POST",
  });
}

export async function fetchPackageFindings(
  packageId: string,
  filters?: { status?: string; severity?: string; domain?: string }
): Promise<VerificationPackageFindingItem[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.domain) params.set("domain", filters.domain);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<VerificationPackageFindingItem[]>(`/verification/packages/${packageId}/findings${qs}`).catch(() => []);
}

export async function createPackageFinding(
  packageId: string,
  data: {
    finding_type: string;
    severity: string;
    title: string;
    description: string;
    target_domain: string;
    target_record_id?: string;
    target_field?: string;
  }
): Promise<VerificationPackageFindingItem> {
  return apiFetch<VerificationPackageFindingItem>(`/verification/packages/${packageId}/findings`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function respondToFinding(
  findingId: string,
  data: { project_response: string }
): Promise<VerificationPackageFindingItem> {
  return apiFetch<VerificationPackageFindingItem>(`/verification/findings/${findingId}/respond`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function resolveFinding(
  findingId: string,
  data: { status_action: "RESOLVED" | "CLOSED"; resolution_notes: string }
): Promise<VerificationPackageFindingItem> {
  return apiFetch<VerificationPackageFindingItem>(`/verification/findings/${findingId}/resolve`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function recordAuditDecision(
  packageId: string,
  data: { decision: "VERIFIED" | "REJECTED"; decision_notes: string }
): Promise<VerificationPackageDetail> {
  return apiFetch<VerificationPackageDetail>(`/verification/packages/${packageId}/decision`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchPackageGrants(packageId: string): Promise<VerificationAccessGrantItem[]> {
  return apiFetch<VerificationAccessGrantItem[]>(`/verification/packages/${packageId}/grants`).catch(() => []);
}

export async function grantAuditorAccess(
  packageId: string,
  data: {
    auditor_email: string;
    auditor_organization: string;
    grantee_role?: string;
    expires_at?: string;
  }
): Promise<VerificationAccessGrantItem> {
  return apiFetch<VerificationAccessGrantItem>(`/verification/packages/${packageId}/grants`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function exportPackageBundle(packageId: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/verification/packages/${packageId}/export`);
}

export async function downloadEvidenceContent(packageId: string, evidenceId: string, fallbackFileName?: string): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("vf_token") : null;
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const res = await fetch(`${base}/verification/packages/${packageId}/evidence/${evidenceId}/content`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Failed to download evidence" }));
    throw new Error(errorData.detail || `Download failed with status ${res.status}`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition");
  let filename = fallbackFileName || `evidence-${evidenceId}`;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) filename = match[1];
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function downloadPackageArchive(packageId: string, packageName?: string): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("vf_token") : null;
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const res = await fetch(`${base}/verification/packages/${packageId}/export/archive`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Failed to export archive" }));
    throw new Error(errorData.detail || `Export failed with status ${res.status}`);
  }
  const blob = await res.blob();
  const filename = `${packageName || "verification-package"}-archive.zip`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function fetchFeedstockBlendBreakdown(runId: string): Promise<MultiBiomassBlendBreakdown> {
  return apiFetch<MultiBiomassBlendBreakdown>(`/biochar/runs/${runId}/blend-breakdown`);
}

export async function fetchProductFormulations(projectId?: string): Promise<BiocharProductFormulationItem[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<BiocharProductFormulationItem[]>(`/biochar/product-formulations${query}`).catch(() => []);
}

export async function createProductFormulation(data: {
  product_name: string;
  product_code: string;
  target_sector: string;
  description?: string;
  biochar_target_ratio?: number;
  project_id?: string;
}): Promise<BiocharProductFormulationItem> {
  return apiFetch<BiocharProductFormulationItem>("/biochar/product-formulations", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchProductBatches(
  projectId?: string,
  formulationId?: string
): Promise<BiocharProductBatchItem[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (formulationId) params.set("formulation_id", formulationId);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<BiocharProductBatchItem[]>(`/biochar/product-batches${qs}`).catch(() => []);
}

export async function createProductBatch(data: {
  formulation_id: string;
  batch_number: string;
  production_date: string;
  total_product_mass_tonnes: number;
  biochar_mass_tonnes: number;
  non_biochar_mass_tonnes?: number;
  packaging_type?: string;
  storage_location?: string;
  biochar_batch_allocations: { biochar_batch_id: string; allocated_biochar_mass_tonnes: number }[];
  non_biochar_ingredients?: {
    ingredient_name: string;
    ingredient_type: string;
    mass_tonnes: number;
    mass_pct: number;
    supplier?: string;
  }[];
  project_id?: string;
}): Promise<BiocharProductBatchItem> {
  return apiFetch<BiocharProductBatchItem>("/biochar/product-batches", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ─── Earth Observation & Satellite MRV API ───

export interface EOProviderCapabilityInfo {
  provider_code: string;
  capability: string;
  is_configured: boolean;
}

export interface EOProviderMatrixResponse {
  providers: Record<string, EOProviderCapabilityInfo>;
}

export interface ProjectAOIResponse {
  status: "NO_AOI" | "CONFIGURED";
  message?: string;
  aoi?: {
    id: string;
    project_id: string;
    name: string;
    aoi_type: string;
    boundary_version_id?: string;
    geometry_geojson: any;
    bbox: { min_lon: number; min_lat: number; max_lon: number; max_lat: number };
    area_ha: number;
    crs: string;
    is_active: boolean;
    created_at: string;
  };
}

export interface ProjectBoundaryVersionItem {
  id: string;
  project_id: string;
  version_number: number;
  effective_date: string;
  source: string;
  reason?: string;
  area_ha: number;
  perimeter_m?: number;
  centroid_lat?: number;
  centroid_lon?: number;
  crs: string;
  created_at: string;
}

export interface EOObservationItem {
  id: string;
  project_id: string;
  aoi_id?: string;
  provider_code: string;
  platform: string;
  sensor: string;
  product_code: string;
  scene_id: string;
  acquisition_timestamp: string;
  spatial_resolution_m: number;
  cloud_cover_pct?: number;
  quality_status: string;
  observation_type: string;
  processing_level: string;
  provenance_hash: string;
  is_baseline: boolean;
  geometry_geojson?: any;
  bbox?: Record<string, number>;
  raw_band_uris?: Record<string, string>;
  asset_uri?: string;
  quality_flags?: Record<string, any>;
  created_at: string;
}

export interface EODerivedLayerItem {
  id: string;
  project_id: string;
  observation_id: string;
  aoi_id?: string;
  layer_type: string;
  formula_identifier: string;
  formula: string;
  band_mapping: Record<string, any>;
  processor_version: string;
  spatial_resolution_m: number;
  statistics: { mean?: number; min?: number; max?: number; std?: number };
  quality_status: string;
  provenance_hash: string;
  created_at: string;
}

export interface EOSpatialAnomalyItem {
  id: string;
  project_id: string;
  aoi_id?: string;
  observation_id?: string;
  anomaly_type: string;
  severity: string;
  status: string;
  description: string;
  review_recommendation: string;
  comparison_metric?: string;
  delta_value?: number;
  detected_at: string;
  corroborated_at?: string;
  corroboration_notes?: string;
}

export async function fetchEOProviders(): Promise<EOProviderMatrixResponse> {
  return apiFetch<EOProviderMatrixResponse>("/earth-observation/providers").catch(() => ({
    providers: {},
  }));
}

export async function fetchProjectActiveAOI(projectId: string): Promise<ProjectAOIResponse> {
  return apiFetch<ProjectAOIResponse>(`/earth-observation/projects/${projectId}/aoi`).catch(() => ({
    status: "NO_AOI",
    message: "No boundary configured.",
  }));
}

export async function setProjectBoundary(
  projectId: string,
  data: {
    name?: string;
    geometry_geojson: any;
    source?: string;
    reason?: string;
  }
): Promise<any> {
  return apiFetch<any>(`/earth-observation/projects/${projectId}/boundary`, {
    method: "POST",
    body: JSON.stringify({
      name: data.name || "Project Boundary",
      geometry_geojson: data.geometry_geojson,
      source: data.source || "DECLARED",
      reason: data.reason,
    }),
  });
}

export async function fetchBoundaryHistory(projectId: string): Promise<ProjectBoundaryVersionItem[]> {
  return apiFetch<ProjectBoundaryVersionItem[]>(
    `/earth-observation/projects/${projectId}/boundary-history`
  ).catch(() => []);
}

export async function fetchProjectObservations(
  projectId: string,
  params?: {
    aoi_id?: string;
    is_baseline?: boolean;
    provider_code?: string;
    limit?: number;
  }
): Promise<EOObservationItem[]> {
  const query = new URLSearchParams();
  if (params?.aoi_id) query.set("aoi_id", params.aoi_id);
  if (params?.is_baseline !== undefined) query.set("is_baseline", String(params.is_baseline));
  if (params?.provider_code) query.set("provider_code", params.provider_code);
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<EOObservationItem[]>(
    `/earth-observation/projects/${projectId}/observations${qs}`
  ).catch(() => []);
}

export async function fetchDerivedLayers(
  projectId: string,
  params?: {
    observation_id?: string;
    layer_type?: string;
  }
): Promise<EODerivedLayerItem[]> {
  const query = new URLSearchParams();
  if (params?.observation_id) query.set("observation_id", params.observation_id);
  if (params?.layer_type) query.set("layer_type", params.layer_type);
  const qs = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<EODerivedLayerItem[]>(
    `/earth-observation/projects/${projectId}/derived-layers${qs}`
  ).catch(() => []);
}

export async function computeDerivedLayer(
  projectId: string,
  data: {
    observation_id: string;
    layer_type: string;
    statistics: Record<string, number>;
    asset_uri?: string;
  }
): Promise<EODerivedLayerItem> {
  return apiFetch<EODerivedLayerItem>(
    `/earth-observation/projects/${projectId}/derived-layers`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function fetchProjectSpatialAnomalies(
  projectId: string,
  params?: {
    status?: string;
    severity?: string;
  }
): Promise<EOSpatialAnomalyItem[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.severity) query.set("severity", params.severity);
  const qs = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<EOSpatialAnomalyItem[]>(
    `/earth-observation/projects/${projectId}/anomalies${qs}`
  ).catch(() => []);
}

export async function corroborateSpatialAnomaly(
  anomalyId: string,
  data: {
    corroborated: boolean;
    notes: string;
    verification_task_id?: string;
  }
): Promise<EOSpatialAnomalyItem> {
  return apiFetch<EOSpatialAnomalyItem>(
    `/earth-observation/anomalies/${anomalyId}/corroborate`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function compileBaselinePackage(
  projectId: string,
  data?: { notes?: string }
): Promise<any> {
  return apiFetch<any>(
    `/earth-observation/projects/${projectId}/baseline-package`,
    {
      method: "POST",
      body: JSON.stringify(data || {}),
    }
  );
}

export async function fetchMRVManifest(projectId: string): Promise<any> {
  return apiFetch<any>(`/earth-observation/projects/${projectId}/manifest`);
}

export async function verifyCOGAsset(
  projectId: string,
  observationId: string,
  assetKey: string = "visual"
): Promise<{
  asset_url: string;
  http_status: number;
  is_partial_content: boolean;
  content_range?: string;
  content_type?: string;
  bytes_read?: number;
  magic_bytes_hex?: string;
  is_valid_geotiff_header: boolean;
  observation_id: string;
  asset_key: string;
  project_id: string;
  ssrf_blocked?: boolean;
  verified_at: string;
}> {
  const params = new URLSearchParams({
    observation_id: observationId,
    asset_key: assetKey,
  });
  return apiFetch<any>(
    `/earth-observation/projects/${projectId}/verify-cog-asset?${params.toString()}`
  );
}
