// =============================================================================

// VeriField Nexus — Enterprise Contextual Header Breadcrumb (CIOS Level 5)

// =============================================================================

// Optimized for mobile & responsive desktop viewports.

// =============================================================================



"use client";

import { useState, useEffect } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchProperties } from "@/lib/api";
import { Property } from "@/lib/types";
import {
  ChevronRight,
  ShieldCheck,
  Search,
} from "lucide-react";
import Link from "next/link";

export default function EnterpriseBreadcrumb() {
  const {
    user,
    activeSector,
    activeProject,
    allowedSectors,
    changeSector,
    changeProject,
    moduleRegistry
  } = useWorkspace();

  const [projects, setProjects] = useState<Property[]>([]);

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

  return (
    <header className="w-full max-w-full bg-[var(--color-surface)] border-b border-[var(--color-border)] px-3 sm:px-4 py-2 flex items-center justify-between gap-2 sm:gap-4 text-xs select-none overflow-x-auto">
      {/* Left: Context Breadcrumb & Sector Selector */}
      <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
        {/* Organization label */}
        <div className="hidden lg:flex items-center gap-1.5 font-semibold text-[var(--color-text-primary)] shrink-0">
          <span className="truncate max-w-[140px]">{user?.organization_id ? "Enterprise Org" : "VeriField Global"}</span>
        </div>

        <ChevronRight size={12} className="hidden lg:block text-[var(--color-text-muted)] shrink-0" />

        {/* Sector Selector */}
        <div className="flex items-center gap-1 bg-[var(--color-background)] border border-[var(--color-border)] rounded-md px-2 py-1 shrink-0">
          <select
            value={activeSector}
            onChange={(e) => changeSector(e.target.value)}
            className="bg-transparent text-[11px] font-semibold text-[var(--color-text-primary)] focus:outline-none cursor-pointer pr-1 max-w-[105px] sm:max-w-none truncate"
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
          <select
            value={activeProject || ""}
            onChange={(e) => changeProject(e.target.value || null)}
            className="bg-transparent text-[11px] font-medium text-[var(--color-text-primary)] focus:outline-none cursor-pointer max-w-[140px] truncate pr-1"
          >
            <option value="">All Projects</option>
            {projects.map((proj: Property) => (
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
          <span>Search assets or telemetry...</span>
          <kbd className="text-[9px] font-mono font-semibold bg-white dark:bg-slate-900 border border-[var(--color-border)] px-1 py-0.2 rounded text-[var(--color-text-muted)]">⌘K</kbd>
        </Link>

        {/* Audit Queue Link (Neutral styling) */}
        <Link
          href="/dashboard/verifications"
          title="Audit Queue"
          aria-label="Audit Queue"
          className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] bg-[var(--color-background)] hover:bg-slate-100 dark:hover:bg-slate-800 border border-[var(--color-border)] px-2.5 py-1 rounded-md transition-colors shrink-0"
        >
          <ShieldCheck size={13} className="text-[var(--color-text-muted)]" />
          <span className="hidden sm:inline">Audit Queue</span>
        </Link>
      </div>
    </header>
  );
}
