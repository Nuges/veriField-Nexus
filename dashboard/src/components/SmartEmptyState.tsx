// =============================================================================

// VeriField Nexus — Smart AI Empty State Component (CIOS Level 5)

// =============================================================================

// Replaces blank states with intelligent AI guidance and one-click actions.

// =============================================================================



"use client";



import React from "react";

import { Sparkles, ArrowRight, Bot, RefreshCw } from "lucide-react";

import Link from "next/link";



interface SmartEmptyStateProps {

  title: string;

  description: string;

  aiInsight?: string;

  primaryActionLabel: string;

  primaryActionHref: string;

  secondaryActionLabel?: string;

  onSecondaryAction?: () => void;

}



export default function SmartEmptyState({

  title,

  description,

  aiInsight,

  primaryActionLabel,

  primaryActionHref,

  secondaryActionLabel,

  onSecondaryAction

}: SmartEmptyStateProps) {

  return (

    <div className="p-8 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] text-center space-y-4 shadow-sm my-4 animate-fade-in">

      <div className="w-12 h-12 rounded-2xl bg-[#00B47A]/15 border border-[#00B47A]/30 flex items-center justify-center text-[#00B47A] mx-auto">

        <Sparkles size={24} className="animate-pulse" />

      </div>



      <div className="max-w-md mx-auto space-y-1">

        <h3 className="text-base font-extrabold text-[var(--color-text-primary)]">{title}</h3>

        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{description}</p>

      </div>



        <div className="max-w-lg mx-auto p-3 rounded-xl bg-gradient-to-r from-emerald-500/10 via-[#00B47A]/5 to-transparent border border-[#00B47A]/20 text-xs text-left flex items-start gap-2">

          <Sparkles size={16} className="text-[#00B47A] shrink-0 mt-0.5" />

          <p className="text-[var(--color-text-primary)] font-medium leading-relaxed">

            <strong className="text-[#00B47A]">System Recommendation:</strong> {aiInsight}

          </p>

        </div>



      <div className="flex flex-wrap items-center justify-center gap-3 pt-2">

        {secondaryActionLabel && onSecondaryAction && (

          <button

            onClick={onSecondaryAction}

            className="px-4 py-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] hover:bg-[var(--color-surface)] transition-all cursor-pointer flex items-center gap-1.5"

          >

            <RefreshCw size={14} className="text-[#00B47A]" />

            <span>{secondaryActionLabel}</span>

          </button>

        )}



        <Link

          href={primaryActionHref}

          className="px-5 py-2 rounded-xl bg-[#00B47A] text-slate-950 font-extrabold text-xs hover:bg-[#009b68] transition-all flex items-center gap-1.5 shadow-md"

        >

          <span>{primaryActionLabel}</span>

          <ArrowRight size={14} />

        </Link>

      </div>

    </div>

  );

}
