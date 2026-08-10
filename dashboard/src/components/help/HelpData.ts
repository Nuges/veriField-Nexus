// =============================================================================
// VeriField Nexus — Comprehensive Enterprise Help & Knowledge Centre Data
// =============================================================================

export interface NavSection {
  id: string;
  title: string;
  icon: string;
  category: "GETTING_STARTED" | "CORE_MODULES" | "CLIMATE_MRV" | "GOVERNANCE" | "REFERENCE";
  readingTimeMinutes: number;
}

export interface FAQItem {
  id: string;
  question: string;
  answer: string;
  category: "General" | "Access & Auth" | "Security & Access" | "Organizations & Projects" | "Assets & Data" | "Verification & Audits" | "Methodologies & MRV" | "Analytics & Metrics" | "Super Admin";
  keywords: string[];
}

export interface GlossaryTerm {
  term: string;
  definition: string;
  category: string;
}

export interface RoleGuide {
  code: string;
  title: string;
  scope: string;
  purpose: string;
  permissions: string[];
  limitations: string[];
  whoCreates: string;
  canSee: string[];
  cannotSee: string[];
}

export interface WorkflowStep {
  step: number;
  title: string;
  actor: string;
  description: string;
  keyOutputs: string[];
}

export const NAV_SECTIONS: NavSection[] = [
  { id: "introduction", title: "1. What is VeriField Nexus?", icon: "BookOpen", category: "GETTING_STARTED", readingTimeMinutes: 5 },
  { id: "workflow", title: "2. Platform End-to-End Workflow", icon: "GitMerge", category: "GETTING_STARTED", readingTimeMinutes: 4 },
  { id: "organizations", title: "3. Organizations Guide", icon: "Building2", category: "CORE_MODULES", readingTimeMinutes: 5 },
  { id: "projects", title: "4. Projects Management", icon: "Briefcase", category: "CORE_MODULES", readingTimeMinutes: 6 },
  { id: "assets", title: "5. Assets & Devices", icon: "Radio", category: "CORE_MODULES", readingTimeMinutes: 5 },
  { id: "activities", title: "6. Activities & MRV Data", icon: "Activity", category: "CORE_MODULES", readingTimeMinutes: 6 },
  { id: "verification", title: "7. Verification & Audits", icon: "ShieldCheck", category: "CLIMATE_MRV", readingTimeMinutes: 6 },
  { id: "analytics", title: "8. Analytics & KPI Guide", icon: "BarChart3", category: "CLIMATE_MRV", readingTimeMinutes: 7 },
  { id: "methodologies", title: "9. Climate Sector Methodologies", icon: "Layers", category: "CLIMATE_MRV", readingTimeMinutes: 8 },
  { id: "roles", title: "10. User Roles & Scopes", icon: "Users", category: "GOVERNANCE", readingTimeMinutes: 7 },
  { id: "super-admin", title: "11. Super Admin Manual", icon: "ShieldAlert", category: "GOVERNANCE", readingTimeMinutes: 9 },
  { id: "permissions", title: "12. Permissions Matrix", icon: "Key", category: "GOVERNANCE", readingTimeMinutes: 5 },
  { id: "search", title: "13. Platform Search Engine", icon: "Search", category: "REFERENCE", readingTimeMinutes: 3 },
  { id: "reports", title: "14. Reports & Exports", icon: "FileText", category: "REFERENCE", readingTimeMinutes: 4 },
  { id: "notifications", title: "15. System Notifications", icon: "Bell", category: "REFERENCE", readingTimeMinutes: 3 },
  { id: "troubleshooting", title: "16. Troubleshooting Guide", icon: "AlertTriangle", category: "REFERENCE", readingTimeMinutes: 6 },
  { id: "faq", title: "17. Frequently Asked Questions (50+ FAQs)", icon: "HelpCircle", category: "REFERENCE", readingTimeMinutes: 12 },
  { id: "shortcuts", title: "18. Keyboard Shortcuts", icon: "Command", category: "REFERENCE", readingTimeMinutes: 2 },
  { id: "glossary", title: "19. Climate & MRV Glossary", icon: "FileCode", category: "REFERENCE", readingTimeMinutes: 6 }
];

export const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    step: 1,
    title: "Access Request & Registration",
    actor: "Organization Admin / User",
    description: "User submits an enterprise access request specifying organization name, country, sector, and requested methodology.",
    keyOutputs: ["Access Request Record", "Pending Approval State"]
  },
  {
    step: 2,
    title: "Super Admin Review & Approval",
    actor: "Platform Super Admin",
    description: "Super Admin inspects the access request in the Governance Portal and approves organization licensing for specific sectors.",
    keyOutputs: ["Provisioned Organization", "Default Admin User Credentials"]
  },
  {
    step: 3,
    title: "Organization Setup & Onboarding",
    actor: "Organization Administrator",
    description: "Org Admin logs in, configures organization preferences, invites team members, and assigns role scopes.",
    keyOutputs: ["Active Tenant Environment", "Provisioned Team Members"]
  },
  {
    step: 4,
    title: "Project Creation & Methodology Binding",
    actor: "Project Manager / Org Admin",
    description: "Manager creates a climate project (e.g., Clean Cookstove Distribution, EV Mobility Fleet) and binds an approved methodology family.",
    keyOutputs: ["Active Climate Project", "Bound Methodology Calculator"]
  },
  {
    step: 5,
    title: "Asset & Device Registration",
    actor: "IoT Engineer / Field Supervisor",
    description: "Physical assets (solar mini-grids, cookstove meters, EV chargers, biochar pyrolyzers) are registered with GPS coordinates and hardware serials.",
    keyOutputs: ["Registered Fleet Assets", "Active Telemetry Pipeline"]
  },
  {
    step: 6,
    title: "Activity Telemetry & Data Collection",
    actor: "Field Agent / IIoT Sensors",
    description: "Field agents submit usage logs via mobile, or smart sensors automatically stream hourly energy/fuel telemetry into the pipeline.",
    keyOutputs: ["Raw Telemetry Logs", "Calculated CO₂ Reductions"]
  },
  {
    step: 7,
    title: "Verification & Trust Scoring Audit",
    actor: "QA Officer / Independent VVB Auditor",
    description: "Activities pass through automated AI trust scoring (>80 = Verified) and independent verification review against evidence records.",
    keyOutputs: ["Verified MRV Package", "Audited Trust Score"]
  },
  {
    step: 8,
    title: "Analytics & Decarbonization Insights",
    actor: "Executive / Portfolio Manager",
    description: "Real-time metrics aggregate across projects to show CO₂ displaced, energy generated, biochar sequestered, and diesel avoided.",
    keyOutputs: ["Live Executive Dashboards", "Sector Performance Charts"]
  },
  {
    step: 9,
    title: "Compliance Ledger & Certification",
    actor: "Compliance Admin / Registry Manager",
    description: "Verified carbon impact records are committed to the immutable compliance ledger for auditability.",
    keyOutputs: ["Immutable Ledger Entries", "Registry Audit Certificate"]
  },
  {
    step: 10,
    title: "Reporting & Credit Registry Export",
    actor: "Auditor / Registry Admin",
    description: "Comprehensive MRV reports and data packages are generated in PDF/CSV/Excel format for carbon registry submission (Verra, Gold Standard).",
    keyOutputs: ["Registry Export Package", "Audited Carbon Credits"]
  }
];

export const ROLE_GUIDES: RoleGuide[] = [
  {
    code: "SUPER_ADMIN",
    title: "Platform Super Admin",
    scope: "PLATFORM (Global)",
    purpose: "Full governance control over the entire multi-tenant platform instance.",
    permissions: ["admin:all", "org:manage", "project:all", "asset:all", "activity:all", "audit:all", "jurisdiction:all", "accreditation:all"],
    limitations: ["None"],
    whoCreates: "Seeded during platform deployment.",
    canSee: ["All Organizations", "All Projects", "All Users", "Security Audit Logs", "Governance Portals"],
    cannotSee: ["None"]
  },
  {
    code: "ORG_ADMIN",
    title: "Organization Administrator",
    scope: "ORGANIZATION",
    purpose: "Full administrative and operational authority over a single organization tenant.",
    permissions: ["org:read", "org:update", "project:all", "asset:all", "activity:all", "team:manage", "billing:manage", "report:all"],
    limitations: ["Cannot access data of other organizations."],
    whoCreates: "Super Admin or Organization Owner.",
    canSee: ["Tenant Projects", "Tenant Assets", "Tenant Users", "Organization Settings", "Tenant Analytics"],
    cannotSee: ["Other Organization Data", "Platform Super Admin Governance"]
  },
  {
    code: "PORTFOLIO_MANAGER",
    title: "Portfolio Manager",
    scope: "ORGANIZATION / PORTFOLIO",
    purpose: "Oversees multiple climate projects across one or more sector portfolios.",
    permissions: ["project:all", "asset:all", "activity:all", "report:all", "ledger:read", "audit:read"],
    limitations: ["Cannot change organization billing or manage org-level settings."],
    whoCreates: "Organization Administrator.",
    canSee: ["All Assigned Projects", "Asset Fleets", "Aggregate Metrics", "Verification Status"],
    cannotSee: ["Org Billing Details", "Platform Super Admin Features"]
  },
  {
    code: "PROJECT_MANAGER",
    title: "Project Manager",
    scope: "PROJECT",
    purpose: "Manages day-to-day operations, asset registration, and activity tracking for specific projects.",
    permissions: ["project:read", "project:update", "asset:all", "activity:all", "team:manage", "report:all"],
    limitations: ["Restricted to assigned project scopes."],
    whoCreates: "Organization Administrator / Portfolio Manager.",
    canSee: ["Assigned Projects", "Project Assets", "Project Activities", "Field Submissions"],
    cannotSee: ["Unassigned Projects", "Organization Financials"]
  },
  {
    code: "QA_OFFICER",
    title: "Quality Assurance / Compliance Officer",
    scope: "ORGANIZATION / PROJECT",
    purpose: "Reviews submitted activity telemetry and evidence for quality and methodology adherence.",
    permissions: ["project:read", "asset:read", "activity:read", "activity:verify", "report:read", "ledger:read"],
    limitations: ["Cannot create projects or delete assets."],
    whoCreates: "Organization Administrator.",
    canSee: ["Submitted Activities", "Evidence Files", "Trust Scores", "Verification Queue"],
    cannotSee: ["Org Settings", "User Management"]
  },
  {
    code: "FIELD_SUPERVISOR",
    title: "Field Supervisor",
    scope: "PROJECT / FIELD FLEET",
    purpose: "Supervises field agents, inspects asset installations, and verifies mobile data entries.",
    permissions: ["project:read", "asset:read", "activity:create", "activity:read", "activity:update", "team:manage"],
    limitations: ["Cannot alter methodology configurations or export registry packages."],
    whoCreates: "Project Manager / Org Admin.",
    canSee: ["Field Activities", "Assigned Agents", "Asset Geolocations"],
    cannotSee: ["Org Financials", "System Logs"]
  },
  {
    code: "FIELD_AGENT",
    title: "Field Agent (Mobile User)",
    scope: "PROJECT (Field Only)",
    purpose: "Captures usage surveys, stove installations, and battery swaps via mobile app.",
    permissions: ["activity:create", "activity:read", "asset:read"],
    limitations: ["Read/write limited strictly to self-captured submissions."],
    whoCreates: "Field Supervisor / Project Manager.",
    canSee: ["Own Submissions", "Assigned Asset Geofences"],
    cannotSee: ["Other Agents' Drafts", "Project Analytics", "User Management"]
  },
  {
    code: "AUDITOR",
    title: "Independent Auditor / VVB Verifier",
    scope: "PROJECT / AUDIT SCOPE",
    purpose: "Independent third-party validation and verification of climate impact data.",
    permissions: ["project:read", "asset:read", "activity:read", "report:read", "ledger:read", "audit:write"],
    limitations: ["Read-only access to MRV data; write access limited strictly to audit findings."],
    whoCreates: "Super Admin or Organization Administrator.",
    canSee: ["Complete Audit Trail", "Evidence Records", "Calculation Formulas", "Sensor Logs"],
    cannotSee: ["Private Financial Contracts", "Internal Org Settings"]
  },
  {
    code: "VIEWER",
    title: "Read-Only Viewer / Investor",
    scope: "ORGANIZATION / PROJECT",
    purpose: "Read-only access for stakeholders, investors, and public observers.",
    permissions: ["project:read", "asset:read", "activity:read", "report:read"],
    limitations: ["Strictly read-only; cannot modify any platform data."],
    whoCreates: "Organization Administrator.",
    canSee: ["Public Analytics", "Verified Reports", "Project Summaries"],
    cannotSee: ["Unverified Drafts", "User Management", "System Logs"]
  }
];

export const GLOSSARY_TERMS: GlossaryTerm[] = [
  { term: "MRV", definition: "Measurement, Reporting, and Verification — the structured framework used to quantify carbon reduction and removal impact.", category: "Climate Architecture" },
  { term: "Carbon Credit", definition: "A tradable certificate representing one metric tonne of carbon dioxide equivalent (tCO₂e) reduced or removed from the atmosphere.", category: "Carbon Markets" },
  { term: "Additionality", definition: "The requirement that carbon impact would not have occurred without the incentive provided by carbon finance.", category: "Methodology" },
  { term: "Baseline Emissions", definition: "The reference scenario representing GHG emissions that would occur in the absence of the project activity.", category: "Methodology" },
  { term: "Project Emissions", definition: "GHG emissions resulting directly from the operation of the climate project activity.", category: "Methodology" },
  { term: "Leakage", definition: "Net change in anthropogenic GHG emissions occurring outside the project boundary attributable to the project activity.", category: "Methodology" },
  { term: "Permanence", definition: "The longevity of carbon storage, ensuring carbon removed remains sequestered without reversal.", category: "Biochar / Removal" },
  { term: "Digital Twin", definition: "A virtual real-time model of a physical climate asset (e.g. solar array, charger) driven by IoT telemetry.", category: "IoT & Hardware" },
  { term: "Trust Score", definition: "An algorithmic confidence rating (0-100) computed from sensor anomaly checks, geofencing, and validation.", category: "Data Governance" },
  { term: "VVB", definition: "Validation and Verification Body — an accredited independent auditor that verifies carbon offset projects.", category: "Compliance" },
  { term: "Tenant Isolation", definition: "Security architecture ensuring an organization's data is logically segregated and inaccessible to other organizations.", category: "Security" },
  { term: "Methodology Family", definition: "A group of related carbon quantification protocols sharing common standards (e.g., Clean Cookstoves, Biochar).", category: "Methodology" },
  { term: "IIoT Telemetry", definition: "Industrial Internet of Things sensor data captured directly from hardware energy meters and chargers.", category: "IoT & Hardware" },
  { term: "Biochar Pyrolysis", definition: "Thermal decomposition of biomass at elevated temperatures in an oxygen-deprived environment to produce stable carbon.", category: "Biochar" },
  { term: "Fuel Displacement", definition: "The reduction in fossil fuel or non-renewable biomass consumption achieved through cleaner technology.", category: "Energy / Mobility" }
];

export const FAQS_LIST: FAQItem[] = [
  {
    id: "faq-1",
    question: "What is the primary purpose of VeriField Nexus?",
    answer: "VeriField Nexus is an enterprise Climate MRV (Measurement, Reporting, and Verification) and Carbon Intelligence platform that automates the collection, calculation, verification, and audit trail of carbon offset data across Clean Cookstoves, Hybrid Energy, Biochar, and EV Mobility sectors.",
    category: "General",
    keywords: ["purpose", "what is", "mrv", "overview"]
  },
  {
    id: "faq-2",
    question: "How does tenant isolation work in VeriField Nexus?",
    answer: "VeriField Nexus uses strict server-side multi-tenant scoping based on organization_id. Every database query, API endpoint, and dashboard resolver enforces organization filtering so users can only access data belonging to their licensed organization.",
    category: "Security & Access",
    keywords: ["tenant", "isolation", "security", "multi-tenant"]
  },
  {
    id: "faq-3",
    question: "Why am I unable to view certain climate sectors or methodologies?",
    answer: "Sector and methodology visibility is governed by your organization's licensed sectors. If your organization is licensed for EV Mobility, your account will only see EV Mobility dashboards and VM0038 methodologies. Contact your Super Admin to update sector licenses.",
    category: "Organizations & Projects",
    keywords: ["sectors", "licensed", "missing sector", "methodology access"]
  },
  {
    id: "faq-4",
    question: "How is CO₂ reduction calculated for Clean Cookstoves?",
    answer: "Cookstove reductions use methodology AMS-II.G / VMR0006 standards: CO₂e = (Biomass Saved in tonnes) × (Fraction of Non-Renewable Biomass fNRB) × (Emission Factor EF). Telemetry from stove usage monitors or field surveys supplies the usage hours.",
    category: "Methodologies & MRV",
    keywords: ["cookstove", "calculation", "ams-ii.g", "co2 reduced"]
  },
  {
    id: "faq-5",
    question: "How is carbon removal quantified for Biochar projects?",
    answer: "Biochar removal uses EBC / Verra VM0044 standards: Net Carbon Removed = (Biochar Mass in dry tonnes) × (Organic Carbon Content % C_org) × (Permanence Factor F_perm) minus pyrolysis processing and transport emissions.",
    category: "Methodologies & MRV",
    keywords: ["biochar", "removal", "ebc", "carbon sequestered"]
  },
  {
    id: "faq-6",
    question: "How is diesel displacement calculated in Hybrid Energy projects?",
    answer: "Hybrid energy mini-grids calculate emissions displaced by taking kWh generated from solar/micro-hydro × baseline diesel generator emission factor (approx 0.8 to 1.0 kg CO₂e/kWh), adjusted for grid loss.",
    category: "Methodologies & MRV",
    keywords: ["hybrid energy", "diesel avoided", "kwh", "mini-grid"]
  },
  {
    id: "faq-7",
    question: "How do EV charging sessions translate to emission reductions?",
    answer: "EV Mobility uses Verra VM0038 / AMS-III.C: CO₂ Displaced = (Kilometers Driven or kWh Charged) × (Baseline Internal Combustion Engine Emission Factor g CO₂/km minus Grid Charging Carbon Intensity).",
    category: "Methodologies & MRV",
    keywords: ["ev mobility", "charging", "vm0038", "diesel avoided"]
  },
  {
    id: "faq-8",
    question: "What is an AI Trust Score and how is it computed?",
    answer: "The Trust Score is an algorithmic index (0 to 100) calculated per activity. It evaluates sensor telemetry continuity, GPS geofencing, timestamp sequence anomalies, and historical device bounds. Scores below 80 are flagged for manual QA review.",
    category: "Verification & Audits",
    keywords: ["trust score", "ai", "audit", "flagged"]
  },
  {
    id: "faq-9",
    question: "Can an approved or verified activity be edited?",
    answer: "No. Once an activity status transitions to APPROVED or VERIFIED, it becomes immutable in the compliance ledger to preserve audit integrity. Any adjustment requires submitting a corrective activity record with audit trail logs.",
    category: "Verification & Audits",
    keywords: ["edit activity", "immutable", "approved", "locked"]
  },
  {
    id: "faq-10",
    question: "Who can approve access requests for new organizations?",
    answer: "Only users holding the Platform Super Admin role (`SUPER_ADMIN`) have permission to review, approve, or reject new organization access requests in the Super Admin Governance Console.",
    category: "Super Admin",
    keywords: ["access request", "super admin", "approval", "onboarding"]
  },
  {
    id: "faq-11",
    question: "How do I invite a new user to my organization?",
    answer: "Organization Admins can navigate to Dashboard > People & Access or Super Admin > Users, click 'Invite User', enter full name, email, select a role (e.g. Field Agent, Project Manager), and click Provision.",
    category: "Access & Auth",
    keywords: ["invite user", "add team member", "provision", "roles"]
  },
  {
    id: "faq-12",
    question: "What happens if a user account is suspended?",
    answer: "When a Super Admin suspends an account, the user's active JWT tokens are immediately revoked. Any subsequent API requests or login attempts return an HTTP 403 Forbidden error until reactivated.",
    category: "Access & Auth",
    keywords: ["suspend account", "blocked", "inactive", "forbidden"]
  },
  {
    id: "faq-13",
    question: "How do I switch between dark mode and light mode?",
    answer: "Click your avatar in the top right header or navigation sidebar to toggle the Theme Switcher. The platform automatically adjusts background tones and switches between dark text (`logo-black.png`) and white text (`logo-white.png`) brand assets.",
    category: "General",
    keywords: ["dark mode", "light mode", "theme", "logo"]
  },
  {
    id: "faq-14",
    question: "What format are reports exported in?",
    answer: "Reports can be exported in PDF (audited executive summary), CSV (raw telemetry and activity logs), and Excel format via the Reports & Analytics module.",
    category: "Assets & Data",
    keywords: ["export", "pdf", "csv", "excel", "reports"]
  },
  {
    id: "faq-15",
    question: "How does the search engine order results across the platform?",
    answer: "Global search and lists apply the platform-wide ordering standard: Role Priority (SUPER_ADMIN → ADMIN → ORG_ADMIN → PORTFOLIO_MANAGER → PROJECT_MANAGER → FIELD_AGENT → AUDITOR → VIEWER), then Alphabetical A-Z, then Newest Created.",
    category: "General",
    keywords: ["search", "sorting", "order", "alphabetical"]
  },
  {
    id: "faq-16",
    question: "What is an Asset in VeriField Nexus?",
    answer: "An Asset represents a physical hardware device or installation registered within a climate project, such as a solar array, EV charging station, cookstove meter, or biochar pyrolyzer.",
    category: "Assets & Data",
    keywords: ["asset", "hardware", "device", "solar"]
  },
  {
    id: "faq-17",
    question: "What is an Activity in VeriField Nexus?",
    answer: "An Activity is an individual operational data point recorded for an asset—such as a 4-hour cooking session, a 45 kWh EV charge, or a 2.5 tonne biochar production batch.",
    category: "Assets & Data",
    keywords: ["activity", "data point", "telemetry", "batch"]
  },
  {
    id: "faq-18",
    question: "Why is a project status shown as 'Pending Audit'?",
    answer: "A project transitions to 'Pending Audit' when all activities have been logged and submitted for independent third-party verification by an accredited VVB auditor.",
    category: "Verification & Audits",
    keywords: ["pending audit", "status", "vvb", "audit"]
  },
  {
    id: "faq-19",
    question: "Can a project belong to multiple organizations?",
    answer: "No. Every project is strictly owned by exactly one Organization tenant to ensure clean financial, operational, and legal accountability.",
    category: "Organizations & Projects",
    keywords: ["project owner", "multi-org", "tenancy", "organization"]
  },
  {
    id: "faq-20",
    question: "How does VeriField Nexus handle offline field data collection?",
    answer: "The VeriField mobile application allows Field Agents to record surveys and stove installations offline. Submissions are stored in local encrypted storage and synced automatically when network connectivity is restored.",
    category: "Assets & Data",
    keywords: ["offline", "mobile app", "sync", "field agent"]
  },
  {
    id: "faq-21",
    question: "What is the difference between actual measurements and derived estimates?",
    answer: "Actual measurements come directly from calibrated hardware sensors (e.g. smart kWh meters). Derived estimates use standardized mathematical models (e.g. usage survey hours × stove rating) when direct metering is impractical.",
    category: "Analytics & Metrics",
    keywords: ["actual", "derived", "measurements", "estimates"]
  },
  {
    id: "faq-22",
    question: "How do I reset my account password?",
    answer: "If you are logged in, go to Settings > Profile > Security to change password. If you forgot your password, contact your Organization Admin or Super Admin to issue a secure password reset link.",
    category: "Access & Auth",
    keywords: ["password reset", "forgot password", "credentials"]
  },
  {
    id: "faq-23",
    question: "What is the Role Permission Catalogue?",
    answer: "Located in Super Admin > Governance, the Role Permission Catalogue is an interactive IAM console where administrators can explore role permissions, scopes, user assignments, permission dependencies, and role comparison deltas.",
    category: "Super Admin",
    keywords: ["iam", "role catalogue", "permissions matrix", "super admin"]
  },
  {
    id: "faq-24",
    question: "Why can't I delete a system role like SUPER_ADMIN or ORG_ADMIN?",
    answer: "Protected system roles are hardcoded to prevent security vulnerabilities and platform lockout. They cannot be deleted or stripped of core permissions.",
    category: "Security & Access",
    keywords: ["protected role", "delete role", "super admin", "locked"]
  },
  {
    id: "faq-25",
    question: "How do I export the entire Role & Permission Matrix?",
    answer: "In Super Admin > Roles & Permissions, click the 'Export CSV' button in the top toolbar to download the complete enterprise roles, scopes, user counts, and atomic permissions matrix.",
    category: "Super Admin",
    keywords: ["export csv", "role matrix", "download", "governance"]
  },
  {
    id: "faq-26",
    question: "What is the difference between an Auditor and a QA Officer?",
    answer: "A QA Officer is an internal organization reviewer who checks data quality. An Auditor (VVB) is an independent external verifier who performs formal third-party audits for carbon credit issuance.",
    category: "Verification & Audits",
    keywords: ["auditor", "qa officer", "vvb", "difference"]
  },
  {
    id: "faq-27",
    question: "What are atomic permissions?",
    answer: "Atomic permissions are granular action codes (such as `project:read`, `activity:create`, `activity:verify`, `report:all`) that define exact API and UI capabilities assigned to roles.",
    category: "Security & Access",
    keywords: ["atomic permissions", "rbac", "granular", "capabilities"]
  },
  {
    id: "faq-28",
    question: "How does the Role Comparison tool work?",
    answer: "In the Role Permission Console, click 'Compare Roles', select two roles from the dropdowns, and the engine immediately displays common matching permissions, unique permissions in Role A, and unique permissions in Role B.",
    category: "Super Admin",
    keywords: ["role comparison", "compare", "delta", "permissions"]
  },
  {
    id: "faq-29",
    question: "How do I view all users assigned to a specific role?",
    answer: "In the Role Permission Console, click any role card to open the Role Detail View, then select the 'Assigned Users' tab to view a searchable, paginated table of accounts holding that role.",
    category: "Super Admin",
    keywords: ["assigned users", "role detail", "user table"]
  },
  {
    id: "faq-30",
    question: "What is the Scope Cascading Graph?",
    answer: "It is a visual representation of how permissions cascade down the enterprise hierarchy: PLATFORM → ORGANIZATION → PORTFOLIO → PROJECT → ACTIVITY → ASSET.",
    category: "Super Admin",
    keywords: ["scope graph", "hierarchy", "cascading", "scoping"]
  },
  {
    id: "faq-31",
    question: "What causes an activity to be flagged as FLAGGED or REVIEW?",
    answer: "Activities are flagged automatically if sensor data contains sudden spikes, GPS coordinates fall outside project geofences, or timestamps are duplicate/out of sequence.",
    category: "Verification & Audits",
    keywords: ["flagged", "review", "anomaly", "sensor spike"]
  },
  {
    id: "faq-32",
    question: "How do I filter activities by date range?",
    answer: "In Dashboard > Activities or Analytics, click the Date Filter dropdown and choose from presets (Today, Yesterday, Last 7 Days, Last 30 Days, This Month, Last Month, This Year) or enter custom dates.",
    category: "Assets & Data",
    keywords: ["date filter", "range", "presets", "activities"]
  },
  {
    id: "faq-33",
    question: "What is a Digital Twin in VeriField Nexus?",
    answer: "A Digital Twin is a software model of an active physical asset (e.g. EV charger) that maintains its current state, telemetry status, operational efficiency, and cumulative CO₂ displacement in real time.",
    category: "Assets & Data",
    keywords: ["digital twin", "telemetry", "real time", "model"]
  },
  {
    id: "faq-34",
    question: "Can I assign a user to multiple projects with different roles?",
    answer: "Yes. Project memberships allow a user to hold distinct project-level roles (e.g. Field Agent on Project A, QA Officer on Project B) while maintaining their primary organization role.",
    category: "Access & Auth",
    keywords: ["project membership", "multiple roles", "scoped roles"]
  },
  {
    id: "faq-35",
    question: "How is fNRB (Fraction of Non-Renewable Biomass) defined?",
    answer: "fNRB represents the proportion of woody biomass harvested unsustainably in a target region. It is a key parameter in cookstove methodology calculations specified by UNFCCC / Verra regional datasets.",
    category: "Methodologies & MRV",
    keywords: ["fnrb", "cookstove", "biomass", "unfccc"]
  },
  {
    id: "faq-36",
    question: "What happens when an organization is deactivated?",
    answer: "Deactivating an organization immediately blocks all associated users from logging in, pauses data ingestion, and archives active projects until reactivated by a Super Admin.",
    category: "Super Admin",
    keywords: ["deactivate org", "suspended org", "tenant block"]
  },
  {
    id: "faq-37",
    question: "Where can I view immutable security audit logs?",
    answer: "Super Admins can view platform-wide security audit logs under Super Admin > Governance > Security Logs. Log items record timestamps, actor user ID, action, target entity, and IP address.",
    category: "Super Admin",
    keywords: ["audit logs", "security logs", "immutable", "actor"]
  },
  {
    id: "faq-38",
    question: "How do I register a new EV Charging Station?",
    answer: "Go to Dashboard > Assets, click 'Register Asset', select 'EV Charging Station', enter serial number, max power rating (kW), connector types (Type 2, CCS2), GPS coordinates, and bind to an active EV project.",
    category: "Assets & Data",
    keywords: ["register asset", "ev station", "charging", "serial number"]
  },
  {
    id: "faq-39",
    question: "How do I register a Biochar Batch?",
    answer: "Go to Dashboard > Assets > Biochar, click 'Register Batch', enter feedstock type (e.g. rice husk, wood waste), dry mass (tonnes), C_org percentage, pyrolysis temperature, and storage location.",
    category: "Assets & Data",
    keywords: ["biochar batch", "feedstock", "pyrolysis", "dry mass"]
  },
  {
    id: "faq-40",
    question: "What is the baseline scenario for EV Mobility projects?",
    answer: "The baseline scenario assumes equivalent passenger-kilometers or freight transport delivered by conventional internal combustion engine (ICE) vehicles burning gasoline or diesel.",
    category: "Methodologies & MRV",
    keywords: ["ev baseline", "ice vehicles", "gasoline", "diesel"]
  },
  {
    id: "faq-41",
    question: "What is the baseline scenario for Hybrid Energy projects?",
    answer: "The baseline scenario assumes electricity supplied by standalone diesel generators operating at standard thermal efficiencies.",
    category: "Methodologies & MRV",
    keywords: ["hybrid baseline", "diesel generator", "mini grid"]
  },
  {
    id: "faq-42",
    question: "How does the system prevent double counting of carbon credits?",
    answer: "VeriField Nexus enforces unique serial number tracking, geofence boundary checks, and commits verified credits to an immutable compliance ledger indexed by project UUID.",
    category: "Security & Access",
    keywords: ["double counting", "serial number", "ledger", "integrity"]
  },
  {
    id: "faq-43",
    question: "Can I customize KPI dashboards for my organization?",
    answer: "Yes. Organization Admins can configure visible widgets, target performance thresholds, and default date ranges under Settings > Sector Dashboards.",
    category: "Analytics & Metrics",
    keywords: ["customize dashboard", "kpi", "widgets", "settings"]
  },
  {
    id: "faq-44",
    question: "What keyboard shortcuts are available?",
    answer: "Press `/` to focus global search, `Esc` to close open modals, `Ctrl + K` to trigger quick command palette, and `Ctrl + P` to print current documentation articles.",
    category: "General",
    keywords: ["shortcuts", "keyboard", "hotkeys", "search"]
  },
  {
    id: "faq-45",
    question: "How do I report a bug or system issue?",
    answer: "Click 'Contact Support' in the Help Centre sidebar or email support@verifield.io with your organization ID, screenshot, and reproduction steps.",
    category: "General",
    keywords: ["support", "bug", "help", "contact"]
  },
  {
    id: "faq-46",
    question: "What browser versions are supported?",
    answer: "VeriField Nexus supports modern evergreen browsers including Google Chrome 100+, Mozilla Firefox 100+, Apple Safari 15+, and Microsoft Edge 100+.",
    category: "General",
    keywords: ["browser", "chrome", "safari", "compatibility"]
  },
  {
    id: "faq-47",
    question: "How often are IoT telemetry metrics updated on the dashboard?",
    answer: "IoT sensor streams update in real-time or near real-time (every 1 to 15 minutes depending on device hardware polling settings).",
    category: "Assets & Data",
    keywords: ["iot update", "real time", "telemetry frequency"]
  },
  {
    id: "faq-48",
    question: "What is an Evidence Record?",
    answer: "An Evidence Record is a supporting document (e.g. photo calibration certificate, laboratory biochar lab analysis, fuel receipt) attached to an activity for audit proof.",
    category: "Verification & Audits",
    keywords: ["evidence record", "lab analysis", "photo", "calibration"]
  },
  {
    id: "faq-49",
    question: "Can I export data for a specific project only?",
    answer: "Yes. Open the Project Detail view, select the 'Data & Analytics' tab, apply desired filters, and click 'Export Project Data'.",
    category: "Assets & Data",
    keywords: ["export project", "project data", "csv export"]
  },
  {
    id: "faq-50",
    question: "How is data encrypted in transit and at rest?",
    answer: "All data in transit is encrypted using TLS 1.3. Database storage and sensitive columns are encrypted at rest using AES-256 standards.",
    category: "Security & Access",
    keywords: ["encryption", "tls", "aes-256", "security"]
  }
];

export const KEYBOARD_SHORTCUTS = [
  { keyCombo: "/", description: "Focus global search bar" },
  { keyCombo: "Ctrl + K", description: "Open quick command search palette" },
  { keyCombo: "Esc", description: "Close active modal, drawer, or search results" },
  { keyCombo: "Ctrl + P", description: "Print current documentation article" },
  { keyCombo: "Alt + H", description: "Navigate to Help & Knowledge Centre" },
  { keyCombo: "Alt + D", description: "Navigate to Main Dashboard" },
  { keyCombo: "Alt + P", description: "Navigate to Projects" },
  { keyCombo: "Alt + A", description: "Navigate to Assets" },
  { keyCombo: "Alt + S", description: "Navigate to Super Admin Portal (Super Admin only)" }
];
