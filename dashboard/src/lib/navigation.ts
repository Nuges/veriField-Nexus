import { isDashboardRoleAllowed, isRouteAuthorized, normalizeRole } from "./roles";
export interface NavItem {
  label: string;
  icon: string;
  href: string;
  badge?: string;
  external?: boolean;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}


/** One canonical destination per feature. The same access rules guard direct URLs. */
export function getNavigationGroups(role?: string | null, flaggedCount?: number | null, pendingCount?: number | null): NavGroup[] {
  if (!isDashboardRoleAllowed(role)) return [];
  const canonicalRole = normalizeRole(role);
  const groups = (): NavGroup[] => {
    switch (canonicalRole) {
      case "SUPER_ADMIN":
        return [
          {
            title: "Platform",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Platform administration", icon: "Sliders", href: "/super-admin" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Programmes", icon: "Globe", href: "/dashboard/poa" },
              { label: "Field operations", icon: "Activity", href: "/dashboard/operations" },
              { label: "Sensors", icon: "Radio", href: "/dashboard/sensors" },
              { label: "Assets", icon: "Layers", href: "/dashboard/assets" },
              { label: "Data quality", icon: "CheckCircle2", href: "/dashboard/monitoring" },
              { label: "Field performance", icon: "Users", href: "/dashboard/agents" },
            ],
          },
          {
            title: "Records & reports",
            items: [
              { label: "Methodologies", icon: "Layers", href: "/dashboard/methodologies" },
              {
                label: "Verification Queue",
                icon: "ShieldCheck",
                href: "/dashboard/verifications",
                badge: pendingCount ? `${pendingCount}` : undefined,
              },
              { label: "Registry", icon: "FileCheck", href: "/dashboard/registry" },
              { label: "Carbon ledger", icon: "Sliders", href: "/dashboard/carbon" },
              { label: "Project map", icon: "Globe", href: "/dashboard/command-center" },
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Administration",
            items: [
              { label: "People & access", icon: "Users", href: "/dashboard/people" },
            ],
          },
          {
            title: "Support",
            items: [
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "ORG_ADMIN":
        return [
          {
            title: "Workspace",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Programmes", icon: "Globe", href: "/dashboard/poa" },
              {
                label: "Field Operations",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Data quality", icon: "Activity", href: "/dashboard/monitoring" },
              { label: "Project map", icon: "Globe", href: "/dashboard/command-center" },
            ],
          },
          {
            title: "Records & reports",
            items: [
              { label: "Sensors", icon: "Radio", href: "/dashboard/sensors" },
              { label: "Assets", icon: "Layers", href: "/dashboard/assets" },
              { label: "Verification", icon: "ShieldCheck", href: "/dashboard/verifications" },
              { label: "Registry", icon: "FileCheck", href: "/dashboard/registry" },
              { label: "Carbon ledger", icon: "Sliders", href: "/dashboard/carbon" },
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Administration",
            items: [
              { label: "People & access", icon: "Users", href: "/dashboard/people" },
              { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
          {
            title: "Support",
            items: [
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "PROJECT_MANAGER":
        return [
          {
            title: "Project Delivery",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Project map", icon: "Globe", href: "/dashboard/command-center" },
              { label: "Programmes", icon: "Globe", href: "/dashboard/poa" },
              {
                label: "Project Activities",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Data quality", icon: "Activity", href: "/dashboard/monitoring" },
            ],
          },
          {
            title: "MRV & Documentation",
            items: [
              { label: "Methodologies", icon: "Layers", href: "/dashboard/methodologies" },
              { label: "Registry", icon: "FileCheck", href: "/dashboard/registry" },
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Support",
            items: [
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai", badge: undefined },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "FIELD_SUPERVISOR":
        return [
          {
            title: "Field Operations",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "Field Activity Queue",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Data quality", icon: "Activity", href: "/dashboard/monitoring" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
            ],
          },
          {
            title: "Reporting & Intelligence",
            items: [
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "FIELD_AGENT":
        return [
          {
            title: "Field Work",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "Capture data",
                icon: "Radio",
                href: "/capture",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Field records", icon: "Activity", href: "/dashboard/operations" },
            ],
          },
          {
            title: "Support",
            items: [
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "QA_OFFICER":
        return [
          {
            title: "MRV & QA/QC Control",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "QA Review",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Flagged Exceptions", icon: "AlertTriangle", href: "/dashboard/anomalies" },
              { label: "Trust Scores", icon: "ShieldCheck", href: "/dashboard/trust-scores" },
              { label: "Verification", icon: "FileCheck", href: "/dashboard/verifications" },
              { label: "Data quality", icon: "Activity", href: "/dashboard/monitoring" },
              { label: "Methodologies", icon: "Layers", href: "/dashboard/methodologies" },
            ],
          },
          {
            title: "Analysis & Reporting",
            items: [
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "VERIFIER":
        return [
          {
            title: "VVB Verification Workspace",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "Verification Queue",
                icon: "ShieldCheck",
                href: "/dashboard/verifications",
                badge: pendingCount ? `${pendingCount}` : undefined,
              },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Data quality", icon: "Activity", href: "/dashboard/monitoring" },
            ],
          },
          {
            title: "Technical Review",
            items: [
              { label: "Methodologies", icon: "Layers", href: "/dashboard/methodologies" },
              { label: "Carbon ledger", icon: "Sliders", href: "/dashboard/carbon" },
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Support",
            items: [
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "AUDITOR":
        return [
          {
            title: "Audit Operations",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "Audit Findings & NCRs",
                icon: "ShieldCheck",
                href: "/dashboard/verifications",
                badge: pendingCount ? `${pendingCount}` : undefined,
              },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Data quality", icon: "Activity", href: "/dashboard/monitoring" },
            ],
          },
          {
            title: "Evidence & Standards",
            items: [
              { label: "Methodologies", icon: "Layers", href: "/dashboard/methodologies" },
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Support",
            items: [
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "COMPLIANCE_ADMIN":
        return [
          {
            title: "Compliance & Sovereign Control",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Project map", icon: "Globe", href: "/dashboard/command-center" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Programmes", icon: "Globe", href: "/dashboard/poa" },
            ],
          },
          {
            title: "Regulatory Documents",
            items: [
              { label: "Methodologies", icon: "Layers", href: "/dashboard/methodologies" },
              { label: "Registry", icon: "FileCheck", href: "/dashboard/registry" },
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Support",
            items: [
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "REGISTRY_ADMIN":
        return [
          {
            title: "Registry Operations",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Registry", icon: "FileCheck", href: "/dashboard/registry" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Carbon ledger", icon: "Sliders", href: "/dashboard/carbon" },
            ],
          },
          {
            title: "Reports & support",
            items: [
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "FINANCE":
        return [
          {
            title: "Carbon Asset & Settlement",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Carbon ledger", icon: "Sliders", href: "/dashboard/carbon" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
            ],
          },
          {
            title: "Financial Reporting",
            items: [
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "INVESTOR":
        return [
          {
            title: "Portfolio Overview",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Carbon ledger", icon: "Sliders", href: "/dashboard/carbon" },
            ],
          },
          {
            title: "Performance & Insights",
            items: [
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "Decision support", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "VIEWER":
      default:
        // Fail-closed read-only workspace
        return [
          {
            title: "Overview",
            items: [
              { label: "Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Knowledge & Guides",
            items: [
              { label: "Help", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];
    }
  };


  const names: Record<string, string> = {"/dashboard": "Overview", "/super-admin": "Platform administration", "/dashboard/projects": "Projects", "/dashboard/operations": "Field operations", "/dashboard/monitoring": "Data quality", "/dashboard/sensors": "Sensors", "/dashboard/assets": "Assets", "/dashboard/people": "People & access", "/dashboard/agents": "Field performance", "/dashboard/verifications": "Verification", "/dashboard/analytics": "Reports", "/dashboard/carbon": "Carbon ledger", "/dashboard/methodologies": "Methodologies", "/dashboard/poa": "Programmes", "/dashboard/command-center": "Project map", "/dashboard/registry": "Registry", "/dashboard/ai": "Decision support", "/dashboard/help": "Help", "/dashboard/settings": "Settings"};
  const seen = new Set<string>();
  return groups().map(group => ({ ...group, items: group.items.map(item => ({...item, label: names[item.href] || item.label})).filter(item => {
    if (seen.has(item.href) || !isRouteAuthorized(item.href, role)) return false;
    seen.add(item.href);
    return true;
  }) })).filter(group => group.items.length);
}
