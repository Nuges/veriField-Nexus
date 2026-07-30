// =============================================================================

// VeriField Nexus — Methodology DNA Route (/dashboard/methodologies)

// =============================================================================

"use client";



import UniversalEntityHeader from "@/components/UniversalEntityHeader";

import { UniversalMethodologyRenderer } from "@/components/UniversalMethodologyRenderer";

import { useWorkspace } from "@/context/WorkspaceContext";



export default function MethodologiesPage() {

  const { activeSector, activeMethodology } = useWorkspace();



  return (

    <div className="space-y-6">

      <UniversalEntityHeader

        entityType="Methodology"

        entityId={activeMethodology || "AMS-II.G"}

        entityName={`Methodological Rules & AST Engine (${activeMethodology || "AMS-II.G"})`}

        currentStage={2}

        currentStageName="2. Methodology DNA & AST Rules"

        ownerRole=""

        ownerName=""

        slaText=""

        status=""

        aiConfidence={99.8}

        aiRecommendation="Emission factors, non-renewable biomass fraction (fNRB), and AST algorithms locked."

        primaryNextActionLabel="Proceed to Fleet Onboarding"

        onPrimaryNextAction={() => {

          window.location.href = "/dashboard/assets";

        }}

      />



      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

        <h2 className="text-lg font-extrabold text-[var(--color-text-primary)] mb-4">

          Active Methodology Parameter Schema

        </h2>

        <UniversalMethodologyRenderer sector={activeSector} methodologyCode={activeMethodology || "AMS-II.G"} />

      </div>

    </div>

  );

}
