"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileText,
  FlaskConical,
  Camera,
  FolderInput,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  Lock,
  Layers,
  ChevronRight,
  ExternalLink,
  Upload,
  Download,
} from "lucide-react";
import { resolveProjectMethodology } from "@/lib/projectMethodology";
import { canReadRegistry } from "@/lib/registryWorkflow";
import { useWorkspace } from "@/context/WorkspaceContext";
import { canonicalSectorCode } from "@/lib/moduleRegistry";
import { downloadLaboratoryImportTemplate } from "@/lib/api";
import { ProjectDocumentsModule } from "@/components/dashboard/ProjectDocumentsModule";
import AgricultureLaboratoryBulkImportView from "@/components/dashboard/AgricultureLaboratoryBulkImportView";

interface IngestionCenterViewProps {
  initialSubView?: "hub" | "documents" | "laboratory";
}

export default function IngestionCenterView({ initialSubView = "hub" }: IngestionCenterViewProps) {
  const { user, activeSector, activeProject, changeProject, projects } = useWorkspace();
  const [activeSubView, setActiveSubView] = useState<"hub" | "documents" | "laboratory">(initialSubView);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);

  const currentProject = projects.find((p) => p.id === activeProject);
  const userRole = (user?.role || "VIEWER").toUpperCase();
  const canonicalSector = canonicalSectorCode(activeSector || "").toUpperCase();

  // Roles permitted to upload project documents per backend policy
  const DOCUMENT_UPLOAD_ROLES = new Set([
    "SUPER_ADMIN",
    "ADMIN",
    "ORG_ADMIN",
    "PROJECT_MANAGER",
    "QA_OFFICER",
    "FIELD_SUPERVISOR",
  ]);
  const canUploadDocuments = DOCUMENT_UPLOAD_ROLES.has(userRole);

  // Roles permitted to commit/update lab batches (requires project:update)
  const LAB_UPLOAD_ROLES = new Set(["SUPER_ADMIN", "ADMIN", "ORG_ADMIN", "PROJECT_MANAGER"]);
  const canUploadLab = LAB_UPLOAD_ROLES.has(userRole);

  const isAgriculture = canonicalSector === "AGRICULTURE_LAND_USE" || canonicalSector === "AGRICULTURE";

  // If viewing documents subview and project is selected
  if (activeSubView === "documents" && activeProject) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-[var(--color-border)]">
          <button
            onClick={() => setActiveSubView("hub")}
            className="flex items-center gap-1.5 text-xs font-semibold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors cursor-pointer"
          >
            ← Return to Ingestion Center
          </button>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-[var(--color-text-muted)]">Active Context:</span>
            <span className="text-xs font-bold text-[var(--color-text-primary)]">
              {currentProject?.name || activeProject}
            </span>
          </div>
        </div>
        <ProjectDocumentsModule
          projectId={activeProject}
          projectName={currentProject?.name || "Active Project"}
          organizationId={currentProject?.organization_id || user?.organization_id || undefined}
          sectorName={activeSector}
          methodologyName={resolveProjectMethodology(currentProject).code}
        />
      </div>
    );
  }

  // If viewing laboratory subview and project is selected
  if (activeSubView === "laboratory" && activeProject && isAgriculture) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-[var(--color-border)]">
          <button
            onClick={() => setActiveSubView("hub")}
            className="flex items-center gap-1.5 text-xs font-semibold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors cursor-pointer"
          >
            ← Return to Ingestion Center
          </button>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-[var(--color-text-muted)]">Active Context:</span>
            <span className="text-xs font-bold text-[var(--color-text-primary)]">
              {currentProject?.name || activeProject}
            </span>
          </div>
        </div>
        <AgricultureLaboratoryBulkImportView projectId={activeProject} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 🧭 INGESTION BANNER & PROJECT CONTEXT */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 shrink-0 mt-0.5">
              <FolderInput size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-extrabold text-[var(--color-text-primary)]">
                  Data & Document Ingestion Center
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                  MRV Gateway
                </span>
              </div>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Centralized pipeline for project design documents (PDDs), physical laboratory assays, and photographic evidence.
              </p>
            </div>
          </div>

          {/* Contextual Project Selector */}
          <div className="flex items-center gap-2 bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-2 shadow-xs shrink-0">
            <span className="text-[11px] font-bold text-[var(--color-text-secondary)]">Project Scope:</span>
            <select
              value={activeProject || ""}
              onChange={(e) => changeProject(e.target.value || null)}
              className="bg-transparent text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none cursor-pointer max-w-[200px] truncate pr-1"
            >
              <option value="">-- Select a Project --</option>
              {projects.map((proj) => (
                <option key={proj.id} value={proj.id}>
                  {proj.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* ACTIVE PROJECT NOTIFICATION */}
        {currentProject ? (
          <div className="flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-emerald-500/5 border border-emerald-500/20 text-xs">
            <div className="flex items-center gap-2">
              <ShieldCheck size={15} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span className="font-medium text-[var(--color-text-primary)]">
                Selected Project: <strong className="font-bold text-emerald-700 dark:text-emerald-300">{currentProject.name}</strong>
              </span>
              <span className="text-[11px] font-mono text-[var(--color-text-muted)]">
                ({currentProject.project_code || currentProject.id.slice(0, 8)})
              </span>
            </div>
            <Link
              href={`/dashboard/projects/${currentProject.id}`}
              className="text-[11px] font-bold text-emerald-700 dark:text-emerald-400 hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>Inspect Project Workspace</span>
              <ExternalLink size={11} />
            </Link>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-800 dark:text-amber-300">
            <AlertTriangle size={15} className="shrink-0" />
            <span>
              <strong>No Project Selected:</strong> Select a project from the dropdown above to enable project-scoped document and laboratory assay ingestion.
            </span>
          </div>
        )}
      </div>

      {templateError && (
        <div role="alert" className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-xs text-red-600 dark:text-red-400">
          {templateError}
        </div>
      )}

      {currentProject && canReadRegistry(user?.role) && <Link href={`/dashboard/projects/${currentProject.id}?tab=registry`} className="inline-block text-xs underline">Review registry requirements for {currentProject.name}</Link>}

      {/* 📦 THE THREE INGESTION PATHWAYS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* CARD A: PROJECT DOCUMENTS & PDD */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4 hover:border-emerald-500/40 transition-all">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2.5 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
                <FileText size={20} />
              </div>
              <span className="text-[10px] font-bold font-mono uppercase px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[var(--color-text-secondary)]">
                PDF · DOCX · XLSX
              </span>
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-[var(--color-text-primary)]">
                Project Documents & PDD
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
                Upload PDDs, monitoring reports, verification reports, methodology documents, baseline studies, land tenure documents and supporting project files.
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-[var(--color-border)] space-y-2">
            {!activeProject ? (
              <div className="text-[11px] font-medium text-amber-700 dark:text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-lg text-center">
                Select a project first
              </div>
            ) : !canUploadDocuments ? (
              <div className="flex items-center justify-center gap-1.5 text-[11px] font-medium text-[var(--color-text-muted)] bg-slate-100 dark:bg-slate-800 px-3 py-2 rounded-xl">
                <Lock size={12} />
                <span>Upload requires Project Manager / Admin</span>
              </div>
            ) : (
              <button
                onClick={() => setActiveSubView("documents")}
                className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer"
              >
                <Upload size={14} />
                <span>Upload Project Document</span>
              </button>
            )}

            {activeProject && (
              <button
                onClick={() => setActiveSubView("documents")}
                className="w-full py-1.5 text-center text-[11px] font-semibold text-[var(--color-text-secondary)] hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors cursor-pointer"
              >
                Browse Uploaded Documents →
              </button>
            )}
          </div>
        </div>

        {/* CARD B: LABORATORY ASSAYS (SECTOR-AWARE) */}
        {isAgriculture ? (
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4 hover:border-emerald-500/40 transition-all">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="p-2.5 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                  <FlaskConical size={20} />
                </div>
                <span className="text-[10px] font-bold font-mono uppercase px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  CSV · XLSX
                </span>
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-[var(--color-text-primary)]">
                  Laboratory Assays
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
                  Import soil laboratory CSV/XLSX results and validate them against registered physical soil samples.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-[var(--color-border)] space-y-2">
              {!activeProject ? (
                <div className="text-[11px] font-medium text-amber-700 dark:text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-lg text-center">
                  Select an Agriculture project first
                </div>
              ) : !canUploadLab ? (
                <div className="flex items-center justify-center gap-1.5 text-[11px] font-medium text-[var(--color-text-muted)] bg-slate-100 dark:bg-slate-800 px-3 py-2 rounded-xl">
                  <Lock size={12} />
                  <span>Lab import requires Project Manager / Admin</span>
                </div>
              ) : (
                <button
                  onClick={() => setActiveSubView("laboratory")}
                  className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer"
                >
                  <FlaskConical size={14} />
                  <span>Upload Lab Workbook</span>
                </button>
              )}

              {activeProject && (
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={async () => {
                      if (!activeProject) return;
                      setDownloadingTemplate(true);
                      setTemplateError(null);
                      try {
                        await downloadLaboratoryImportTemplate(activeProject, "csv");
                      } catch (err: unknown) {
                        setTemplateError(err instanceof Error ? err.message : "Failed to download laboratory template");
                      } finally {
                        setDownloadingTemplate(false);
                      }
                    }}
                    disabled={downloadingTemplate}
                    data-testid="btn-hub-download-lab-template"
                    className="flex-1 py-2 px-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] hover:bg-[var(--color-surface)] text-[var(--color-text-primary)] font-semibold text-[11px] transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <Download size={13} />
                    <span>{downloadingTemplate ? "Downloading..." : "Download Lab Template"}</span>
                  </button>
                  <button
                    onClick={() => setActiveSubView("laboratory")}
                    className="flex-1 py-2 px-3 text-center text-[11px] font-semibold text-[var(--color-text-secondary)] hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors cursor-pointer border border-transparent hover:border-[var(--color-border)] rounded-xl"
                  >
                    Manage Batches →
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4 opacity-75">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-[var(--color-text-muted)] border border-[var(--color-border)]">
                  <Layers size={20} />
                </div>
                <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                  SECTOR SPECIFIC
                </span>
              </div>
              <div>
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                  Sector Physical Evidence
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
                  Laboratory soil assay imports are configured for the Agriculture & Land Use sector. Switch workspace sector to activate laboratory ingestion.
                </p>
              </div>
            </div>
            <div className="pt-2 border-t border-[var(--color-border)]">
              <span className="text-[11px] font-mono text-[var(--color-text-muted)] block text-center">
                Active: {activeSector.toUpperCase()}
              </span>
            </div>
          </div>
        )}

        {/* CARD C: FIELD PROOF & EVIDENCE */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4 hover:border-emerald-500/40 transition-all">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2.5 rounded-xl bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                <Camera size={20} />
              </div>
              <span className="text-[10px] font-bold font-mono uppercase px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                EXIF · GPS · SHA-256
              </span>
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-[var(--color-text-primary)]">
                Field Proof & Evidence
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
                Upload or capture project field photographs and supporting evidence with cryptographic tamper-evident signatures.
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-[var(--color-border)] space-y-2">
            <Link
              href="/capture"
              className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer text-center"
            >
              <Camera size={14} />
              <span>Open Evidence Capture</span>
            </Link>

            <Link
              href="/dashboard/operations?tab=evidence"
              className="w-full block py-1.5 text-center text-[11px] font-semibold text-[var(--color-text-secondary)] hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors cursor-pointer"
            >
              Open Proof Evidence Vault →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
