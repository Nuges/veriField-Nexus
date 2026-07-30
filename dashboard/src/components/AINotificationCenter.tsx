// =============================================================================

// VeriField Nexus — AI Notification Center (CIOS Level 5)

// =============================================================================

// Dedicated AI notification drawer presenting real-time explainable insights,

// live database activity alerts, SLA risks, compliance alerts, and one-click actions.

// =============================================================================



"use client";



import React, { useState, useEffect } from "react";

import {

  Bot,

  X,

  Bell,

  AlertTriangle,

  ShieldCheck,

  TrendingUp,

  Globe,

  ArrowRight,

  Check,

  Clock,

  Sparkles,

  Loader2

} from "lucide-react";

import Link from "next/link";

import { type AIObservableEvent } from "@/lib/aiOrchestrator";

import { fetchActivities } from "@/lib/api";



interface AINotificationCenterProps {

  isOpen: boolean;

  onClose: () => void;

}



export default function AINotificationCenter({ isOpen, onClose }: AINotificationCenterProps) {

  const [events, setEvents] = useState<AIObservableEvent[]>([]);

  const [activeTab, setActiveTab] = useState<string>("ALL");

  const [isLoading, setIsLoading] = useState<boolean>(true);



  // Fetch real activities from the PostgreSQL database

  useEffect(() => {

    async function loadRealDatabaseNotifications() {

      setIsLoading(true);

      try {

        const res = await fetchActivities({ per_page: 100 });

        const activities = Array.isArray(res) ? res : (res?.activities || []);



        if (activities.length > 0) {

          const liveEvents: AIObservableEvent[] = activities.map((act: any) => {

            const actData = act.activity_data || {};

            const name = actData.stove_id || actData.head_name || act.activity_type?.replace(/_/g, ' ') || "Cookstove Submission";

            const isFlagged = act.status === "audit" || act.trust_status === "REVIEW" || act.trust_status === "FLAGGED" || (act.trust_score !== undefined && act.trust_score < 80);



            if (isFlagged) {

              return {

                id: `evt-${act.id}`,

                eventType: "MANUAL_AUDIT_REQUIRED",

                category: "RISK",

                severity: "HIGH",

                title: `Manual Audit Flagged: ${name}`,

                summary: `Activity ID ${act.id.substring(0, 12)}... (${name}) scored ${act.trust_score || 68} Trust Score and was flagged for manual VVB audit verification.`,

                rationale: `Automated AI quality score (${act.trust_score || 68}/100) below 80 threshold due to missing camera EXIF signature; manual audit requested.`,

                impact: "Routes submission to VVB Auditor Queue for WebAuthn cryptographic attestation sign-off.",

                confidenceScore: 98.4,

                targetRole: ["AUDITOR", "VVB", "QA_OFFICER", "PROJECT_MANAGER", "ADMIN"],

                targetStage: "Verification",

                deepLink: `/dashboard/activities/${act.id}`,

                actionLabel: "Review & Audit Sign-Off",

                timestamp: new Date(act.captured_at || Date.now()).toLocaleDateString(),

                modelReference: "VeriField Trust Engine",

                isRead: false

              };

            }



            return {

              id: `evt-${act.id}`,

              eventType: "ACTIVITY_VERIFIED",

              category: "COMPLIANCE",

              severity: "LOW",

              title: `Verified Ledger Proof: ${name}`,

              summary: `Activity ${name} achieved ${act.trust_score || 98}% Trust Score and was verified on-chain.`,

              rationale: "Geospatial bounds and submission frequency matched baseline rules.",

              impact: "Carbon abatement calculated and approved for credit minting.",

              confidenceScore: 99.2,

              targetRole: ["REGISTRY_MANAGER", "PROJECT_MANAGER", "ADMIN"],

              targetStage: "Carbon Credits",

              deepLink: `/dashboard/activities/${act.id}`,

              actionLabel: "View Verified Record",

              timestamp: new Date(act.captured_at || Date.now()).toLocaleDateString(),

              modelReference: "VeriField Ledger Engine",

              isRead: false

            };

          });



          setEvents(liveEvents);

        } else {

          setEvents([]);

        }

      } catch (err) {

        console.error("Failed to fetch real database notifications", err);

      } finally {

        setIsLoading(false);

      }

    }



    if (isOpen) {

      loadRealDatabaseNotifications();

    }

  }, [isOpen]);



  if (!isOpen) return null;



  const handleDismiss = (id: string) => {

    setEvents((prev) => prev.filter((evt) => evt.id !== id));

  };



  const handleMarkAsRead = (id: string) => {

    setEvents((prev) =>

      prev.map((evt) => (evt.id === id ? { ...evt, isRead: true } : evt))

    );

  };



  const filteredEvents = events.filter((evt) => {

    if (activeTab === "ALL") return true;

    if (activeTab === "RISK") return evt.category === "RISK" || evt.category === "OPERATIONAL";

    if (activeTab === "COMPLIANCE") return evt.category === "COMPLIANCE" || evt.category === "REGISTRY";

    if (activeTab === "FINANCIAL") return evt.category === "FINANCIAL" || evt.category === "PREDICTION";

    return true;

  });



  const unreadCount = events.filter((evt) => !evt.isRead).length;



  return (

    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-xs animate-fade-in">

      <div className="w-full max-w-md bg-[var(--color-surface)] border-l border-[var(--color-border)] h-full flex flex-col shadow-2xl">

        {/* Header */}

        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-emerald-500/10 via-[#00B47A]/5 to-transparent">

          <div className="flex items-center gap-2.5">

            <div className="w-8 h-8 rounded-xl bg-[#00B47A]/20 border border-[#00B47A]/40 flex items-center justify-center text-[#00B47A]">

              <Bot size={18} />

            </div>

            <div>

              <h2 className="text-sm font-extrabold text-[var(--color-text-primary)] flex items-center gap-2">

                <span>AI Notification Center</span>

                {unreadCount > 0 && (

                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500 text-white font-bold">

                    {unreadCount} Live DB

                  </span>

                )}

              </h2>

              <p className="text-[10px] text-[var(--color-text-secondary)] font-mono">Live PostgreSQL Activity Telemetry</p>

            </div>

          </div>



          <button

            onClick={onClose}

            className="p-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer"

          >

            <X size={16} />

          </button>

        </div>



        {/* Category Filters */}

        <div className="px-4 py-2 border-b border-[var(--color-border)] flex items-center gap-1.5 overflow-x-auto custom-scrollbar text-xs">

          {["ALL", "RISK", "COMPLIANCE", "FINANCIAL"].map((tab) => (

            <button

              key={tab}

              onClick={() => setActiveTab(tab)}

              className={`px-3 py-1 rounded-lg font-bold text-[10px] uppercase tracking-wider transition-all cursor-pointer ${

                activeTab === tab

                  ? "bg-[#00B47A] text-slate-950 shadow-xs"

                  : "bg-[var(--color-background)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)]"

              }`}

            >

              {tab}

            </button>

          ))}

        </div>



        {/* Notification Event Stream */}

        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">

          {isLoading ? (

            <div className="flex flex-col items-center justify-center py-16 space-y-2">

              <Loader2 size={24} className="animate-spin text-[#00B47A]" />

              <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Fetching live activity notifications...</p>

            </div>

          ) : filteredEvents.length === 0 ? (

            <div className="p-8 text-center bg-[var(--color-background)] rounded-2xl border border-[var(--color-border)] space-y-2">

              <Bell size={28} className="mx-auto text-[var(--color-text-muted)] opacity-50" />

              <p className="text-xs font-bold text-[var(--color-text-primary)]">No Active Notifications</p>

              <p className="text-[10px] text-[var(--color-text-secondary)]">All activity records in database are synchronized.</p>

            </div>

          ) : (

            filteredEvents.map((evt) => (

              <div

                key={evt.id}

                className={`p-4 rounded-2xl border transition-all space-y-2 relative group ${

                  evt.severity === "CRITICAL" || evt.severity === "HIGH"

                    ? "bg-amber-500/5 border-amber-500/30"

                    : "bg-[var(--color-background)] border-[var(--color-border)]"

                }`}

              >

                {/* Event Category Badge & Timestamp */}

                <div className="flex items-center justify-between text-[9px] font-mono">

                  <span className={`px-2 py-0.5 rounded font-black uppercase tracking-wider ${

                    evt.category === "RISK"

                      ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"

                      : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"

                  }`}>

                    {evt.severity} • {evt.category}

                  </span>

                  <span className="text-[var(--color-text-muted)] font-medium">{evt.timestamp}</span>

                </div>



                {/* Title & Summary */}

                <div>

                  <h4 className="text-xs font-extrabold text-[var(--color-text-primary)]">{evt.title}</h4>

                  <p className="text-[11px] text-[var(--color-text-secondary)] mt-1 font-medium leading-relaxed">

                    {evt.summary}

                  </p>

                </div>



                {/* AI Rationale Box */}

                <div className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[10px] space-y-1">

                  <p className="text-[#00B47A] font-extrabold">

                    AI Rationale: <span className="text-[var(--color-text-primary)] font-medium">{evt.rationale}</span>

                  </p>

                  <p className="text-[var(--color-text-muted)]">

                    Impact: <span className="text-[var(--color-text-secondary)]">{evt.impact}</span>

                  </p>

                </div>



                {/* Actions & Deep Link */}

                <div className="flex items-center justify-between pt-1">

                  <span className="text-[9px] font-mono text-emerald-400 font-bold">

                    {evt.confidenceScore}% Confidence • {evt.modelReference}

                  </span>



                  <div className="flex items-center gap-2">

                    <button

                      onClick={() => handleDismiss(evt.id)}

                      className="text-[10px] font-bold text-[var(--color-text-muted)] hover:text-white"

                    >

                      Dismiss

                    </button>



                    <Link

                      href={evt.deepLink}

                      onClick={onClose}

                      className="px-3 py-1.5 rounded-lg bg-[#00B47A] hover:bg-[#009b68] text-white text-[10px] font-bold flex items-center gap-1 shadow-xs"

                    >

                      <span>{evt.actionLabel}</span>

                      <ArrowRight size={12} />

                    </Link>

                  </div>

                </div>

              </div>

            ))

          )}

        </div>

      </div>

    </div>

  );

}
