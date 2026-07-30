// =============================================================================

// VeriField Nexus — Enterprise Mission Control Dashboard (CIOS Level 5)

// =============================================================================

"use client";



import React, { useState, useEffect } from "react";

import { useWorkspace } from "@/context/WorkspaceContext";

import { fetchDashboardPayload } from "@/lib/api";

import DashboardHeader from "./DashboardHeader";

import WidgetRenderer from "./WidgetRenderer";

import SpatialModule from "./SpatialModule";

import RegistryModule from "./RegistryModule";

import AnalyticsTabs from "./AnalyticsTabs";

import RoleBasedDashboard from "../RoleBasedDashboard";

import VerificationPipelineStages from "../VerificationPipelineStages";

import { AlertTriangle, Terminal, RefreshCw, Bot, ShieldCheck, ArrowRight, Clock, AlertOctagon } from "lucide-react";

import Link from "next/link";



export default function EnterpriseDashboard() {

  const { activeSector, activeMethodology, activeProject, workspaceError, user, isLoading: isWorkspaceLoading } = useWorkspace();

  const [dashboardData, setDashboardData] = useState<any>(null);

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

      } catch (err: any) {

        setError(err.message || "Failed to load enterprise dashboard.");

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



  const sectorCode = workspace?.code || activeSector || "COOKSTOVES";

  const badgeName = workspace?.badge || `${sectorCode.replace("_", " ")} ENGINE`;

  const titleName = workspace?.name || `${sectorCode.replace("_", " ")} Sector`;



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

          const totalSubmissions = dashboardData?.kpis?.find((k: any) => k.id === "installations" || k.label?.includes("Submissions") || k.label?.includes("Assets") || k.label?.includes("Installations"))?.value ?? 0;

          const hasSubmissions = typeof totalSubmissions === "number" && totalSubmissions > 0;



          return (

            <>

              <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs space-y-2">

                <div className="flex flex-wrap items-center justify-between gap-2">

                  <div className="flex flex-wrap items-center gap-2 min-w-0">

                    <ShieldCheck size={18} className="text-[#00B47A] shrink-0" />

                    <span className="font-bold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">

                      Operational Summary

                    </span>

                  </div>

                </div>

                <p className="text-xs text-[var(--color-text-secondary)] font-medium leading-relaxed">

                  {!hasSubmissions

                    ? `0 field activities submitted for ${project?.name || titleName}. Emission telemetry stream active and awaiting field data capture.`

                    : `Active project carbon yield tracking operational across ${totalSubmissions} verified field submissions.`

                  }

                </p>

              </div>



              {/* 2. ACTION REQUIRED & RISKS & ACTIONS */}

              <div className="grid grid-cols-1 md:grid-cols-12 gap-4">

                {/* Action Required (7 Cols) */}

                <div className="md:col-span-7 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 space-y-3">

                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] pb-2">

                    <div className="flex items-center gap-2">

                      <ShieldCheck size={16} className="text-[#00B47A] shrink-0" />

                      <span className="font-bold text-xs uppercase tracking-wider text-[var(--color-text-primary)]">

                        Action Required

                      </span>

                    </div>

                  </div>



                  <div className="space-y-2 text-xs">

                    {!hasSubmissions ? (

                      <div className="p-4 text-center text-zinc-500 text-xs font-mono rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">

                        No pending actions required.

                      </div>

                    ) : (

                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">

                        <div className="flex items-center gap-2.5">

                          <div className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />

                          <div>

                            <p className="font-bold text-[var(--color-text-primary)]">Execute VVB Independent Audit Sign-off</p>

                            <p className="text-[10px] text-[var(--color-text-secondary)]">Target Stage: Phase 5 (Verification)</p>

                          </div>

                        </div>

                        <Link

                          href="/dashboard/verifications"

                          className="px-3 py-1.5 rounded-lg bg-zinc-900 text-white font-bold text-[11px] hover:bg-black transition-all flex items-center gap-1 shadow-xs shrink-0 self-end sm:self-auto"

                        >

                          <span>Sign Task</span>

                          <ArrowRight size={12} />

                        </Link>

                      </div>

                    )}

                  </div>

                </div>



                {/* Risks & Actions (5 Cols) */}

                <div className="md:col-span-5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 space-y-3">

                  <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">

                    <div className="flex items-center gap-2">

                      <AlertOctagon size={16} className="text-emerald-500 shrink-0" />

                      <span className="font-bold text-xs uppercase tracking-wider text-[var(--color-text-primary)]">

                        Risks & Actions

                      </span>

                    </div>

                  </div>



                  <div className="space-y-2 text-xs">

                    <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] flex items-start gap-2.5">

                      <Clock size={16} className="text-emerald-500 shrink-0 mt-0.5" />

                      <div>

                        <p className="font-bold text-[var(--color-text-primary)]">

                          {!hasSubmissions ? "No SLA Risks Detected" : "SLA Tracking Operational"}

                        </p>

                        <p className="text-[10px] text-[var(--color-text-secondary)] font-mono mt-0.5">

                          {!hasSubmissions ? "All active verification pipelines nominal." : "SLA: Active • Owner: Lead Auditor"}

                        </p>

                      </div>

                    </div>

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
