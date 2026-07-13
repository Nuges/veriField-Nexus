"use client";

import React, { useState, useEffect } from "react";
import { CheckCircle, AlertCircle, FileText, Upload, ChevronRight, Activity, MapPin, Calculator, ShieldCheck } from "lucide-react";

export default function DynamicWorkspace({ methodologyId }: { methodologyId: string }) {
  const [schema, setSchema] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState("data");
  const [calculationResult, setCalculationResult] = useState<any>(null);
  const [calcLoading, setCalcLoading] = useState(false);

  useEffect(() => {
    async function fetchSchema() {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/methodologies/${methodologyId}/workspace-schema`);
        if (!response.ok) throw new Error("Failed to load schema");
        const data = await response.json();
        setSchema(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchSchema();
  }, [methodologyId]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="flex h-full flex-col items-center justify-center space-y-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <h2 className="text-xl font-medium text-slate-800">Workspace Unavailable</h2>
        <p className="text-slate-500">Could not load the methodology schema.</p>
      </div>
    );
  }

  const handleInputChange = (key: string, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const executeCalculation = async () => {
    setCalcLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/methodologies/${methodologyId}/calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const result = await response.json();
      setCalculationResult(result);
    } catch (err) {
      console.error(err);
    } finally {
      setCalcLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        <div>
          <div className="flex items-center space-x-2 text-sm font-medium text-indigo-600">
            <span className="rounded-full bg-indigo-50 px-2.5 py-0.5">{schema.methodology.code}</span>
            <span>•</span>
            <span>{schema.methodology.registry}</span>
            <span>•</span>
            <span>v{schema.methodology.version}</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{schema.methodology.name}</h1>
        </div>
        <button className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2">
          Submit to Registry
        </button>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Left Column: Data Entry */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Tabs */}
          <div className="flex space-x-1 rounded-xl bg-slate-100 p-1">
            {["data", "evidence", "workflow"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex flex-1 items-center justify-center space-x-2 rounded-lg py-2.5 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {tab === "data" && <Activity className="h-4 w-4" />}
                {tab === "evidence" && <FileText className="h-4 w-4" />}
                {tab === "workflow" && <ShieldCheck className="h-4 w-4" />}
                <span className="capitalize">{tab}</span>
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === "data" && (
            <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
              <h2 className="mb-6 text-lg font-medium text-slate-900">Monitoring Data</h2>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                {schema.form_schema.ui_order.map((key: string) => {
                  const field = schema.form_schema.properties[key];
                  const isRequired = schema.form_schema.required.includes(key);
                  return (
                    <div key={key} className="space-y-1">
                      <label className="block text-sm font-medium text-slate-700">
                        {field.title} {isRequired && <span className="text-red-500">*</span>}
                      </label>
                      {field.description && (
                        <p className="text-xs text-slate-500">{field.description}</p>
                      )}
                      <div className="relative mt-1 rounded-md shadow-sm">
                        <input
                          type={field.type === "number" ? "number" : "text"}
                          className="block w-full rounded-lg border-0 py-2.5 pl-3 pr-12 text-slate-900 ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                          placeholder={`Enter ${field.title.toLowerCase()}`}
                          value={formData[key] || ""}
                          onChange={(e) => handleInputChange(key, field.type === "number" ? parseFloat(e.target.value) : e.target.value)}
                        />
                        {field.unit && (
                          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                            <span className="text-sm text-slate-500">{field.unit}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === "evidence" && (
            <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
              <h2 className="mb-6 text-lg font-medium text-slate-900">Required Evidence</h2>
              <div className="space-y-4">
                {schema.evidence_requirements.map((req: any, idx: number) => (
                  <div key={idx} className="flex items-start space-x-4 rounded-xl border border-slate-200 p-4 transition-colors hover:bg-slate-50">
                    <div className="mt-1 rounded-lg bg-indigo-50 p-2 text-indigo-600">
                      {req.evidence_type === "photo" ? <Upload className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-slate-900">
                        {req.name}
                        {req.rule_type === "required" && (
                          <span className="ml-2 inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">Required</span>
                        )}
                      </h3>
                      <p className="mt-1 text-sm text-slate-500">{req.description}</p>
                    </div>
                    <button className="rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50">
                      Upload
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {activeTab === "workflow" && schema.workflow && (
            <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
               <h2 className="mb-6 text-lg font-medium text-slate-900">Workflow: {schema.workflow.name}</h2>
               <div className="space-y-6">
                 {schema.workflow.stages.map((stage: any, idx: number) => (
                   <div key={idx} className="relative">
                     <div className="flex items-center">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-600 ring-4 ring-white">
                          {stage.sequence_order}
                        </div>
                        <h3 className="ml-4 text-base font-semibold text-slate-900">{stage.name}</h3>
                     </div>
                     <div className="ml-4 mt-2 border-l-2 border-slate-200 pl-8 pb-4">
                        {stage.tasks.map((task: any, tIdx: number) => (
                          <div key={tIdx} className="mb-2 flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
                             <div className="flex items-center space-x-3">
                               <CheckCircle className="h-5 w-5 text-slate-400" />
                               <span className="text-sm font-medium text-slate-700">{task.name}</span>
                             </div>
                             <span className="text-xs font-medium text-slate-500 capitalize">{task.task_type.replace('_', ' ')}</span>
                          </div>
                        ))}
                     </div>
                   </div>
                 ))}
               </div>
            </div>
          )}

        </div>

        {/* Right Column: Calculations & Rules */}
        <div className="space-y-6">
          <div className="rounded-2xl bg-slate-900 p-6 text-white shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-medium text-white flex items-center space-x-2">
                <Calculator className="h-5 w-5 text-indigo-400" />
                <span>Calculation Engine</span>
              </h2>
            </div>
            
            <div className="space-y-4 mb-6">
              {schema.calculation_rules.map((rule: any, idx: number) => (
                <div key={idx} className="rounded-lg bg-slate-800/50 p-3 ring-1 ring-white/10">
                  <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">{rule.name}</div>
                  <code className="text-sm text-indigo-300 block overflow-x-auto whitespace-pre font-mono">
                    {rule.formula}
                  </code>
                </div>
              ))}
            </div>

            <button
              onClick={executeCalculation}
              disabled={calcLoading}
              className="w-full rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50"
            >
              {calcLoading ? "Computing..." : "Run Calculations"}
            </button>

            {calculationResult && (
              <div className="mt-6 border-t border-white/10 pt-4">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Results:</h3>
                {Object.entries(calculationResult.results).map(([k, v]: [string, any]) => (
                  <div key={k} className="flex justify-between items-center mb-2">
                    <span className="text-sm text-slate-400">{k}</span>
                    <span className="text-base font-semibold text-emerald-400">{typeof v === 'number' ? v.toFixed(4) : v}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
            <h2 className="mb-4 text-lg font-medium text-slate-900">Validation Rules</h2>
            <div className="space-y-3">
              {schema.validation_rules.map((rule: any, idx: number) => (
                <div key={idx} className="flex items-start space-x-3 text-sm">
                  <ShieldCheck className="h-5 w-5 flex-shrink-0 text-emerald-500" />
                  <div>
                    <span className="font-medium text-slate-900">{rule.name}</span>
                    <p className="mt-0.5 text-slate-500 font-mono text-xs">{rule.expression}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
