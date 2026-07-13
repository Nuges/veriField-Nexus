"use client";

import React, { useState } from 'react';
import { BookOpen, FileText, CheckCircle2, FileWarning, ArrowUpCircle, Trash2 } from 'lucide-react';

interface Framework {
  id: string;
  name: string;
  version: string;
}

export function ComplianceFrameworksModule({ data }: { data: Framework[] }) {
  const [frameworks] = useState(data || []);

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium">Compliance Frameworks</h3>
          <p className="text-sm text-slate-500">Manage rule packages and validation schemas enforced on this jurisdiction.</p>
        </div>
        <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">
          <BookOpen className="h-4 w-4" /> Adopt Framework
        </button>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h4 className="text-sm font-semibold text-slate-500 uppercase">Active Frameworks</h4>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="p-3 font-medium">Framework Name</th>
              <th className="p-3 font-medium">Version</th>
              <th className="p-3 font-medium">Rule Count</th>
              <th className="p-3 font-medium">Health State</th>
              <th className="p-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {frameworks.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center p-8 text-slate-500">
                  <FileWarning className="mx-auto h-8 w-8 text-slate-300 mb-2" />
                  No compliance frameworks adopted. System will not block invalid transactions.
                </td>
              </tr>
            ) : frameworks.map((fw) => (
              <tr key={fw.id} className="hover:bg-slate-50">
                <td className="p-3 font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-500" />
                  {fw.name}
                </td>
                <td className="p-3 font-mono text-xs">v{fw.version}</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 border border-slate-200">42 Rules</span>
                </td>
                <td className="p-3">
                  <span className="flex items-center text-green-600 text-sm">
                    <CheckCircle2 className="h-4 w-4 mr-1" /> Active
                  </span>
                </td>
                <td className="p-3 text-right flex justify-end gap-2">
                  <button className="text-slate-400 hover:text-blue-500" title="Upgrade Version"><ArrowUpCircle className="h-4 w-4" /></button>
                  <button className="text-slate-400 hover:text-red-500" title="Retire"><Trash2 className="h-4 w-4" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
