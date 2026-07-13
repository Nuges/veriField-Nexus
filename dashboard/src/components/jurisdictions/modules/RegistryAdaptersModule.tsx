"use client";

import React, { useState } from 'react';
import { Link2, Unlink, RefreshCw, Activity, Settings2 } from 'lucide-react';

interface Registry {
  id: string;
  name: string;
  type: string;
  status: string;
}

export function RegistryAdaptersModule({ data }: { data: Registry[] }) {
  const [registries, setRegistries] = useState(data || []);

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium">Registry Connections</h3>
          <p className="text-sm text-slate-500">Manage synchronisation with external registries.</p>
        </div>
        <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">
          <Link2 className="h-4 w-4" /> Connect Registry
        </button>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h4 className="text-sm font-semibold text-slate-500 uppercase">Active Connections</h4>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="p-3 font-medium">Registry Name</th>
              <th className="p-3 font-medium">Adapter Protocol</th>
              <th className="p-3 font-medium">Sync Status</th>
              <th className="p-3 font-medium">Last Synced</th>
              <th className="p-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {registries.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center p-8 text-slate-500">
                  <Unlink className="mx-auto h-8 w-8 text-slate-300 mb-2" />
                  No registries connected.
                </td>
              </tr>
            ) : registries.map((reg) => (
              <tr key={reg.id} className="hover:bg-slate-50">
                <td className="p-3 font-medium flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${reg.status === 'CONNECTED' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  {reg.name}
                </td>
                <td className="p-3 font-mono text-xs">{reg.type}</td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${reg.status === 'CONNECTED' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-700'}`}>
                    {reg.status}
                  </span>
                </td>
                <td className="p-3 text-xs text-slate-500">2 mins ago</td>
                <td className="p-3 text-right flex justify-end gap-2">
                  <button className="text-slate-400 hover:text-blue-500" title="Force Sync"><RefreshCw className="h-4 w-4" /></button>
                  <button className="text-slate-400 hover:text-slate-700" title="Logs"><Activity className="h-4 w-4" /></button>
                  <button className="text-slate-400 hover:text-slate-700" title="Settings"><Settings2 className="h-4 w-4" /></button>
                  <button className="text-slate-400 hover:text-red-500" title="Disconnect"><Unlink className="h-4 w-4" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
