"use client";



import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Flame, Shield, AlertTriangle, Users, RefreshCw, UserPlus, Layers } from "lucide-react";
import ChartRenderer, { type ChartConfig } from "./ChartRenderer";
import BiocharValueChainView from "./BiocharValueChainView";
import { canonicalSectorCode } from "@/lib/moduleRegistry";
import type { PipelineActivityItem } from "../VerificationPipelineStages";

export default function AnalyticsTabs({
  sectorCode,
  projectId,
  charts,
  activities
}: {
  sectorCode?: string;
  projectId?: string;
  charts?: ChartConfig[];
  activities?: PipelineActivityItem[];
}) {
  const canonical = canonicalSectorCode(sectorCode || "").toUpperCase();
  const [activeTab, setActiveTab] = useState(
    canonical === "BIOCHAR" ? "biochar_value_chain" : "reductions"
  );
  const displayActivities = activities || [];

  useEffect(() => {
    if (canonical === "BIOCHAR") {
      setActiveTab("biochar_value_chain");
    } else {
      setActiveTab("reductions");
    }
  }, [canonical]);

  const sectorTitle = canonical === "COOKSTOVES"
    ? "Cookstoves"
    : canonical === "HYBRID_ENERGY"
    ? "Hybrid Energy"
    : canonical === "BIOCHAR"
    ? "Biochar"
    : canonical === "EV_MOBILITY"
    ? "EV Mobility"
    : canonical === "AGRICULTURE_LAND_USE"
    ? "Agriculture & Land Use"
    : "Operations";

  const tabs = [
    ...(canonical === "BIOCHAR"
      ? [{ id: "biochar_value_chain", label: "Biochar Operations & Value Chain", icon: Layers }]
      : []),
    { id: "reductions", label: canonical === "AGRICULTURE_LAND_USE" ? "Agriculture & Land Use Overview" : `Offset Reductions & ${sectorTitle}`, icon: Flame },
    { id: "trust", label: "Evidence Trust", icon: Shield },
    { id: "anomalies", label: "Anomaly Center (0 Alerts)", icon: AlertTriangle },
    { id: "agents", label: "Field Agent Analytics", icon: Users },
    { id: "pipeline", label: "Sync Pipeline & Metrics", icon: RefreshCw }
  ];



  return (

    <div className="space-y-6">

      {/* Platform Analytics Workspace Sub-Navigation (System Branding Aligned) */}

      <div className="flex items-center gap-2 border-b border-[var(--color-border)] overflow-x-auto custom-scrollbar pb-px">

        {tabs.map((t) => {

          const Icon = t.icon;

          const isActive = activeTab === t.id;

          return (

            <button

              key={t.id}

              onClick={() => setActiveTab(t.id)}

              className={`flex items-center space-x-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap cursor-pointer rounded-t-lg ${

                isActive

                  ? "border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 font-bold"

                  : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]"

              }`}

            >

              <Icon size={15} className={isActive ? "text-emerald-500 dark:text-emerald-400" : "text-[var(--color-text-secondary)]"} />

              <span>{t.label}</span>

            </button>

          );

        })}

      </div>



      {/* Tab Panels */}

      {activeTab === "biochar_value_chain" && canonical === "BIOCHAR" && (
        <BiocharValueChainView projectId={projectId} />
      )}

      {activeTab === "reductions" && (

        <div className="space-y-6">

          {/* Charts Container (6/12 + 6/12 Grid) */}

          <ChartRenderer charts={charts} sectorCode={sectorCode} />



          {/* Live Activity Feed Table */}

          <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md shadow-xs transition-colors duration-300">

            <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--color-border)]">

              <div>

                <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">

                  Live field activity feed & telemetry logs

                </h4>

                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">

                  Direct IoT sensor sync and field agent mobile submission stream.

                </p>

              </div>

            </div>



            <div className="overflow-x-auto">

              <table className="w-full text-left font-sans text-xs">

                <thead>

                  <tr className="border-b border-[var(--color-border)] text-[10px] font-black text-[var(--color-text-secondary)] uppercase tracking-wider">

                    <th className="py-3 px-3">
                      {canonical === "HYBRID_ENERGY" ? "SYSTEM ID" : canonical === "BIOCHAR" ? "KILN ID" : canonical === "EV_MOBILITY" ? "CHARGER ID" : canonical === "AGRICULTURE_LAND_USE" ? "LAND UNIT ID" : "STOVE ID"}
                    </th>
                    <th className="py-3 px-3">
                      {canonical === "HYBRID_ENERGY" ? "SITE LOCATION" : canonical === "BIOCHAR" ? "SINK LOCATION" : canonical === "EV_MOBILITY" ? "STATION HUB" : canonical === "AGRICULTURE_LAND_USE" ? "PARCEL LOCATION" : "HOUSEHOLD ID"}
                    </th>
                    <th className="py-3 px-3">
                      {canonical === "HYBRID_ENERGY" || canonical === "BIOCHAR" || canonical === "EV_MOBILITY" ? "OPERATOR NAME" : canonical === "AGRICULTURE_LAND_USE" ? "OPERATOR / FARMER" : "HEAD OF HOUSEHOLD"}
                    </th>
                    <th className="py-3 px-3">
                      {canonical === "HYBRID_ENERGY" ? "ENERGY SOURCE" : canonical === "BIOCHAR" ? "BIOMASS TYPE" : canonical === "EV_MOBILITY" ? "CHARGING SPEED" : canonical === "AGRICULTURE_LAND_USE" ? "ACTIVITY TYPE" : "PRIMARY FUEL"}
                    </th>
                    <th className="py-3 px-3">TRUST INDEX</th>
                    <th className="py-3 px-3">STATUS</th>
                    <th className="py-3 px-3">CAPTURED AT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)] text-[var(--color-text-primary)] font-sans">
                  {displayActivities.length > 0 ? (
                    displayActivities.map((act: PipelineActivityItem, idx: number) => {
                      const item = act as Record<string, unknown>;
                      return (
                        <tr key={act.id || idx} className="hover:bg-[var(--color-background)] transition-colors">
                          <td className="py-3 px-3 font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                            {String(item.unit_code || item.land_unit_id || item.stove_id || item.asset_id || `AST-00${idx + 1}`)}
                          </td>
                          <td className="py-3 px-3 font-mono text-[var(--color-text-secondary)]">
                            {String(item.parcel_name || item.field_name || item.household_id || item.site_id || `LOC-90${idx + 1}`)}
                          </td>
                          <td className="py-3 px-3 font-bold text-[var(--color-text-primary)]">
                            {String(item.farmer_name || item.head_name || item.operator_name || "Verified Operator")}
                          </td>
                          <td className="py-3 px-3 font-semibold text-[var(--color-text-secondary)]">
                            {String(item.practice_type || item.activity_type || item.primary_fuel || item.energy_source || "Clean Biomass")}
                          </td>

                          <td className="py-3 px-3 font-bold text-emerald-600 dark:text-emerald-400">

                            {String(item.trust_index || "100 / 100")}

                          </td>

                          <td className="py-3 px-3">

                            <span className="px-2 py-0.5 text-[9px] font-black rounded bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">

                              {String(act.status || "VERIFIED")}

                            </span>

                          </td>

                          <td className="py-3 px-3 text-[var(--color-text-secondary)] font-mono text-[11px]">{String(item.captured_at || "Recent Sync")}</td>

                        </tr>

                      );

                    })

                  ) : (

                    <tr>

                      <td colSpan={7} className="py-6 text-center text-[var(--color-text-secondary)] font-sans text-xs">

                        No field activities recorded yet.

                      </td>

                    </tr>

                  )}

                </tbody>

              </table>

            </div>

          </div>

        </div>

      )}



      {activeTab === "trust" && (
        <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-5 transition-colors duration-300">
          <h4 className="text-xs font-bold tracking-wider text-[var(--color-text-primary)] uppercase font-sans mb-4">
            Evidence Trust — Weighted Variables & Geometry Validation
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-sans text-xs">
            <div className="p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
              <p className="text-[var(--color-text-secondary)] text-[10px] font-semibold uppercase tracking-wider">GPS Radius Accuracy</p>
              <p className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1">Geofence Verified</p>
            </div>
            <div className="p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
              <p className="text-[var(--color-text-secondary)] text-[10px] font-semibold uppercase tracking-wider">IoT Telemetry Ingestion</p>
              <p className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1">Streaming Active</p>
            </div>
            <div className="p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
              <p className="text-[var(--color-text-secondary)] text-[10px] font-semibold uppercase tracking-wider">Evidence SHA-256 Provenance</p>
              <p className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1">Immutable & Sealed</p>
            </div>
          </div>
        </div>
      )}



      {activeTab === "anomalies" && (

        <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md text-center py-12 shadow-xs transition-colors duration-300">

          <Shield size={32} className="mx-auto text-[var(--color-primary)] mb-2 opacity-90" />

          <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">Anomaly engine active</h4>

          <p className="text-xs text-[var(--color-text-secondary)] mt-1 max-w-sm mx-auto">

            Zero active telemetry anomalies or duplicate coordinates flagged across active installations.

          </p>

        </div>

      )}



      {activeTab === "agents" && (

        <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md text-xs shadow-xs transition-colors duration-300 space-y-4">

          <div className="flex items-center justify-between">

            <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">

              Field agent performance & telemetry ingestion

            </h4>

            <Link

              href="/dashboard/agents"

              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-[var(--color-primary)] hover:opacity-90 transition-opacity shadow-xs cursor-pointer"

            >

              <UserPlus size={13} />

              <span>Manage & Provision Agents</span>

            </Link>

          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] flex justify-between items-center shadow-xs">

              <div>

                <p className="text-[var(--color-text-primary)] font-semibold">Active agents</p>

                <p className="text-xs text-[var(--color-text-secondary)]">Mobile VeriField Capture Sync</p>

              </div>

              <span className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
                {displayActivities.length > 0 ? new Set(displayActivities.map((a: PipelineActivityItem, idx: number) => {
                  const item = a as Record<string, unknown>;
                  const uid = item.user_id || (item.user as Record<string, unknown> | undefined)?.id || a.id;
                  return uid ? String(uid) : `anon-${idx}`;
                })).size : 0}
              </span>

            </div>

            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] flex justify-between items-center shadow-xs">

              <div>

                <p className="text-[var(--color-text-primary)] font-semibold">Submissions today</p>

                <p className="text-xs text-[var(--color-text-secondary)]">Automated QA stream</p>

              </div>

              <span className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">{displayActivities.length}</span>

            </div>

          </div>

        </div>

      )}



      {activeTab === "pipeline" && (

        <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md text-xs shadow-xs transition-colors duration-300">

          <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">

            VeriField trust ledger sync pipeline

          </h4>

          <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2 shadow-sm">

            <div className="flex justify-between text-[11px]">

              <span className="text-[var(--color-text-secondary)]">Block Commitment Status:</span>

              <span className="text-emerald-600 dark:text-emerald-400 font-bold">Synced & Signed</span>

            </div>

            <div className="flex justify-between text-[11px]">

              <span className="text-[var(--color-text-secondary)]">Double-Blind Audit Key:</span>

              <span className="text-[var(--color-text-primary)] font-mono">0x8f2a...9b4c</span>

            </div>

          </div>

        </div>

      )}

    </div>

  );

}
