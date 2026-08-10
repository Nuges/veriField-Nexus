// =============================================================================

// VeriField Nexus — Enterprise Dynamic Sidebar Component (Level 5 CIOS)

// =============================================================================

// Standardized Enterprise Navigation Hierarchy following global ERP standards.

// Dynamic badges and role-based navigation sequence.

// Projects is the consolidated main entry point for both Projects and Asset Fleets.

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

  HelpCircle

} from "lucide-react";

import { useState, useEffect } from "react";

import { useWorkspace } from "@/context/WorkspaceContext";

import { fetchActivities } from "@/lib/api";



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

  HelpCircle

};



interface WorkspaceNavItem {

  label: string;

  icon: string;

  href: string;

  badge?: string;

}



export default function DynamicSidebar() {

  const pathname = usePathname();

  const { user, isSidebarCollapsed } = useWorkspace();

  const [isDark, setIsDark] = useState(false);

  const [flaggedCount, setFlaggedCount] = useState<number | null>(null);

  const [pendingCount, setPendingCount] = useState<number | null>(null);



  useEffect(() => {

    const updateTheme = () => {

      setIsDark(document.documentElement.classList.contains("dark"));

    };

    updateTheme();



    const observer = new MutationObserver(updateTheme);

    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });



    return () => observer.disconnect();

  }, []);



  // Fetch real-time activity counts from the database

  useEffect(() => {

    async function loadRealTimeCounts() {

      try {

        const res = await fetchActivities();

        const activities = Array.isArray(res) ? res : (res?.activities || []);

        if (activities.length > 0) {

          const flagged = activities.filter((a: any) =>

            a.trust_status === "REVIEW" || a.trust_status === "FLAGGED" || (a.trust_score !== undefined && a.trust_score < 80)

          ).length;

          const pending = activities.filter((a: any) =>

            a.verification_status === "PENDING" || a.trust_status === "REVIEW" || a.status === "audit"

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



  const userRole = (user?.role || "ADMIN").toUpperCase();



  // Role-Exclusive Dynamic Navigation Sequences (Consolidated Projects Entry Point)

  const getRoleNavigation = (): WorkspaceNavItem[] => {

    const defaultNav: WorkspaceNavItem[] = [
      { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
      { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
      { label: "Methodology", icon: "Layers", href: "/dashboard/methodologies" },
      {
        label: "Field Operations",
        icon: "Radio",
        href: "/dashboard/operations",
        badge: flaggedCount !== null && flaggedCount > 0 ? `${flaggedCount} Review` : undefined
      },
      { label: "Monitoring", icon: "Activity", href: "/dashboard/monitoring" },
      {
        label: "Verification",
        icon: "ShieldCheck",
        href: "/dashboard/verifications",
        badge: pendingCount !== null && pendingCount > 0 ? `${pendingCount} Audit` : undefined
      },
      { label: "Carbon Credits", icon: "Sliders", href: "/dashboard/carbon" },
      { label: "Compliance", icon: "Globe", href: "/dashboard/command-center" },
      { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai", badge: "Proactive" },
      { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
      { label: "People & Agents", icon: "Users", href: "/dashboard/agents" },
      { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
      { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
    ];

    if (userRole === "AUDITOR" || userRole === "VVB" || userRole === "VERIFIER") {
      return [
        { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
        {
          label: "Verification",
          icon: "ShieldCheck",
          href: "/dashboard/verifications",
          badge: pendingCount !== null && pendingCount > 0 ? `${pendingCount} Audit` : undefined
        },
        { label: "Monitoring", icon: "Activity", href: "/dashboard/monitoring" },
        { label: "Compliance", icon: "Globe", href: "/dashboard/command-center" },
        { label: "Carbon Credits", icon: "Sliders", href: "/dashboard/carbon" },
        { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
        { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai", badge: "Proactive" },
        { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
        { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
      ];
    }

    if (userRole === "FIELD_AGENT") {
      return [
        { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
        {
          label: "Field Operations",
          icon: "Radio",
          href: "/dashboard/operations",
          badge: flaggedCount !== null && flaggedCount > 0 ? `${flaggedCount} Review` : undefined
        },
        { label: "Monitoring", icon: "Activity", href: "/dashboard/monitoring" },
        { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai" },
        { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
        { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
      ];
    }

    if (userRole === "QA_OFFICER") {
      return [
        { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
        {
          label: "Field Operations",
          icon: "Radio",
          href: "/dashboard/operations",
          badge: flaggedCount !== null && flaggedCount > 0 ? `${flaggedCount} Review` : undefined
        },
        { label: "Monitoring", icon: "Activity", href: "/dashboard/monitoring" },
        {
          label: "Verification",
          icon: "ShieldCheck",
          href: "/dashboard/verifications",
          badge: pendingCount !== null && pendingCount > 0 ? `${pendingCount} Audit` : undefined
        },
        { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
        { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai" },
        { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
        { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
      ];
    }

    if (userRole === "REGISTRY_MANAGER" || userRole === "REGISTRY") {
      return [
        { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
        { label: "Carbon Credits", icon: "Sliders", href: "/dashboard/carbon" },
        {
          label: "Verification",
          icon: "ShieldCheck",
          href: "/dashboard/verifications",
          badge: pendingCount !== null && pendingCount > 0 ? `${pendingCount} Audit` : undefined
        },
        { label: "Compliance", icon: "Globe", href: "/dashboard/command-center" },
        { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
        { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai" },
        { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
        { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
      ];
    }

    // Admin-level roles get full navigation
    if (userRole === "ADMIN" || userRole === "ORG_ADMIN" || userRole === "SUPER_ADMIN" || userRole === "PORTFOLIO_MANAGER" || userRole === "IOT_ENGINEER") {
      return defaultNav;
    }

    // Restrictive default for business/unmapped roles
    return [
      { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
      { label: "Projects", icon: "Briefcase", href: "/dashboard/projects" },
      { label: "Monitoring", icon: "Activity", href: "/dashboard/monitoring" },
      { label: "Reports", icon: "FileText", href: "/dashboard/analytics" },
      { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai" },
      { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
      { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
    ];

  };



  const workspaceNav = getRoleNavigation();



  const getIsActive = (href: string) => {

    if (!pathname) return false;

    if (href === "/dashboard") return pathname === "/dashboard";

    return pathname.startsWith(href);

  };



  return (

    <>

      <aside

        className={`hidden md:flex flex-col bg-[var(--color-surface)] border-r border-[var(--color-border)] h-screen sticky top-0 transition-all duration-300 z-50 ${

          isSidebarCollapsed ? "w-20" : "w-64"

        }`}

      >

        {/* Brand Header */}

        <div className="h-14 flex items-center justify-between px-4 border-b border-[var(--color-border)] shrink-0">

          {!isSidebarCollapsed && (

            <div className="flex items-center gap-2">

              <ThemeLogo className="h-6 w-auto object-contain" />

            </div>

          )}

          {isSidebarCollapsed && (

            <div className="w-full flex justify-center">

              <div className="w-7 h-7 rounded-lg bg-[#00B47A]/10 flex items-center justify-center border border-[#00B47A]/20">

                <span className="text-[#00B47A] font-bold text-base leading-none">V</span>

              </div>

            </div>

          )}

        </div>



        {/* STANDARDIZED ENTERPRISE NAVIGATION */}

        <div className="flex-1 overflow-y-auto py-3 px-2.5 custom-scrollbar space-y-1">

          {!isSidebarCollapsed && (

            <div className="px-2 pb-1.5 flex items-center justify-between text-[9px] font-black uppercase tracking-widest text-[var(--color-text-secondary)] opacity-80">

              <span>{userRole.replace("_", " ")} WORKSPACE</span>

              <span className="text-[8px] font-mono text-[#00B47A] bg-emerald-500/10 px-1 py-0.5 rounded border border-emerald-500/20">CIOS L5</span>

            </div>

          )}

          {workspaceNav.map((item, idx) => {

            const Icon = ICON_MAP[item.icon] || LayoutDashboard;

            const active = getIsActive(item.href);

            return (

              <Link

                key={idx}

                href={item.href}

                className={`flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all duration-150 group text-xs ${

                  active

                    ? "bg-[#00B47A]/10 text-[#00B47A] font-bold border border-[#00B47A]/20 dark:bg-[#00B47A]/20 shadow-xs"

                    : "text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] hover:text-[var(--color-text-primary)]"

                }`}

              >

                <Icon size={16} className={`shrink-0 ${active ? "text-[#00B47A]" : "text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)]"}`} />

                {!isSidebarCollapsed && (

                  <div className="flex items-center justify-between w-full min-w-0">

                    <span className="truncate tracking-wide">{item.label}</span>

                    {item.badge && (

                      <span className="text-[8px] font-black px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 font-mono">

                        {item.badge}

                      </span>

                    )}

                  </div>

                )}

              </Link>

            );

          })}

        </div>



        {/* USER PROFILE FOOTER */}

        <div className="p-3 border-t border-[var(--color-border)] shrink-0">

          <div className={`flex items-center ${isSidebarCollapsed ? 'justify-center' : 'gap-2.5'} p-1.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] shadow-xs`}>

            <div className="w-7 h-7 rounded-full border border-emerald-500/20 overflow-hidden bg-emerald-500/10 flex items-center justify-center shrink-0">

              {user?.avatar_url ? (

                <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />

              ) : (

                <span className="text-[10px] font-black text-emerald-400">

                  {user?.full_name ? user.full_name.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2) : "AD"}

                </span>

              )}

            </div>

            {!isSidebarCollapsed && (

              <div className="flex flex-col min-w-0">

                <span className="text-[11px] font-bold text-[var(--color-text-primary)] truncate leading-tight">

                  {user?.full_name || "Admin User"}

                </span>

                <span className="text-[9px] text-[var(--color-text-secondary)] font-semibold uppercase tracking-wider truncate">

                  {user?.role ? user.role.replace("_", " ") : "Org Admin"}

                </span>

              </div>

            )}

          </div>

        </div>

      </aside>

    </>

  );

}
