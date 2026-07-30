// =============================================================================

// VeriField Nexus — Field Operations Workspace Hub

// =============================================================================



"use client";



import React, { useState, Suspense } from "react";

import { useSearchParams, useRouter } from "next/navigation";

import Link from "next/link";

import { Radio, FileText, ShieldCheck, Activity, Loader2, Globe } from "lucide-react";



import ActivitiesPage from "../activities/page";

import AuditsPage from "../audits/page";

import VerificationsPage from "../verifications/page";

import SensorsPage from "../sensors/page";



function OperationsWorkspaceContent() {

  const searchParams = useSearchParams();

  const router = useRouter();

  const initialTab = searchParams.get("tab") || "activities";

  const [activeTab, setActiveTab] = useState<string>(initialTab);



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

    { id: "telemetry", label: "IoT Telemetry Feeds", icon: Radio },

  ];



  return (

    <div className="min-h-screen bg-[var(--color-background)] space-y-6">

      {/* Workspace Header & Tab Bar */}

      <div className="border-b border-[var(--color-border)] pb-2">

        <div className="flex items-center justify-between mb-4">

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

          <div className="flex items-center gap-3">

            <Link

              href="/dashboard/command-center"

              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-bold hover:border-[#00B47A] transition-all text-[#00B47A]"

            >

              <Globe size={14} />

              <span>Unified Spatial Command Center</span>

            </Link>

            <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] text-xs font-mono font-bold">

              LIVE DISPATCH & CAPTURE STREAM

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

        {activeTab === "evidence" && <AuditsPage />}

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
