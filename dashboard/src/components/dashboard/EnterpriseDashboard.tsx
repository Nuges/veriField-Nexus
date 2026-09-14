// =============================================================================

// VeriField Nexus — Enterprise Mission Control Dashboard (CIOS Level 5)

// =============================================================================

"use client";



import React, { useState, useEffect } from "react";

import { useWorkspace } from "@/context/WorkspaceContext";
import { canonicalSectorCode } from "@/lib/moduleRegistry";
import { fetchDashboardPayload } from "@/lib/api";

import DashboardHeader from "./DashboardHeader";

import WidgetRenderer from "./WidgetRenderer";

import SpatialModule from "./SpatialModule";

import RegistryModule from "./RegistryModule";

import AnalyticsTabs from "./AnalyticsTabs";

import RoleBasedDashboard from "../RoleBasedDashboard";

import VerificationPipelineStages, { getVerificationPipelineStage, type PipelineActivityItem } from "../VerificationPipelineStages";

import { AlertTriangle, Terminal, RefreshCw, ShieldCheck, ArrowRight, Clock } from "lucide-react";

import Link from "next/link";



interface DashboardPayload {
  kpis?: Array<{ id: string; label: string; value: string | number; change?: string; trend?: string }>;
  charts?: Array<{ id: string; title: string; type: string; data?: unknown }>;
  activities?: PipelineActivityItem[];
  activity_total?: number;
  asset_total?: number;
  assets?: Array<{ id: string; name?: string; status?: string }>;
  [key: string]: unknown;
}

export default function EnterpriseDashboard() {

  const { activeSector, activeMethodology, activeProject, workspaceError, user, isLoading: isWorkspaceLoading } = useWorkspace();

  const [dashboardData, setDashboardData] = useState<DashboardPayload | null>(null);

  const [isLoading, setIsLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<"executive" | "operations">("executive");



  useEffect(() => {

    async function loadData() {

      if (isWorkspaceLoading) return;



      if (!activeSector || !activeMethodology) {

        setIsLoading(false);

        return;

      }

      setIsLoading(true);

      setError(null);

      try {

        const payload = await fetchDashboardPayload(activeSector, activeMethodology, activeProject || undefined);

        setDashboardData(payload);

      } catch (err) {

        setError(err instanceof Error ? err.message : "Failed to load enterprise dashboard.");

      } finally {

        setIsLoading(false);

      }

    }

    loadData();

  }, [activeSector, activeMethodology, activeProject, isWorkspaceLoading]);



  if (isWorkspaceLoading) {

    return (

      <div className="flex h-[70vh] w-full flex-col items-center justify-center p-6 bg-[var(--color-bg-primary)]">

        <div className="text-center space-y-3">

          <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-[#00B47A] mx-auto animate-spin">

            <RefreshCw size={20} />

          </div>

          <div className="text-sm font-bold text-[var(--color-text-primary)] font-mono">

            Resolving Licensed Workspace & Sector Metrics...

          </div>

        </div>

      </div>

    );

  }



  if (workspaceError) {

    return (

      <div className="flex h-[70vh] w-full flex-col items-center justify-center p-6 bg-[var(--color-bg-primary)]">

        <div className="max-w-md text-center space-y-4">

          <AlertTriangle className="h-12 w-12 mx-auto text-amber-500" />

          <h2 className="text-xl font-medium text-[var(--color-text-primary)]">Configuration Missing</h2>

          <p className="text-[var(--color-text-secondary)]">{workspaceError}</p>

        </div>

      </div>

    );

  }



  if (error) {

    return (

      <div className="flex h-[70vh] w-full flex-col items-center justify-center p-6 bg-[var(--color-bg-primary)]">

        <div className="max-w-md text-center space-y-4">

          <AlertTriangle className="h-12 w-12 mx-auto text-red-500" />

          <h2 className="text-xl font-medium text-[var(--color-text-primary)]">Error Loading Mission Control</h2>

          <p className="text-[var(--color-text-secondary)] text-xs font-mono">{error}</p>

          <div className="pt-2 flex justify-center gap-3">

            <button

              onClick={() => {

                setError(null);

                setIsLoading(true);

                window.location.reload();

              }}

              className="px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors shadow-sm cursor-pointer"

            >

              Reload Page

            </button>

          </div>

        </div>

      </div>

    );

  }



  if (isLoading) {

    return (

      <div className="flex h-[70vh] w-full flex-col items-center justify-center bg-[var(--color-bg-primary)] space-y-3">

        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent" />

        <p className="text-slate-400 text-xs font-bold tracking-widest uppercase font-mono animate-pulse">

          Connecting to VeriField Mission Control Engine...

        </p>

      </div>

    );

  }



  const workspace = dashboardData?.workspace;

  const methodology = dashboardData?.methodology;

  const project = dashboardData?.project;



  const sectorCode = canonicalSectorCode(workspace?.code || activeSector) || "cookstoves";

  const badgeName = workspace?.badge || `${sectorCode.toUpperCase().replace("_", " ")} ENGINE`;

  const titleName = workspace?.name || `${sectorCode.toUpperCase().replace("_", " ")} Sector`;



  return (

    <div className="min-h-screen bg-[var(--color-background)] transition-colors duration-300 pb-12">

      <div className="w-full px-0 py-2 space-y-6">

        {/* Header */}

        <DashboardHeader

          userName={user?.full_name}

          badge={badgeName}

          title={titleName}

          methodologyName={methodology?.name}

          projectName={project?.name}

          viewMode={viewMode}

          onViewModeChange={setViewMode}

        />



        {/* ROLE-BASED EXCLUSIVE MISSION CONTROL DASHBOARD */}

        <RoleBasedDashboard dashboardData={dashboardData} sectorCode={sectorCode} />



        {/* 1. EXECUTIVE SUMMARY SURFACE */}
        {(() => {
          const activitiesList = dashboardData?.activities || [];
          const totalActivities =
            typeof dashboardData?.activity_total === "number"
              ? dashboardData.activity_total
              : activitiesList.length;

          let pendingCount = 0;
          let flaggedCount = 0;
          let manualReviewCount = 0;

          activitiesList.forEach((act: PipelineActivityItem) => {
            const stage = getVerificationPipelineStage(act);
            if (stage === "flagged") flaggedCount++;
            else if (stage === "manual_review") manualReviewCount++;
            else if (stage === "pending") pendingCount++;
          });

          const summarySectorName = project?.name || titleName;
          const summaryCopy =
            totalActivities === 0
              ? `0 field activities submitted for ${summarySectorName}. Awaiting field data capture.`
              : totalActivities === 1
              ? `1 field activity submitted for ${summarySectorName}.`
              : `${totalActivities} field activities submitted for ${summarySectorName}.`;

          return (
            <>
              <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1.5">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={16} className="text-[#008A5E] shrink-0" />
                  <span className="font-semibold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">
                    Operational Status & Summary
                  </span>
                </div>
                <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                  {summaryCopy}
                </p>
              </div>

              {/* 2. ACTION REQUIRED & RISKS & ACTIONS */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                {/* Action Required (7 Cols) */}
                <div className="md:col-span-7 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">
                    <div className="flex items-center gap-2">
                      <ShieldCheck size={15} className="text-[#008A5E] shrink-0" />
                      <span className="font-semibold text-xs uppercase tracking-wider text-[var(--color-text-primary)]">
                        Action Required
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    {flaggedCount > 0 ? (
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-2.5 rounded-md bg-red-500/10 border border-red-500/30">
                        <div className="flex items-center gap-2.5">
                          <div className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
                          <div>
                            <p className="font-semibold text-[var(--color-text-primary)]">
                              {flaggedCount} Flagged {flaggedCount === 1 ? "Activity" : "Activities"} Detected
                            </p>
                            <p className="text-[11px] text-[var(--color-text-secondary)]">
                              Potential telemetry anomaly requires verification investigation.
                            </p>
                          </div>
                        </div>
                        <Link
                          href="/dashboard/anomalies"
                          className="px-3 py-1.5 rounded-md bg-red-600 hover:bg-red-700 text-white font-semibold text-xs transition-colors flex items-center gap-1 shrink-0 self-end sm:self-auto"
                        >
                          <span>Review Anomalies</span>
                          <ArrowRight size={12} />
                        </Link>
                      </div>
                    ) : manualReviewCount > 0 ? (
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-2.5 rounded-md bg-blue-500/10 border border-blue-500/30">
                        <div className="flex items-center gap-2.5">
                          <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                          <div>
                            <p className="font-semibold text-[var(--color-text-primary)]">
                              {manualReviewCount} {manualReviewCount === 1 ? "Activity Requires" : "Activities Require"} Manual Review
                            </p>
                            <p className="text-[11px] text-[var(--color-text-secondary)]">
                              Pending independent VVB auditor evaluation and sign-off.
                            </p>
                          </div>
                        </div>
                        <Link
                          href="/dashboard/verifications"
                          className="px-3 py-1.5 rounded-md bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors flex items-center gap-1 shrink-0 self-end sm:self-auto"
                        >
                          <span>Open Queue</span>
                          <ArrowRight size={12} />
                        </Link>
                      </div>
                    ) : pendingCount > 0 ? (
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-2.5 rounded-md bg-amber-500/10 border border-amber-500/30">
                        <div className="flex items-center gap-2.5">
                          <div className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                          <div>
                            <p className="font-semibold text-[var(--color-text-primary)]">
                              {pendingCount} Field {pendingCount === 1 ? "Activity" : "Activities"} Pending Verification
                            </p>
                            <p className="text-[11px] text-[var(--color-text-secondary)]">
                              Awaiting AI Trust Engine ingestion and audit validation.
                            </p>
                          </div>
                        </div>
                        <Link
                          href="/dashboard/activities"
                          className="px-3 py-1.5 rounded-md bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs transition-colors flex items-center gap-1 shrink-0 self-end sm:self-auto"
                        >
                          <span>View Pipeline</span>
                          <ArrowRight size={12} />
                        </Link>
                      </div>
                    ) : (
                      <div className="p-4 text-center text-[var(--color-text-muted)] text-xs rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
                        No pending actions required.
                      </div>
                    )}
                  </div>
                </div>

                {/* Activity Timeline / Risks (5 Cols) */}
                <div className="md:col-span-5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">
                    <div className="flex items-center gap-2">
                      <Clock size={15} className="text-[#008A5E] shrink-0" />
                      <span className="font-semibold text-xs uppercase tracking-wider text-[var(--color-text-primary)]">
                        Activity Timeline
                      </span>
                    </div>
                  </div>
                  <div className="space-y-2 text-xs">
                    {flaggedCount > 0 ? (
                      <div className="p-2.5 rounded-md bg-red-500/10 border border-red-500/20 text-xs text-red-600 dark:text-red-400 font-medium">
                        {flaggedCount} potential data {flaggedCount === 1 ? "anomaly" : "anomalies"} currently flagged for investigation.
                      </div>
                    ) : totalActivities === 0 ? (
                      <div className="p-4 text-center text-[var(--color-text-muted)] text-xs rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
                        No recent anomalies or risks reported.
                      </div>
                    ) : (
                      <div className="p-2.5 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-secondary)]">
                        All {totalActivities} field {totalActivities === 1 ? "submission" : "submissions"} verified within normal operational bounds.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          );
        })()}



        {/* Operations View Banner (When active) */}

        {viewMode === "operations" && (

          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-sans flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 shadow-sm transition-all duration-300">

            <div className="flex items-center space-x-2.5">

              <div className="p-1.5 rounded-lg bg-zinc-900 text-white shrink-0">

                <Terminal size={16} />

              </div>

              <span className="font-bold uppercase tracking-wider text-[var(--color-text-primary)]">

                HARDWARE & TELEMETRY CONSOLE ACTIVE

              </span>

            </div>

            <div className="flex items-center space-x-2 text-xs text-[var(--color-text-secondary)] font-medium shrink-0">

              <RefreshCw size={14} className="animate-spin text-[#00B47A]" />

              <span>Streaming IoT Telemetry Feeds</span>

            </div>

          </div>

        )}



        {/* VERIFICATION PIPELINE STAGES BAR */}

        <VerificationPipelineStages activities={dashboardData?.activities} />



        {/* KPI Row (4 Cards) */}

        <WidgetRenderer kpis={dashboardData?.kpis} sectorCode={sectorCode} />



        {/* Middle Grid: Spatial Validation (8/12 Cols) & Certified Registry Manifests (4/12 Cols) */}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">

          <div className="lg:col-span-8 flex flex-col">

            <SpatialModule sectorCode={sectorCode} assets={dashboardData?.assets} />

          </div>

          <div className="lg:col-span-4 flex flex-col">

            <RegistryModule sectorCode={sectorCode} />

          </div>

        </div>



        {/* Bottom Platform Analytics Workspace (5 Tabs, Charts & Live Activity Feed) */}

        <AnalyticsTabs sectorCode={sectorCode} charts={dashboardData?.charts} activities={dashboardData?.activities} />

      </div>

    </div>

  );

}
