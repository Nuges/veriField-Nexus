// =============================================================================
// VeriField Nexus — People & Access Workspace Hub
// =============================================================================
// Consolidated IAM directory, role-based access control (RBAC), and field agent
// performance analytics in a single unified workspace.
// =============================================================================

"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Users, ShieldCheck, Loader2 } from "lucide-react";

import AgentsPage from "../agents/page";
import AccessControlClient from "@/components/access-control/AccessControlClient";

function PeopleWorkspaceContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialTab = searchParams.get("tab") || "access";
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam && (tabParam === "access" || tabParam === "agents")) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    router.replace(`/dashboard/people?tab=${tabId}`, { scroll: false });
  };

  const tabs = [
    { id: "access", label: "Team & Access (IAM / RBAC)", icon: ShieldCheck },
    { id: "agents", label: "Field Agent Performance", icon: Users },
  ];

  return (
    <div className="min-h-screen bg-[var(--color-background)] space-y-6 pb-12">
      {/* Workspace Header & Tab Bar */}
      <div className="space-y-4">
        {/* Workspace Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-[var(--color-border)] pb-3 overflow-x-auto custom-scrollbar">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap shadow-xs ${
                  isActive
                    ? "bg-[#008A5E] text-white font-extrabold"
                    : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] border border-[var(--color-border)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                <Icon size={15} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Panels */}
      <div>
        {activeTab === "access" && <AccessControlClient />}
        {activeTab === "agents" && <AgentsPage />}
      </div>
    </div>
  );
}

export default function PeopleWorkspaceHub() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center h-64 space-y-3">
          <Loader2 className="animate-spin text-[#008A5E]" size={32} />
          <p className="text-xs font-semibold text-[var(--color-text-secondary)] animate-pulse">
            Loading People & Access Workspace...
          </p>
        </div>
      }
    >
      <PeopleWorkspaceContent />
    </Suspense>
  );
}

