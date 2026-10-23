// =============================================================================

// VeriField Nexus — Enterprise Contextual Header Breadcrumb (CIOS Level 5)

// =============================================================================

// Optimized for mobile & responsive desktop viewports.

// =============================================================================



"use client";

import { useWorkspace } from "@/context/WorkspaceContext";
import {
  ChevronRight,
  ShieldCheck,
  Search,
} from "lucide-react";
import Link from "next/link";
import { getCanonicalSectorLabel } from "@/lib/sectors";
import { isRouteAuthorized } from "@/lib/roles";

export default function EnterpriseBreadcrumb() {
  const {
    user,
    activeSector,
    activeProject,
    allowedSectors,
    changeSector,
    changeProject,
    moduleRegistry,
    projects,
  } = useWorkspace();

  return (
    <header className="w-full max-w-full bg-[var(--color-surface)] border-b border-[var(--color-border)] px-3 sm:px-4 py-2 flex items-center justify-between gap-2 sm:gap-4 text-xs select-none overflow-x-auto">
      {/* Left: Context Breadcrumb & Sector Selector */}
      <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
        {/* Organization label */}
        <div className="hidden lg:flex items-center gap-1.5 font-semibold text-[var(--color-text-primary)] shrink-0">
          <span className="truncate max-w-[140px]">{user?.organization || "VeriField Nexus"}</span>
        </div>

        <ChevronRight size={12} className="hidden lg:block text-[var(--color-text-muted)] shrink-0" />

        {/* Sector Selector */}
        <div className="flex items-center gap-1 bg-[var(--color-background)] border border-[var(--color-border)] rounded-md px-2 py-1 shrink-0">
          <select
            data-testid="sector-selector"
            value={activeSector}
            onChange={(e) => changeSector(e.target.value)}
            className="bg-transparent text-[11px] font-semibold text-[var(--color-text-primary)] focus:outline-none cursor-pointer pr-1 max-w-[105px] sm:max-w-none truncate"
          >
            {allowedSectors.map((sec) => (
              <option key={sec} value={sec}>
                {getCanonicalSectorLabel(sec)}
              </option>
            ))}
          </select>
        </div>

        {/* Project Selector (Desktop) */}
        <div className="hidden sm:flex items-center gap-1 bg-[var(--color-background)] border border-[var(--color-border)] rounded-md px-2 py-1 shrink-0">
          <select
            data-testid="project-selector"
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
      </div>

      {/* Right: Search bar & Quick Utilities */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Search Input Button */}
        <Link
          href="/dashboard/projects"
          className="hidden md:flex items-center gap-2 bg-[var(--color-background)] hover:bg-slate-100 dark:hover:bg-slate-800 border border-[var(--color-border)] rounded-md px-2.5 py-1 text-[11px] text-[var(--color-text-secondary)] transition-colors"
        >
          <Search size={13} />
          <span>Find a project</span>
        </Link>

        {/* Audit Queue Link (Neutral styling) */}
        {isRouteAuthorized("/dashboard/verifications", user?.role) && <Link
          href="/dashboard/verifications"
          title="Verification"
          aria-label="Verification"
          className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] bg-[var(--color-background)] hover:bg-slate-100 dark:hover:bg-slate-800 border border-[var(--color-border)] px-2.5 py-1 rounded-md transition-colors shrink-0"
        >
          <ShieldCheck size={13} className="text-[var(--color-text-muted)]" />
          <span className="hidden sm:inline">Verification</span>
        </Link>}
      </div>
    </header>
  );
}
