// =============================================================================

// VeriField Nexus — Fleet & Assets Route (/dashboard/assets)

// =============================================================================

"use client";



import UniversalEntityHeader from "@/components/UniversalEntityHeader";

import PropertiesPage from "../properties/page";



export default function AssetsPage() {

  return (

    <div className="space-y-6">

      <UniversalEntityHeader

        entityType="Asset Fleet"

        entityId="AST-FLEET-01"

        entityName="IoT Fleet & Asset Hardware Calibration"

        currentStage={3}

        currentStageName="3. Fleet & Asset Onboarding"

        ownerRole=""

        ownerName=""

        slaText=""

        status=""

        aiRecommendation="All sensors online and emitting telemetry."

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
