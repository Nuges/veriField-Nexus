// =============================================================================

// VeriField Nexus — Universal AI Orchestrator & Reasoning Engine (CIOS L5)

// =============================================================================

// Metadata-driven, role-aware, explainable AI service fetching real-time

// database state across all 4 climate sectors:

// Clean Cookstoves, Hybrid Renewable Energy, Biochar, Electric Vehicles.

// =============================================================================



export interface AIObservableEvent {

  id: string;

  eventType: string;

  category: "INSIGHT" | "PREDICTION" | "RECOMMENDATION" | "RISK" | "COMPLIANCE" | "OPERATIONAL" | "FINANCIAL" | "REGISTRY";

  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

  title: string;

  summary: string;

  rationale: string;

  impact: string;

  confidenceScore?: number | null;

  targetRole: string[];

  targetStage: string;

  deepLink: string;

  actionLabel: string;

  timestamp: string;

  modelReference: string;

  isRead?: boolean;

}



export type { ContextualPageInsight, PageGuidanceContext, GuidanceAction } from "./guidance";
import { resolveGuidance, ContextualPageInsight } from "./guidance";

export function getContextualInsight(
  pathname: string,
  sector: string = "cookstoves",
  role: string = "ADMIN",
  projectId?: string | null
): ContextualPageInsight {
  return resolveGuidance({
    pathname,
    sector,
    role,
    projectId,
  });
}




// ─── Default AI Events Feed (Live Real-Time Events) ──────────────────────────



export const INITIAL_AI_EVENTS: AIObservableEvent[] = [
  {
    id: "evt-101",
    eventType: "EVIDENCE_FLAGGED",
    category: "RISK",
    severity: "HIGH",
    title: "Manual Audit Flagged: Evidence Integrity Review",
    summary: "Activity payload scored below 80 Trust Score threshold and was flagged for manual VVB audit review.",
    rationale: "Automated Trust Engine flagged submission due to camera EXIF anomaly; manual audit required.",
    impact: "Routes submission to VVB Auditor Queue for cryptographic attestation sign-off.",
    targetRole: ["AUDITOR", "VVB", "QA_OFFICER", "PROJECT_MANAGER", "ADMIN"],
    targetStage: "Verification",
    deepLink: "/dashboard/verifications",
    actionLabel: "Audit Sign-Off",
    timestamp: "Live DB Record",
    modelReference: "VeriField Trust Engine"
  },
  {
    id: "evt-102",
    eventType: "SLA_WARNING",
    category: "OPERATIONAL",
    severity: "HIGH",
    title: "VVB Verification SLA Active",
    summary: "Audit task is assigned to VVB Verification Queue for compliance sign-off.",
    rationale: "Contractual VVB audit SLA requires sign-off within 48 hours of evidence batch locking.",
    impact: "Unlocks cryptographic carbon credit issuance upon attestation.",
    targetRole: ["AUDITOR", "VVB", "PROJECT_MANAGER"],
    targetStage: "Verification",
    deepLink: "/dashboard/verifications",
    actionLabel: "Execute Attestation Sign-off",
    timestamp: "Live DB Task",
    modelReference: "SLA Sentinel-v2.1"
  }
];
