// Verification script for WorkspaceContext filtering logic (self-contained, pure JS)

// Smart classification mapping layer (copied exactly from WorkspaceContext.tsx)
function mapToWorkspace(record) {
  if (!record) return null;

  const normalizeVal = (value) => {
    if (typeof value !== "string") return "";
    return value.toLowerCase().trim();
  };

  const methodology = normalizeVal(record.methodology || record.methodology_used);
  const type = normalizeVal(record.property_type || record.activity_type || record.type);
  const category = normalizeVal(record.category);
  const desc = normalizeVal(record.description || record.name || record.address || "");
  
  // Extract tags if present
  let tagsStr = "";
  if (record.tags) {
    if (Array.isArray(record.tags)) {
      tagsStr = record.tags.map((t) => normalizeVal(String(t))).join(" ");
    } else {
      tagsStr = normalizeVal(record.tags);
    }
  }

  const allText = `${type} ${category} ${desc} ${tagsStr} ${methodology}`.toLowerCase();

  // 1. Methodology-based
  const isCookstoveMethodology =
    methodology.includes("gs_mecd") ||
    methodology.includes("mecd") ||
    methodology.includes("tpddtec") ||
    methodology.includes("vmr0050") ||
    methodology.includes("vm0006") ||
    allText.includes("gs_mecd") ||
    allText.includes("mecd") ||
    allText.includes("tpddtec") ||
    allText.includes("vmr0050") ||
    allText.includes("vm0006");

  if (isCookstoveMethodology) {
    return "cookstove";
  }

  const isEnergyMethodology =
    methodology.includes("ams-i.f") ||
    methodology.includes("renewable") ||
    methodology.includes("vm0038") ||
    allText.includes("ams-i.f") ||
    allText.includes("renewable") ||
    allText.includes("vm0038");

  if (isEnergyMethodology) {
    return "energy";
  }

  // 2. Cookstove Workspace Rules
  const hasCookstoveKeywords = 
    allText.includes("cookstove") || 
    allText.includes("biomass") || 
    allText.includes("clean cooking") ||
    allText.includes("cooking") ||
    allText.includes("stove");

  const hasFieldSignals =
    allText.includes("field") ||
    allText.includes("installation") ||
    allText.includes("deployment") ||
    allText.includes("monitoring");

  const hasAfoluOrSustainability =
    allText.includes("afolu") ||
    allText.includes("forestry") ||
    allText.includes("farming") ||
    allText.includes("agri") ||
    allText.includes("agriculture") ||
    allText.includes("sustainability");

  const hasCookstoveContext =
    allText.includes("household") ||
    allText.includes("energy displacement") ||
    allText.includes("cooking usage") ||
    allText.includes("biomass cooking relevance") ||
    allText.includes("displacement");

  if (hasCookstoveKeywords || (hasFieldSignals && allText.includes("cookstove"))) {
    return "cookstove";
  }

  // AFOLU / sustainability (STRICT CONDITION)
  if (hasAfoluOrSustainability) {
    if (hasCookstoveContext || hasCookstoveKeywords) {
      return "cookstove";
    }
  }

  // 3. Hybrid Energy Workspace Rules
  const hasEnergyKeywords = 
    allText.includes("solar") || 
    allText.includes("inverter") || 
    allText.includes("battery") || 
    allText.includes("mini-grid") || 
    allText.includes("hybrid") ||
    allText.includes("energy system") ||
    allText.includes("commercial energy displacement") ||
    allText.includes("industrial energy system");

  if (hasEnergyKeywords) {
    return "energy";
  }

  if (allText.includes("energy") && allText.includes("displacement")) {
    return "energy";
  }

  // 4. Ambiguous fallback mapping rules:
  // - If record.category includes energy + inverter/solar -> hybrid energy
  if (category.includes("energy") && (category.includes("inverter") || category.includes("solar") || allText.includes("inverter") || allText.includes("solar"))) {
    return "energy";
  }
  // - If ambiguous but tagged "field / installation / cookstove / biomass" -> cookstove
  if (allText.includes("field") || allText.includes("installation") || allText.includes("cookstove") || allText.includes("biomass")) {
    return "cookstove";
  }
  // - If ambiguous energy infrastructure -> hybrid energy
  if (allText.includes("energy") || allText.includes("infrastructure") || allText.includes("electricity") || allText.includes("power")) {
    return "energy";
  }

  // Strict exclusions return null (standalone forestry/agriculture, transport/mobility/vehicles, generic properties, etc.)
  return null;
}

// Mock datasets matching real DB records
const mockProperties = [
  { id: "prop-cookstove-1", name: "Port Harcourt Clean Cookstove", property_type: "cookstove" },
  { id: "prop-mecd-2", name: "MECD Gold Standard Household Unit", property_type: "GS_MECD" },
  { id: "prop-solar-3", name: "Solar Microgrid Block A", property_type: "solar_installation" },
  { id: "prop-battery-4", name: "Inverter Battery Storage Room", property_type: "battery_room" },
  { id: "prop-forestry-5", name: "Forestry Canopy Conservation Zone", property_type: "forestry_standalone" }, // Legacy: Should be ignored
  { id: "prop-agri-6", name: "Farming Soil Plot", property_type: "agriculture_standalone" }, // Legacy: Should be ignored
  { id: "prop-vehicle-7", name: "Electric Delivery Van EV-01", property_type: "vehicle_mobility" }, // Legacy: Should be ignored
  { id: "prop-sustainability-8", name: "Sustainable Cooking Fuel Field Activity", property_type: "sustainability", tags: ["field_activity", "cookstove"] }, // Conditional AFOLU/sustainability -> Cookstove
];

const mockLedger = [
  { id: "ledger-cookstove", methodology: "GS_MECD", tco2e: 45 },
  { id: "ledger-energy", methodology: "ams-i.f", tco2e: 120, category: "energy" },
  { id: "ledger-transport", methodology: "ams-iii.c", tco2e: 15, category: "transport" }, // Legacy: Should be ignored
  { id: "ledger-forestry", methodology: "AR-ACM0003", tco2e: 80, category: "forestry" }, // Legacy: Should be ignored
];

// Mock the callbacks and state
function runTest() {
  console.log("=== RUNNING WORKSPACE FILTER TEST ===\n");

  const sectors = ["cookstove", "energy"];

  sectors.forEach((activeSector) => {
    console.log(`\n--- Active Workspace: ${activeSector.toUpperCase()} ---`);

    // 1. Test properties
    console.log("\n[Testing Properties Filtering]");
    console.log("TOTAL RECORDS:", mockProperties.length);
    const filteredProps = mockProperties.filter((record) => {
      const mapped = mapToWorkspace(record);
      console.log("RECORD MAPPED:", record.id, mapped);
      
      const keep = mapped === activeSector;
      if (!keep) {
        console.log("DROPPED RECORD:", {
          id: record.id,
          reason: mapped !== activeSector ? "workspace_mismatch" : "null_mapping"
        });
      }
      return keep;
    });
    console.log("AFTER FILTER:", filteredProps.length);

    // 2. Test ledger
    console.log("\n[Testing Ledger Filtering]");
    console.log("TOTAL RECORDS:", mockLedger.length);
    const filteredLedger = mockLedger.filter((record) => {
      const mapped = mapToWorkspace(record);
      console.log("RECORD MAPPED:", record.id, mapped);
      
      const keep = mapped === activeSector;
      if (!keep) {
        console.log("DROPPED RECORD:", {
          id: record.id,
          reason: mapped !== activeSector ? "workspace_mismatch" : "null_mapping"
        });
      }
      return keep;
    });
    console.log("AFTER FILTER:", filteredLedger.length);
  });
}

runTest();
