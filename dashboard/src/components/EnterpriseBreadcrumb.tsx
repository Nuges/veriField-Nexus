// =============================================================================

// VeriField Nexus — Enterprise Contextual Header Breadcrumb (CIOS Level 5)

// =============================================================================

// Optimized for mobile & responsive desktop viewports.

// =============================================================================



"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchProperties } from "@/lib/api";
import {
  ChevronRight,
  Globe,
  Layers,
  MapPin,
  Building,
  ShieldCheck,
  Search,
  Bell,
  HelpCircle,
  CheckCircle2
} from "lucide-react";
import Link from "next/link";

export default function EnterpriseBreadcrumb() {
  const pathname = usePathname();
  const {
    user,
    activeSector,
    activeMethodology,
    activeProject,
    allowedSectors,
    changeSector,
    changeProject,
    moduleRegistry
  } = useWorkspace();

  const [projects, setProjects] = useState<any[]>([]);

  useEffect(() => {
    async function loadProjects() {
      try {
        const res = await fetchProperties();
        if (res && res.properties) {
          setProjects(res.properties);
        }
      } catch (err) {
        console.error("Failed to load projects for breadcrumb context", err);
      }
    }
    loadProjects();
  }, []);

  const getStageFromPath = (path: string | null) => {
    if (!path || path === "/dashboard") return "Mission Control";
    if (path.startsWith("/dashboard/poa")) return "Programmes (PoA)";
    if (path.startsWith("/dashboard/portfolio")) return "PoA & Portfolio";
    if (path.startsWith("/dashboard/projects")) return "Projects";
    if (path.startsWith("/dashboard/methodologies")) return "Methodology";
    if (path.startsWith("/dashboard/assets")) return "Assets";
    if (path.startsWith("/dashboard/operations")) return "Field Operations";
    if (path.startsWith("/dashboard/monitoring")) return "Monitoring";
    if (path.startsWith("/dashboard/verifications")) return "Verification";
    if (path.startsWith("/dashboard/carbon")) return "Carbon Credits";
    if (path.startsWith("/dashboard/command-center")) return "Compliance";
    if (path.startsWith("/dashboard/ai")) return "AI Assistant";
    if (path.startsWith("/dashboard/analytics")) return "Reports";
    if (path.startsWith("/dashboard/settings")) return "Settings";
    if (path.startsWith("/dashboard/people")) return "People & Access";
    if (path.startsWith("/dashboard/access-control")) return "People & Access";
    if (path.startsWith("/dashboard/agents")) return "People & Access";
    return "Operations";
  };

  const currentStage = getStageFromPath(pathname);

  return (
    <header className="w-full bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-2 flex items-center justify-between gap-4 text-xs shrink-0 select-none">
      {/* Left: Context Breadcrumb & Sector Selector */}
      <div className="flex items-center gap-2 min-w-0">
        {/* Organization label */}
        <div className="hidden lg:flex items-center gap-1.5 font-semibold text-[var(--color-text-primary)] shrink-0">
          <Building size={14} className="text-[#008A5E]" />
          <span className="truncate max-w-[140px]">{user?.organization_id ? "Enterprise Org" : "VeriField Global"}</span>
        </div>

        <ChevronRight size={12} className="hidden lg:block text-[var(--color-text-muted)] shrink-0" />

        {/* Sector Selector */}
        <div className="flex items-center gap-1 bg-[var(--color-background)] border border-[var(--color-border)] rounded-md px-2 py-1 shrink-0">
          <Layers size={13} className="text-[#008A5E] shrink-0" />
          <select
            value={activeSector}
            onChange={(e) => changeSector(e.target.value)}
            className="bg-transparent text-[11px] font-semibold text-[var(--color-text-primary)] focus:outline-none cursor-pointer pr-1"
          >
            {allowedSectors.map((sec) => (
              <option key={sec} value={sec}>
                {moduleRegistry[sec]?.name || sec.charAt(0).toUpperCase() + sec.slice(1).replace("_", " ")}
              </option>
            ))}
          </select>
        </div>

        {/* Project Selector (Desktop) */}
        <div className="hidden sm:flex items-center gap-1 bg-[var(--color-background)] border border-[var(--color-border)] rounded-md px-2 py-1 shrink-0">
          <MapPin size={13} className="text-[#008A5E] shrink-0" />
          <select
            value={activeProject || ""}
            onChange={(e) => changeProject(e.target.value || null)}
            className="bg-transparent text-[11px] font-medium text-[var(--color-text-primary)] focus:outline-none cursor-pointer max-w-[140px] truncate pr-1"
          >
            <option value="">All Projects</option>
            {projects.map((proj: any) => (
              <option key={proj.id} value={proj.id}>
                {proj.name}
              </option>
            ))}
          </select>
        </div>

        <ChevronRight size={12} className="hidden md:block text-[var(--color-text-muted)] shrink-0" />

        {/* Operational Stage Badge */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-[#008A5E] dark:text-emerald-400 font-semibold text-[11px] border border-emerald-200 dark:border-emerald-800 shrink-0">
          <CheckCircle2 size={12} className="shrink-0 text-[#008A5E]" />
          <span>{currentStage}</span>
        </div>
      </div>

      {/* Right: Search bar & Quick Utilities */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Search Input Button */}
        <Link
          href="/dashboard/projects"
          className="hidden md:flex items-center gap-2 bg-[var(--color-background)] hover:bg-slate-100 dark:hover:bg-slate-800 border border-[var(--color-border)] rounded-md px-2.5 py-1 text-[11px] text-[var(--color-text-secondary)] transition-colors"
        >
          <Search size={13} />
          <span>Search assets or telemetry...</span>
          <kbd className="text-[9px] font-mono font-semibold bg-white dark:bg-slate-900 border border-[var(--color-border)] px-1 py-0.2 rounded text-[var(--color-text-muted)]">⌘K</kbd>
        </Link>

        {/* Quick Links */}
        <Link
          href="/dashboard/help"
          title="Help & Guides"
          className="p-1.5 rounded-md text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <HelpCircle size={15} />
        </Link>

        <Link
          href="/dashboard/verifications"
          title="Audit Queue"
          className="flex items-center gap-1 text-[11px] font-semibold text-[#008A5E] bg-emerald-50 dark:bg-emerald-950/40 hover:bg-emerald-100 border border-emerald-200 dark:border-emerald-800 px-2 py-1 rounded-md transition-colors"
        >
          <ShieldCheck size={13} />
          <span className="hidden sm:inline">Audit Queue</span>
        </Link>
      </div>
    </header>
  );
}
