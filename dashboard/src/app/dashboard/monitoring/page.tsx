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
    { id: "trust", label: "Trust & Integrity", icon: ShieldCheck },
    { id: "historian", label: "Telemetry Historian", icon: Activity },
    { id: "anomalies", label: "Anomaly Exceptions", icon: ShieldAlert },
    { id: "pipeline", label: "Pipeline Validations", icon: FolderGit2 },
  ];

  return (
    <div className="min-h-screen bg-[var(--color-background)] space-y-6">
      {/* Workspace Header & Tab Bar */}
      <div className="border-b border-[var(--color-border)] pb-2">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)]">
              System Health & Telemetry Observability
            </h1>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Real-time sensor telemetry streams, anomaly detections, and pipeline data integrity.
            </p>
          </div>
        </div>

        {/* Workspace Tabs */}
        <div className="flex items-center space-x-1 overflow-x-auto custom-scrollbar border-b border-[var(--color-border)]">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`flex items-center space-x-2 px-3.5 py-2 text-xs font-semibold transition-all cursor-pointer whitespace-nowrap border-b-2 -mb-px ${
                  isActive
                    ? "border-[#008A5E] text-[#008A5E]"
                    : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border)]"
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
