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

  Clock,

  Sparkles,

  AlertTriangle,

  UserCheck,

  CheckCircle2,

  Layers,

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

    icon: any;

    color: string;

    bgActive: string;

    borderActive: string;

    textColor: string;

    badgeBg: string;

  }> = [

    {

      id: "pending",

      label: "Pending",

      icon: Clock,

      color: "text-amber-400",

      bgActive: "bg-amber-500/15",

      borderActive: "border-amber-500/40",

      textColor: "text-amber-400",

      badgeBg: "bg-amber-500/10 border-amber-500/20 text-amber-300",

    },

    {

      id: "ai_verified",

      label: "AI Verified",

      icon: Sparkles,

      color: "text-emerald-400",

      bgActive: "bg-emerald-500/15",

      borderActive: "border-emerald-500/40",

      textColor: "text-emerald-400",

      badgeBg: "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",

    },

    {

      id: "flagged",

      label: "Flagged",

      icon: AlertTriangle,

      color: "text-red-400",

      bgActive: "bg-red-500/15",

      borderActive: "border-red-500/40",

      textColor: "text-red-400",

      badgeBg: "bg-red-500/10 border-red-500/20 text-red-300",

    },

    {

      id: "manual_review",

      label: "Manual Review",

      icon: UserCheck,

      color: "text-blue-400",

      bgActive: "bg-blue-500/15",

      borderActive: "border-blue-500/40",

      textColor: "text-blue-400",

      badgeBg: "bg-blue-500/10 border-blue-500/20 text-blue-300",

    },

    {

      id: "approved",

      label: "Approved",

      icon: CheckCircle2,

      color: "text-purple-400",

      bgActive: "bg-purple-500/15",

      borderActive: "border-purple-500/40",

      textColor: "text-purple-400",

      badgeBg: "bg-purple-500/10 border-purple-500/20 text-purple-300",

    },

  ];



  return (

    <div className={`p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs space-y-3.5 ${className}`}>

      {/* Header */}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--color-border)] pb-3">

        <div className="space-y-0.5">

          <div className="flex items-center gap-2">

            <Layers size={16} className="text-[#00B47A]" />

            <h3 className="font-extrabold text-xs uppercase tracking-wider text-[var(--color-text-primary)]">

              VERIFICATION PIPELINE STAGES

            </h3>

          </div>

          <p className="text-[11px] text-[var(--color-text-secondary)] font-medium">

            Click stage to filter the Field Map and Anomaly feeds dynamically (Click again to reset)

          </p>

        </div>



        {activeStage && (

          <button

            onClick={() => handleStageClick(activeStage)}

            className="self-start sm:self-auto px-2.5 py-1 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 transition-all cursor-pointer"

          >

            <FilterX size={12} />

            <span>Reset Stage Filter</span>

          </button>

        )}

      </div>



      {/* 5 Stage Cards Grid */}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">

        {stages.map((st) => {

          const Icon = st.icon;

          const cnt = counts[st.id];

          const pct = getPercentage(cnt);

          const isSelected = activeStage === st.id;



          return (

            <button

              key={st.id}

              onClick={() => handleStageClick(st.id)}

              className={`p-3.5 rounded-xl border text-left transition-all duration-200 cursor-pointer flex flex-col justify-between space-y-2 relative overflow-hidden group ${

                isSelected

                  ? `${st.bgActive} ${st.borderActive} ring-1 ring-emerald-500/30 shadow-md`

                  : "bg-[var(--color-background)] border-[var(--color-border)] hover:border-emerald-500/30 hover:bg-[#141F20]/30"

              }`}

            >

              {/* Top Row: Icon & Label */}

              <div className="flex items-center justify-between gap-1.5">

                <div className="flex items-center gap-1.5 min-w-0">

                  <Icon size={15} className={`${st.color} shrink-0`} />

                  <span className="text-xs font-bold text-[var(--color-text-primary)] truncate">

                    {st.label}

                  </span>

                </div>

                {isSelected && (

                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping shrink-0" />

                )}

              </div>



              {/* Middle Row: Percentage & Count */}

              <div className="flex items-center justify-between gap-2.5 pt-1">

                <span className={`text-xl sm:text-2xl font-black font-mono tracking-tight ${st.textColor}`}>

                  {pct}%

                </span>

                <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded-md border shrink-0 ${st.badgeBg}`}>

                  {cnt}

                </span>

              </div>



              {/* Bottom Progress Bar */}

              <div className="w-full bg-[#141F20] h-1.5 rounded-full overflow-hidden">

                <div

                  className={`h-full rounded-full transition-all duration-500 ${

                    st.id === "pending" ? "bg-amber-400" :

                    st.id === "ai_verified" ? "bg-emerald-400" :

                    st.id === "flagged" ? "bg-red-400" :

                    st.id === "manual_review" ? "bg-blue-400" : "bg-purple-400"

                  }`}

                  style={{ width: `${Math.max(pct, cnt > 0 ? 5 : 0)}%` }}

                />

              </div>

            </button>

          );

        })}

      </div>

    </div>

  );

}
