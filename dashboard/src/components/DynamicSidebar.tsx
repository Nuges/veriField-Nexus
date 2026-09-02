// =============================================================================
// VeriField Nexus — Enterprise Dynamic Sidebar Component (Level 5 CIOS)
// =============================================================================
// Standardized Enterprise Navigation Hierarchy.
// Strictly segregated navigation tailored to each canonical role persona.
// Unknown roles fail closed to the least-privileged VIEWER workspace.
// =============================================================================

"use client";

import Link from "next/link";
import { ThemeLogo } from "@/components/common/ThemeLogo";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radio,
  Briefcase,
  Activity,
  Users,
  Settings,
  Globe,
  Sliders,
  Layers,
  ShieldCheck,
  Zap,
  Bot,
  FileText,
  HelpCircle,
  Lock,
  DollarSign,
  TrendingUp,
  FileCheck,
  CheckCircle2,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchActivities } from "@/lib/api";
import { getSectorTerminology } from "@/lib/moduleRegistry";
import { normalizeRole, CANONICAL_ROLES, CanonicalRole } from "@/lib/roles";

const ICON_MAP: Record<string, any> = {
  LayoutDashboard,
  Radio,
  Briefcase,
  Activity,
  Users,
  Settings,
  Globe,
  Sliders,
  Layers,
  ShieldCheck,
  Zap,
  Bot,
  FileText,
  HelpCircle,
  Lock,
  DollarSign,
  TrendingUp,
  FileCheck,
  CheckCircle2,
};

interface NavItem {
  label: string;
  icon: string;
  href: string;
  badge?: string;
  external?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

export function DynamicSidebar() {
  const pathname = usePathname();
  const { user, activeSector } = useWorkspace();
  const [flaggedCount, setFlaggedCount] = useState<number | null>(null);
  const [pendingCount, setPendingCount] = useState<number | null>(null);

  const sectorTerms = getSectorTerminology(activeSector);
  const canonicalRole = normalizeRole(user?.role);

  useEffect(() => {
    async function loadRealTimeCounts() {
      try {
        const res = await fetchActivities();
        const activities = Array.isArray(res) ? res : res?.activities || [];
        if (activities.length > 0) {
          const flagged = activities.filter(
            (a: any) =>
              a.trust_status === "REVIEW" ||
              a.trust_status === "FLAGGED" ||
              (a.trust_score !== undefined && a.trust_score < 80)
          ).length;
          const pending = activities.filter(
            (a: any) =>
              a.verification_status === "PENDING" ||
              a.trust_status === "REVIEW" ||
              a.status === "audit"
          ).length;
          setFlaggedCount(flagged);
          setPendingCount(pending);
        }
      } catch (err) {
        console.error("Failed to load real-time sidebar badges", err);
      }
    }
    loadRealTimeCounts();
  }, []);

  // ─── Purpose-Built Navigation Per Canonical Persona ────────────────────────
  const getNavGroups = (): NavGroup[] => {
    switch (canonicalRole) {
      case "SUPER_ADMIN":
        return [
          {
            title: "Platform Governance",
            items: [
              { label: "Global Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Global Infrastructure", icon: "Sliders", href: "/super-admin" },
              { label: "All Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "PoA Programmes", icon: "Globe", href: "/dashboard/poa" },
            ],
          },
          {
            title: "MRV, Registry & Carbon",
            items: [
              { label: "Methodologies", icon: "Layers", href: "/dashboard/methodologies" },
              {
                label: "Verification Queue",
                icon: "ShieldCheck",
                href: "/dashboard/verifications",
                badge: pendingCount ? `${pendingCount}` : undefined,
              },
              { label: "Carbon Ledger", icon: "Sliders", href: "/dashboard/carbon" },
              { label: "Compliance Center", icon: "Globe", href: "/dashboard/command-center" },
              { label: "Global Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Administration",
            items: [
              { label: "Tenant & User Access", icon: "Users", href: "/dashboard/people" },
              { label: "Platform Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
          {
            title: "Intelligence",
            items: [
              { label: "AI Orchestrator", icon: "Bot", href: "/dashboard/ai", badge: "Live" },
              { label: "Help & Knowledge", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "ORG_ADMIN":
        return [
          {
            title: "Governance & Operations",
            items: [
              { label: "Organization Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: sectorTerms.projectsNavLabel, icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Programmes (PoA)", icon: "Globe", href: "/dashboard/poa" },
              {
                label: "Field Operations",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Live Telemetry", icon: "Activity", href: "/dashboard/monitoring" },
            ],
          },
          {
            title: "Reporting & Assets",
            items: [
              { label: "Carbon Ledger", icon: "Sliders", href: "/dashboard/carbon" },
              { label: "Organization Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Administration & Security",
            items: [
              { label: "People & Access", icon: "Users", href: "/dashboard/people" },
              { label: "Organization Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
          {
            title: "Intelligence & Guides",
            items: [
              { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai", badge: "Live" },
              { label: "Help & Knowledge", icon: "HelpCircle", href: "/dashboard/help" },
            ],
          },
        ];

      case "PROJECT_MANAGER":
        return [
          {
            title: "Project Delivery",
            items: [
              { label: "Project Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
              { label: sectorTerms.projectsNavLabel, icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Programmes (PoA)", icon: "Globe", href: "/dashboard/poa" },
              {
                label: "Project Activities",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Monitoring & IoT", icon: "Activity", href: "/dashboard/monitoring" },
            ],
          },
          {
            title: "MRV & Documentation",
            items: [
              { label: "Methodology & PDD", icon: "Layers", href: "/dashboard/methodologies" },
              { label: "Registry Packages", icon: "FileCheck", href: "/dashboard/registry" },
              { label: "Project Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Intelligence & Guides",
            items: [
              { label: "AI Project Assistant", icon: "Bot", href: "/dashboard/ai", badge: "Live" },
              { label: "Project Guidelines", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Settings & Profile", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "FIELD_SUPERVISOR":
        return [
          {
            title: "Field Operations",
            items: [
              { label: "Supervisor Overview", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "Field Activity Queue",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Device Telemetry", icon: "Activity", href: "/dashboard/monitoring" },
              { label: sectorTerms.projectsNavLabel, icon: "Briefcase", href: "/dashboard/projects" },
            ],
          },
          {
            title: "Reporting & Intelligence",
            items: [
              { label: "Field Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "Field AI Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Account Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "FIELD_AGENT":
        return [
          {
            title: "Field Work",
            items: [
              { label: "My Assignments", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "Activity Capture",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Device & Sensor Status", icon: "Activity", href: "/dashboard/monitoring" },
            ],
          },
          {
            title: "Intelligence & Guides",
            items: [
              { label: "Field AI Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help & Knowledge", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Account Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "QA_OFFICER":
        return [
          {
            title: "MRV & QA/QC Control",
            items: [
              { label: "MRV Control Center", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Monitoring Data", icon: "Activity", href: "/dashboard/monitoring" },
              {
                label: "QA/QC Review Queue",
                icon: "Radio",
                href: "/dashboard/operations",
                badge: flaggedCount ? `${flaggedCount}` : undefined,
              },
              { label: "Methodologies", icon: "Layers", href: "/dashboard/methodologies" },
            ],
          },
          {
            title: "Analysis & Reporting",
            items: [
              { label: "MRV Analytics", icon: "FileText", href: "/dashboard/analytics" },
              { label: "AI Quality Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Account Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "VERIFIER":
        return [
          {
            title: "VVB Verification Workspace",
            items: [
              { label: "Verification Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "Verification Queue",
                icon: "ShieldCheck",
                href: "/dashboard/verifications",
                badge: pendingCount ? `${pendingCount}` : undefined,
              },
              { label: "Assigned Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Monitoring & Lineage", icon: "Activity", href: "/dashboard/monitoring" },
            ],
          },
          {
            title: "Technical Review",
            items: [
              { label: "Methodology & PDD", icon: "Layers", href: "/dashboard/methodologies" },
              { label: "Carbon Ledger View", icon: "Sliders", href: "/dashboard/carbon" },
              { label: "Verification Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Intelligence & Standards",
            items: [
              { label: "AI Audit Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "VVB Guidelines", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Verifier Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "AUDITOR":
        return [
          {
            title: "Audit Operations",
            items: [
              { label: "Audit Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
              {
                label: "Audit Findings & NCRs",
                icon: "ShieldCheck",
                href: "/dashboard/verifications",
                badge: pendingCount ? `${pendingCount}` : undefined,
              },
              { label: "Audited Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Sensor Evidence & Lineage", icon: "Activity", href: "/dashboard/monitoring" },
            ],
          },
          {
            title: "Evidence & Standards",
            items: [
              { label: "Methodology Evidence", icon: "Layers", href: "/dashboard/methodologies" },
              { label: "Audit Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Audit Intelligence",
            items: [
              { label: "AI Audit Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "Audit Standards", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Audit Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "COMPLIANCE_ADMIN":
        return [
          {
            title: "Compliance & Sovereign Control",
            items: [
              { label: "Compliance Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Article 6 Command Center", icon: "Globe", href: "/dashboard/command-center" },
              { label: "Project Portfolio", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "PoA Programmes", icon: "Globe", href: "/dashboard/poa" },
            ],
          },
          {
            title: "Regulatory Documents",
            items: [
              { label: "Methodologies & NDC", icon: "Layers", href: "/dashboard/methodologies" },
              { label: "Registry Packages", icon: "FileCheck", href: "/dashboard/registry" },
              { label: "Compliance Reports", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Intelligence & Guides",
            items: [
              { label: "AI Compliance Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "Host Country Guidelines", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Compliance Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "REGISTRY_ADMIN":
        return [
          {
            title: "Registry Operations",
            items: [
              { label: "Registry Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Submission Packages", icon: "FileCheck", href: "/dashboard/registry" },
              { label: "Registered Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Carbon Credit Ledger", icon: "Sliders", href: "/dashboard/carbon" },
            ],
          },
          {
            title: "Reports & Intelligence",
            items: [
              { label: "Issuance Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "AI Registry Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "Registry Standards", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Registry Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "FINANCE":
        return [
          {
            title: "Carbon Asset & Settlement",
            items: [
              { label: "Finance Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Carbon Credit Ledger", icon: "Sliders", href: "/dashboard/carbon" },
              { label: "Project Valuations", icon: "Briefcase", href: "/dashboard/projects" },
            ],
          },
          {
            title: "Financial Reporting",
            items: [
              { label: "Financial & Yield Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "AI Financial Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help & Knowledge", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Finance Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];

      case "INVESTOR":
        return [
          {
            title: "Portfolio Overview",
            items: [
              { label: "Portfolio Dashboard", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Funded Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Carbon Assets", icon: "Sliders", href: "/dashboard/carbon" },
            ],
          },
          {
            title: "Performance & Insights",
            items: [
              { label: "Performance Reports", icon: "FileText", href: "/dashboard/analytics" },
              { label: "AI Portfolio Assistant", icon: "Bot", href: "/dashboard/ai" },
              { label: "Help & Knowledge", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "Account Settings", icon: "Settings", href: "/dashboard/settings" },
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
              { label: "Portfolio Overview", icon: "LayoutDashboard", href: "/dashboard" },
              { label: "Public Projects", icon: "Briefcase", href: "/dashboard/projects" },
              { label: "Reports & Certificates", icon: "FileText", href: "/dashboard/analytics" },
            ],
          },
          {
            title: "Knowledge & Guides",
            items: [
              { label: "Help & Knowledge", icon: "HelpCircle", href: "/dashboard/help" },
              { label: "User Settings", icon: "Settings", href: "/dashboard/settings" },
            ],
          },
        ];
    }
  };

  const navGroups = getNavGroups();

  const getIsActive = (href: string) => {
    if (!pathname) return false;
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <aside className="w-64 bg-[var(--color-surface)] border-r border-[var(--color-border)] flex flex-col h-screen fixed left-0 top-0 z-30 select-none shadow-sm transition-colors duration-200">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-[var(--color-border)] gap-3 bg-[var(--color-surface)]">
        <ThemeLogo className="h-8 w-auto" />
      </div>

      {/* Role Persona Tag */}
      <div className="px-5 py-2 bg-[var(--color-background)] border-b border-[var(--color-border)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-mono tracking-wider font-bold text-[var(--color-text-primary)] uppercase">
            {canonicalRole.replace("_", " ")}
          </span>
        </div>
        <span className="text-[9px] font-mono text-[var(--color-text-secondary)] uppercase tracking-widest font-semibold">
          LEVEL 5
        </span>
      </div>

      {/* Scrollable Navigation Groups */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5 scrollbar-thin scrollbar-thumb-[var(--color-border)]">
        {navGroups.map((group, gIdx) => (
          <div key={gIdx} className="space-y-1">
            <div className="px-3 text-[10px] font-mono uppercase tracking-wider text-[var(--color-text-secondary)] font-bold mb-1.5 opacity-80">
              {group.title}
            </div>
            {group.items.map((item, iIdx) => {
              const Icon = ICON_MAP[item.icon] || LayoutDashboard;
              const active = getIsActive(item.href);

              return (
                <Link
                  key={iIdx}
                  href={item.href}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 ${
                    active
                      ? "bg-emerald-500/10 text-[#008A5E] dark:text-emerald-400 font-bold border border-emerald-500/20 shadow-xs"
                      : "text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon className={`w-4 h-4 shrink-0 ${active ? "text-[#008A5E] dark:text-emerald-400" : "text-[var(--color-text-secondary)]"}`} />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded-full font-mono font-bold ${
                        item.badge === "Live"
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 animate-pulse"
                          : "bg-amber-500/20 text-amber-600 dark:text-amber-300 border border-amber-500/30"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-[var(--color-border)] bg-[var(--color-background)] text-[10px] font-mono text-[var(--color-text-secondary)] flex items-center justify-between">
        <span>CIOS v5.4-PROD</span>
        <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-semibold">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
          SECURE
        </span>
      </div>
    </aside>
  );
}

export default DynamicSidebar;


