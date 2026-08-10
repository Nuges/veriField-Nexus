// =============================================================================

// VeriField Nexus — Monitoring Workspace Hub

// =============================================================================



"use client";



import React, { useState, Suspense } from "react";

import { useSearchParams, useRouter } from "next/navigation";

import { Activity, ShieldCheck, ShieldAlert, FolderGit2, Loader2 } from "lucide-react";



import TrustScoresPage from "../trust-scores/page";
import AnomaliesPage from "../anomalies/page";
import CommunityPage from "../community/page";
import { TelemetryHistorianConsole } from "@/components/monitoring/TelemetryHistorianConsole";
import { DataQualityEventConsole } from "@/components/monitoring/DataQualityEventConsole";

function MonitoringWorkspaceContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialTab = searchParams.get("tab") || "trust";
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    router.replace(`/dashboard/monitoring?tab=${tabId}`, { scroll: false });
  };

  const tabs = [
    { id: "trust", label: "AI Trust Engine", icon: ShieldCheck },
    { id: "historian", label: "Historical Telemetry (Historian)", icon: Activity },
    { id: "anomalies", label: "Anomaly Centre", icon: ShieldAlert },
    { id: "pipeline", label: "Sync Pipeline & Validations", icon: FolderGit2 },
  ];



  return (

    <div className="min-h-screen bg-[var(--color-background)] space-y-6">

      {/* Workspace Header & Tab Bar */}

      <div className="border-b border-[var(--color-border)] pb-2">

        <div className="flex items-center justify-between mb-4">

          <div>

            <span className="text-[10px] font-black uppercase tracking-widest text-[#00B47A]">

              MONITORING WORKSPACE

            </span>

            <h1 className="text-2xl font-black text-[var(--color-text-primary)]">

              AI Trust Engine & Real-Time Observability

            </h1>

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
      <div className="pt-2 space-y-6">
        {activeTab === "trust" && <TrustScoresPage />}
        {activeTab === "historian" && (
          <div className="space-y-6">
            <TelemetryHistorianConsole />
            <DataQualityEventConsole />
          </div>
        )}
        {activeTab === "anomalies" && <AnomaliesPage />}
        {activeTab === "pipeline" && <CommunityPage />}
      </div>

    </div>

  );

}



export default function MonitoringWorkspaceHub() {

  return (

    <Suspense fallback={

      <div className="flex items-center justify-center h-64">

        <Loader2 className="animate-spin text-emerald-500" size={32} />

      </div>

    }>

      <MonitoringWorkspaceContent />

    </Suspense>

  );

}
