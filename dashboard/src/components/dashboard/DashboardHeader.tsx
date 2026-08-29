"use client";



import React from "react";

import { LayoutGrid, Terminal, Sun, Moon, HelpCircle } from "lucide-react";



interface DashboardHeaderProps {

  userName?: string;

  badge?: string;

  title?: string;

  methodologyName?: string;

  projectName?: string;

  viewMode: "executive" | "operations";

  onViewModeChange: (mode: "executive" | "operations") => void;

}

export default function DashboardHeader({

  viewMode,

  onViewModeChange,

}: DashboardHeaderProps) {

  return (

    <div className="flex items-center justify-between gap-4 mb-4 pb-2 border-b border-[var(--color-border)]">

      {/* Clean Mode Switcher */}

      <div className="flex items-center justify-between w-full">

        <div className="inline-flex items-center bg-slate-100 dark:bg-slate-800/80 p-0.5 rounded-lg border border-[var(--color-border)]">

          <button

            onClick={() => onViewModeChange("executive")}

            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${

              viewMode === "executive"

                ? "bg-white dark:bg-slate-900 text-[var(--color-text-primary)] shadow-xs"

                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"

            }`}

          >

            <LayoutGrid size={13} />

            <span>Executive View</span>

          </button>

          <button

            onClick={() => onViewModeChange("operations")}

            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${

              viewMode === "operations"

                ? "bg-white dark:bg-slate-900 text-[var(--color-text-primary)] shadow-xs"

                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"

            }`}

          >

            <Terminal size={13} />

            <span>Operations Feed</span>

          </button>

        </div>

        <div className="flex items-center gap-2">

          <a

            href="/dashboard/help"

            className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:text-[#008A5E] hover:border-emerald-300 dark:hover:border-emerald-700 transition-colors text-xs font-medium"

            title="Open VeriField Nexus Help & Knowledge Centre"

          >

            <HelpCircle size={14} className="text-[#008A5E]" />

            <span>Help & Guides</span>

          </a>

          <button

            onClick={() => {

              if (document.documentElement.classList.contains("dark")) {

                document.documentElement.classList.remove("dark");

                localStorage.setItem("vf_theme", "light");

              } else {

                document.documentElement.classList.add("dark");

                localStorage.setItem("vf_theme", "dark");

              }

            }}

            className="p-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"

            title="Toggle Light / Dark Theme"

          >

            <Sun size={14} className="dark:hidden" />

            <Moon size={14} className="hidden dark:block" />

          </button>

        </div>

      </div>

    </div>

  );

}
