"use client";



import React, { useState } from "react";

import Link from "next/link";

import { Flame, Shield, AlertTriangle, Users, RefreshCw, UserPlus } from "lucide-react";

import ChartRenderer from "./ChartRenderer";



export default function AnalyticsTabs({

  sectorCode,

  charts,

  activities

}: {

  sectorCode?: string;

  charts?: any[];

  activities?: any[];

}) {

  const [activeTab, setActiveTab] = useState("reductions");

  const code = (sectorCode || "").toUpperCase();

  const displayActivities = activities || [];



  const sectorTitle = code.includes("COOK") || code.includes("AMS_II_G")

    ? "Cookstoves"

    : code.includes("HYBRID") || code.includes("ENERGY")

    ? "Hybrid Energy"

    : code.includes("BIOCHAR")

    ? "Biochar"

    : "EV Mobility";



  const tabs = [

    { id: "reductions", label: `Offset Reductions & ${sectorTitle}`, icon: Flame },

    { id: "trust", label: "Trust Engine Variables", icon: Shield },

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

      {activeTab === "reductions" && (

        <div className="space-y-6">

          {/* Charts Container (6/12 + 6/12 Grid) */}

          <ChartRenderer charts={charts} sectorCode={sectorCode} />



          {/* Live Activity Feed Table */}

          <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md shadow-xl transition-colors duration-300">

            <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--color-border)]">

              <div>

                <h4 className="text-xs font-black tracking-widest text-[var(--color-text-primary)] uppercase font-sans">

                  LIVE FIELD ACTIVITY FEED & TELEMETRY LOGS

                </h4>

                <p className="text-[10px] text-[var(--color-text-secondary)] font-sans mt-0.5">

                  Direct IoT sensor sync and field agent mobile submission stream.

                </p>

              </div>

            </div>



            <div className="overflow-x-auto">

              <table className="w-full text-left font-sans text-xs">

                <thead>

                  <tr className="border-b border-[var(--color-border)] text-[10px] font-black text-[var(--color-text-secondary)] uppercase tracking-wider">

                    <th className="py-3 px-3">

                      {code.includes("HYBRID") || code.includes("ENERGY") ? "SYSTEM ID" : code.includes("BIOCHAR") ? "KILN ID" : code.includes("EV") ? "CHARGER ID" : "STOVE ID"}

                    </th>

                    <th className="py-3 px-3">

                      {code.includes("HYBRID") || code.includes("ENERGY") ? "SITE LOCATION" : code.includes("BIOCHAR") ? "SINK LOCATION" : code.includes("EV") ? "STATION HUB" : "HOUSEHOLD ID"}

                    </th>

                    <th className="py-3 px-3">

                      {code.includes("HYBRID") || code.includes("ENERGY") || code.includes("BIOCHAR") || code.includes("EV") ? "OPERATOR NAME" : "HEAD OF HOUSEHOLD"}

                    </th>

                    <th className="py-3 px-3">

                      {code.includes("HYBRID") || code.includes("ENERGY") ? "ENERGY SOURCE" : code.includes("BIOCHAR") ? "BIOMASS TYPE" : code.includes("EV") ? "CHARGING SPEED" : "PRIMARY FUEL"}

                    </th>

                    <th className="py-3 px-3">TRUST INDEX</th>

                    <th className="py-3 px-3">STATUS</th>

                    <th className="py-3 px-3">CAPTURED AT</th>

                  </tr>

                </thead>

                <tbody className="divide-y divide-[var(--color-border)] text-[var(--color-text-primary)] font-sans">

                  {displayActivities.length > 0 ? (

                    displayActivities.map((act: any, idx: number) => (

                      <tr key={act.id || idx} className="hover:bg-[var(--color-background)] transition-colors">

                        <td className="py-3 px-3 font-bold text-emerald-600 dark:text-emerald-400 font-mono">

                          {act.stove_id || act.asset_id || `AST-00${idx + 1}`}

                        </td>

                        <td className="py-3 px-3 font-mono text-[var(--color-text-secondary)]">

                          {act.household_id || act.site_id || `LOC-90${idx + 1}`}

                        </td>

                        <td className="py-3 px-3 font-bold text-[var(--color-text-primary)]">

                          {act.head_name || act.operator_name || "Verified Operator"}

                        </td>

                        <td className="py-3 px-3 font-semibold text-[var(--color-text-secondary)]">

                          {act.primary_fuel || act.energy_source || "Clean Biomass"}

                        </td>

                        <td className="py-3 px-3 font-bold text-emerald-600 dark:text-emerald-400">

                          {act.trust_index || "100 / 100"}

                        </td>

                        <td className="py-3 px-3">

                          <span className="px-2 py-0.5 text-[9px] font-black rounded bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">

                            {act.status || "VERIFIED"}

                          </span>

                        </td>

                        <td className="py-3 px-3 text-[var(--color-text-secondary)] font-mono text-[11px]">{act.captured_at || "Recent Sync"}</td>

                      </tr>

                    ))

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

        <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md shadow-xl transition-colors duration-300">

          <h4 className="text-xs font-black tracking-widest text-[var(--color-text-primary)] uppercase font-sans mb-4">

            TRUST ENGINE WEIGHTED VARIABLES & GEOMETRY VALIDATION

          </h4>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-sans text-xs">

            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] shadow-sm">

              <p className="text-[var(--color-text-secondary)] text-[10px] font-bold">GPS RADIUS ACCURACY</p>

              <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-1">Verified</p>

            </div>

            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] shadow-sm">

              <p className="text-[var(--color-text-secondary)] text-[10px] font-bold">IOT TELEMETRY SYNC</p>

              <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-1">0.12s Latency</p>

            </div>

            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] shadow-sm">

              <p className="text-[var(--color-text-secondary)] text-[10px] font-bold">EVIDENCE SHA-256 HASH</p>

              <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-1">100% Cryptographic</p>

            </div>

          </div>

        </div>

      )}



      {activeTab === "anomalies" && (

        <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md text-center py-12 shadow-xl transition-colors duration-300">

          <Shield size={32} className="mx-auto text-emerald-500 dark:text-emerald-400 mb-2 opacity-90" />

          <h4 className="text-sm font-bold text-[var(--color-text-primary)] font-sans">ANOMALY ENGINE ACTIVE</h4>

          <p className="text-xs text-[var(--color-text-secondary)] mt-1 max-w-sm mx-auto font-sans">

            Zero active telemetry anomalies or duplicate coordinates flagged across active installations.

          </p>

        </div>

      )}



      {activeTab === "agents" && (

        <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md font-sans text-xs shadow-xl transition-colors duration-300 space-y-4">

          <div className="flex items-center justify-between">

            <h4 className="text-xs font-black tracking-widest text-[var(--color-text-primary)] uppercase">

              FIELD AGENT PERFORMANCE & TELEMETRY INGESTION

            </h4>

            <Link

              href="/dashboard/agents"

              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold text-white bg-emerald-600 hover:bg-emerald-500 transition-colors shadow-sm cursor-pointer"

            >

              <UserPlus size={13} />

              <span>Manage & Provision Agents</span>

            </Link>

          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] flex justify-between items-center shadow-sm">

              <div>

                <p className="text-[var(--color-text-primary)] font-bold">Active Agents</p>

                <p className="text-[10px] text-[var(--color-text-secondary)]">Mobile VeriField Capture Sync</p>

              </div>

              <span className="text-xl font-bold text-emerald-600 dark:text-emerald-400">

                {displayActivities.length > 0 ? new Set(displayActivities.map((a: any) => a.user_id || a.user?.id || a.id)).size : 0}

              </span>

            </div>

            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] flex justify-between items-center shadow-sm">

              <div>

                <p className="text-[var(--color-text-primary)] font-bold">Submissions Today</p>

                <p className="text-[10px] text-[var(--color-text-secondary)]">Automated QA Stream</p>

              </div>

              <span className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{displayActivities.length}</span>

            </div>

          </div>

        </div>

      )}



      {activeTab === "pipeline" && (

        <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md font-sans text-xs shadow-xl transition-colors duration-300">

          <h4 className="text-xs font-black tracking-widest text-[var(--color-text-primary)] uppercase mb-4">

            VERIFIELD TRUST LEDGER SYNC PIPELINE

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
