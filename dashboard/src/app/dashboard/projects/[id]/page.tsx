// =============================================================================
// VeriField Nexus — Project Workspace Hub & Ingestion Portal
// =============================================================================

"use client";

import React, { useState, useEffect, Suspense, useMemo } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Activity as ActivityIcon,
  MapPin,
  ShieldCheck,
  Calendar,
  Clock,
  Copy,
  Check,
  FileText,
  UploadCloud,
  FlaskConical,
  Radio,
  Layers,
  Loader2,
  Globe,
  Tag,
  Building,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { fetchProjectById, fetchLandUnits, fetchActivities, type LandUnitRecord } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useToast } from "@/components/Toast";
import { ProjectDocumentsModule } from "@/components/dashboard/ProjectDocumentsModule";
import AgricultureLaboratoryBulkImportView from "@/components/dashboard/AgricultureLaboratoryBulkImportView";
import AuditsListView from "@/components/verification/AuditsListView";
import { resolveProjectMethodology } from "@/lib/projectMethodology";
import VerificationsPage from "../../verifications/page";
import SensorsPage from "../../sensors/page";

function ProjectDetailPageContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { user, activeSector, changeProject } = useWorkspace();

  const projectId = (params?.id as string) || "";
  const initialTab = searchParams.get("tab") || "overview";
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  const [project, setProject] = useState<any | null>(null);
  const [landUnits, setLandUnits] = useState<LandUnitRecord[]>([]);
  const [activitiesCount, setActivitiesCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [copiedId, setCopiedId] = useState<boolean>(false);

  // Sync active project in WorkspaceContext so subviews like SensorsPage pick up this project
  useEffect(() => {
    if (projectId) {
      changeProject(projectId);
    }
  }, [projectId, changeProject]);

  // Load project details, land units, and activities count
  useEffect(() => {
    async function loadProject() {
      if (!projectId) return;
      setIsLoading(true);
      try {
        const [projRes, luRes, actRes] = await Promise.allSettled([
          fetchProjectById(projectId),
          fetchLandUnits(projectId),
          fetchActivities({ project_id: projectId })
        ]);

        if (projRes.status === "fulfilled" && projRes.value) {
          setProject(projRes.value);
        }
        if (luRes.status === "fulfilled" && Array.isArray(luRes.value)) {
          setLandUnits(luRes.value);
        }
        if (actRes.status === "fulfilled") {
          const acts = actRes.value as any;
          const count = acts?.total != null
            ? acts.total
            : Array.isArray(acts)
            ? acts.length
            : acts?.activities?.length || 0;
          setActivitiesCount(count);
        }
      } catch (err) {
        console.error("Failed to load project details:", err);
      } finally {
        setIsLoading(false);
      }
    }
    loadProject();
  }, [projectId]);

  const handleCopyId = async () => {
    if (!projectId) return;
    try {
      await navigator.clipboard.writeText(projectId);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
      toast.success("Copied", "Project ID copied to clipboard.");
    } catch {
      toast.error("Copy Failed", "Clipboard access unavailable.");
    }
  };

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    router.replace(`/dashboard/projects/${projectId}?tab=${tabId}`, { scroll: false });
  };

  const isAgriculture = useMemo(() => {
    const s = (activeSector || project?.sector || "").toUpperCase();
    return s.includes("AGRI") || s.includes("LAND") || !s;
  }, [activeSector, project]);

  const resolvedMethodology = useMemo(() => {
    return resolveProjectMethodology(project);
  }, [project]);

  const tabs = [
    { id: "overview", label: "Project Overview", icon: ActivityIcon },
    { id: "land-units", label: `Land Units & Parcels (${landUnits.length})`, icon: Layers },
    { id: "documents", label: "Project Documents & PDD", icon: UploadCloud },
    ...(isAgriculture
      ? [{ id: "laboratory", label: "Laboratory Assays", icon: FlaskConical }]
      : []),
    { id: "evidence", label: "Proof Evidence Vault", icon: FileText },
    { id: "telemetry", label: "Live Telemetry & Devices", icon: Radio },
    { id: "verification", label: "Verification Hub", icon: ShieldCheck },
  ];

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-[#00B47A]" />
        <p className="text-xs font-semibold text-[var(--color-text-secondary)]">
          Retrieving project workspace and MRV records...
        </p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-12 text-center max-w-md mx-auto space-y-3 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl">
        <AlertCircle size={32} className="text-amber-500 mx-auto" />
        <h3 className="text-base font-bold text-[var(--color-text-primary)]">Project Not Found</h3>
        <p className="text-xs text-[var(--color-text-secondary)]">
          The requested project ID does not exist or is not authorized for your organization.
        </p>
        <Link
          href="/dashboard/properties"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#00B47A] text-white text-xs font-bold"
        >
          <ArrowLeft size={13} />
          <span>Return to Projects Directory</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-fade-in-up text-[var(--color-text-primary)]">
      {/* 🧭 NAVIGATION & BREADCRUMB */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/dashboard/properties"
          className="px-3 py-1.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors flex items-center gap-1.5 text-xs font-bold"
        >
          <ArrowLeft size={13} />
          <span>Projects Directory</span>
        </Link>

        <div className="flex items-center gap-2">
          <div className="text-[10px] font-mono bg-[var(--color-surface)] border border-[var(--color-border)] px-3 py-1.5 rounded-xl text-[var(--color-text-secondary)] flex items-center gap-2">
            <span className="font-extrabold text-[#00B47A]">PROJECT ID:</span>
            <span className="font-mono">{projectId.slice(0, 8)}…{projectId.slice(-4)}</span>
            <button
              type="button"
              onClick={handleCopyId}
              className="p-0.5 rounded hover:text-[#00B47A] cursor-pointer"
              title="Copy Project ID"
            >
              {copiedId ? <Check size={12} className="text-[#00B47A]" /> : <Copy size={12} />}
            </button>
          </div>
        </div>
      </div>

      {/* 🏛️ HEADER HERO */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-[#00B47A] text-[10px] font-extrabold tracking-wider uppercase border border-emerald-500/20">
                ACTIVE CLIMATE PROJECT
              </span>
              <span className="text-[11px] font-mono text-[var(--color-text-muted)] flex items-center gap-1">
                <Clock size={12} /> Registered {project.created_at ? new Date(project.created_at).toLocaleDateString() : "Active"}
              </span>
            </div>
            <h1 className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">
              {project.name}
            </h1>
            <p className="text-xs text-[var(--color-text-secondary)] mt-1 flex items-center gap-2">
              <MapPin size={13} className="text-[#00B47A]" />
              <span>{project.country || "Nigeria"}</span>
              <span className="text-[var(--color-border)]">•</span>
              <span
                className="font-mono text-[11px] text-[#00B47A]"
                data-testid="project-methodology-subtitle"
              >
                {resolvedMethodology.code}
              </span>
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-3 gap-3 shrink-0">
            <div className="px-4 py-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-center">
              <span className="text-[10px] font-bold uppercase text-[var(--color-text-muted)] block">Activities</span>
              <span className="text-lg font-black text-[var(--color-text-primary)]">{activitiesCount}</span>
            </div>
            <div className="px-4 py-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-center">
              <span className="text-[10px] font-bold uppercase text-[var(--color-text-muted)] block">Land Units</span>
              <span className="text-lg font-black text-[var(--color-text-primary)]">{landUnits.length}</span>
            </div>
            <div className="px-4 py-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-center">
              <span className="text-[10px] font-bold uppercase text-[var(--color-text-muted)] block">Status</span>
              <span className="text-xs font-black text-[#00B47A] block mt-1">VERIFIED</span>
            </div>
          </div>
        </div>

        {/* Workspace Tab Bar */}
        <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pt-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? "bg-[#00B47A] text-slate-950 shadow-md font-black"
                    : "bg-[var(--color-background)] text-[var(--color-text-secondary)] border border-[var(--color-border)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                <Icon size={14} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 📑 TAB PANELS */}
      <div className="space-y-6">
        {/* TAB: OVERVIEW */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Quick Ingestion Callout Card */}
            <div className="p-5 rounded-2xl bg-gradient-to-r from-emerald-950/20 via-[var(--color-surface)] to-[var(--color-surface)] border border-[#00B47A]/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <span className="text-[10px] font-black uppercase tracking-wider text-[#00B47A]">
                  DATA & DOCUMENT INGESTION
                </span>
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                  Ready to ingest Project Design Documents or Laboratory Assays?
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)]">
                  Upload PDF/DOCX monitoring files or bulk laboratory soil measurements directly into this project workspace.
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleTabChange("documents")}
                  className="px-4 py-2 rounded-xl bg-[#00B47A] hover:bg-[#009b68] text-slate-950 font-bold text-xs shadow-md transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <UploadCloud size={14} />
                  <span>Ingest Project Documents</span>
                </button>
                {isAgriculture && (
                  <button
                    onClick={() => handleTabChange("laboratory")}
                    className="px-4 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-bold text-xs transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <FlaskConical size={14} />
                    <span>Ingest Lab Assays</span>
                  </button>
                )}
              </div>
            </div>

            {/* Project Specifications Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)] flex items-center gap-1.5">
                  <Tag size={13} className="text-[#00B47A]" />
                  <span>Methodology & Accounting Standard</span>
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-[var(--color-border)]">
                    <span className="text-[var(--color-text-secondary)]">Standard Code</span>
                    <span
                      className="font-mono font-bold text-[var(--color-text-primary)]"
                      data-testid="project-methodology-code"
                    >
                      {resolvedMethodology.code}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[var(--color-border)]">
                    <span className="text-[var(--color-text-secondary)]">Version</span>
                    <span
                      className="font-mono font-bold text-[var(--color-text-primary)]"
                      data-testid="project-methodology-version"
                    >
                      {resolvedMethodology.version || (resolvedMethodology.isAssigned ? "1.0" : "—")}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[var(--color-border)]">
                    <span className="text-[var(--color-text-secondary)]">Sector Domain</span>
                    <span className="font-bold text-[var(--color-text-primary)]">
                      {activeSector || "AGRICULTURE_LAND_USE"}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[var(--color-text-secondary)]">Crediting Period</span>
                    <span className="font-medium text-[var(--color-text-primary)]">
                      {project.crediting_start ? `${project.crediting_start} → ${project.crediting_end || "Ongoing"}` : "Standard 10-Year Renewable"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)] flex items-center gap-1.5">
                  <Globe size={13} className="text-[#00B47A]" />
                  <span>Operational Governance & Boundaries</span>
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-[var(--color-border)]">
                    <span className="text-[var(--color-text-secondary)]">Country / Jurisdiction</span>
                    <span className="font-bold text-[var(--color-text-primary)]">{project.country || "Nigeria"}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[var(--color-border)]">
                    <span className="text-[var(--color-text-secondary)]">Bound Land Units</span>
                    <span className="font-mono font-bold text-[var(--color-text-primary)]">{landUnits.length} Parcels</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[var(--color-border)]">
                    <span className="text-[var(--color-text-secondary)]">Recorded Telemetry Transmissions</span>
                    <span className="font-mono font-bold text-[#00B47A]">{activitiesCount} Records</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[var(--color-text-secondary)]">Tenant Ownership</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">Tenant-Verified</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB: LAND UNITS & BOUNDARIES */}
        {activeTab === "land-units" && (
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <div>
                <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
                  Bound Land Units & Soil Strata ({landUnits.length})
                </h2>
                <p className="text-[11px] text-[var(--color-text-secondary)]">
                  Parcels, cadastral boundaries, and soil sampling strata bound to {project.name}.
                </p>
              </div>
            </div>

            {landUnits.length === 0 ? (
              <div className="p-8 text-center bg-[var(--color-background)] rounded-xl border border-[var(--color-border)] space-y-2">
                <Layers size={24} className="text-[var(--color-text-muted)] mx-auto" />
                <p className="text-xs font-bold text-[var(--color-text-primary)]">No Land Units Bound to Project</p>
                <p className="text-[11px] text-[var(--color-text-secondary)] max-w-sm mx-auto">
                  Spatial boundaries can be ingested via geospatial GeoJSON boundaries or registered in the Spatial Command Center.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--color-border)] text-[11px] font-semibold text-[var(--color-text-secondary)] bg-[#F8FAFC] dark:bg-slate-900">
                      <th className="py-2.5 px-3">Land Unit Code</th>
                      <th className="py-2.5 px-3">Name</th>
                      <th className="py-2.5 px-3">Area (ha)</th>
                      <th className="py-2.5 px-3">Unit Type</th>
                      <th className="py-2.5 px-3">Land Use / Soil</th>
                      <th className="py-2.5 px-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)]">
                    {landUnits.map((unit) => (
                      <tr key={unit.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50">
                        <td className="py-2.5 px-3 font-mono font-bold text-[11px] text-[#00B47A]">
                          {unit.code || unit.id.slice(0, 8)}
                        </td>
                        <td className="py-2.5 px-3 font-medium text-[var(--color-text-primary)]">
                          {unit.name || "Agricultural Parcel"}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[var(--color-text-secondary)]">
                          {unit.area_ha != null ? `${Number(unit.area_ha).toFixed(2)} ha` : "—"}
                        </td>
                        <td className="py-2.5 px-3 text-[var(--color-text-secondary)]">
                          {unit.unit_type || "Parcel"}
                        </td>
                        <td className="py-2.5 px-3 text-[var(--color-text-muted)] text-[11px]">
                          {unit.land_use_category || unit.soil_type || "Cropland"}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/50 text-[#00B47A] border border-emerald-200 dark:border-emerald-800">
                            Active
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB: PROJECT DOCUMENTS & PDD */}
        {activeTab === "documents" && (
          <ProjectDocumentsModule
            projectId={projectId}
            projectName={project.name}
            organizationId={project.organization_id || user?.organization_id}
            sectorName={activeSector || "AGRICULTURE_LAND_USE"}
            methodologyName={resolvedMethodology.isAssigned ? resolvedMethodology.code : "Under Assessment"}
          />
        )}

        {/* TAB: LABORATORY ASSAYS */}
        {activeTab === "laboratory" && isAgriculture && (
          <AgricultureLaboratoryBulkImportView projectId={projectId} />
        )}

        {/* TAB: EVIDENCE */}
        {activeTab === "evidence" && (
          <AuditsListView />
        )}

        {/* TAB: LIVE TELEMETRY */}
        {activeTab === "telemetry" && (
          <SensorsPage />
        )}

        {/* TAB: VERIFICATION */}
        {activeTab === "verification" && (
          <VerificationsPage />
        )}
      </div>
    </div>
  );
}

export default function ProjectDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-[#00B47A]" />
        </div>
      }
    >
      <ProjectDetailPageContent />
    </Suspense>
  );
}
