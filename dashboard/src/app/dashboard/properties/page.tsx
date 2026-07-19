// =============================================================================
// VeriField Nexus — Properties/Assets Page
// =============================================================================
// Executive carbon assets directory and live sustainability verification ledger.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Plus, 
  Search, 
  Building2, 
  Home, 
  Factory, 
  Leaf, 
  Sparkles,
  ArrowRight,
  ShieldCheck,
  TreePine,
  CloudLightning,
  Layers
} from "lucide-react";
import { fetchProperties } from "@/lib/api";
import type { Property } from "@/lib/types";

import { useWorkspace } from "@/context/WorkspaceContext";

export default function PropertiesPage() {
  const { filterProperties } = useWorkspace();
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

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

  // Filter properties by active workspace sector context
  const isolatedProperties = filterProperties(properties);

  // Derive dynamic dashboard stats from the assets
  const totalAssetsCount = isolatedProperties.length;
  const verifiedAssetsCount = isolatedProperties.filter(
    p => (p.sustainability_metrics as any)?.status?.toLowerCase().includes("verif")
  ).length;
  
  const totalCarbonOffset = isolatedProperties.reduce(
    (acc, p) => acc + (Number((p.sustainability_metrics as any)?.carbon_offset_kg) || 0), 
    0
  );

  // Snappy client-side search query matching
  const filteredProperties = isolatedProperties.filter(p => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      (p.name || "").toLowerCase().includes(query) ||
      (p.property_type || "").toLowerCase().includes(query) ||
      (p.address || "").toLowerCase().includes(query)
    );
  });

  return (
    <div className="space-y-6 animate-fade-in-up">
      
      {/* 👑 EXECUTIVE TITLE & DESCRIPTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/15">
              MRV Registry
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1">
            Registered Carbon Assets
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Audit energy efficiency scores, inspect geographical placements, and review computed carbon credits.
          </p>
        </div>
      </div>

      {/* 📊 DYNAMIC METRICS SUMMARY CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Total Assets Summary */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Monitored Assets</p>
            <p className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">
              {isLoading ? "..." : totalAssetsCount}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Registered stoves & cookers</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-[#00B47A] group-hover:text-white transition-all duration-300">
            <Layers size={18} />
          </div>
        </div>

        {/* Total Carbon Offsets Dynamic Sum */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-blue-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Verified Emissions Offsets</p>
            <p className="text-2xl font-black text-blue-400 tracking-tight">
              {isLoading ? "..." : `${totalCarbonOffset.toLocaleString()} kg`}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Avoided CO₂ output</p>
          </div>
          <div className="p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl text-blue-400 shrink-0 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300">
            <TreePine size={18} />
          </div>
        </div>

        {/* Verified Gold Status Counts */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-purple-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Certified Gold Standard</p>
            <p className="text-2xl font-black text-[#00B47A] tracking-tight">
              {isLoading ? "..." : verifiedAssetsCount}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Fully verified MRV status</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-purple-500 group-hover:text-white transition-all duration-300">
            <ShieldCheck size={18} />
          </div>
        </div>

      </div>

      {/* 🧭 SNAPPY REAL-TIME TOOLBAR */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full max-w-md group">
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] group-focus-within:text-[#00B47A] transition-colors" />
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search assets by name, type, or region..." 
            className="w-full pl-11 pr-4 py-2.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-xs text-[var(--color-text-primary)] placeholder:text-slate-500 focus:border-[#00B47A]/40 focus:ring-1 focus:ring-[#00B47A]/30 focus:outline-none transition-all shadow-inner font-semibold"
          />
        </div>
        
        <span className="text-[10px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-widest shrink-0 self-end sm:self-center">
          Active ledger: {filteredProperties.length} results
        </span>
      </div>

      {/* 🧭 ASSETS GRID CONTAINER */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-3">
          <div className="w-7 h-7 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
          <p className="text-[var(--color-text-secondary)] text-xs font-semibold tracking-tight animate-pulse">
            Retrieving secure MRV properties...
          </p>
        </div>
      ) : filteredProperties.length === 0 ? (
        <div className="p-12 text-center flex flex-col items-center justify-center bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-md mx-auto shadow-sm">
          <Building2 size={36} className="text-[var(--color-text-muted)] mb-3 animate-pulse" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">No Assets Matched</h3>
          <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
            There are no registered assets matching your query search. Please try adjusting your parameters.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProperties.map((property) => {
            const Icon = getIcon(property.property_type);
            const metrics = property.sustainability_metrics as any || {};
            const isVerified = metrics?.status?.toLowerCase().includes("verif");
            const isFlagged = metrics?.status?.toLowerCase().includes("flag");

            return (
              <Link 
                href={`/dashboard/properties/${property.id}`} 
                key={property.id} 
                className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden hover:border-[#00B47A]/30 hover:shadow-lg hover:shadow-black/10 transition-all duration-300 group flex flex-col justify-between"
              >
                {/* Upper Module */}
                <div className="p-4.5">
                  <div className="flex items-start justify-between mb-3.5">
                    <div className="w-10 h-10 rounded-xl bg-[#00B47A]/5 border border-[#00B47A]/10 group-hover:bg-[#00B47A] group-hover:text-white flex items-center justify-center text-[#00B47A] transition-all duration-300 shrink-0">
                      <Icon size={18} />
                    </div>
                    <span className="px-2.5 py-0.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[9px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider">
                      {property.property_type}
                    </span>
                  </div>
                  
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[#00B47A] transition-colors truncate" title={property.name}>
                    {property.name}
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-1 line-clamp-2 min-h-[32px] font-medium leading-relaxed">
                    {property.address || "No region/address was registered."}
                  </p>
                </div>
                
                {/* Lower Module / Sustainability Info */}
                <div className="p-4.5 bg-[var(--color-background)]/50 border-t border-[var(--color-border)] flex-1 flex flex-col justify-end">
                  <div className="flex items-center gap-1.5 mb-3">
                    <Leaf size={13} className="text-[#00B47A]" />
                    <span className="text-[9px] font-extrabold text-[#00B47A] uppercase tracking-widest">
                      Sustainability Profile
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-2">
                    
                    <div className="bg-[var(--color-surface)] rounded-xl p-2.5 border border-[var(--color-border)] shadow-inner">
                      <p className="text-[8px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-wider mb-0.5">Energy Score</p>
                      <p className="text-xs font-black text-[#00B47A] font-mono">
                        {metrics?.energy_score || 'N/A'}
                      </p>
                    </div>

                    <div className="bg-[var(--color-surface)] rounded-xl p-2.5 border border-[var(--color-border)] shadow-inner">
                      <p className="text-[8px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-wider mb-0.5">Offset CO₂</p>
                      <p className="text-xs font-black text-blue-400 font-mono truncate">
                        {metrics?.carbon_offset_kg ? `${metrics.carbon_offset_kg}kg` : 'N/A'}
                      </p>
                    </div>

                    <div className="bg-[var(--color-surface)] rounded-xl p-2.5 border border-[var(--color-border)] shadow-inner overflow-hidden">
                      <p className="text-[8px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-wider mb-0.5">Status</p>
                      <p className={`text-[10px] font-extrabold uppercase truncate ${
                        isVerified 
                          ? "text-[#00B47A]" 
                          : isFlagged 
                          ? "text-red-500" 
                          : "text-amber-500"
                      }`} title={metrics?.status || 'Unverified'}>
                        {metrics?.status || 'Unverified'}
                      </p>
                    </div>

                  </div>

                  {/* Micro-interaction Hover Indicator */}
                  <div className="mt-3.5 pt-2.5 border-t border-[var(--color-border)]/5 flex items-center justify-between text-[9px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <span>Inspect Ledger Details</span>
                    <ArrowRight size={12} className="text-[#00B47A] transform translate-x-0 group-hover:translate-x-1 transition-transform" />
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
