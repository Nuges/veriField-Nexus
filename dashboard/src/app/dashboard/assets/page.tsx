// =============================================================================
// VeriField Nexus — Fleet & Assets Route (/dashboard/assets)
// =============================================================================

"use client";

import UniversalEntityHeader from "@/components/UniversalEntityHeader";
import PropertiesPage from "../properties/page";
import { useWorkspace } from "@/context/WorkspaceContext";
import { getSectorTerminology } from "@/lib/moduleRegistry";

export default function AssetsPage() {
  const { activeSector } = useWorkspace();
  const sectorTerms = getSectorTerminology(activeSector);

  return (
    <div className="space-y-6">
      <UniversalEntityHeader
        entityType={sectorTerms.entityTypeAsset}
        entityId={`AST-${sectorTerms.sectorCode.toUpperCase().slice(0, 5)}-01`}
        entityName={`${sectorTerms.sectorName} Hardware & Telemetry Calibration`}
        currentStage={3}
        currentStageName={sectorTerms.stage3DetailedName}
        ownerRole=""
        ownerName=""
        slaText=""
        status=""
        aiRecommendation={`All ${sectorTerms.assetPlural.toLowerCase()} online and emitting verified MRV telemetry.`}
        primaryNextActionLabel="Dispatch Field Calibration Task"
        onPrimaryNextAction={() => {
          window.location.href = "/dashboard/operations";
        }}
      />

      {/* Render Assets / Properties Directory */}
      <PropertiesPage />
    </div>
  );
}
