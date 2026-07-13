// =============================================================================
// VeriField Nexus — Universal UI Components (Level 5 CIOS)
// =============================================================================
// Central export for all dynamic, metadata-driven UI components.
// These components read from the backend UI config instead of hardcoding layout.
// =============================================================================

"use client";

import React from "react";
import { Loader2 } from "lucide-react";

export function DynamicWorkspace({ children }: { children: React.ReactNode }) {
  return <div className="dynamic-workspace">{children}</div>;
}

export function DynamicDashboard({ title }: { title: string }) {
  return (
    <div className="p-6 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl">
      <h2 className="text-xl font-bold">{title}</h2>
      <p className="text-[var(--color-text-secondary)] mt-2">Dynamic Dashboard Content</p>
    </div>
  );
}

export function DynamicGrid({ data, columns }: { data: any[], columns: any[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-[var(--color-surface-hover)]">
            {columns.map((c, i) => <th key={i} className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase">{c.header}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border)] bg-[var(--color-surface)]">
          {data.map((row, i) => (
            <tr key={i}>
              {columns.map((c, j) => <td key={j} className="p-4 text-sm">{row[c.accessor]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DynamicTree() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Tree View (Stub)</div>;
}

export function DynamicTimeline() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Timeline View (Stub)</div>;
}

export function DynamicForm({ schema, onSubmit }: { schema: any, onSubmit: (data: any) => void }) {
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); onSubmit({}); }}>
      <div className="p-4 border border-[var(--color-border)] rounded-xl bg-[var(--color-surface)]">
        <p className="text-sm text-[var(--color-text-secondary)] mb-4">Dynamically generated form from metadata schema</p>
        <button type="submit" className="px-4 py-2 bg-[#00B47A] text-black font-semibold rounded-lg text-sm">
          Submit
        </button>
      </div>
    </form>
  );
}

export function DynamicSchemaRenderer() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Schema Renderer (Stub)</div>;
}

export function DynamicWorkflow() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Workflow Engine (Stub)</div>;
}

export function DynamicApprovalConsole() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Approval Console (Stub)</div>;
}

export function DynamicTelemetryConsole() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Telemetry Feed (Stub)</div>;
}

export function DynamicHardwareConsole() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Hardware Status (Stub)</div>;
}

export function DynamicComplianceViewer() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Compliance Viewer (Stub)</div>;
}

export function DynamicRegistryViewer() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Registry Viewer (Stub)</div>;
}

export function DynamicAuditViewer() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Audit Log (Stub)</div>;
}

export function DynamicEvidenceViewer() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Evidence Vault (Stub)</div>;
}

export function DynamicSearch() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Global Search (Stub)</div>;
}

export function DynamicNotificationCenter() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Notifications (Stub)</div>;
}

export function DynamicCommandPalette() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Command Palette (Stub)</div>;
}

export function DynamicReportBuilder() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Report Builder (Stub)</div>;
}

export function DynamicDocumentViewer() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Document Viewer (Stub)</div>;
}

export function DynamicMediaViewer() {
  return <div className="p-4 text-[var(--color-text-secondary)] border rounded-xl">Media Gallery (Stub)</div>;
}
