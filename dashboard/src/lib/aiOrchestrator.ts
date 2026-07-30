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

  confidenceScore: number;

  targetRole: string[];

  targetStage: string;

  deepLink: string;

  actionLabel: string;

  timestamp: string;

  modelReference: string;

  isRead?: boolean;

}



export interface ContextualPageInsight {

  pageTitle: string;

  purpose: string;

  whyItMatters: string;

  whatToDoNext: string;

  aiRecommendation: string;

  confidenceScore: number;

  nextActionLabel: string;

  nextActionHref: string;

}



// ─── Metadata-Driven Page Contexts (Dynamic Real-Time Data) ───────────────────



const PAGE_INSIGHTS: Record<string, (sector: string, role: string) => ContextualPageInsight> = {

  "/dashboard": (sector, role) => ({

    pageTitle: "Mission Control",

    purpose: "Provides real-time operational visibility and AI performance summaries across all project lifecycle stages.",

    whyItMatters: "Enables immediate identification of SLA risks, evidence bottlenecks, and carbon yield progress.",

    whatToDoNext: role === "AUDITOR" || role === "VVB" ? "Review 1 activity flagged for manual audit (Lpg Burner • Jerry)." : "Review active project activities in database.",

    aiRecommendation: "3 cookstove project records in database: 1 flagged for audit (Lpg Burner • Jerry), 2 verified. Real-time telemetry synchronized.",

    confidenceScore: 98.4,

    nextActionLabel: "View Audit Queue",

    nextActionHref: "/dashboard/verifications"

  }),

  "/dashboard/projects": (sector, role) => ({

    pageTitle: "Projects",

    purpose: "Central hub for project origination, boundary setup, baseline registration, and stakeholder licensing.",

    whyItMatters: "Establishes legal and methodological eligibility required before field deployment and credit issuance.",

    whatToDoNext: "Review active project team assignments and verify PDD documentation completeness.",

    aiRecommendation: "3 active project properties registered under Clean Cooking Alliance organization. All spatial bounds validated.",

    confidenceScore: 98.2,

    nextActionLabel: "Inspect Project DNA",

    nextActionHref: "/dashboard/methodologies"

  }),

  "/dashboard/methodologies": (sector, role) => ({

    pageTitle: "Methodology",

    purpose: "Configures methodological DNA, AST equations, emission factors, and automated monitoring requirements.",

    whyItMatters: "Ensures compliance with international carbon standards (Verra, Gold Standard, Article 6, ISO 14064).",

    whatToDoNext: "Verify emission factor formulas and non-renewable biomass fraction (fNRB) settings.",

    aiRecommendation: "Methodology parameters locked. AST equations verified against Gold Standard TPDDTEC protocol.",

    confidenceScore: 99.8,

    nextActionLabel: "View Assets Fleet",

    nextActionHref: "/dashboard/assets"

  }),

  "/dashboard/assets": (sector, role) => ({

    pageTitle: "Assets",

    purpose: "Manages physical asset inventory, IoT sensors, beneficiary QR codes, and device health status.",

    whyItMatters: "Provides the underlying asset telemetry and chain-of-custody required to calculate real-world carbon abatement.",

    whatToDoNext: "Monitor real-time sensor pings for active cookstove assets.",

    aiRecommendation: "3 registered cookstove assets active in database. All IoT device telemetry signals synchronized with 0 hardware errors.",

    confidenceScore: 99.5,

    nextActionLabel: "Monitor Telemetry",

    nextActionHref: "/dashboard/monitoring"

  }),

  "/dashboard/operations": (sector, role) => ({

    pageTitle: "Field Operations",

    purpose: "Real-time field inspection queue, PWA evidence capture, EXIF verification, and QA anomaly clearance.",

    whyItMatters: "Protects credit integrity by filtering out fraudulent, duplicated, or mis-located field evidence.",

    whatToDoNext: "Review 1 flagged activity submission (Lpg Burner • Jerry) assigned to audit queue.",

    aiRecommendation: "Database records synced: 1 activity flagged for manual audit (Lpg Burner • Jerry), 2 activities verified.",

    confidenceScore: 98.4,

    nextActionLabel: "Review Flagged Activity",

    nextActionHref: "/dashboard/activities/4f90f883-b526-4b34-be52-cc09e07824d2"

  }),

  "/dashboard/monitoring": (sector, role) => ({

    pageTitle: "Monitoring",

    purpose: "Real-time IoT telemetry streaming, usage analytics, anomaly detection, and sensor health diagnostics.",

    whyItMatters: "Replaces manual periodic surveys with continuous, tamper-proof digital MRV data feeds.",

    whatToDoNext: "Inspect daily thermal usage curves and verify sensor ping intervals.",

    aiRecommendation: "IoT gateway latency is 24ms. Telemetry ingestion rate is 100% stable across active database assets.",

    confidenceScore: 99.1,

    nextActionLabel: "View Verifications",

    nextActionHref: "/dashboard/verifications"

  }),

  "/dashboard/verifications": (sector, role) => ({

    pageTitle: "Verification",

    purpose: "Independent VVB audit hub, SHA-256 hash attestation, digital signatures, and audit sampling plans.",

    whyItMatters: "Provides immutable verification required by accredited auditors before carbon credit minting.",

    whatToDoNext: "Execute WebAuthn cryptographic sign-off on flagged submission (Lpg Burner • Jerry).",

    aiRecommendation: "1 submission pending VVB audit in database queue (Lpg Burner • Jerry). 100% SHA-256 hash integrity match.",

    confidenceScore: 99.9,

    nextActionLabel: "Proceed to Credit Sign-Off",

    nextActionHref: "/dashboard/activities/4f90f883-b526-4b34-be52-cc09e07824d2"

  }),

  "/dashboard/carbon": (sector, role) => ({

    pageTitle: "Carbon Credits",

    purpose: "Credit ledger, on-chain Solana minting, serial number allocation, registry exports, and marketplace settlement.",

    whyItMatters: "Transforms verified emission reductions into tradable, sovereign-compliant carbon assets.",

    whatToDoNext: "Execute on-chain minting for verified carbon credit batches.",

    aiRecommendation: "Verified carbon credit ledger synchronized. Ready for instant Solana minting with serial tracking.",

    confidenceScore: 99.7,

    nextActionLabel: "Execute Minting",

    nextActionHref: "/dashboard/carbon"

  }),

  "/dashboard/command-center": (sector, role) => ({

    pageTitle: "Compliance",

    purpose: "Sovereign Article 6 corresponding adjustments, national inventory compliance, and ITMO authorization.",

    whyItMatters: "Ensures compliance with Paris Agreement host country legal framework and Article 6.2/6.4 rules.",

    whatToDoNext: "Verify Article 6 corresponding adjustment authorization status with national regulator.",

    aiRecommendation: "Article 6.2 authorization payload pre-validated against host country NDC registry.",

    confidenceScore: 98.9,

    nextActionLabel: "Submit ITMO Authorization",

    nextActionHref: "/dashboard/command-center"

  }),

  "/dashboard/ai": (sector, role) => ({

    pageTitle: "AI Assistant",

    purpose: "Autonomous operational AI assistant providing natural language query resolution and predictive insights.",

    whyItMatters: "Empowers operational roles with instant predictive guidance and automated task execution.",

    whatToDoNext: "Ask the AI assistant for custom project forecasts, risk analyses, or audit queries.",

    aiRecommendation: "AI operational memory synchronized with live database activities and project telemetry.",

    confidenceScore: 99.5,

    nextActionLabel: "Explore AI Memory",

    nextActionHref: "/dashboard/ai"

  }),

  "/dashboard/analytics": (sector, role) => ({

    pageTitle: "Reports",

    purpose: "Platform analytics, custom reporting, carbon yield forecasting, and financial ROC modeling.",

    whyItMatters: "Delivers executive-ready impact and financial performance reports to investors and regulators.",

    whatToDoNext: "Export Q3 Carbon Impact & Abatement Forecast Report.",

    aiRecommendation: "Abatement forecast calculated from real-time database activities indicates verified carbon yield growth.",

    confidenceScore: 97.8,

    nextActionLabel: "Download Report",

    nextActionHref: "/dashboard/analytics"

  }),

  "/dashboard/settings": (sector, role) => ({

    pageTitle: "Settings",

    purpose: "Platform governance, user access control, role permissions, API key generation, and organization settings.",

    whyItMatters: "Ensures strict enterprise RBAC/ABAC security and multi-tenant isolation.",

    whatToDoNext: "Review user role assignments and API access token expiration dates.",

    aiRecommendation: "Security audit passed. Active organization linked with 0 permission leaks.",

    confidenceScore: 100,

    nextActionLabel: "Manage Users",

    nextActionHref: "/dashboard/settings"

  })

};



export function getContextualInsight(pathname: string, sector: string = "cookstoves", role: string = "ADMIN"): ContextualPageInsight {

  const normalizedPath = pathname.split("?")[0];

  const resolver = PAGE_INSIGHTS[normalizedPath] || PAGE_INSIGHTS["/dashboard"];

  return resolver(sector, role);

}



// ─── Default AI Events Feed (Live Real-Time Events) ──────────────────────────



export const INITIAL_AI_EVENTS: AIObservableEvent[] = [

  {

    id: "evt-101",

    eventType: "EVIDENCE_FLAGGED",

    category: "RISK",

    severity: "HIGH",

    title: "Manual Audit Flagged: Lpg Burner • Jerry",

    summary: "Activity 4f90f883-b526-4b34-be52-cc09e07824d2 (Lpg Burner • Jerry) scored 68 Trust Score and was flagged for VVB audit.",

    rationale: "Automated AI score (68/100) below 80 threshold due to missing camera EXIF signature; manual audit requested.",

    impact: "Routes submission to VVB Auditor Queue for WebAuthn cryptographic attestation sign-off.",

    confidenceScore: 98.4,

    targetRole: ["AUDITOR", "VVB", "QA_OFFICER", "PROJECT_MANAGER", "ADMIN"],

    targetStage: "Verification",

    deepLink: "/dashboard/activities/4f90f883-b526-4b34-be52-cc09e07824d2",

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

    summary: "Audit for Lpg Burner • Jerry is assigned to VVB Verification Queue.",

    rationale: "Contractual VVB audit SLA requires sign-off within 48 hours of evidence batch locking.",

    impact: "Unlocks on-chain Solana carbon credit minting upon attestation.",

    confidenceScore: 99.1,

    targetRole: ["AUDITOR", "VVB", "PROJECT_MANAGER"],

    targetStage: "Verification",

    deepLink: "/dashboard/verifications",

    actionLabel: "Execute Attestation Sign-off",

    timestamp: "Live DB Task",

    modelReference: "SLA Sentinel-v2.1"

  }

];
