// =============================================================================

// VeriField Nexus — Methodology DNA Route (/dashboard/methodologies)

// =============================================================================

"use client";



import UniversalEntityHeader from "@/components/UniversalEntityHeader";
import { UniversalMethodologyRenderer } from "@/components/UniversalMethodologyRenderer";
import { useWorkspace } from "@/context/WorkspaceContext";
import { getSectorTerminology } from "@/lib/moduleRegistry";

export default function MethodologiesPage() {
  const { activeSector, activeMethodology } = useWorkspace();
  const sectorTerms = getSectorTerminology(activeSector);

  const methCode = activeMethodology || (activeSector === "hybrid_energy" ? "ACM0002" : activeSector === "biochar" ? "VM0042" : activeSector === "ev_mobility" ? "AMS-III.C" : "AMS-II.G");

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
        <h2 className="text-lg font-extrabold text-[var(--color-text-primary)] mb-4">
          Active Methodology Parameter Schema
        </h2>
        <UniversalMethodologyRenderer sector={activeSector} methodologyCode={methCode} />
      </div>
    </div>
  );

}
