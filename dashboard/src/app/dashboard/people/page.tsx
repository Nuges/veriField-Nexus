// =============================================================================

// VeriField Nexus — People Workspace Hub

// =============================================================================



"use client";



import React, { useState, Suspense } from "react";

import { useSearchParams, useRouter } from "next/navigation";

import { Users, UserCheck, Loader2 } from "lucide-react";



import AgentsPage from "../agents/page";

import AccessControlClient from "@/components/access-control/AccessControlClient";



function PeopleWorkspaceContent() {

  const searchParams = useSearchParams();

  const router = useRouter();

  const initialTab = searchParams.get("tab") || "agents";

  const [activeTab, setActiveTab] = useState<string>(initialTab);



  const handleTabChange = (tabId: string) => {

    setActiveTab(tabId);

    router.replace(`/dashboard/people?tab=${tabId}`, { scroll: false });

  };



  const tabs = [

    { id: "agents", label: "Field Agents Management", icon: Users },

    { id: "access", label: "Auditors & Access Control (RBAC)", icon: UserCheck },

  ];



  return (

    <div className="min-h-screen bg-[var(--color-background)] space-y-6">

      {/* Workspace Header & Tab Bar */}

      <div className="border-b border-[var(--color-border)] pb-2">

        <div className="flex items-center justify-between mb-4">

          <div>

            <span className="text-[10px] font-black uppercase tracking-widest text-[#00B47A]">

              PEOPLE WORKSPACE

            </span>

            <h1 className="text-2xl font-black text-[var(--color-text-primary)]">

              Field Operations & Access Governance

            </h1>

          </div>

          <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] text-xs font-mono font-bold">

            IDENTITY & PRIVILEGES PROVISIONED

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

        {activeTab === "agents" && <AgentsPage />}

        {activeTab === "access" && <AccessControlClient />}

      </div>

    </div>

  );

}



export default function PeopleWorkspaceHub() {

  return (

    <Suspense fallback={

      <div className="flex items-center justify-center h-64">

        <Loader2 className="animate-spin text-emerald-500" size={32} />

      </div>

    }>

      <PeopleWorkspaceContent />

    </Suspense>

  );

}
