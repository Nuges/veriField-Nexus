"use client";

import React, { useState, useEffect } from "react";
import {
  FileText,
  Upload,
  Download,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
  FileCheck,
  Eye,
  RefreshCw,
  X,
  FileCode,
  FileSpreadsheet,
  AlertOctagon,
  Sparkles,
} from "lucide-react";
import {
  fetchProjectDocuments,
  uploadProjectDocument,
  downloadDocument,
  generateAndDownloadReport,
  fetchRegistryPackage,
  downloadArticle6PackageZip,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

interface ProjectDocumentsModuleProps {
  projectId: string;
  projectName?: string;
  organizationId?: string;
  sectorName?: string;
  methodologyName?: string;
}

export const ProjectDocumentsModule: React.FC<ProjectDocumentsModuleProps> = ({
  projectId,
  projectName = "Climate Project",
  organizationId,
  sectorName = "Clean Sector",
  methodologyName = "Standard Methodology",
}) => {
  const { user } = useWorkspace();
  const effectiveOrgId = organizationId || user?.organization_id || undefined;

  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedDocForBreakdown, setSelectedDocForBreakdown] = useState<any | null>(null);
  const [registryPackageModalOpen, setRegistryPackageModalOpen] = useState(false);
  const [registryPackageData, setRegistryPackageData] = useState<any | null>(null);
  const [loadingPackage, setLoadingPackage] = useState(false);

  // Upload Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState("PDD");
  const [customTitle, setCustomTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [generatingReport, setGeneratingReport] = useState(false);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const data = await fetchProjectDocuments(projectId);
      setDocuments(data || []);
    } catch (err) {
      console.error("Failed to load project documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) {
      loadDocs();
    }
  }, [projectId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      if (!customTitle) {
        setCustomTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setUploadError("");
    setUploadStage("Validating Magic Bytes & Security Header...");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("document_type", docType);
      if (customTitle) formData.append("title", customTitle);

      setUploadStage("Uploading & Parsing Document Structure...");
      const result = await uploadProjectDocument(projectId, formData);

      setUploadStage("Reconciling MRV Invariants & Indexing Knowledge...");
      await loadDocs();
      setUploadModalOpen(false);
      setSelectedFile(null);
      setCustomTitle("");
    } catch (err: any) {
      setUploadError(err.message || "Document upload failed");
    } finally {
      setUploading(false);
      setUploadStage("");
    }
  };

  const handleDownload = async (doc: any) => {
    try {
      await downloadDocument(doc.id, doc.original_filename);
    } catch (err: any) {
      alert(err.message || "Failed to download document.");
    }
  };

  const handleGenerateReport = async () => {
    const orgIdToUse = effectiveOrgId;
    if (!orgIdToUse) {
      alert("Organization context is required to generate report. Please ensure your user account is assigned to an active organization.");
      return;
    }
    setGeneratingReport(true);
    try {
      await generateAndDownloadReport(orgIdToUse, projectId, `${projectName} MRV Carbon Ledger Certificate`);
    } catch (err: any) {
      alert(err.message || "Failed to generate and download MRV report.");
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleInspectRegistryPackage = async (registry: string) => {
    setLoadingPackage(true);
    setRegistryPackageModalOpen(true);
    setRegistryPackageData(null);
    try {
      const data = await fetchRegistryPackage(registry, projectId);
      setRegistryPackageData(data);
    } catch (err: any) {
      alert(err.message || "Failed to build registry package.");
      setRegistryPackageModalOpen(false);
    } finally {
      setLoadingPackage(false);
    }
  };

  const getDocIcon = (type: string) => {
    switch (type) {
      case "PDD":
        return <FileCheck className="w-5 h-5 text-emerald-600" />;
      case "MONITORING_REPORT":
      case "VERIFICATION_REPORT":
        return <Layers className="w-5 h-5 text-blue-600" />;
      case "METHODOLOGY":
        return <FileCode className="w-5 h-5 text-purple-600" />;
      default:
        return <FileText className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PROCESSED":
      case "VERIFIED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5" /> Reconciled
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5" /> Review Flags
          </span>
        );
      case "OCR_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
            <Clock className="w-3.5 h-3.5" /> Scanned PDF (OCR)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-gradient-to-r from-emerald-900/10 via-emerald-800/5 to-transparent border border-emerald-500/20">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
            Project Documentation & Methodology Ingestion
          </h3>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
            Context: <span className="font-medium text-emerald-700 dark:text-emerald-400">{projectName}</span> · Sector: {sectorName} · Methodology: {methodologyName}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => handleInspectRegistryPackage("VERRA")}
            className="px-3 py-1.5 text-xs font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 transition"
          >
            Export Verra Bundle
          </button>
          <button
            onClick={() => handleInspectRegistryPackage("GOLD_STANDARD")}
            className="px-3 py-1.5 text-xs font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 transition"
          >
            Export Gold Standard
          </button>
          <button
            onClick={handleGenerateReport}
            disabled={generatingReport}
            className="px-3 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            {generatingReport ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
            Generate MRV PDF
          </button>
          <button
            onClick={() => setUploadModalOpen(true)}
            className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition flex items-center gap-1.5 shadow-sm"
          >
            <Upload className="w-3.5 h-3.5" />
            Ingest Document
          </button>
        </div>
      </div>

      {/* Documents Table */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-900 shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-500 flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-emerald-600" />
            Loading project documentation...
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 mx-auto text-gray-400 mb-3 stroke-[1.5]" />
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">No project documents uploaded yet</h4>
            <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1 mb-4">
              Upload PDDs, monitoring reports, or baseline methodologies to extract facts and verify reconciliation against registry standards.
            </p>
            <button
              onClick={() => setUploadModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition shadow-sm"
            >
              <Upload className="w-3.5 h-3.5" /> Upload Document
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 dark:bg-gray-800/60 text-gray-500 border-b border-gray-200 dark:border-gray-800 font-medium">
                <tr>
                  <th className="py-3 px-4">Document Title</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Trust Score</th>
                  <th className="py-3 px-4">SHA-256 Digest</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50/70 dark:hover:bg-gray-800/40 transition">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        {getDocIcon(doc.document_type)}
                        <div>
                          <p className="font-medium text-gray-900 dark:text-gray-100">{doc.title}</p>
                          <p className="text-[11px] text-gray-500">{doc.original_filename} · {(doc.file_size / 1024).toFixed(0)} KB</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 font-mono text-[11px] text-gray-700 dark:text-gray-300">
                        {doc.document_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-gray-600 dark:text-gray-400">
                      v{doc.version}
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(doc.status)}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => setSelectedDocForBreakdown(doc)}
                        className={`inline-flex items-center gap-1 font-bold px-2 py-0.5 rounded text-xs transition ${
                          doc.trust_score >= 90
                            ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                            : doc.trust_score >= 70
                            ? "bg-amber-50 text-amber-700 hover:bg-amber-100"
                            : "bg-red-50 text-red-700 hover:bg-red-100"
                        }`}
                      >
                        {doc.trust_score?.toFixed(1) || "100.0"}%
                        <Eye className="w-3 h-3 ml-0.5 opacity-60" />
                      </button>
                    </td>
                    <td className="py-3 px-4 font-mono text-[10px] text-gray-500">
                      {doc.sha256 ? `${doc.sha256.slice(0, 10)}...${doc.sha256.slice(-6)}` : "—"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDownload(doc)}
                        className="p-1 text-gray-500 hover:text-emerald-600 transition"
                        title="Download Physical Document"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
              <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <Upload className="w-5 h-5 text-emerald-600" />
                Ingest Supporting Document / PDD
              </h4>
              <button onClick={() => setUploadModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Document Classification
                </label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="PDD">Project Design Document (PDD)</option>
                  <option value="MONITORING_REPORT">Monitoring Report</option>
                  <option value="VALIDATION_REPORT">Validation Report</option>
                  <option value="VERIFICATION_REPORT">Verification Report</option>
                  <option value="METHODOLOGY">Methodology / Standard Specs</option>
                  <option value="STAKEHOLDER_DOCUMENT">Stakeholder Consultation</option>
                  <option value="LEGAL_DOCUMENT">Land Tenure / Legal Agreement</option>
                  <option value="CALIBRATION_DOCUMENT">Hardware Calibration Certificate</option>
                  <option value="MRV_SUPPORTING_DOCUMENT">MRV Supporting Calculation</option>
                  <option value="OTHER_SUPPORTING_DOCUMENT">Other Supporting Document</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Document Title (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Kenya Clean Stoves PDD v2.1"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Select Document File (.pdf, .docx, .xlsx, .csv, .txt)
                </label>
                <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-5 text-center hover:border-emerald-500 transition">
                  <input
                    type="file"
                    accept=".pdf,.docx,.xlsx,.csv,.txt"
                    onChange={handleFileChange}
                    className="hidden"
                    id="doc-file-upload"
                  />
                  <label htmlFor="doc-file-upload" className="cursor-pointer space-y-1 block">
                    <FileText className="w-8 h-8 mx-auto text-emerald-600 mb-1" />
                    <p className="text-xs font-semibold text-gray-800 dark:text-gray-200">
                      {selectedFile ? selectedFile.name : "Click to choose file or drag & drop"}
                    </p>
                    <p className="text-[11px] text-gray-500">
                      Max file size 50 MB. Validates magic bytes & SHA-256 hash.
                    </p>
                  </label>
                </div>
              </div>

              {uploadStage && (
                <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 rounded-lg text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                  {uploadStage}
                </div>
              )}

              {uploadError && (
                <div className="p-3 bg-red-50 dark:bg-red-950/40 rounded-lg text-xs text-red-800 dark:text-red-300 flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-red-600 flex-shrink-0" />
                  {uploadError}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedFile || uploading}
                  className="px-4 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition shadow-sm disabled:opacity-50"
                >
                  {uploading ? "Ingesting..." : "Ingest & Reconcile"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Trust Breakdown Modal */}
      {selectedDocForBreakdown && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
              <div>
                <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  Document Trust & MRV Reconciliation Audit
                </h4>
                <p className="text-xs text-gray-500 mt-0.5">{selectedDocForBreakdown.title} (v{selectedDocForBreakdown.version})</p>
              </div>
              <button onClick={() => setSelectedDocForBreakdown(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Score Pill */}
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-gray-200 dark:border-gray-700">
              <div>
                <p className="text-xs text-gray-500 uppercase font-semibold">Integrity Trust Score</p>
                <h3 className="text-2xl font-black text-gray-900 dark:text-gray-100 mt-0.5">
                  {selectedDocForBreakdown.trust_score?.toFixed(1)}%
                </h3>
              </div>
              <div>
                {getStatusBadge(selectedDocForBreakdown.status)}
              </div>
            </div>

            {/* Reconciliation Check Points */}
            <div className="space-y-2">
              <h5 className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                Reconciliation Audit Checks
              </h5>
              {selectedDocForBreakdown.trust_breakdown?.reasons?.map((item: any, idx: number) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
                    item.status === "PASS"
                      ? "bg-emerald-50/50 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/40 text-emerald-900 dark:text-emerald-300"
                      : item.status === "WARN"
                      ? "bg-amber-50/50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900/40 text-amber-900 dark:text-amber-300"
                      : "bg-red-50/50 border-red-200 dark:bg-red-950/20 dark:border-red-900/40 text-red-900 dark:text-red-300"
                  }`}
                >
                  {item.status === "PASS" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  ) : item.status === "WARN" ? (
                    <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertOctagon className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <span className="font-semibold">{item.label}: </span>
                    <span>{item.message}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Extracted Structured PDD Facts */}
            {selectedDocForBreakdown.extracted_data?.fields && (
              <div className="space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                <h5 className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                  Extracted PDD Metadata
                </h5>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(selectedDocForBreakdown.extracted_data.fields).map(([k, v]: [string, any]) => (
                    <div key={k} className="p-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                      <p className="text-[10px] text-gray-500 uppercase font-semibold">{k.replace(/_/g, " ")}</p>
                      <p className="font-medium text-gray-900 dark:text-gray-100 mt-0.5">
                        {v?.value ? String(v.value) : <span className="text-gray-400 italic">Unresolved</span>}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Registry Package Inspection Modal */}
      {registryPackageModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
              <div>
                <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-blue-600" />
                  Registry Submission Package Manifest
                </h4>
                <p className="text-xs text-gray-500 mt-0.5">Live Verifiable MRV Submission Bundle</p>
              </div>
              <button onClick={() => setRegistryPackageModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingPackage ? (
              <div className="p-12 text-center text-sm text-gray-500 flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                Compiling submission package...
              </div>
            ) : registryPackageData ? (
              <div className="space-y-4 text-xs">
                {/* Readiness Matrix */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/40 rounded-lg border border-emerald-200 dark:border-emerald-900 text-center">
                    <p className="text-[10px] text-emerald-800 dark:text-emerald-300 uppercase font-semibold">Data Manifest</p>
                    <p className="font-bold text-emerald-900 dark:text-emerald-200 mt-0.5">{registryPackageData.readiness_matrix?.data_manifest}</p>
                  </div>
                  <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/40 rounded-lg border border-emerald-200 dark:border-emerald-900 text-center">
                    <p className="text-[10px] text-emerald-800 dark:text-emerald-300 uppercase font-semibold">Doc Package</p>
                    <p className="font-bold text-emerald-900 dark:text-emerald-200 mt-0.5">{registryPackageData.readiness_matrix?.document_package}</p>
                  </div>
                  <div className="p-2.5 bg-blue-50 dark:bg-blue-950/40 rounded-lg border border-blue-200 dark:border-blue-900 text-center col-span-2">
                    <p className="text-[10px] text-blue-800 dark:text-blue-300 uppercase font-semibold">External Gateway Status</p>
                    <p className="font-semibold text-blue-900 dark:text-blue-200 mt-0.5 text-[11px] truncate">
                      {registryPackageData.readiness_matrix?.external_submission}
                    </p>
                  </div>
                </div>

                {/* Quantification Summary */}
                <div className="p-3 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-gray-200 dark:border-gray-700 flex items-center justify-between">
                  <div>
                    <span className="text-gray-500 font-medium">Verified Reductions: </span>
                    <span className="font-bold text-emerald-600 text-sm">{registryPackageData.mrv_quantification?.total_reductions_tco2e} tCO₂e</span>
                  </div>
                  <div>
                    <span className="text-gray-500 font-medium">Verified Assets: </span>
                    <span className="font-bold text-gray-900 dark:text-gray-100">{registryPackageData.mrv_quantification?.total_verified_assets} units</span>
                  </div>
                  <div>
                    <span className="text-gray-500 font-medium">Package Hash: </span>
                    <span className="font-mono text-[10px] text-gray-600 dark:text-gray-400">{registryPackageData.package_hash?.slice(0, 10)}...</span>
                  </div>
                </div>

                {/* Raw JSON Preview */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[11px] font-semibold text-gray-700 dark:text-gray-300">Authoritative Submission Documents</p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={async () => {
                          try {
                            const std = registryPackageData.registry_standard || "VERRA";
                            await downloadArticle6PackageZip(std, projectId);
                          } catch (err: any) {
                            alert(err.message || "Failed to download ZIP package.");
                          }
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition shadow-sm"
                      >
                        <Download className="w-3 h-3" /> Download Certified ZIP (PDF + DOCX + CSV)
                      </button>
                      <button
                        onClick={() => {
                          const blob = new Blob([JSON.stringify(registryPackageData, null, 2)], { type: "application/json" });
                          const url = window.URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = `${registryPackageData.package_id || "registry_package"}.json`;
                          document.body.appendChild(a);
                          a.click();
                          a.remove();
                          window.URL.revokeObjectURL(url);
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-md transition"
                      >
                        <Download className="w-3 h-3" /> JSON Manifest
                      </button>
                    </div>
                  </div>
                  <pre className="p-3 bg-gray-950 text-emerald-400 rounded-xl text-[10px] overflow-x-auto max-h-60 font-mono">
                    {JSON.stringify(registryPackageData, null, 2)}
                  </pre>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
