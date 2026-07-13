"use client";

import React, { useState } from 'react';
import { PlusCircle, MoreHorizontal, ShieldCheck, Search, Download, Trash2, Power } from 'lucide-react';

interface VVB {
  id: string;
  name: string;
  accreditation: string;
  scopes: string[];
  status: string;
}

export function ValidationBodiesModule({ data }: { data: VVB[] }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [vvbs, setVvbs] = useState(data || []);

  const filteredVvbs = vvbs.filter(v => 
    v.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    v.accreditation.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const suspendVvb = (id: string) => {
    setVvbs(vvbs.map(v => v.id === id ? { ...v, status: 'SUSPENDED' } : v));
  };

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium">Validation & Verification Bodies</h3>
          <p className="text-sm text-slate-500">Manage accredited auditors for this jurisdiction.</p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium border border-slate-300 rounded-md hover:bg-slate-50">
            <Download className="h-4 w-4" /> Export
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">
            <PlusCircle className="h-4 w-4" /> Assign VVB
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center">
          <h4 className="text-sm font-semibold text-slate-500 uppercase">Accredited Bodies ({filteredVvbs.length})</h4>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2 h-4 w-4 text-slate-400" />
            <input 
              placeholder="Search VVBs..." 
              className="pl-8 h-8 w-full rounded-md border border-slate-300 text-sm px-3"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="p-3 font-medium">Organization Name</th>
              <th className="p-3 font-medium">Accreditation ID</th>
              <th className="p-3 font-medium">Approved Scopes</th>
              <th className="p-3 font-medium">Status</th>
              <th className="p-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredVvbs.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center p-8 text-slate-500">
                  <ShieldCheck className="mx-auto h-8 w-8 text-slate-300 mb-2" />
                  No Validation Bodies assigned.
                </td>
              </tr>
            ) : filteredVvbs.map((vvb) => (
              <tr key={vvb.id} className="hover:bg-slate-50">
                <td className="p-3 font-medium">{vvb.name}</td>
                <td className="p-3 font-mono text-xs">{vvb.accreditation}</td>
                <td className="p-3">
                  <div className="flex gap-1 flex-wrap">
                    {vvb.scopes.map(s => (
                      <span key={s} className="px-2 py-0.5 border rounded text-[10px] text-slate-600">{s}</span>
                    ))}
                  </div>
                </td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${vvb.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {vvb.status}
                  </span>
                </td>
                <td className="p-3 text-right">
                  <button onClick={() => suspendVvb(vvb.id)} className="text-slate-400 hover:text-red-500" title="Suspend">
                    <Power className="h-4 w-4 inline" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
