// =============================================================================

// VeriField Nexus — Verification Pipeline Stages Component

// =============================================================================

// Renders dynamic verification stages (Pending, AI Verified, Flagged, Manual Review, Approved)

// with live percentage and count calculations derived from backend database activities.

// Enables click-to-filter on Field Maps, Anomaly feeds, and audit queues.

// =============================================================================



"use client";



import { useEffect, useState } from "react";

import {
  FilterX
} from "lucide-react";

import { fetchActivities } from "@/lib/api";



export type PipelineStage = "pending" | "ai_verified" | "flagged" | "manual_review" | "approved";



interface VerificationPipelineStagesProps {

  selectedStage?: PipelineStage | null;

  onStageChange?: (stage: PipelineStage | null) => void;

  activities?: any[];

  className?: string;

}



/**

 * Canonical Mutually Exclusive Pipeline State Machine (Front-end & Back-end Contract)

 * Guarantee: Every activity maps to EXACTLY ONE stage.

 * Precedence:

 * 1. APPROVED

 * 2. FLAGGED

 * 3. MANUAL_REVIEW

 * 4. AI_VERIFIED

 * 5. PENDING (Default fallback)

 */

export function getVerificationPipelineStage(a: any): PipelineStage {

  if (a?.pipeline_stage) {

    const ps = String(a.pipeline_stage).toLowerCase();

    if (ps === "approved") return "approved";

    if (ps === "flagged") return "flagged";

    if (ps === "manual_review") return "manual_review";

    if (ps === "ai_verified") return "ai_verified";

    if (ps === "pending") return "pending";

  }



  const st = (a?.status || "").toLowerCase().trim();

  const val_st = (a?.validation_status || "").toUpperCase().trim();

  const trust = typeof a?.trust_score === "number" ? a.trust_score : null;



  if (val_st === "APPROVED" || st === "approved") {

    return "approved";

  }

  if (st === "flagged" || st === "anomaly" || (trust !== null && trust < 70)) {

    return "flagged";

  }

  if (st === "review" || st === "audit" || (trust !== null && trust >= 70 && trust < 80)) {

    return "manual_review";

  }

  if (st === "verified" || (trust !== null && trust >= 80)) {

    return "ai_verified";

  }

  return "pending";

}



export default function VerificationPipelineStages({

  selectedStage: externalSelectedStage,

  onStageChange,

  activities: externalActivities,

  className = "",

}: VerificationPipelineStagesProps) {

  const [internalSelectedStage, setInternalSelectedStage] = useState<PipelineStage | null>(null);

  const [activities, setActivities] = useState<any[]>(externalActivities || []);

  const [isLoading, setIsLoading] = useState(!externalActivities);



  const activeStage = externalSelectedStage !== undefined ? externalSelectedStage : internalSelectedStage;



  useEffect(() => {

    if (externalActivities) {

      setActivities(externalActivities);

      setIsLoading(false);

      return;

    }



    async function loadPipelineMetrics() {

      setIsLoading(true);

      try {

        const res = await fetchActivities({ per_page: 500 });

        const list = Array.isArray(res) ? res : (res?.activities || []);

        setActivities(list);

      } catch (err) {

        console.warn("Pipeline stages fetch notice:", err);

      } finally {

        setIsLoading(false);

      }

    }

    loadPipelineMetrics();

  }, [externalActivities]);



  const total = activities.length;



  // Mutually Exclusive & Exhaustive Stage Count Calculation (Sum == Total)

  const counts: Record<PipelineStage, number> = {

    pending: 0,

    ai_verified: 0,

    flagged: 0,

    manual_review: 0,

    approved: 0,

  };



  activities.forEach(a => {

    const stg = getVerificationPipelineStage(a);

    counts[stg] = (counts[stg] || 0) + 1;

  });



  const getPercentage = (count: number) => {

    if (total === 0) return 0;

    return Math.round((count / total) * 100);

  };



  const handleStageClick = (stage: PipelineStage) => {

    const nextStage = activeStage === stage ? null : stage;

    if (externalSelectedStage === undefined) {

      setInternalSelectedStage(nextStage);

    }

    if (onStageChange) {

      onStageChange(nextStage);

    }

  };



  const stages: Array<{

    id: PipelineStage;

    label: string;
    color: string;
    bgActive: string;
    borderActive: string;
    textColor: string;
    badgeBg: string;
  }> = [
    {
      id: "pending",
      label: "Pending",
      color: "text-amber-500 dark:text-amber-400",
      bgActive: "bg-amber-500/10",
      borderActive: "border-amber-500/40",
      textColor: "text-amber-600 dark:text-amber-400",
      badgeBg: "text-amber-600 dark:text-amber-300",
    },
    {
      id: "ai_verified",
      label: "AI Verified",
      color: "text-emerald-500 dark:text-emerald-400",
      bgActive: "bg-emerald-500/10",
      borderActive: "border-emerald-500/40",
      textColor: "text-[#008A5E] dark:text-emerald-400",
      badgeBg: "text-[#008A5E] dark:text-emerald-300",
    },
    {
      id: "flagged",
      label: "Flagged",
      color: "text-red-500 dark:text-red-400",
      bgActive: "bg-red-500/10",
      borderActive: "border-red-500/40",
      textColor: "text-red-600 dark:text-red-400",
      badgeBg: "text-red-600 dark:text-red-300",
    },
    {
      id: "manual_review",
      label: "Manual Review",
      color: "text-blue-500 dark:text-blue-400",
      bgActive: "bg-blue-500/10",
      borderActive: "border-blue-500/40",
      textColor: "text-blue-600 dark:text-blue-400",
      badgeBg: "text-blue-600 dark:text-blue-300",
    },
    {
      id: "approved",
      label: "Approved",
      color: "text-purple-500 dark:text-purple-400",
      bgActive: "bg-purple-500/10",
      borderActive: "border-purple-500/40",
      textColor: "text-purple-600 dark:text-purple-400",
      badgeBg: "text-purple-600 dark:text-purple-300",
    },
  ];

  return (
    <div className={`p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--color-border)] pb-3">
        <div className="space-y-0.5">
          <h3 className="font-bold text-xs uppercase tracking-wider text-[var(--color-text-primary)]">
            Verification Pipeline Stages
          </h3>
          <p className="text-[11px] text-[var(--color-text-secondary)] font-normal">
            Click stage to filter the Field Map and Anomaly feeds dynamically (Click again to reset)
          </p>
        </div>

        {activeStage && (
          <button
            onClick={() => handleStageClick(activeStage)}
            className="self-start sm:self-auto px-2.5 py-1 rounded-md bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-500 dark:text-red-400 text-[10px] font-semibold uppercase tracking-wider flex items-center gap-1 transition-all cursor-pointer"
          >
            <FilterX size={12} />
            <span>Reset Stage Filter</span>
          </button>
        )}
      </div>

      {/* 5 Stage Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {stages.map((st) => {
          const cnt = counts[st.id];
          const pct = getPercentage(cnt);
          const isSelected = activeStage === st.id;

          return (
            <button
              key={st.id}
              onClick={() => handleStageClick(st.id)}
              className={`p-3 rounded-lg border text-left transition-colors cursor-pointer flex flex-col justify-between space-y-2 relative overflow-hidden ${
                isSelected
                  ? `${st.bgActive} ${st.borderActive} ring-1 ring-[var(--color-border)]`
                  : "bg-[var(--color-background)] border-[var(--color-border)] hover:border-[var(--color-border-hover,rgba(0,180,122,0.3))]"
              }`}
            >
              {/* Top Row: Label & Active indicator */}
              <div className="flex items-center justify-between gap-1.5">
                <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">
                  {st.label}
                </span>
                {isSelected && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                )}
              </div>

              {/* Middle Row: Percentage & Count */}
              <div className="flex items-baseline justify-between gap-2 pt-0.5">
                <span className={`text-xl font-bold font-mono tracking-tight ${st.textColor}`}>
                  {pct}%
                </span>
                <span className="text-xs font-mono text-[var(--color-text-secondary)] shrink-0">
                  {cnt} {cnt === 1 ? "record" : "records"}
                </span>
              </div>

              {/* Bottom Progress Bar: Clean subtle track, only filled if count > 0 */}
              <div className="w-full bg-[var(--color-border)] h-1 rounded-full overflow-hidden">
                {cnt > 0 && (
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      st.id === "pending" ? "bg-amber-500" :
                      st.id === "ai_verified" ? "bg-emerald-500" :
                      st.id === "flagged" ? "bg-red-500" :
                      st.id === "manual_review" ? "bg-blue-500" : "bg-purple-500"
                    }`}
                    style={{ width: `${Math.max(pct, 5)}%` }}
                  />
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
