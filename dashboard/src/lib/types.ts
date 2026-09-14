// =============================================================================

// VeriField Nexus — Dashboard TypeScript Types

// =============================================================================

// Shared type definitions for all dashboard components.

// =============================================================================



export interface User {

  id: string;

  email: string | null;

  phone: string | null;

  full_name: string;

  role: string;

  avatar_url: string | null;

  organization: string | null;

  organization_id: string | null;

  is_active: boolean;
  status?: string;
  requires_password_change: boolean;

  sector?: string;

  licensed_sectors: string[] | null;

  licensed_methodologies?: string[] | null;

  country: string | null;

  project_type: string | null;

  created_at: string;

  updated_at: string;

}



export interface Activity {

  id: string;

  user_id: string;

  agent_name?: string | null;

  property_id: string | null;

  activity_type: string;

  activity_data: Record<string, unknown> | null;

  description: string | null;

  image_url: string | null;

  image_hash?: string | null;

  latitude: number | null;

  longitude: number | null;

  gps_accuracy: number | null;

  environment_type: string | null;

  radius_used_m: number | null;

  duplicate_flag: boolean | null;

  override_reason: string | null;

  captured_at: string;

  submitted_at: string;

  trust_score: number | null;

  trust_flags: Record<string, unknown> | null;

  status: string;

  pipeline_stage?: string | null;

  validation_status?: string | null;

  trust_status?: string | null;

  client_id: string | null;

  applied_quantity_kg?: number | null;

  biochar_batch_id?: string | null;

  sector?: string | null;

  created_at: string;

}



export interface ActivityListResponse {

  activities: Activity[];

  total: number;

  page: number;

  per_page: number;

  total_pages: number;

}



export interface Property {

  id: string;

  owner_id: string;

  name: string;

  address: string | null;

  property_type: string;

  latitude: number | null;

  longitude: number | null;

  sustainability_metrics: Record<string, unknown> | null;

  environment_type?: string;

  verification_status?: string;

  project_id?: string | null;
  organization_id?: string | null;
  sector?: string | null;
  created_at: string;
  updated_at: string;
}



export interface TrustScoreBreakdown {

  activity_id: string;

  gps_score: number;

  image_score: number;

  frequency_score: number;

  final_score: number;

  flags: Record<string, unknown> | null;

  calculated_at: string;

}



export interface TrustDistribution {

  high: number;

  medium: number;

  low: number;

  unscored: number;

}



export interface AnalyticsOverview {

  total_submissions: number;

  total_users: number;

  total_properties: number;

  avg_trust_score: number | null;

  flagged_activities: number;

  submissions_today: number;

  submissions_this_week: number;

}



export interface DailySubmission {

  date: string;

  count: number;

  avg_trust_score: number | null;

}



export interface ActivityTypeSummary {

  activity_type: string;

  count: number;

  percentage: number;

  avg_trust_score: number | null;

}



export interface AnalyticsTrends {

  daily_submissions: DailySubmission[];

  activity_types: ActivityTypeSummary[];

  trust_distribution: TrustDistribution;

}



export interface Project {
  id: string;
  name: string;
  project_code?: string | null;
  methodology_id: string;
  sector_id?: string | null;
  sector?: string | null;
  country?: string | null;
  organization_id?: string | null;
  status?: string | null;
  registry_id: string | null;
  baseline_parameters: Record<string, unknown>;
  created_at: string;
}

export interface CarbonCalculation {
  id: string;
  project_id: string;
  activity_id: string;
  methodology_used: string;
  tco2e_generated: number;
  calculation_log: Record<string, unknown> | null;
  status: string;
  created_at: string;
}



export interface AgentPerformance {

  id: string;

  full_name: string;

  email: string | null;

  role: string;

  organization: string | null;

  total_submissions: number;

  avg_trust_score: number | null;

  flagged_count: number;

  flag_rate: number;

  suspicious: boolean;

  status?: string;

}



export interface AgentPerformanceResponse {
  agents: AgentPerformance[];
  total_agents: number;
  suspicious_count: number;
}

export interface Organization {
  id: string;
  name: string;
  org_type: string;
  status: string;
  parent_id?: string | null;
  metadata_context?: Record<string, unknown>;
  version?: number;
  plan?: string;
  max_installations?: number;
  max_agents?: number;
  licensed_sectors?: string[] | null;
  licensed_methodologies?: string[] | null;
  created_at: string;
  updated_at?: string;
}

export interface AuditFinding {
  id: string;
  project_id: string;
  activity_id?: string | null;
  auditor_id?: string | null;
  severity: string;
  finding_type: string;
  description: string;
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface LedgerTransaction {
  id: string;
  project_id?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  details?: Record<string, unknown>;
  created_at: string;
}

export interface CarbonMintResponse {
  status: string;
  message: string;
  batch_id: string;
  serial_number: string;
  total_tco2e: number;
  target_chain: string;
  recipient_wallet: string;
  transaction_signature: string;
  explorer_url: string;
  payload_hash: string;
  signature_hash: string;
  minted_at: string;
  records_minted: number;
}

export interface StandardApiResponse<T = unknown> {
  success: boolean;
  data: T;
  message?: string;
  errors?: string[];
  pagination?: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
  metadata?: Record<string, unknown>;
}
