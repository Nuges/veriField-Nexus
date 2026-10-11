// =============================================================================

// VeriField Nexus — Methodology DNA Route (/dashboard/methodologies)

// =============================================================================

"use client";



import UniversalEntityHeader from "@/components/UniversalEntityHeader";
import { UniversalMethodologyRenderer } from "@/components/UniversalMethodologyRenderer";
import { useWorkspace } from "@/context/WorkspaceContext";
import { getSectorTerminology } from "@/lib/moduleRegistry";
import { UNCONFIGURED_METHODOLOGY_CODES } from "@/lib/sectors";

export default function MethodologiesPage() {
  const { activeSector, activeMethodology } = useWorkspace();
  const sectorTerms = getSectorTerminology(activeSector);

  const methCode = activeMethodology || (activeSector === "hybrid_energy" ? "AMS-I.F" : activeSector === "biochar" ? "VM0044" : activeSector === "ev_mobility" ? "VM0038" : activeSector === "cookstoves" ? "GS_MECD" : "VM0042");

  // Gating is derived from the canonical methodology registry (lib/sectors.ts),
  // not from a hardcoded sector list.
  const normalizedMethCode = methCode.trim().toUpperCase().replace(/[-.\s]/g, "_");
  const isMethodologyGated = UNCONFIGURED_METHODOLOGY_CODES.has(normalizedMethCode);

  return (
    <div className="space-y-6">
      <UniversalEntityHeader
        entityType="Methodology"
        entityId={methCode}
        entityName={`Methodological Rules & AST Engine (${methCode})`}
        currentStage={2}
        currentStageName="2. Methodology DNA & AST Rules"
        ownerRole=""
        ownerName=""
        slaText=""
        status=""
        aiConfidence={99.8}
        aiRecommendation="Emission factors, non-renewable biomass fraction (fNRB), and AST algorithms locked."
        primaryNextActionLabel={sectorTerms.proceedToStage3Label}
        onPrimaryNextAction={() => {
          window.location.href = "/dashboard/assets";
        }}
      />

      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <h2 className="text-lg font-extrabold text-[var(--color-text-primary)]">
            Active Methodology Parameter Schema
          </h2>
          {isMethodologyGated && (
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30">
                SUPPORTED PILOT SECTOR
              </span>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/30">
                METHODOLOGY ENGINE GATED
              </span>
            </div>
          )}
        </div>
        {isMethodologyGated && (
          <div className="mb-4 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-xs font-medium leading-relaxed">
            Telemetry, field operations and project setup are available. Official production quantification is not yet enabled.
          </div>
        )}
        <UniversalMethodologyRenderer sector={activeSector} methodologyCode={methCode} />
      </div>
    </div>
  );

}
