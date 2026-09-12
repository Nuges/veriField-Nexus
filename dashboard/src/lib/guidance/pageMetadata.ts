// =============================================================================
// VeriField Nexus — Base Page Guidance Metadata
// =============================================================================
// Static purpose, impact, query placeholders, and suggested queries.
// Fully aligned with the real verified route inventory.
// =============================================================================

import { BasePageMetadata } from "./types";

export const BASE_PAGE_METADATA: Record<string, BasePageMetadata> = {
  "/dashboard": {
    pageTitle: "Mission Control",
    basePurpose: "Provides real-time operational visibility and activity summaries across all project lifecycle stages.",
    baseWhyItMatters: "Enables immediate identification of reporting bottlenecks, telemetry gaps, and carbon yield progress.",
    baseWhatToDoNext: "Review active operational records and open exceptions.",
    defaultAction: {
      label: "View Verification Queue",
      href: "/dashboard/verifications",
      mutation: false
    },
    queryPlaceholder: "Ask about operational status, active projects, or reporting status...",
    suggestedQueries: [
      "What operational activities require attention today?",
      "Are there any active telemetry ingestion anomalies?",
      "Which projects are currently generating verified evidence?",
      "What is the status of pending verification batches?"
    ]
  },

  "/dashboard/projects": {
    pageTitle: "Projects",
    basePurpose: "Manage project origination, boundaries, methodology assignment, stakeholder licensing, and deployment readiness.",
    baseWhyItMatters: "Project configuration establishes the operational and methodological foundation used by field capture, monitoring, verification, and reporting.",
    baseWhatToDoNext: "Review project setup and team assignments.",
    defaultAction: {
      label: "Review Project Setup",
      href: "/dashboard/projects",
      permission: "project:edit",
      mutation: false
    },
    queryPlaceholder: "Ask about project status, setup, assignments, or readiness...",
    suggestedQueries: [
      "Which projects require attention?",
      "Which projects are missing methodology configuration?",
      "Which projects have unresolved setup issues?",
      "What is blocking field deployment?"
    ]
  },

  "/dashboard/monitoring": {
    pageTitle: "Monitoring",
    basePurpose: "Review operational monitoring data, telemetry availability, reporting continuity, and exceptions requiring investigation.",
    baseWhyItMatters: "Reliable monitoring evidence supports defensible emissions calculations and verification readiness.",
    baseWhatToDoNext: "Review unresolved monitoring exceptions.",
    defaultAction: {
      label: "Review Monitoring Exceptions",
      href: "/dashboard/monitoring",
      mutation: false
    },
    queryPlaceholder: "Ask about monitoring gaps, telemetry, or exceptions...",
    suggestedQueries: [
      "Which assets have missing telemetry?",
      "Which projects have monitoring gaps?",
      "What changed since the last reporting period?",
      "Which sites need investigation?"
    ]
  },

  "/dashboard/verifications": {
    pageTitle: "Verification",
    basePurpose: "Review evidence packages, verification status, outstanding findings, and verifier actions.",
    baseWhyItMatters: "Verification determines whether project evidence is sufficiently complete and defensible for the applicable methodology and reporting process.",
    baseWhatToDoNext: "Review open verification findings.",
    defaultAction: {
      label: "Review Verification Queue",
      href: "/dashboard/verifications",
      permission: "activity:verify",
      mutation: true
    },
    queryPlaceholder: "Ask about findings, evidence, or verification status...",
    suggestedQueries: [
      "Which submissions are awaiting verification?",
      "Which findings remain unresolved?",
      "What evidence is missing?",
      "Which project is closest to verification completion?"
    ]
  },

  "/dashboard/trust-scores": {
    pageTitle: "Trust Scores",
    basePurpose: "Evaluate the quality and consistency of field evidence using the system's configured trust indicators.",
    baseWhyItMatters: "Trust scores help prioritize records requiring further review without replacing formal verification judgement.",
    baseWhatToDoNext: "Review low-confidence field evidence.",
    defaultAction: {
      label: "Inspect Flagged Evidence",
      href: "/dashboard/operations",
      mutation: false
    },
    queryPlaceholder: "Ask about trust indicators, evidence scores, or anomalies...",
    suggestedQueries: [
      "Which field activities have trust scores below threshold?",
      "What factors contributed to recent trust score deductions?",
      "Are there GPS or timestamp irregularities in recent submissions?",
      "Which projects maintain the highest evidence consistency?"
    ]
  },

  "/dashboard/sensors": {
    pageTitle: "Sensors",
    basePurpose: "Manage registered monitoring devices, connectivity, data ingestion, device assignment, and operational status.",
    baseWhyItMatters: "Reliable sensor availability improves monitoring continuity and reduces evidence gaps.",
    baseWhatToDoNext: "Investigate devices requiring attention.",
    defaultAction: {
      label: "Review Offline Sensors",
      href: "/dashboard/sensors",
      mutation: false
    },
    queryPlaceholder: "Ask about device status, connectivity, or reporting gaps...",
    suggestedQueries: [
      "Which sensors are offline?",
      "Which devices have stopped reporting?",
      "Which projects have incomplete sensor coverage?",
      "Are there unassigned devices in inventory?"
    ]
  },

  "/dashboard/assets": {
    pageTitle: "Assets",
    basePurpose: "Manage physical project assets and their relationship to projects, sites, telemetry, and evidence.",
    baseWhyItMatters: "Correct asset registration provides traceability between physical infrastructure and reported monitoring evidence.",
    baseWhatToDoNext: "Review asset registration records and device linkages.",
    defaultAction: {
      label: "Review Asset Inventory",
      href: "/dashboard/assets",
      mutation: false
    },
    queryPlaceholder: "Ask about asset inventory, health status, or deployments...",
    suggestedQueries: [
      "Which assets lack linked telemetry sensors?",
      "Are all deployed assets assigned to active projects?",
      "Which assets have recorded maintenance events?",
      "What is the total count of operational assets?"
    ]
  },

  "/dashboard/operations": {
    pageTitle: "Field Operations",
    basePurpose: "Review field submissions, GPS evidence, photographs, timestamps, and capture completeness.",
    baseWhyItMatters: "Complete and traceable field evidence improves auditability and verification readiness.",
    baseWhatToDoNext: "Review pending field activity submissions in the operational queue.",
    defaultAction: {
      label: "Review Operational Queue",
      href: "/dashboard/operations",
      permission: "activity:approve",
      mutation: true
    },
    queryPlaceholder: "Ask about field submissions, evidence capture, or inspection logs...",
    suggestedQueries: [
      "How many field submissions are pending QA review?",
      "Are there evidence submissions with missing GPS coordinates?",
      "Which field agents completed inspections today?",
      "What is the current approval rate for field evidence?"
    ]
  },

  "/dashboard/audits": {
    pageTitle: "Audits",
    basePurpose: "Review audit events, evidence history, user actions, and governance records.",
    baseWhyItMatters: "A complete audit trail supports accountability, investigation, and external assurance.",
    baseWhatToDoNext: "Inspect recent security and administrative event records.",
    defaultAction: {
      label: "View Audit History",
      href: "/dashboard/audits",
      permission: "audit:create",
      mutation: false
    },
    queryPlaceholder: "Ask about audit events, changes, or user activity...",
    suggestedQueries: [
      "Which administrative actions occurred in the last 24 hours?",
      "Were any configuration changes made without approval?",
      "Are there unresolved audit findings for active projects?",
      "Which user accounts had failed authentication attempts?"
    ]
  },

  "/dashboard/access-control": {
    pageTitle: "Access Control",
    basePurpose: "Manage user roles, organizational permissions, project assignments, and separation-of-duty constraints.",
    baseWhyItMatters: "Correct access configuration limits unauthorized actions and protects project evidence integrity.",
    baseWhatToDoNext: "Review user role assignments and least-privilege boundaries.",
    defaultAction: {
      label: "Manage Access Matrix",
      href: "/dashboard/access-control",
      permission: "users:manage",
      mutation: true
    },
    queryPlaceholder: "Ask about roles, permissions, or project access...",
    suggestedQueries: [
      "Which users have permission to verify evidence?",
      "Are there accounts with administrative privileges without MFA?",
      "Which users have access to multiple projects?",
      "Are separation-of-duty controls satisfied for verifiers?"
    ]
  },

  "/dashboard/people": {
    pageTitle: "People & Teams",
    basePurpose: "Manage organizational team members, roles, project assignments, and contact records.",
    baseWhyItMatters: "Clear team assignments ensure accountability for field operations, compliance, and reporting.",
    baseWhatToDoNext: "Review team assignments across active project sites.",
    defaultAction: {
      label: "Manage Team Members",
      href: "/dashboard/people",
      permission: "users:manage",
      mutation: true
    },
    queryPlaceholder: "Ask about team members, roles, or project assignments...",
    suggestedQueries: [
      "Which team members are assigned to each project?",
      "Are there pending invitations for new team members?",
      "Who is the designated project manager for active sites?",
      "Which roles require credential renewal?"
    ]
  },

  "/dashboard/agents": {
    pageTitle: "Field Agents",
    basePurpose: "Manage registered field enumerators, mobile app deployments, assignment zones, and field capture quotas.",
    baseWhyItMatters: "Active and properly trained field agents ensure consistent evidence collection in the field.",
    baseWhatToDoNext: "Review active field agent assignments and submission rates.",
    defaultAction: {
      label: "Review Agent Roster",
      href: "/dashboard/agents",
      permission: "users:manage",
      mutation: false
    },
    queryPlaceholder: "Ask about field agent assignments, sync status, or quotas...",
    suggestedQueries: [
      "How many field agents are currently active in the field?",
      "Which agents have offline submissions pending synchronization?",
      "What is the average evidence collection rate per agent?",
      "Which zones require additional field agent coverage?"
    ]
  },

  "/dashboard/analytics": {
    pageTitle: "Analytics",
    basePurpose: "Interpret current project and operational data using verified system records.",
    baseWhyItMatters: "Analytics supports management decisions without altering underlying monitoring or verification evidence.",
    baseWhatToDoNext: "Generate verified operational progress and abatement reports.",
    defaultAction: {
      label: "Review Analytical Reports",
      href: "/dashboard/analytics",
      mutation: false
    },
    queryPlaceholder: "Ask about project performance, emissions reduction, or metrics...",
    suggestedQueries: [
      "What is the verified emissions reduction to date?",
      "How does current yield compare against baseline projections?",
      "Which projects have the highest evidence completion rate?",
      "What is the forecast carbon abatement for the current quarter?"
    ]
  },

  "/dashboard/registry": {
    pageTitle: "Registry",
    basePurpose: "Review registry-ready project information, issuance preparation, status, and relevant records.",
    baseWhyItMatters: "Registry readiness depends on complete project, monitoring, verification, and documentation workflows.",
    baseWhatToDoNext: "Verify submission readiness for completed verification batches.",
    defaultAction: {
      label: "Review Registry Submissions",
      href: "/dashboard/registry",
      permission: "registry:submit",
      mutation: true
    },
    queryPlaceholder: "Ask about registry status, issuance preparation, or batches...",
    suggestedQueries: [
      "Which batches are ready for registry submission?",
      "What documentation is required before issuance review?",
      "What is the status of pending registry approvals?",
      "Are serial allocations matched with verified reductions?"
    ]
  },

  "/dashboard/settings": {
    pageTitle: "Settings",
    basePurpose: "Configure organization profile, API keys, notification preferences, and system defaults.",
    baseWhyItMatters: "Settings govern tenant identity, data routing, integration credentials, and security defaults.",
    baseWhatToDoNext: "Review organization security settings and API key expirations.",
    defaultAction: {
      label: "Manage Settings",
      href: "/dashboard/settings",
      permission: "settings:edit",
      mutation: true
    },
    queryPlaceholder: "Ask about organization settings, API keys, or configurations...",
    suggestedQueries: [
      "Which API keys are active for this organization?",
      "When was the organization profile last updated?",
      "What notification channels are configured?",
      "Are webhooks operating with valid endpoint URLs?"
    ]
  },

  "/dashboard/settings/sectors": {
    pageTitle: "Sector Settings",
    basePurpose: "Manage licensed climate methodology sectors, protocol versions, and sector-specific parameters.",
    baseWhyItMatters: "Accurate sector configuration ensures data models and emission formulas adhere to approved standards.",
    baseWhatToDoNext: "Verify licensed sector parameters and default methodology versions.",
    defaultAction: {
      label: "Review Sector Configuration",
      href: "/dashboard/settings/sectors",
      permission: "settings:edit",
      mutation: true
    },
    queryPlaceholder: "Ask about sector licenses, methodology versions, or protocols...",
    suggestedQueries: [
      "Which sectors are currently licensed for this organization?",
      "Are all active methodologies on current protocol versions?",
      "What default emission factors are configured?",
      "How do sector parameters map to project configurations?"
    ]
  },

  "/dashboard/carbon": {
    pageTitle: "Carbon Credits",
    basePurpose: "Deterministic credit ledger, serial allocation, cryptographic verification sealing, and registry issuance settlement.",
    baseWhyItMatters: "Transforms verified emission reductions into tradable, sovereign-compliant carbon assets.",
    baseWhatToDoNext: "Review verified batches eligible for credit issuance.",
    defaultAction: {
      label: "View Ledger Records",
      href: "/dashboard/carbon",
      permission: "ledger:mint",
      mutation: true
    },
    queryPlaceholder: "Ask about credit issuance, ledger serials, or verified batches...",
    suggestedQueries: [
      "What is the total verified credit balance in the ledger?",
      "Which batches have completed cryptographic sealing?",
      "Are there pending retirements or transfers?",
      "What serial blocks were issued in the latest verification period?"
    ]
  },

  "/dashboard/command-center": {
    pageTitle: "Compliance",
    basePurpose: "Sovereign Article 6 corresponding adjustments, national inventory compliance, and ITMO authorization.",
    baseWhyItMatters: "Ensures compliance with Paris Agreement host country legal frameworks and Article 6.2/6.4 rules.",
    baseWhatToDoNext: "Verify Article 6 corresponding adjustment authorization status with host party regulators.",
    defaultAction: {
      label: "Review ITMO Authorizations",
      href: "/dashboard/command-center",
      permission: "itmo:authorize",
      mutation: true
    },
    queryPlaceholder: "Ask about Article 6 authorization, ITMO status, or compliance...",
    suggestedQueries: [
      "What is the authorization status of active Article 6 transfers?",
      "Are bilateral cooperative approach agreements verified?",
      "Which projects have obtained host country Letter of Approval?",
      "Are corresponding adjustment entries registered in the national ledger?"
    ]
  },

  "/dashboard/energy": {
    pageTitle: "Energy & Mini-Grids",
    basePurpose: "Monitor renewable energy generation, smart inverter outputs, storage battery states, and grid displacement.",
    baseWhyItMatters: "Generation data proves renewable power delivery and quantifies fossil fuel baseline displacement.",
    baseWhatToDoNext: "Review daily energy generation curves and inverter availability.",
    defaultAction: {
      label: "Inspect Energy Telemetry",
      href: "/dashboard/monitoring",
      mutation: false
    },
    queryPlaceholder: "Ask about generation yields, inverter status, or energy telemetry...",
    suggestedQueries: [
      "What is today's total kilowatt-hour generation across sites?",
      "Which inverters are operating below rated capacity?",
      "Are there mini-grids reporting communication outages?",
      "What is the calculated diesel fuel displacement for this month?"
    ]
  },

  "/dashboard/community": {
    pageTitle: "Community & Safeguards",
    basePurpose: "Track community benefits, local employment, stakeholder consultations, and socio-economic impact metrics.",
    baseWhyItMatters: "Community safeguards verify co-benefits required by premium carbon standards (SDG alignment).",
    baseWhatToDoNext: "Review stakeholder consultation records and benefit distribution logs.",
    defaultAction: {
      label: "Review Safeguards Evidence",
      href: "/dashboard/community",
      mutation: false
    },
    queryPlaceholder: "Ask about community benefits, stakeholder feedback, or SDG impact...",
    suggestedQueries: [
      "Which stakeholder consultations have completed documentation?",
      "Are there open grievance reports requiring resolution?",
      "What are the verified local employment figures?",
      "How are project co-benefits aligned with UN SDGs?"
    ]
  },

  "/dashboard/anomalies": {
    pageTitle: "Exceptions & Anomalies",
    basePurpose: "Identify and investigate telemetry outliers, reporting gaps, data inconsistencies, and sensor exceptions.",
    baseWhyItMatters: "Prompt anomaly resolution prevents evidence rejection during third-party verification audits.",
    baseWhatToDoNext: "Review open telemetry exceptions and investigate flagged sensor feeds.",
    defaultAction: {
      label: "Resolve Open Anomalies",
      href: "/dashboard/anomalies",
      mutation: false
    },
    queryPlaceholder: "Ask about telemetry exceptions, outliers, or flagged feeds...",
    suggestedQueries: [
      "How many open anomalies require investigation?",
      "Which assets have recurrent reporting gaps?",
      "Were any data inconsistencies flagged in recent capture batches?",
      "What is the average resolution time for telemetry exceptions?"
    ]
  },

  "/dashboard/portfolio": {
    pageTitle: "Portfolio",
    basePurpose: "Strategic overview of all operational projects, aggregate carbon abatement, capital deployment, and geographic footprint.",
    baseWhyItMatters: "Portfolio visibility allows asset managers to assess performance, risk exposure, and issuance timelines across multiple projects.",
    baseWhatToDoNext: "Review cross-project performance metrics and issuance forecasts.",
    defaultAction: {
      label: "Review All Projects",
      href: "/dashboard/projects",
      mutation: false
    },
    queryPlaceholder: "Ask about portfolio performance, aggregate yield, or milestones...",
    suggestedQueries: [
      "What is the total active project count across all sectors?",
      "Which projects are on schedule for next registry issuance?",
      "What is the aggregate emissions reduction target for the portfolio?",
      "Which regions represent the largest share of operational assets?"
    ]
  },

  "/dashboard/poa": {
    pageTitle: "Programme of Activities",
    basePurpose: "Manage coordinated Programmes of Activities (PoA) and individual Component Project Activities (CPAs).",
    baseWhyItMatters: "PoA structures enable scalable aggregation of distributed small-scale climate mitigation activities.",
    baseWhatToDoNext: "Review inclusion status of new Component Project Activities.",
    defaultAction: {
      label: "Review PoA Inclusions",
      href: "/dashboard/poa",
      permission: "project:create",
      mutation: false
    },
    queryPlaceholder: "Ask about PoA registrations, CPA inclusions, or boundaries...",
    suggestedQueries: [
      "How many CPAs are registered under this Programme of Activities?",
      "Which Component Project Activities are pending validation?",
      "What is the cumulative emissions reduction across all CPAs?",
      "Are geographic boundaries verified for recent CPA inclusions?"
    ]
  },

  "/dashboard/map": {
    pageTitle: "Geospatial Intelligence",
    basePurpose: "Visualize geospatial deployment zones, asset coordinates, project boundaries, and regional telemetry feeds.",
    baseWhyItMatters: "Spatial traceability verifies that activities occur within registered, legally permitted project boundaries.",
    baseWhatToDoNext: "Inspect spatial boundary layers and verify asset GPS clustering.",
    defaultAction: {
      label: "Inspect Map Layers",
      href: "/dashboard/map",
      mutation: false
    },
    queryPlaceholder: "Ask about spatial coordinates, boundaries, or asset locations...",
    suggestedQueries: [
      "Are all deployed assets within authorized project boundaries?",
      "Which sites have missing or imprecise GPS coordinates?",
      "Are there overlapping spatial polygons between projects?",
      "What is the geographical dispersion of active monitoring devices?"
    ]
  },

  "/dashboard/methodologies": {
    pageTitle: "Methodologies",
    basePurpose: "Configure approved carbon quantification protocols, baseline formulas, emission factors, and monitoring plans.",
    baseWhyItMatters: "Methodology parameters ensure compliance with international standards such as Verra, Gold Standard, and Article 6.",
    baseWhatToDoNext: "Verify baseline emission factors and calculation formulas.",
    defaultAction: {
      label: "Review Methodology Parameters",
      href: "/dashboard/methodologies",
      mutation: false
    },
    queryPlaceholder: "Ask about quantification methodologies, baseline formulas, or standards...",
    suggestedQueries: [
      "Which methodologies are active for current projects?",
      "Are all emission factor parameters locked for verification?",
      "What standards bodies govern the active protocols?",
      "How are baseline non-renewable biomass or grid factors defined?"
    ]
  },

  "/dashboard/properties": {
    pageTitle: "Properties",
    basePurpose: "Manage spatial sites, mini-grid parcels, community zones, and physical installation properties.",
    baseWhyItMatters: "Property registration anchors project activities to verified geographic land parcels and local communities.",
    baseWhatToDoNext: "Review registered property boundaries and site ownership documentation.",
    defaultAction: {
      label: "View Property Registry",
      href: "/dashboard/properties",
      mutation: false
    },
    queryPlaceholder: "Ask about property records, land parcels, or site verification...",
    suggestedQueries: [
      "Which properties are linked to active project activities?",
      "Are land tenure and consent documents verified for all sites?",
      "What is the total acreage under active project monitoring?",
      "Which property records require boundary updates?"
    ]
  },

  "/dashboard/activities": {
    pageTitle: "Activities",
    basePurpose: "Chronological operational activity stream, evidence logs, inspection reports, and maintenance records.",
    baseWhyItMatters: "Activity logs provide the chronological proof required for tamper-evident digital MRV audit trails.",
    baseWhatToDoNext: "Review recent field activity submissions.",
    defaultAction: {
      label: "View All Activities",
      href: "/dashboard/activities",
      mutation: false
    },
    queryPlaceholder: "Ask about recent activities, submissions, or field logs...",
    suggestedQueries: [
      "What activities were recorded in the past 48 hours?",
      "Which activities were flagged during automated validation?",
      "Are there activity records pending verifier sign-off?",
      "How many total activities were synchronized this week?"
    ]
  },

  "/dashboard/help": {
    pageTitle: "Help & Documentation",
    basePurpose: "Access platform guides, MRV protocol documentation, API specifications, and operational manuals.",
    baseWhyItMatters: "Clear documentation ensures operational compliance, correct field procedures, and efficient user onboarding.",
    baseWhatToDoNext: "Browse guidance articles or search protocol documentation.",
    defaultAction: {
      label: "Browse Documentation",
      href: "/dashboard/help",
      mutation: false
    },
    queryPlaceholder: "Ask about system usage, protocol guides, or operational procedures...",
    suggestedQueries: [
      "How do I configure a new project methodology?",
      "What are the requirements for cryptographic verification signing?",
      "How do field agents synchronize offline submissions?",
      "What are the API endpoints for automated telemetry ingestion?"
    ]
  },

  "/dashboard/ai": {
    pageTitle: "Decision Support",
    basePurpose: "Operational decision support providing natural language query resolution and contextual insights.",
    baseWhyItMatters: "Empowers operational roles with verification guidance, risk evaluation, and telemetry analysis.",
    baseWhatToDoNext: "Investigate project telemetry, anomaly patterns, or verification exceptions.",
    defaultAction: {
      label: "Explore Intelligence Feeds",
      href: "/dashboard/ai",
      mutation: false
    },
    queryPlaceholder: "Ask about operational data, project anomalies, or verification readiness...",
    suggestedQueries: [
      "What are the top operational risks across active projects?",
      "Which projects have the largest evidence backlogs?",
      "Are there unusual patterns in recent sensor telemetry?",
      "What steps are required to prepare for upcoming audits?"
    ]
  }
};

export const FALLBACK_PAGE_METADATA: BasePageMetadata = {
  pageTitle: "Operational Guidance",
  basePurpose: "Review operational workspace data, active project context, and compliance documentation.",
  baseWhyItMatters: "Centralized workspace management maintains operational continuity and MRV integrity across climate initiatives.",
  baseWhatToDoNext: "Review active project properties and operational records.",
  defaultAction: {
    label: "View Projects",
    href: "/dashboard/projects",
    mutation: false
  },
  queryPlaceholder: "Ask about operational data, project status, or verification...",
  suggestedQueries: [
    "What operational items require review?",
    "Which projects are currently active?",
    "What is the status of active telemetry feeds?",
    "Are there unresolved compliance items?"
  ]
};
