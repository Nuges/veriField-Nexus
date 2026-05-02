// =============================================================================
// VeriField Nexus — Properties Page
// =============================================================================
// Manage real estate properties and sustainability metrics.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Search, Building2, Home, Factory, Leaf } from "lucide-react";
import { fetchProperties } from "@/lib/api";
import type { Property } from "@/lib/types";

export default function PropertiesPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadProps() {
      try {
        const res = await fetchProperties();
        setProperties(res.properties);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    loadProps();
  }, []);

  const getIcon = (type: string) => {
    switch (type) {
      case 'residential': return Home;
      case 'commercial': return Building2;
      case 'industrial': return Factory;
      default: return Building2;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Assets</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Manage field assets and sustainability metrics</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex gap-4 animate-fade-in-up animation-delay-100">
        <div className="relative flex-1 max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input 
            type="text" 
            placeholder="Search assets..." 
            className="w-full pl-10 pr-4 py-2 bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl text-sm text-[var(--color-text-primary)] focus:border-emerald-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Asset Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-[var(--color-text-secondary)]">Loading assets...</div>
      ) : properties.length === 0 ? (
        <div className="p-12 text-center flex flex-col items-center bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl">
          <Building2 size={48} className="text-[var(--color-text-muted)] mb-4" />
          <h3 className="text-lg font-medium text-[var(--color-text-primary)]">No assets found</h3>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Add your first asset to start tracking sustainability.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fade-in-up animation-delay-200">
          {properties.map((property) => {
            const Icon = getIcon(property.property_type);
            const metrics = property.sustainability_metrics as any || {};
            
            return (
              <Link href={`/dashboard/properties/${property.id}`} key={property.id} className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden hover:border-[#475569] transition-all group cursor-pointer flex flex-col hover:shadow-lg hover:shadow-black/20 block">
                <div className="p-5 border-b border-[var(--color-border)]">
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-12 h-12 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center">
                      <Icon size={24} className="text-emerald-400" />
                    </div>
                    <span className="px-2.5 py-1 rounded-md bg-[var(--color-surface)] text-slate-300 text-xs font-medium uppercase tracking-wider border border-[var(--color-border)]">
                      {property.property_type}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-[var(--color-text-primary)] truncate" title={property.name}>{property.name}</h3>
                  <p className="text-sm text-[var(--color-text-secondary)] mt-1 line-clamp-2 min-h-[40px]">{property.address || "No address provided"}</p>
                </div>
                
                <div className="p-5 bg-[var(--color-surface)]/50 flex-1 flex flex-col justify-end">
                  <div className="flex items-center gap-2 mb-3">
                    <Leaf size={16} className="text-emerald-500" />
                    <span className="text-sm font-medium text-slate-300">Sustainability Profile</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-[var(--color-surface)] rounded-lg p-3 border border-[var(--color-border)]">
                      <p className="text-xs text-[var(--color-text-muted)] mb-1">Energy Score</p>
                      <p className="text-lg font-semibold text-emerald-400">{metrics?.energy_score || 'N/A'}</p>
                    </div>
                    <div className="bg-[var(--color-surface)] rounded-lg p-3 border border-[var(--color-border)]">
                      <p className="text-xs text-[var(--color-text-muted)] mb-1">Carbon Offset</p>
                      <p className="text-lg font-semibold text-blue-400">{metrics?.carbon_offset_kg ? `${metrics.carbon_offset_kg}kg` : 'N/A'}</p>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
