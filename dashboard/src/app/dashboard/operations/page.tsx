"use client";
import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useWorkspace } from "@/context/WorkspaceContext";
import { canPerformAction } from "@/lib/roles";
import ActivitiesPage from "../activities/page";
import IngestionCenterView from "@/components/ingestion/IngestionCenterView";

const LEGACY_DESTINATIONS: Record<string, string> = {
  telemetry: "/dashboard/sensors", verification: "/dashboard/verifications",
  evidence: "/dashboard/audits", spatial: "/dashboard/command-center",
};
function OperationsContent() {
  const params = useSearchParams();
  const router = useRouter();
  const { user, activeProject } = useWorkspace();
  const tab = params.get("tab") || "activities";
  const canSubmit = canPerformAction("evidence:upload", user?.role);
  useEffect(() => {
    if (LEGACY_DESTINATIONS[tab]) router.replace(LEGACY_DESTINATIONS[tab]);
  }, [tab, router]);
  if (LEGACY_DESTINATIONS[tab]) return <p>Opening workspace…</p>;
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-xl font-semibold">Field operations</h1>
      {canSubmit && <Link href={activeProject ? `/capture?project=${activeProject}` : "/capture"} className="rounded-lg bg-emerald-700 text-white px-4 py-2 text-sm font-medium">Capture data</Link>}
    </div>
    <nav aria-label="Field operations" className="flex gap-5 border-b border-[var(--color-border)] text-sm">
      <Link className={`pb-3 ${tab !== "ingestion" ? "border-b-2 border-emerald-600 font-semibold" : ""}`} href="/dashboard/operations">Field records</Link>
      {canSubmit && <Link className={`pb-3 ${tab === "ingestion" ? "border-b-2 border-emerald-600 font-semibold" : ""}`} href="/dashboard/operations?tab=ingestion">Documents & data</Link>}
    </nav>
    {tab === "ingestion" && canSubmit ? <IngestionCenterView /> : <ActivitiesPage />}
  </div>;
}
export default function OperationsPage() {
  return <Suspense fallback={<p>Loading field operations…</p>}><OperationsContent /></Suspense>;
}
