// =============================================================================
// VeriField Nexus — Agriculture MRV Laboratory Bulk Data Import Console
// =============================================================================
// Comprehensive Bulk Lab Ingestion:
// Template Download -> File Upload -> Automated Column Mapping ->
// Multi-Analyte Scientific Validation & Unit Normalization ->
// Pre-Commit Staged Preview -> Deduplication -> Transactional Commit to Canonical Ledger
// =============================================================================

"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  UploadCloud,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  Database,
  Lock,
  Layers,
  FileText,
  Clock,
  Sparkles,
  ShieldCheck,
  Check,
  Eye,
} from "lucide-react";
import {
  fetchLaboratoryImportBatches,
  fetchLaboratoryImportBatch,
  fetchLaboratoryImportRows,
  uploadLaboratoryBulkFile,
  validateLaboratoryImportBatch,
  commitLaboratoryImportBatch,
  getLaboratoryImportTemplateUrl,
  getLaboratoryImportErrorsUrl,
  fetchSamplingCampaigns,
  type LaboratoryImportBatchItem,
  type LaboratoryImportRowItem,
  type LaboratoryImportValidationResult,
  type SamplingCampaignRecord,
} from "@/lib/api";

interface Props {
  projectId: string;
  onImportSuccess?: () => void;
  isAuditor?: boolean;
  isFieldAgent?: boolean;
}

export default function AgricultureLaboratoryBulkImportView({
  projectId,
  onImportSuccess,
  isAuditor = false,
  isFieldAgent = false,
}: Props) {
  const canUpload = !isAuditor && !isFieldAgent;

  // Data states
  const [batches, setBatches] = useState<LaboratoryImportBatchItem[]>([]);
  const [campaigns, setCampaigns] = useState<SamplingCampaignRecord[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [activeBatch, setActiveBatch] = useState<LaboratoryImportBatchItem | null>(null);
  const [activeRows, setActiveRows] = useState<LaboratoryImportRowItem[]>([]);
  const [rowStatusFilter, setRowStatusFilter] = useState<string>("ALL");

  // Loading and feedback states
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Upload Form states
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [labName, setLabName] = useState("Eurofins Agri Testing");
  const [campaignId, setCampaignId] = useState("");

  // Mapping Form states
  const [mappingConfig, setMappingConfig] = useState<Record<string, string>>({
    sample_code_column: "sample_code",
    analyte_column: "analyte",
    value_column: "raw_value",
    unit_column: "raw_unit",
    depth_from_column: "depth_from_cm",
    depth_to_column: "depth_to_cm",
    analysis_date_column: "analysis_date",
    method_column: "method",
    lab_sample_id_column: "lab_sample_id",
    notes_column: "notes",
  });
  const [importValidOnly, setImportValidOnly] = useState(false);
  const [importAsRevision, setImportAsRevision] = useState(false);

  // Load batches and campaigns
  const loadBatches = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [batchList, campList] = await Promise.all([
        fetchLaboratoryImportBatches(projectId),
        fetchSamplingCampaigns(projectId),
      ]);
      setBatches(batchList);
      setCampaigns(campList);

      if (batchList.length > 0 && !selectedBatchId) {
        setSelectedBatchId(batchList[0].id);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load laboratory import batches.");
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedBatchId]);

  useEffect(() => {
    loadBatches();
  }, [loadBatches]);

  // Load active batch details and rows
  useEffect(() => {
    if (!projectId || !selectedBatchId) {
      setActiveBatch(null);
      setActiveRows([]);
      return;
    }
    let isCancelled = false;

    const loadBatchDetail = async () => {
      try {
        const [b, r] = await Promise.all([
          fetchLaboratoryImportBatch(projectId, selectedBatchId),
          fetchLaboratoryImportRows(projectId, selectedBatchId),
        ]);
        if (!isCancelled) {
          setActiveBatch(b);
          setActiveRows(r);
          if (b?.mapping_config) {
            setMappingConfig((prev) => ({ ...prev, ...b.mapping_config }));
          }
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          console.warn("Failed loading batch detail:", err);
        }
      }
    };

    loadBatchDetail();
    return () => {
      isCancelled = true;
    };
  }, [projectId, selectedBatchId]);

  // Handle File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setErrorMsg(null);
    }
  };

  // Handle Upload
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMsg("Please select a .csv or .xlsx laboratory data file.");
      return;
    }
    setUploading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const newBatch = await uploadLaboratoryBulkFile(
        projectId,
        selectedFile,
        labName.trim() || undefined,
        campaignId.trim() || undefined
      );
      setSuccessMsg(
        `Batch uploaded successfully! Staged ${newBatch.total_rows} rows from '${newBatch.original_filename}'.`
      );
      setSelectedFile(null);
      await loadBatches();
      setSelectedBatchId(newBatch.id);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to upload laboratory file.");
    } finally {
      setUploading(false);
    }
  };

  // Handle Re-Validate
  const handleValidate = async () => {
    if (!activeBatch) return;
    setValidating(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const valRes: LaboratoryImportValidationResult = await validateLaboratoryImportBatch(
        projectId,
        activeBatch.id,
        {
          mapping_config: mappingConfig,
          laboratory_name: activeBatch.laboratory_name,
          sampling_campaign_id: activeBatch.sampling_campaign_id,
        }
      );
      setSuccessMsg(
        `Validation completed: ${valRes.valid_rows} valid, ${valRes.warning_rows} warnings, ${valRes.error_rows} errors.`
      );
      // Reload batch and rows
      const [updatedBatch, updatedRows] = await Promise.all([
        fetchLaboratoryImportBatch(projectId, activeBatch.id),
        fetchLaboratoryImportRows(projectId, activeBatch.id),
      ]);
      setActiveBatch(updatedBatch);
      setActiveRows(updatedRows);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Validation failed.");
    } finally {
      setValidating(false);
    }
  };

  // Handle Commit
  const handleCommit = async () => {
    if (!activeBatch) return;
    setCommitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const commitRes = await commitLaboratoryImportBatch(projectId, activeBatch.id, {
        import_valid_only: importValidOnly,
        laboratory_name: activeBatch.laboratory_name,
        import_as_revision: importAsRevision,
      });
      setSuccessMsg(commitRes.message);
      // Reload batches and active batch
      await loadBatches();
      const updatedBatch = await fetchLaboratoryImportBatch(projectId, activeBatch.id);
      setActiveBatch(updatedBatch);
      if (onImportSuccess) {
        onImportSuccess();
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to commit batch to canonical lab ledger.");
    } finally {
      setCommitting(false);
    }
  };

  // Filtered rows
  const filteredRows = useMemo(() => {
    if (rowStatusFilter === "ALL") return activeRows;
    return activeRows.filter((r) => r.validation_status === rowStatusFilter);
  }, [activeRows, rowStatusFilter]);

  const isCommitted = activeBatch?.status === "IMPORTED" || activeBatch?.status === "PARTIALLY_IMPORTED";

  return (
    <div className="space-y-6" data-testid="laboratory-bulk-import-console">
      {/* Feedback Alerts */}
      {errorMsg && (
        <div
          data-testid="lab-import-error-banner"
          className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-600 dark:text-red-400 flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <AlertCircle size={14} className="shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-xs font-bold ml-2 cursor-pointer">
            ✕
          </button>
        </div>
      )}
      {successMsg && (
        <div
          data-testid="lab-import-success-banner"
          className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-600 dark:text-emerald-400 flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 size={14} className="shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-xs font-bold ml-2 cursor-pointer">
            ✕
          </button>
        </div>
      )}

      {/* Top Action Bar: Template Downloads & Info */}
      <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold text-emerald-600 dark:text-emerald-400 tracking-wider">
              Automated Ingestion Pipeline
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 font-semibold">
              CSV • XLSX
            </span>
          </div>
          <h3 className="text-base font-bold text-[var(--color-text-primary)] mt-0.5 flex items-center gap-2">
            <FileSpreadsheet size={18} className="text-emerald-500" />
            Laboratory Bulk Data Import
          </h3>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            Stage and validate lab assays with automated column mapping, sample code cross-matching, deterministic
            unit normalization (SOC g/kg), and immutable SHA-256 provenance archiving.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <a
            href={getLaboratoryImportTemplateUrl(projectId, "csv")}
            download="verifield_laboratory_import_template.csv"
            data-testid="btn-download-csv-template"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] hover:bg-[var(--color-surface)] text-[var(--color-text-primary)] transition-colors cursor-pointer"
          >
            <Download size={13} />
            <span>CSV Template</span>
          </a>
          <a
            href={getLaboratoryImportTemplateUrl(projectId, "xlsx")}
            download="verifield_laboratory_import_template.xlsx"
            data-testid="btn-download-xlsx-template"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] hover:bg-[var(--color-surface)] text-[var(--color-text-primary)] transition-colors cursor-pointer"
          >
            <Download size={13} />
            <span>Excel (.xlsx) Template</span>
          </a>
        </div>
      </div>

      {/* Grid: Upload Box + Batch Selector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Step 1: Upload Card */}
        <div className="lg:col-span-1 p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] flex items-center gap-1.5">
              <UploadCloud size={14} className="text-emerald-500" />
              1. Upload Lab File
            </h4>
            <span className="text-[10px] text-[var(--color-text-muted)]">Max 50MB</span>
          </div>

          <form onSubmit={handleUpload} className="space-y-3.5 text-xs">
            <div>
              <label className="block text-[var(--color-text-secondary)] font-medium mb-1">
                Data File (.csv, .xlsx) *
              </label>
              <input
                type="file"
                accept=".csv, .xlsx, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, text/csv"
                onChange={handleFileChange}
                disabled={!canUpload || uploading}
                data-testid="input-lab-import-file"
                className="w-full text-xs text-[var(--color-text-secondary)] file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-500/10 file:text-emerald-600 dark:file:text-emerald-400 hover:file:bg-emerald-500/20 cursor-pointer"
              />
              {selectedFile && (
                <div className="mt-1 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium truncate">
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                </div>
              )}
            </div>

            <div>
              <label className="block text-[var(--color-text-secondary)] font-medium mb-1">
                Accredited Testing Laboratory
              </label>
              <input
                type="text"
                value={labName}
                onChange={(e) => setLabName(e.target.value)}
                disabled={!canUpload || uploading}
                placeholder="e.g. Eurofins Agro Testing / SGS Environmental"
                data-testid="input-lab-name"
                className="w-full px-3 py-1.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
              />
            </div>

            <div>
              <label className="block text-[var(--color-text-secondary)] font-medium mb-1">
                Associated Sampling Campaign (Optional)
              </label>
              <select
                value={campaignId}
                onChange={(e) => setCampaignId(e.target.value)}
                disabled={!canUpload || uploading}
                data-testid="select-lab-campaign"
                className="w-full px-3 py-1.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] cursor-pointer"
              >
                <option value="">All Campaigns / Unspecified</option>
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.campaign_code} — {c.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={!canUpload || uploading || !selectedFile}
              data-testid="btn-upload-lab-file"
              className="w-full py-2 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-sm"
            >
              <UploadCloud size={14} className={uploading ? "animate-bounce" : ""} />
              <span>{uploading ? "Ingesting & Hashing..." : "Upload & Stage Assays"}</span>
            </button>
          </form>
        </div>

        {/* Step 2 & History: Batches List */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] flex items-center gap-1.5">
              <Database size={14} className="text-blue-500" />
              Import Batches History ({batches.length})
            </h4>
            <button
              onClick={loadBatches}
              disabled={loading}
              className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
          </div>

          {batches.length === 0 ? (
            <div className="p-8 text-center text-xs text-[var(--color-text-muted)] space-y-1">
              <FileSpreadsheet size={24} className="mx-auto text-[var(--color-text-muted)] opacity-50" />
              <p>No bulk laboratory import batches recorded for this project yet.</p>
              <p className="text-[11px]">Download a template above and upload your laboratory report to begin.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] uppercase font-bold text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                  <tr>
                    <th className="pb-2">Batch / File</th>
                    <th className="pb-2">Laboratory</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2 text-right">Rows</th>
                    <th className="pb-2 text-right">Uploaded</th>
                    <th className="pb-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]">
                  {batches.map((b) => {
                    const isSelected = selectedBatchId === b.id;
                    return (
                      <tr
                        key={b.id}
                        data-testid={`batch-row-${b.id}`}
                        onClick={() => setSelectedBatchId(b.id)}
                        className={`hover:bg-[var(--color-background)] cursor-pointer transition-colors ${
                          isSelected ? "bg-emerald-500/5 font-medium" : ""
                        }`}
                      >
                        <td className="py-2.5 pr-2">
                          <div className="font-semibold text-[var(--color-text-primary)] truncate max-w-[180px]">
                            {b.original_filename}
                          </div>
                          <div className="font-mono text-[10px] text-[var(--color-text-muted)]">
                            {b.file_type} • {(b.file_size_bytes / 1024).toFixed(1)} KB
                          </div>
                        </td>
                        <td className="py-2.5 pr-2 text-[var(--color-text-secondary)]">
                          {b.laboratory_name || "—"}
                        </td>
                        <td className="py-2.5 pr-2">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              b.status === "IMPORTED"
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                : b.status === "PARTIALLY_IMPORTED"
                                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                : b.status === "VALIDATED"
                                ? "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                                : b.status === "VALIDATED_WITH_ERRORS"
                                ? "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                                : "bg-zinc-500/10 text-zinc-500"
                            }`}
                          >
                            {b.status}
                          </span>
                        </td>
                        <td className="py-2.5 pr-2 text-right">
                          <span className="font-mono">{b.total_rows}</span>
                          {b.status === "IMPORTED" ? (
                            <span className="text-[10px] text-emerald-500 ml-1">({b.imported_rows} imp)</span>
                          ) : b.error_rows > 0 ? (
                            <span className="text-[10px] text-red-500 ml-1">({b.error_rows} err)</span>
                          ) : null}
                        </td>
                        <td className="py-2.5 pr-2 text-right text-[11px] text-[var(--color-text-muted)]">
                          {new Date(b.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-2.5 text-right">
                          <button
                            data-testid={`btn-select-batch-${b.id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedBatchId(b.id);
                            }}
                            className={`px-2 py-1 rounded text-[11px] font-semibold border ${
                              isSelected
                                ? "bg-emerald-600 text-white border-emerald-600"
                                : "bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]"
                            }`}
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Selected Batch Details & Processing Pipeline */}
      {activeBatch && (
        <div className="space-y-6 pt-2" data-testid="active-batch-detail-panel">
          {/* Batch Metadata Header */}
          <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[var(--color-text-primary)]">Active Import Batch</span>
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-muted)]">
                  {activeBatch.id}
                </span>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    activeBatch.status === "IMPORTED"
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : activeBatch.status === "PARTIALLY_IMPORTED"
                      ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                      : activeBatch.status === "VALIDATED"
                      ? "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                      : activeBatch.status === "VALIDATED_WITH_ERRORS"
                      ? "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                      : "bg-zinc-500/10 text-zinc-500"
                  }`}
                >
                  {activeBatch.status}
                </span>
              </div>
              <div className="text-xs text-[var(--color-text-secondary)] flex flex-wrap items-center gap-3">
                <span>
                  File: <strong className="text-[var(--color-text-primary)]">{activeBatch.original_filename}</strong>
                </span>
                <span>•</span>
                <span>
                  SHA-256: <strong className="font-mono text-[10px]">{activeBatch.file_sha256.substring(0, 16)}...</strong>
                </span>
                <span>•</span>
                <span>
                  Lab: <strong className="text-[var(--color-text-primary)]">{activeBatch.laboratory_name || "Unspecified"}</strong>
                </span>
              </div>
            </div>

            {/* Error CSV Download button if errors present */}
            {activeBatch.error_rows > 0 && (
              <a
                href={getLaboratoryImportErrorsUrl(projectId, activeBatch.id)}
                download={`lab_import_errors_${activeBatch.id}.csv`}
                data-testid="btn-download-error-csv"
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 transition-colors cursor-pointer shrink-0"
              >
                <Download size={13} />
                <span>Export Errors ({activeBatch.error_rows} rows)</span>
              </a>
            )}
          </div>

          {/* Validation Metrics Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
              <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider">
                Total Staged Rows
              </div>
              <div className="text-xl font-bold font-mono text-[var(--color-text-primary)] mt-1">
                {activeBatch.total_rows}
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-emerald-500/30 bg-emerald-500/5">
              <div className="text-[10px] uppercase font-bold text-emerald-600 dark:text-emerald-400 tracking-wider">
                Valid Assays
              </div>
              <div className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1">
                {activeBatch.valid_rows}
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-amber-500/30 bg-amber-500/5">
              <div className="text-[10px] uppercase font-bold text-amber-600 dark:text-amber-400 tracking-wider">
                Warnings / Supersedes
              </div>
              <div className="text-xl font-bold font-mono text-amber-600 dark:text-amber-400 mt-1">
                {activeBatch.warning_rows}
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-rose-500/30 bg-rose-500/5">
              <div className="text-[10px] uppercase font-bold text-rose-600 dark:text-rose-400 tracking-wider">
                Validation Errors
              </div>
              <div className="text-xl font-bold font-mono text-rose-600 dark:text-rose-400 mt-1">
                {activeBatch.error_rows}
              </div>
            </div>
          </div>

          {/* Step 3: Column Mapping & Validation Configuration */}
          {!isCommitted && (
            <div className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] flex items-center gap-1.5">
                    <Layers size={14} className="text-purple-500" />
                    2. Column Mapping & Parameters
                  </h4>
                  <p className="text-[11px] text-[var(--color-text-secondary)]">
                    Verify header mappings to ensure accurate sample resolution and scientific conversions.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleValidate}
                  disabled={validating}
                  data-testid="btn-revalidate-batch"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white cursor-pointer transition-colors"
                >
                  <RefreshCw size={12} className={validating ? "animate-spin" : ""} />
                  <span>{validating ? "Validating..." : "Re-Validate Staged Assays"}</span>
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">
                    Sample Code Column *
                  </label>
                  <input
                    type="text"
                    value={mappingConfig.sample_code_column || ""}
                    onChange={(e) => setMappingConfig({ ...mappingConfig, sample_code_column: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">Analyte Column *</label>
                  <input
                    type="text"
                    value={mappingConfig.analyte_column || ""}
                    onChange={(e) => setMappingConfig({ ...mappingConfig, analyte_column: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">Value Column *</label>
                  <input
                    type="text"
                    value={mappingConfig.value_column || ""}
                    onChange={(e) => setMappingConfig({ ...mappingConfig, value_column: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">Raw Unit Column *</label>
                  <input
                    type="text"
                    value={mappingConfig.unit_column || ""}
                    onChange={(e) => setMappingConfig({ ...mappingConfig, unit_column: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">Depth From Column</label>
                  <input
                    type="text"
                    value={mappingConfig.depth_from_column || ""}
                    onChange={(e) => setMappingConfig({ ...mappingConfig, depth_from_column: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">Depth To Column</label>
                  <input
                    type="text"
                    value={mappingConfig.depth_to_column || ""}
                    onChange={(e) => setMappingConfig({ ...mappingConfig, depth_to_column: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">Analysis Date Column</label>
                  <input
                    type="text"
                    value={mappingConfig.analysis_date_column || ""}
                    onChange={(e) => setMappingConfig({ ...mappingConfig, analysis_date_column: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">Method Column</label>
                  <input
                    type="text"
                    value={mappingConfig.method_column || ""}
                    onChange={(e) => setMappingConfig({ ...mappingConfig, method_column: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Staged Rows Table & Preview */}
          <div className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] flex items-center gap-1.5">
                  <Eye size={14} className="text-emerald-500" />
                  3. Staged Assays Preview ({filteredRows.length} of {activeRows.length} rows)
                </h4>
                <p className="text-[11px] text-[var(--color-text-secondary)]">
                  Inspect matched physical samples, raw measurement entries, and canonical conversions (g/kg).
                </p>
              </div>

              {/* Status Filter buttons */}
              <div className="flex items-center gap-1 bg-[var(--color-background)] p-1 rounded-lg border border-[var(--color-border)] text-[11px]">
                {["ALL", "VALID", "WARNING", "ERROR"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setRowStatusFilter(st)}
                    className={`px-2 py-0.5 rounded font-semibold transition-colors cursor-pointer ${
                      rowStatusFilter === st
                        ? "bg-[var(--color-surface)] text-[var(--color-text-primary)] shadow-xs"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                  <tr>
                    <th className="pb-2">Row #</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Matched Sample</th>
                    <th className="pb-2">Analyte</th>
                    <th className="pb-2 text-right">Raw Measurement</th>
                    <th className="pb-2 text-right">Normalized (Canonical)</th>
                    <th className="pb-2">Validation Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)] font-sans">
                  {filteredRows.slice(0, 30).map((r) => {
                    const isError = r.validation_status === "ERROR";
                    const isWarning = r.validation_status === "WARNING";
                    const isValid = r.validation_status === "VALID";

                    return (
                      <tr
                        key={r.id}
                        data-testid={`row-${r.source_row_number}`}
                        className={`hover:bg-[var(--color-background)] ${
                          isError ? "bg-red-500/5" : isWarning ? "bg-amber-500/5" : ""
                        }`}
                      >
                        <td className="py-2.5 font-mono text-[11px] text-[var(--color-text-muted)]">
                          {r.source_row_number}
                        </td>
                        <td className="py-2.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              isValid
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                : isWarning
                                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                            }`}
                          >
                            {r.validation_status}
                          </span>
                        </td>
                        <td className="py-2.5">
                          {r.matched_sample_code ? (
                            <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                              {r.matched_sample_code}
                            </span>
                          ) : (
                            <span className="font-mono text-zinc-500">
                              {r.raw_row_payload?.sample_code || "—"}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 font-medium">
                          {r.canonical_analyte || r.raw_row_payload?.analyte || "—"}
                        </td>
                        <td className="py-2.5 text-right font-mono">
                          {r.raw_value != null ? (
                            <span>
                              {r.raw_value} <span className="text-[10px] text-zinc-500">{r.raw_unit}</span>
                            </span>
                          ) : (
                            <span className="text-zinc-500">—</span>
                          )}
                        </td>
                        <td className="py-2.5 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                          {r.normalized_value != null ? (
                            <span>
                              {r.normalized_value}{" "}
                              <span className="text-[10px] font-normal">{r.normalized_unit}</span>
                            </span>
                          ) : (
                            <span className="text-zinc-500">—</span>
                          )}
                        </td>
                        <td className="py-2.5 max-w-xs truncate text-[11px]">
                          {r.validation_messages && r.validation_messages.length > 0 ? (
                            <div className="space-y-0.5">
                              {r.validation_messages.map((m, mIdx) => (
                                <div
                                  key={mIdx}
                                  className={m.severity === "ERROR" ? "text-rose-500 font-medium" : "text-amber-500"}
                                >
                                  {m.message}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span className="text-emerald-500 text-[10px]">Passed checks</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredRows.length > 30 && (
                <div className="p-2 text-center text-[11px] text-[var(--color-text-muted)] bg-[var(--color-background)] rounded mt-2">
                  Showing first 30 rows of {filteredRows.length} total staged rows.
                </div>
              )}
            </div>
          </div>

          {/* Step 5: Transactional Commit to Canonical Ledger */}
          <div className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-emerald-500" />
                4. Commit to Canonical Laboratory Ledger
              </h4>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                {isCommitted
                  ? "This batch has already been transactionally committed into official LaboratoryAnalysis and LaboratoryResult records."
                  : "Atomically injects validated assays into official LaboratoryAnalysis and LaboratoryResult records, advances sample status to ANALYZED, and seals batch provenance."}
              </p>
            </div>

            {!isCommitted && canUpload && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 shrink-0">
                <label className="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={importAsRevision}
                    onChange={(e) => setImportAsRevision(e.target.checked)}
                    data-testid="checkbox-import-as-revision"
                    className="rounded border-[var(--color-border)] text-amber-600 focus:ring-amber-500"
                  />
                  <span>Confirm overwrite revisions</span>
                </label>

                {activeBatch.error_rows > 0 && (
                  <label className="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={importValidOnly}
                      onChange={(e) => setImportValidOnly(e.target.checked)}
                      data-testid="checkbox-import-valid-only"
                      className="rounded border-[var(--color-border)] text-emerald-600 focus:ring-emerald-500"
                    />
                    <span>Import valid rows only (skip {activeBatch.error_rows} errors)</span>
                  </label>
                )}

                <button
                  type="button"
                  onClick={handleCommit}
                  disabled={committing || (activeBatch.error_rows > 0 && !importValidOnly) || activeBatch.valid_rows === 0}
                  data-testid="btn-commit-batch"
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-semibold text-xs flex items-center gap-2 transition-colors cursor-pointer shadow-sm"
                >
                  <Check size={14} className={committing ? "animate-spin" : ""} />
                  <span>{committing ? "Committing..." : "Commit Assays to Ledger"}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
