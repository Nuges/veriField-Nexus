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
  requires_password_change: boolean;
  sector: string;
  licensed_sectors: string[] | null;
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
  methodology_id: string;
  registry_id: string | null;
  baseline_parameters: Record<string, any>;
  created_at: string;
}

export interface CarbonCalculation {
  id: string;
  project_id: string;
  activity_id: string;
  methodology_used: string;
  tco2e_generated: number;
  calculation_log: any;
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
