"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Download, RefreshCw } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchRegistryReadiness, fetchRegistryDocumentMatrix, downloadRegistryPackage, downloadRegistryDocument } from "@/lib/api";
import { canReadRegistry, registryExportBlockReason, registryPreparationLabel, type RegistryDocumentMatrix, type RegistryReadiness } from "@/lib/registryWorkflow";
import { resolveProjectMethodology } from "@/lib/projectMethodology";
import { isRouteAuthorized } from "@/lib/roles";

export default function RegistryModule({ projectId, sectorCode }: { sectorCode?: string; projectId?: string }) {
  const { user, projects } = useWorkspace();
  const project = projects.find((item) => item.id === projectId);
  const allowed = canReadRegistry(user?.role);
  const [standard, setStandard] = useState("VERRA");
  const [snapshot, setSnapshot] = useState<{ key: string; readiness: RegistryReadiness; matrix: RegistryDocumentMatrix } | null>(null);
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const [feedback, setFeedback] = useState<{ key: string; error?: string; success?: string } | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const key = `${projectId || ""}:${standard}`;
  const current = snapshot?.key === key ? snapshot : null;
  const readiness = current?.readiness || null;
  const currentFeedback = feedback?.key === key ? feedback : null;
  const busy = busyKey === key;

  useEffect(() => {
    let cancelled = false;
    if (!project || !allowed) return;
    setLoading(true); setSnapshot(null); setFeedback(null);
    Promise.all([fetchRegistryReadiness(project.id, standard), fetchRegistryDocumentMatrix()])
      .then(([result, matrix]) => {
        if (cancelled) return;
        if (result.project_id !== project.id || result.target_standard !== standard) throw new Error("Readiness does not match the selected project and registry.");
        setSnapshot({ key, readiness: result, matrix });
      })
      .catch((error: unknown) => { if (!cancelled) setFeedback({ key, error: error instanceof Error ? error.message : "Readiness could not be loaded." }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [project?.id, standard, allowed, revision, key]);

  if (!allowed) return <div role="status" className="p-5 rounded-xl border border-[var(--color-border)] text-sm">Your role does not have registry-read access. Use your authorized project workspace to review evidence.</div>;
  if (!project) return <div role="status" className="p-5 rounded-xl border border-[var(--color-border)] text-sm">Select an authorized project to review its registry requirements.</div>;
  const blocked = registryExportBlockReason(project, readiness, standard, sectorCode);
  const documents = readiness?.document_readiness || [];
  const authorityId = standard === "VERRA" ? "VERRA_VCS" : "GOLD_STANDARD";
  const authority = current?.matrix.authorities?.find((item) => item.id === authorityId);

  async function download(documentId?: string, format?: "pdf" | "docx" | "json") {
    if (!project || blocked || busy) return;
    setBusyKey(key); setFeedback(null);
    try {
      if (documentId && format) await downloadRegistryDocument(standard, project.id, documentId, format);
      else await downloadRegistryPackage(standard, project.id);
      setFeedback({ key, success: documentId ? "Review document downloaded." : "Export Available — review package downloaded. No external submission has been made." });
    } catch (error) { setFeedback({ key, error: error instanceof Error ? error.message : "Download failed." }); }
    finally { setBusyKey((value) => value === key ? null : value); }
  }

  return <section aria-label="Registry preparation" className="space-y-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-5">
    <div className="flex flex-wrap justify-between gap-3">
      <div><h2 className="text-base font-semibold">Registry Readiness</h2><p className="text-xs text-[var(--color-text-secondary)] mt-1">{project.name} · {resolveProjectMethodology(project).code}</p></div>
      <label className="text-xs flex items-center gap-2">Registry<select aria-label="Target registry" value={standard} onChange={(event) => setStandard(event.target.value)} className="p-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-background)]"><option value="VERRA">Verra</option><option value="GOLD_STANDARD">Gold Standard</option></select></label>
    </div>
    <p className="text-xs text-[var(--color-text-secondary)]">Internal preparation only. Requirements and generated drafts do not establish external submission, acceptance, verification or credit issuance.</p>
    <div className="flex flex-wrap items-center gap-3 text-xs">
      <span data-testid="registry-preparation-state" className="px-3 py-1 rounded-lg border border-[var(--color-border)]">{loading ? "Loading requirements…" : registryPreparationLabel(readiness)}</span>
      {readiness?.evaluated_at && <span>Assessed: {new Date(readiness.evaluated_at).toLocaleString()}</span>}
      <button type="button" onClick={() => setRevision((value) => value + 1)} disabled={loading} className="flex items-center gap-1 disabled:opacity-50"><RefreshCw size={13} />Refresh</button>
    </div>
    {currentFeedback?.error && <p role="alert" className="text-xs text-red-600 dark:text-red-400">{currentFeedback.error}</p>}
    {currentFeedback?.success && <p role="status" className="text-xs text-emerald-700 dark:text-emerald-300">{currentFeedback.success}</p>}
    {blocked && <p className="text-xs p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">{blocked}</p>}
    {readiness && <div className="space-y-4">
      <div><h3 className="text-sm font-semibold">Missing requirements</h3><ul className="list-disc pl-5 text-xs space-y-1 mt-2">{[...(readiness.blocking_items || []), ...(readiness.missing_requirements || [])].map((item, index) => <li key={`${index}:${item}`}>{item.replace(/_/g, " ")}</li>)}</ul>
        {!readiness.blocking_items?.length && !readiness.missing_requirements?.length && <p className="text-xs mt-2">No missing requirements reported by the backend assessment.</p>}
      </div>
      <div className="overflow-x-auto"><h3 className="text-sm font-semibold mb-2">Documents for review</h3><p className="text-xs text-[var(--color-text-secondary)] mb-2">{authority?.name || standard} · Requirement catalog version {current?.matrix.version || "not provided"}. Document assessments describe internal completeness.</p>
        <table className="w-full text-xs text-left"><thead><tr className="border-b border-[var(--color-border)]"><th className="p-2">Requirement</th><th className="p-2">Assessment</th><th className="p-2">Review draft</th></tr></thead><tbody>
          {documents.map((document) => <tr key={document.document_id} className="border-b border-[var(--color-border)] align-top">
            <td className="p-2">{document.official_name || document.nexus_name || document.document_id}<div className="text-[var(--color-text-secondary)] mt-1">{document.mandatory ? "Required" : "Conditional"} · {document.document_class?.replace(/_/g, " ")}</div></td>
            <td className="p-2">{document.completeness_status || "Not assessed"}{document.blocking_requirements?.map((item) => <div key={item} className="mt-1">{item.replace(/_/g, " ")}</div>)}</td>
            <td className="p-2">{document.nexus_generated && !["OFFICIAL_AUTHORITY_RECORD", "OFFICIAL_AUTHORITY_FORM"].includes(document.document_class || "")
              ? <div className="flex gap-2">{(document.supported_formats || []).filter((format) => ["PDF", "DOCX", "JSON"].includes(format.toUpperCase())).map((format) => <button key={format} type="button" disabled={!!blocked || busy || loading} onClick={() => download(document.document_id, format.toLowerCase() as "pdf" | "docx" | "json")} className="underline disabled:opacity-40">{format}</button>)}</div>
              : "Upload an independently obtained record through Project Documents."}</td>
          </tr>)}
        </tbody></table>
        {!documents.length && <p className="text-xs mt-2">No document-level assessment was returned. No completeness is inferred.</p>}
      </div>
    </div>}
    <div className="flex flex-wrap gap-3 text-xs border-t border-[var(--color-border)] pt-3">
      <Link href={`/dashboard/projects/${project.id}?tab=documents`} className="underline">Project Documents</Link>
      {/agri|land/i.test(project.sector || sectorCode || "") && <Link href={`/dashboard/projects/${project.id}?tab=laboratory`} className="underline">Laboratory Results</Link>}
      {isRouteAuthorized("/dashboard/verifications", user?.role) && <Link href={`/dashboard/projects/${project.id}?tab=verification`} className="underline">Verification</Link>}
      <button type="button" onClick={() => download()} disabled={!!blocked || busy || loading} data-testid="registry-download-package" className="flex items-center gap-1 px-3 py-2 rounded-lg border border-[var(--color-border)] disabled:opacity-40"><Download size={13} />{busy ? "Downloading…" : "Download Review Package"}</button>
    </div>
  </section>;
}
