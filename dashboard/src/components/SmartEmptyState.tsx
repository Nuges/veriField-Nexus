// =============================================================================

// VeriField Nexus — Smart AI Empty State Component (CIOS Level 5)

// =============================================================================

// Replaces blank states with intelligent AI guidance and one-click actions.

// =============================================================================



"use client";



import React from "react";

import { Inbox, ArrowRight, Info } from "lucide-react";

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

    <div className="p-8 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-center space-y-4 my-4">

      <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 border border-[var(--color-border)] flex items-center justify-center text-[var(--color-text-secondary)] mx-auto">

        <Inbox size={20} />

      </div>



      <div className="max-w-md mx-auto space-y-1">

        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>

        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{description}</p>

      </div>



      {aiInsight && (

        <div className="max-w-lg mx-auto p-3 rounded-md bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200/60 dark:border-emerald-800/40 text-xs text-left flex items-start gap-2.5">

          <Info size={15} className="text-[#008A5E] shrink-0 mt-0.5" />

          <p className="text-[var(--color-text-primary)] leading-relaxed">

            <strong className="text-[#008A5E] font-semibold">Guidance: </strong>{aiInsight}

          </p>

        </div>

      )}



      <div className="flex flex-wrap items-center justify-center gap-2.5 pt-1">

        <Link

          href={primaryActionHref}

          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white text-xs font-semibold transition-colors"

        >

          <span>{primaryActionLabel}</span>

          <ArrowRight size={13} />

        </Link>



        {secondaryActionLabel && onSecondaryAction && (

          <button

            onClick={onSecondaryAction}

            className="px-3 py-1.5 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] hover:bg-slate-100 dark:hover:bg-slate-800 text-[var(--color-text-primary)] text-xs font-medium transition-colors"

          >

            {secondaryActionLabel}

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
