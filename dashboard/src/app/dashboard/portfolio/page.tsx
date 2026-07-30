// =============================================================================

// VeriField Nexus — Portfolio Workspace Hub

// =============================================================================



"use client";



import React, { useState, Suspense } from "react";

import { useSearchParams, useRouter } from "next/navigation";

import { Briefcase, Layers, Globe, FileText, BarChart3, Loader2 } from "lucide-react";



import PropertiesPage from "../properties/page";

import POAPortfolioPage from "../poa/page";

import CarbonReportsPage from "../carbon/page";

import RegistryExportPage from "../registry/page";

import AnalyticsPage from "../analytics/page";



function PortfolioWorkspaceContent() {

  const searchParams = useSearchParams();

  const router = useRouter();

  const initialTab = searchParams.get("tab") || "projects";

  const [activeTab, setActiveTab] = useState<string>(initialTab);



  const handleTabChange = (tabId: string) => {

    setActiveTab(tabId);

    router.replace(`/dashboard/portfolio?tab=${tabId}`, { scroll: false });

  };



  const tabs = [

    { id: "projects", label: "Projects & Assets", icon: Layers },

    { id: "poa", label: "Programme of Activities (POA)", icon: Globe },

    { id: "carbon", label: "Carbon Reports", icon: FileText },

    { id: "registry", label: "Registry Exports", icon: Briefcase },

    { id: "analytics", label: "Portfolio Analytics", icon: BarChart3 },

  ];



  return (

    <div className="min-h-screen bg-[var(--color-background)] space-y-6">

      {/* Workspace Header & Tab Bar */}

      <div className="border-b border-[var(--color-border)] pb-2">

        <div className="flex items-center justify-between mb-4">

          <div>

            <span className="text-[10px] font-black uppercase tracking-widest text-[#00B47A]">

              PORTFOLIO WORKSPACE

            </span>

            <h1 className="text-2xl font-black text-[var(--color-text-primary)]">

              Climate Asset & POA Portfolio Management

            </h1>

          </div>

          <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] text-xs font-mono font-bold">

            VERRA & GOLD STANDARD FEDERATED

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

        {activeTab === "projects" && <PropertiesPage />}

        {activeTab === "poa" && <POAPortfolioPage />}

        {activeTab === "carbon" && <CarbonReportsPage />}

        {activeTab === "registry" && <RegistryExportPage />}

        {activeTab === "analytics" && <AnalyticsPage />}

      </div>

    </div>

  );

}



export default function PortfolioWorkspaceHub() {

  return (

    <Suspense fallback={

      <div className="flex items-center justify-center h-64">

        <Loader2 className="animate-spin text-emerald-500" size={32} />

      </div>

    }>

      <PortfolioWorkspaceContent />

    </Suspense>

  );

}
