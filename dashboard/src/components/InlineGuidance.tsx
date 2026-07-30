// =============================================================================

// VeriField Nexus — Inline Guidance Component

// =============================================================================

// Role-aware contextual guidance banner with next-step recommendations.

// Shows relevant guidance for each user role at the top of dashboard pages.

// =============================================================================



"use client";



import React, { useState, useEffect } from "react";

import { Lightbulb, X, ArrowRight, CheckCircle2 } from "lucide-react";

import Link from "next/link";



interface InlineGuidanceProps {

  role?: string;

  page?: string;

  sectorCode?: string;

  data?: {

    pendingSyncs?: number;

    pendingReviews?: number;

    verificationPct?: number;

    assetsRemaining?: number;

    activeUsers?: number;

    pendingApprovals?: number;

  };

}



interface GuidanceItem {

  message: string;

  actionLabel?: string;

  actionHref?: string;

  priority: "info" | "action" | "success";

}



function getGuidanceForRole(

  role: string,

  page: string,

  data?: InlineGuidanceProps["data"]

): GuidanceItem[] {

  const items: GuidanceItem[] = [];

  const r = role.toUpperCase();



  if (r === "FIELD_AGENT" || r === "field_agent") {

    if (data?.pendingSyncs && data.pendingSyncs > 0) {

      items.push({

        message: `You have ${data.pendingSyncs} pending sync(s). Ensure your data is uploaded before leaving the field.`,

        actionLabel: "View Sync Status",

        actionHref: "/dashboard/activities",

        priority: "action",

      });

    }

    items.push({

      message: "Capture evidence with your camera and GPS enabled for the highest trust scores.",

      priority: "info",

    });

  } else if (r === "QA_OFFICER" || r === "qa_officer") {

    if (data?.pendingReviews && data.pendingReviews > 0) {

      items.push({

        message: `${data.pendingReviews} activities need QA review. Start with the lowest trust scores for maximum impact.`,

        actionLabel: "Review Queue",

        actionHref: "/dashboard/activities",

        priority: "action",

      });

    }

    items.push({

      message: "Use the trust score breakdown to prioritize which evidence to review first.",

      priority: "info",

    });

  } else if (r === "PROJECT_MANAGER" || r === "project_manager") {

    if (data?.verificationPct !== undefined) {

      items.push({

        message: `Verification progress: ${data.verificationPct}% complete. ${data.assetsRemaining ?? 0} assets remaining.`,

        actionLabel: "View Projects",

        actionHref: "/dashboard/projects",

        priority: data.verificationPct >= 90 ? "success" : "action",

      });

    }

    items.push({

      message: "Review project timelines and reassign field teams as needed.",

      priority: "info",

    });

  } else if (r.includes("ADMIN") || r === "admin") {

    items.push({

      message: `System running. ${data?.activeUsers ?? 0} active users.${data?.pendingApprovals ? ` ${data.pendingApprovals} pending approvals.` : ""}`,

      actionLabel: "System Settings",

      actionHref: "/dashboard/settings",

      priority: "info",

    });

  } else if (r === "VVB_AUDITOR" || r === "vvb_auditor") {

    items.push({

      message: "Review the immutable audit trail and evidence packages for verification readiness.",

      actionLabel: "Audit Trail",

      actionHref: "/dashboard/audit",

      priority: "info",

    });

  } else if (r === "REGISTRY_MANAGER" || r === "registry_manager") {

    items.push({

      message: "Check registry export readiness. Ensure all projects have complete verification before export.",

      actionLabel: "Registry Export",

      actionHref: "/dashboard/registry",

      priority: "info",

    });

  }



  return items;

}



export default function InlineGuidance({ role, page, sectorCode, data }: InlineGuidanceProps) {

  const [dismissed, setDismissed] = useState(false);

  const [loaded, setLoaded] = useState(false);



  useEffect(() => {

    const key = `vf_guidance_dismissed_${role}_${page}`;

    const d = typeof window !== "undefined" ? localStorage.getItem(key) : null;

    if (d) setDismissed(true);

    setLoaded(true);

  }, [role, page]);



  if (!loaded || dismissed) return null;



  const guidance = getGuidanceForRole(role || "admin", page || "dashboard", data);

  if (guidance.length === 0) return null;



  const handleDismiss = () => {

    setDismissed(true);

    const key = `vf_guidance_dismissed_${role}_${page}`;

    if (typeof window !== "undefined") {

      localStorage.setItem(key, "1");

    }

  };



  const item = guidance[0]; // Show the most important one



  const bgClass =

    item.priority === "action"

      ? "from-yellow-500/10 to-transparent border-yellow-500/30"

      : item.priority === "success"

      ? "from-emerald-500/10 to-transparent border-emerald-500/30"

      : "from-blue-500/10 to-transparent border-blue-500/30";



  const iconColor =

    item.priority === "action" ? "text-yellow-400" : item.priority === "success" ? "text-emerald-400" : "text-blue-400";



  return (

    <div className={`mb-4 rounded-xl bg-gradient-to-r ${bgClass} border px-4 py-3 flex items-center justify-between gap-3`}>

      <div className="flex items-center gap-3 min-w-0">

        <p className="text-xs font-medium text-[var(--color-text-primary)] truncate">{item.message}</p>

      </div>

      <div className="flex items-center gap-2 shrink-0">

        {item.actionLabel && item.actionHref && (

          <Link

            href={item.actionHref}

            className="px-3 py-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-[10px] font-bold text-[var(--color-text-primary)] hover:bg-[var(--color-background)] transition-all flex items-center gap-1"

          >

            {item.actionLabel} <ArrowRight size={10} />

          </Link>

        )}

        <button

          onClick={handleDismiss}

          className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer"

          aria-label="Dismiss guidance"

        >

          <X size={14} />

        </button>

      </div>

    </div>

  );

}
