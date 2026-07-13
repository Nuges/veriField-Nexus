"use client";

import React, { useState } from "react";
import { Camera, Upload, AlertCircle } from "lucide-react";

export interface FormFieldDef {
  key: string;
  label: string;
  type: 'string' | 'int' | 'float' | 'enum' | 'boolean';
  required?: boolean;
  options?: string[];
  placeholder?: string;
}

export interface PhotoFieldDef {
  key: string;
  label: string;
  required?: boolean;
  prompt: string;
}

export interface FormSection {
  title: string;
  fields: FormFieldDef[];
}

export interface MethodologySchema {
  sections: FormSection[];
  photos: PhotoFieldDef[];
}

interface Props {
  schema: MethodologySchema;
  values: Record<string, any>;
  onChange: (key: string, value: any) => void;
  onPhotoUpload: (key: string, file: File) => void;
  photoPreviews: Record<string, string>;
}

export function UniversalMethodologyRenderer({ schema, values, onChange, onPhotoUpload, photoPreviews }: Props) {
  if (!schema || !schema.sections) {
    return <div className="p-4 text-center text-sm text-slate-500">No methodology schema provided.</div>;
  }

  return (
    <div className="space-y-8">
      {schema.sections.map((section, idx) => (
        <div key={idx} className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-[var(--color-border)] bg-slate-50/50 dark:bg-slate-900/50">
            <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{section.title}</h3>
          </div>
          <div className="p-5 space-y-4">
            {section.fields.map((field) => (
              <div key={field.key} className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--color-text-secondary)]">
                  {field.label} {field.required && <span className="text-red-500">*</span>}
                </label>
                
                {field.type === 'enum' ? (
                  <select
                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500 transition-colors"
                    value={values[field.key] || ""}
                    onChange={(e) => onChange(field.key, e.target.value)}
                    required={field.required}
                  >
                    <option value="" disabled>Select {field.label}</option>
                    {field.options?.map(opt => (
                      <option key={opt} value={opt}>{opt.replace(/_/g, " ").toUpperCase()}</option>
                    ))}
                  </select>
                ) : field.type === 'boolean' ? (
                  <div className="flex items-center gap-3 mt-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="radio" 
                        name={field.key} 
                        value="true" 
                        checked={values[field.key] === true || values[field.key] === "true"}
                        onChange={() => onChange(field.key, true)}
                        className="accent-emerald-500 w-4 h-4"
                        required={field.required}
                      />
                      <span className="text-sm text-[var(--color-text-primary)]">Yes</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="radio" 
                        name={field.key} 
                        value="false" 
                        checked={values[field.key] === false || values[field.key] === "false"}
                        onChange={() => onChange(field.key, false)}
                        className="accent-emerald-500 w-4 h-4"
                        required={field.required}
                      />
                      <span className="text-sm text-[var(--color-text-primary)]">No</span>
                    </label>
                  </div>
                ) : (
                  <input
                    type={field.type === 'int' || field.type === 'float' ? 'number' : 'text'}
                    step={field.type === 'float' ? '0.01' : '1'}
                    placeholder={field.placeholder || ""}
                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 transition-colors"
                    value={values[field.key] || ""}
                    onChange={(e) => onChange(field.key, e.target.value)}
                    required={field.required}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {schema.photos && schema.photos.length > 0 && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-[var(--color-border)] bg-slate-50/50 dark:bg-slate-900/50">
            <h3 className="text-sm font-bold text-[var(--color-text-primary)]">Evidence Photography</h3>
          </div>
          <div className="p-5 space-y-6">
            {schema.photos.map((photo) => (
              <div key={photo.key} className="space-y-2">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
                      {photo.label} {photo.required && <span className="text-red-500">*</span>}
                    </h4>
                    <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">{photo.prompt}</p>
                  </div>
                </div>
                
                <div className="mt-3">
                  {photoPreviews[photo.key] ? (
                    <div className="relative rounded-xl overflow-hidden border border-[var(--color-border)] aspect-video bg-black/5 group">
                      <img src={photoPreviews[photo.key]} alt={photo.label} className="w-full h-full object-cover" />
                      <label className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer backdrop-blur-sm">
                        <Upload size={24} className="text-white mb-2" />
                        <span className="text-xs font-bold text-white uppercase tracking-wider">Retake Photo</span>
                        <input
                          type="file"
                          accept="image/*"
                          capture="environment"
                          className="hidden"
                          onChange={(e) => {
                            if (e.target.files?.[0]) onPhotoUpload(photo.key, e.target.files[0]);
                          }}
                        />
                      </label>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center border-2 border-dashed border-[var(--color-border)] hover:border-emerald-500/50 hover:bg-emerald-500/5 rounded-xl aspect-video cursor-pointer transition-all">
                      <Camera size={28} className="text-[var(--color-text-muted)] mb-2" />
                      <span className="text-xs font-bold text-[var(--color-text-secondary)] uppercase tracking-wider">Capture {photo.label}</span>
                      <input
                        type="file"
                        accept="image/*"
                        capture="environment"
                        className="hidden"
                        required={photo.required}
                        onChange={(e) => {
                          if (e.target.files?.[0]) onPhotoUpload(photo.key, e.target.files[0]);
                        }}
                      />
                    </label>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
