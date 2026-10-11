// =============================================================================

// VeriField Nexus — Field Operations Workspace Hub

// =============================================================================



"use client";



import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Radio, FileText, ShieldCheck, Activity, Loader2, Globe } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchProperties } from "@/lib/api";

import ActivitiesPage from "../activities/page";
import AuditsListView from "@/components/verification/AuditsListView";
import VerificationsPage from "../verifications/page";
import SensorsPage from "../sensors/page";

function OperationsWorkspaceContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialTab = searchParams.get("tab") || "activities";
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const { activeProject, changeProject } = useWorkspace();
  const [projects, setProjects] = useState<any[]>([]);

  useEffect(() => {
    async function loadProjects() {
      try {
        const res = await fetchProperties();
        if (res && res.properties) {
          setProjects(res.properties);
        }
      } catch (err) {
        console.error("Failed to load projects in operations workspace", err);
      }
    }
    loadProjects();
  }, []);

  const handleTabChange = (tabId: string) => {
    if (tabId === "spatial") {
      router.push("/dashboard/command-center");
      return;
    }
    setActiveTab(tabId);
    router.replace(`/dashboard/operations?tab=${tabId}`, { scroll: false });
  };

  const tabs = [
    { id: "activities", label: "Field Activities", icon: Activity },
    { id: "evidence", label: "Proof Evidence Vault", icon: FileText },
    { id: "verification", label: "Verifications Hub", icon: ShieldCheck },
    { id: "telemetry", label: "Live Telemetry", icon: Radio },
  ];

  return (
    <div className="min-h-screen bg-[var(--color-background)] space-y-6">
      {/* Workspace Header & Tab Bar */}
      <div className="border-b border-[var(--color-border)] pb-2">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div>
              <span className="text-[10px] font-black uppercase tracking-widest text-[#00B47A]">
                OPERATIONAL WORKSPACE
              </span>
              <h1 className="text-2xl font-black text-[var(--color-text-primary)]">
                Field Operations Control Center
              </h1>
            </div>
            <Link
              href="/dashboard/agents"
              className="px-3 py-1.5 rounded-xl bg-[#00B47A] hover:bg-[#009b68] text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5 shrink-0"
            >
              <span>+ Provision Field Agent</span>
            </Link>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Project Selector */}
            <div className="flex items-center gap-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Project:</span>
              <select
                data-testid="operations-project-selector"
                value={activeProject || ""}
                onChange={(e) => changeProject(e.target.value || null)}
                className="bg-transparent text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none cursor-pointer max-w-[180px] truncate pr-1"
              >
                <option value="">All Projects</option>
                {projects.map((proj) => (
                  <option key={proj.id} value={proj.id}>
                    {proj.name}
                  </option>
                ))}
              </select>
            </div>

            <Link
              href="/dashboard/command-center"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-bold hover:border-[#00B47A] transition-all text-[#00B47A]"
            >
              <Globe size={14} />
              <span>Spatial Command</span>
            </Link>

            <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] text-xs font-mono font-bold">
              LIVE DISPATCH STREAM
            </div>
          </div>
        </div>



        {/* Workspace Tabs */}

        <div className="flex items-center space-x-2 overflow-x-auto custom-scrollbar">

          {tabs.map((tab) => {

            const Icon = tab.icon;

            const isActive = activeTab === tab.id;

            return (

              <button

                key={tab.id}

                onClick={() => handleTabChange(tab.id)}

                className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${

                  isActive

                    ? "bg-[#00B47A] text-slate-950 shadow-md font-black"

                    : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] border border-[var(--color-border)] hover:text-[var(--color-text-primary)]"

                }`}

              >

                <Icon size={15} />

                <span>{tab.label}</span>

              </button>

            );

          })}

        </div>

      </div>



      {/* Tab Workspace Panels */}

      <div className="pt-2">

        {activeTab === "activities" && <ActivitiesPage />}

        {activeTab === "evidence" && <AuditsListView />}

        {activeTab === "verification" && <VerificationsPage />}

        {activeTab === "telemetry" && <SensorsPage />}

      </div>

    </div>

  );

}



export default function OperationsWorkspaceHub() {

  return (

    <Suspense fallback={

      <div className="flex items-center justify-center h-64">

        <Loader2 className="animate-spin text-emerald-500" size={32} />

      </div>

    }>

      <OperationsWorkspaceContent />

    </Suspense>

  );

}
