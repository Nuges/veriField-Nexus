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

import { ChevronRight, Globe, Layers, MapPin, Building, ShieldCheck } from "lucide-react";



export default function EnterpriseBreadcrumb() {

  const pathname = usePathname();

  const { activeSector, activeMethodology, activeProject, allowedSectors, changeSector, changeProject, moduleRegistry } = useWorkspace();

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



  // Standardized Enterprise Operational Labels

  const getStageFromPath = (path: string | null) => {

    if (!path || path === "/dashboard") return "Mission Control";

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

    return "Operations";

  };



  const currentStage = getStageFromPath(pathname);



  return (

    <div className="w-full bg-[var(--color-surface)] border-b border-[var(--color-border)] px-2.5 sm:px-4 py-1.5 sm:py-2 flex items-center justify-between gap-2 sm:gap-4 overflow-x-auto custom-scrollbar text-xs shrink-0 select-none">

      <div className="flex items-center gap-1.5 sm:gap-2 whitespace-nowrap min-w-0 shrink-0">

        {/* 1. Organization Segment (Desktop Only) */}

        <div className="hidden md:flex items-center gap-1.5 font-semibold text-[var(--color-text-primary)] shrink-0">

          <Building size={14} className="text-[#00B47A]" />

          <span>VeriField Org</span>

        </div>



        <ChevronRight size={12} className="hidden md:block text-[var(--color-text-secondary)] opacity-50 shrink-0" />



        {/* 2. Country / Jurisdiction (Tablet/Desktop) */}

        <div className="hidden sm:flex items-center gap-1.5 font-medium text-[var(--color-text-secondary)] shrink-0">

          <Globe size={14} className="text-emerald-500" />

          <span>Nigeria (NG)</span>

        </div>



        <ChevronRight size={12} className="hidden sm:block text-[var(--color-text-secondary)] opacity-50 shrink-0" />



        {/* 3. Sector Context Switcher (Mobile Touch-Friendly) */}

        <div className="relative flex items-center shrink-0">

          <Layers size={14} className="text-[#00B47A] mr-1 shrink-0" />

          <select

            value={activeSector}

            onChange={(e) => changeSector(e.target.value)}

            className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-md px-1.5 py-0.5 text-[11px] sm:text-xs font-bold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A] cursor-pointer max-w-[120px] sm:max-w-none truncate"

          >

            {allowedSectors.map((sec) => (

              <option key={sec} value={sec}>

                {moduleRegistry[sec]?.name || sec.charAt(0).toUpperCase() + sec.slice(1).replace("_", " ")}

              </option>

            ))}

          </select>

        </div>



        <ChevronRight size={12} className="text-[var(--color-text-secondary)] opacity-50 shrink-0" />



        {/* 4. Project Context Switcher (Mobile Truncated) */}

        <div className="relative flex items-center shrink-0">

          <MapPin size={14} className="text-emerald-500 mr-1 shrink-0" />

          <select

            value={activeProject || ""}

            onChange={(e) => changeProject(e.target.value || null)}

            className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-md px-1.5 py-0.5 text-[11px] sm:text-xs font-medium text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A] cursor-pointer max-w-[100px] sm:max-w-[160px] truncate"

          >

            <option value="">-- All Projects --</option>

            {projects.map((proj: any) => (

              <option key={proj.id} value={proj.id}>

                {proj.name}

              </option>

            ))}

          </select>

        </div>



        <ChevronRight size={12} className="text-[var(--color-text-secondary)] opacity-50 shrink-0" />



        {/* 5. Methodology Code */}

        <div className="flex items-center gap-1 font-mono text-[10px] sm:text-[11px] px-1.5 sm:px-2 py-0.5 rounded bg-emerald-500/10 text-[#00B47A] border border-emerald-500/20 font-bold shrink-0">

          <span>{activeMethodology || (activeSector === "hybrid_energy" ? "ACM0002" : activeSector === "biochar" ? "VM0042" : activeSector === "ev_mobility" ? "AMS-III.C" : "AMS-II.G")}</span>

        </div>



        <ChevronRight size={12} className="text-[var(--color-text-secondary)] opacity-50 shrink-0" />



        {/* 6. Operational Stage Badge */}

        <div className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-0.5 rounded-full bg-[#00B47A]/15 text-[#00B47A] font-bold text-[10px] sm:text-[11px] border border-[#00B47A]/30 shrink-0">

          <ShieldCheck size={12} className="shrink-0" />

          <span className="truncate max-w-[90px] sm:max-w-none">{currentStage}</span>

        </div>

      </div>





    </div>

  );

}
