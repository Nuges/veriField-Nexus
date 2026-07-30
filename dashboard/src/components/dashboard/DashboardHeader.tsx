"use client";



import React from "react";

import { LayoutGrid, Terminal, Sun, Moon } from "lucide-react";



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

      {/* Clean Mode Switcher & Theme Controls */}

      <div className="flex items-center justify-between w-full">

        <div className="flex items-center bg-[var(--color-surface)] p-1 rounded-xl border border-[var(--color-border)] shadow-xs">

          <button

            onClick={() => onViewModeChange("executive")}

            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${

              viewMode === "executive"

                ? "bg-[#00B47A] text-slate-950 shadow-xs font-extrabold"

                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"

            }`}

          >

            <LayoutGrid size={14} />

            <span>Executive View</span>

          </button>



          <button

            onClick={() => onViewModeChange("operations")}

            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${

              viewMode === "operations"

                ? "bg-[#00B47A] text-slate-950 shadow-xs font-extrabold"

                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"

            }`}

          >

            <Terminal size={14} />

            <span>Operations View</span>

          </button>

        </div>



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

          className="p-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all shadow-xs cursor-pointer"

          title="Toggle Day (Light) / Night (Dark Obsidian) Theme"

        >

          <Sun size={15} className="block dark:hidden text-amber-500" />

          <Moon size={15} className="hidden dark:block text-emerald-400" />

        </button>

      </div>

    </div>

  );

}
