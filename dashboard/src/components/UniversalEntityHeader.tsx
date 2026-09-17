// =============================================================================

// VeriField Nexus — Universal Entity Lifecycle Banner Header (CIOS Level 5)

// =============================================================================

"use client";



import { ShieldCheck, Clock, User, ArrowRight, Bot, CheckCircle2 } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { getSectorLifecycleStages, getSectorTerminology } from "@/lib/moduleRegistry";



interface SecondaryAction {

  label: string;

  onClick: () => void;

  variant?: "danger" | "neutral";

}



interface UniversalEntityHeaderProps {

  entityType: string;

  entityId: string;

  entityName: string;

  currentStage: number; // 1 to 6

  currentStageName: string;

  ownerRole: string;

  ownerName: string;

  slaText?: string;

  status: string;

  aiConfidence?: number;

  aiRecommendation?: string;

  primaryNextActionLabel: string;

  onPrimaryNextAction: () => void;

  secondaryActions?: SecondaryAction[];

}



export default function UniversalEntityHeader({

  entityType,

  entityId,

  entityName,

  currentStage,

  currentStageName,

  ownerRole,

  ownerName,

  slaText,

  status,

  aiConfidence,

  aiRecommendation,

  primaryNextActionLabel,

  onPrimaryNextAction,

  secondaryActions = [],

}: UniversalEntityHeaderProps) {

  const { activeSector } = useWorkspace();
  const lifecycleStages = getSectorLifecycleStages(activeSector);
  const sectorTerms = getSectorTerminology(activeSector);

  // Normalize displayed current stage name if stage 3 is active
  const resolvedCurrentStageName = currentStage === 3 && currentStageName.toLowerCase().includes("fleet") && activeSector !== "ev_mobility"
    ? sectorTerms.stage3DetailedName
    : currentStageName;



  const getStatusColor = (st: string) => {

    switch (st.toUpperCase()) {

      case "VERIFIED":

      case "ISSUED":

      case "APPROVED":

        return "bg-emerald-500/15 text-[var(--color-primary)] border-emerald-500/30";

      case "FLAGGED":

      case "REJECTED":

      case "RISK":

        return "bg-rose-500/15 text-rose-400 border-rose-500/30";

      default:

        return "bg-amber-500/15 text-amber-400 border-amber-500/30";

    }

  };



  return (
    <div className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 mb-6 space-y-4">
      {/* 1. Top Entity Metadata & Status Ribbon */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-medium text-[var(--color-text-secondary)] uppercase">
            {entityType} #{entityId}
          </span>
          <h1 className="text-base font-bold text-[var(--color-text-primary)] truncate">
            {entityName}
          </h1>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {status ? (
            <span className={`px-2 py-0.5 rounded-md font-mono font-semibold uppercase border text-[10px] ${getStatusColor(status)}`}>
              {status}
            </span>
          ) : null}

          {ownerName ? (
            <div className="flex items-center gap-1.5 font-medium text-[var(--color-text-secondary)]">
              <User size={14} className="text-[var(--color-text-secondary)]" />
              <span>Owner: <strong className="text-[var(--color-text-primary)]">{ownerName} {ownerRole ? `(${ownerRole})` : ""}</strong></span>
            </div>
          ) : null}

          {slaText ? (

            <div className="flex items-center gap-1.5 font-medium text-amber-400">

              <Clock size={14} />

              <span>{slaText}</span>

            </div>

          ) : null}

        </div>

      </div>



      {/* 2. 6-Stage Carbon Lifecycle Progress Timeline */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-medium text-[var(--color-text-secondary)]">
          <span>Carbon project operational lifecycle</span>
          <span>Current phase: <strong className="text-[var(--color-primary)] font-semibold">{resolvedCurrentStageName}</strong></span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-1.5">
          {lifecycleStages.map((stg, idx) => {
            const stageNum = idx + 1;
            const isPassed = stageNum < currentStage;
            const isCurrent = stageNum === currentStage;

            return (
              <div
                key={idx}
                className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                  isPassed
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                    : isCurrent
                    ? "bg-[var(--color-primary)]/15 text-[var(--color-primary)] border-[var(--color-primary)]/40 shadow-xs font-semibold"
                    : "bg-[var(--color-background)]/50 text-[var(--color-text-secondary)] opacity-50 border-[var(--color-border)]"
                }`}
              >
                <span className="truncate">{stg}</span>
                {isPassed && <CheckCircle2 size={12} className="shrink-0 text-emerald-600 dark:text-emerald-400 ml-1" />}
                {isCurrent && <ShieldCheck size={12} className="shrink-0 text-[var(--color-primary)] ml-1" />}
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Proactive Embedded AI Recommendation Card */}
      {aiRecommendation && (
        <div className="p-3.5 rounded-xl bg-emerald-500/5 border border-emerald-500/20 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
          <div className="flex items-start gap-2.5">
            <Bot size={18} className="text-[var(--color-primary)] shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-[var(--color-primary)] text-xs">Verification insight</span>
                {aiConfidence && aiConfidence > 0 ? (
                  <span className="text-xs bg-emerald-500/20 text-[var(--color-primary)] px-2 py-0.5 rounded-full font-medium">
                    {aiConfidence}% confidence
                  </span>
                ) : null}
              </div>

              <p className="text-[var(--color-text-primary)] font-medium mt-0.5 leading-snug">

                "{aiRecommendation}"

              </p>

            </div>

          </div>

        </div>

      )}



      {/* 4. One Primary Next Action Engine & Secondary Handoffs */}

      <div className="pt-2 flex flex-wrap items-center justify-between gap-3">

        <div className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">

          <span>Target Destination: <strong className="text-[var(--color-text-primary)]">{currentStageName} Queue</strong></span>

        </div>



        <div className="flex items-center gap-2.5">

          {secondaryActions.map((sec, i) => (

            <button

              key={i}

              onClick={sec.onClick}

              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors border cursor-pointer ${
                sec.variant === "danger"
                  ? "bg-rose-500/10 text-rose-400 border-rose-500/20 hover:bg-rose-500/20"
                  : "bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] border-[var(--color-border)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              {sec.label}
            </button>
          ))}

          <button
            onClick={onPrimaryNextAction}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-medium text-xs transition-colors cursor-pointer shadow-xs"
          >
            <span>{primaryNextActionLabel}</span>
            <ArrowRight size={14} />
          </button>

        </div>

      </div>

    </div>

  );

}
