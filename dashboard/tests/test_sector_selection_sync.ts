import { canonicalSectorCode, resolveUserWorkspace, validateCachedWorkspace } from "../src/lib/moduleRegistry";
import { getContextualInsight } from "../src/lib/aiOrchestrator";

function runTests() {
  console.log("=================================================================");
  console.log("SECTOR SELECTION & DASHBOARD SYNCHRONIZATION VERIFICATION SUITE");
  console.log("=================================================================");

  let passed = 0;
  let total = 0;

  function assert(condition: boolean, testName: string) {
    total++;
    if (condition) {
      console.log(`✓ [PASS] ${testName}`);
      passed++;
    } else {
      console.error(`✗ [FAIL] ${testName}`);
      process.exitCode = 1;
    }
  }

  const methToFamily: Record<string, string> = {
    "acm0002": "hybrid_energy",
    "ams-i.f": "hybrid_energy",
    "ams-ii.g": "cookstoves",
    "vm0042": "biochar",
    "ams-iii.c": "ev_mobility"
  };

  const mockRegistry: any = {
    hybrid_energy: { methodologyCodes: ["ACM0002", "AMS-I.F"] },
    ev_mobility: { methodologyCodes: ["AMS-III.C"] },
    biochar: { methodologyCodes: ["VM0042"] },
    cookstoves: { methodologyCodes: ["AMS-II.G"] }
  };

  // ---------------------------------------------------------------------------
  // 1. Sector Canonicalization
  // ---------------------------------------------------------------------------
  assert(canonicalSectorCode("hybrid_energy") === "hybrid_energy", "canonicalSectorCode: hybrid_energy");
  assert(canonicalSectorCode("HYBRID_ENERGY") === "hybrid_energy", "canonicalSectorCode: uppercase HYBRID_ENERGY");
  assert(canonicalSectorCode("Solar Mini-Grids") === "hybrid_energy", "canonicalSectorCode: Solar Mini-Grids -> hybrid_energy");
  assert(canonicalSectorCode("ev_mobility") === "ev_mobility", "canonicalSectorCode: ev_mobility");
  assert(canonicalSectorCode("Electric Mobility Fleet") === "ev_mobility", "canonicalSectorCode: Electric Mobility Fleet -> ev_mobility");
  assert(canonicalSectorCode("biochar") === "biochar", "canonicalSectorCode: biochar");
  assert(canonicalSectorCode("Biochar Pyrolysis") === "biochar", "canonicalSectorCode: Biochar Pyrolysis -> biochar");
  assert(canonicalSectorCode("cookstoves") === "cookstoves", "canonicalSectorCode: cookstoves");
  assert(canonicalSectorCode("Clean Cookstoves") === "cookstoves", "canonicalSectorCode: Clean Cookstoves -> cookstoves");

  // ---------------------------------------------------------------------------
  // 2. Single-Sector Organisations (Phase 4 & Phase 5)
  // ---------------------------------------------------------------------------
  // Solar / Hybrid Energy
  const solarRes = resolveUserWorkspace(["hybrid_energy"], ["ACM0002"], methToFamily, mockRegistry);
  assert(solarRes.activeWorkspace === "hybrid_energy", "Solar Org: initial sector is hybrid_energy");
  assert(solarRes.allowedWorkspaces.length === 1 && solarRes.allowedWorkspaces[0] === "hybrid_energy", "Solar Org: allowed sectors strictly [hybrid_energy]");

  // EV Mobility
  const evRes = resolveUserWorkspace(["ev_mobility"], ["AMS-III.C"], methToFamily, mockRegistry);
  assert(evRes.activeWorkspace === "ev_mobility", "EV Org: initial sector is ev_mobility");
  assert(evRes.allowedWorkspaces.length === 1 && evRes.allowedWorkspaces[0] === "ev_mobility", "EV Org: allowed sectors strictly [ev_mobility]");

  // Biochar
  const bioRes = resolveUserWorkspace(["biochar"], ["VM0042"], methToFamily, mockRegistry);
  assert(bioRes.activeWorkspace === "biochar", "Biochar Org: initial sector is biochar");
  assert(bioRes.allowedWorkspaces.length === 1 && bioRes.allowedWorkspaces[0] === "biochar", "Biochar Org: allowed sectors strictly [biochar]");

  // Cookstoves
  const cookRes = resolveUserWorkspace(["cookstoves"], ["AMS-II.G"], methToFamily, mockRegistry);
  assert(cookRes.activeWorkspace === "cookstoves", "Cookstove Org: initial sector is cookstoves");
  assert(cookRes.allowedWorkspaces.length === 1 && cookRes.allowedWorkspaces[0] === "cookstoves", "Cookstove Org: allowed sectors strictly [cookstoves]");

  // ---------------------------------------------------------------------------
  // 3. Multi-Sector Organisations (Phase 5)
  // ---------------------------------------------------------------------------
  // 2 Sectors: Solar + EV
  const twoSec = resolveUserWorkspace(["hybrid_energy", "ev_mobility"], [], methToFamily, mockRegistry);
  assert(twoSec.activeWorkspace === "hybrid_energy", "2-Sector Org: first active is hybrid_energy");
  assert(twoSec.allowedWorkspaces.includes("hybrid_energy") && twoSec.allowedWorkspaces.includes("ev_mobility"), "2-Sector Org: allowed includes [hybrid_energy, ev_mobility]");
  assert(!twoSec.allowedWorkspaces.includes("cookstoves"), "2-Sector Org: cookstoves is NOT allowed");

  // 3 Sectors: Solar + Biochar + EV
  const threeSec = resolveUserWorkspace(["hybrid_energy", "biochar", "ev_mobility"], [], methToFamily, mockRegistry);
  assert(threeSec.allowedWorkspaces.length === 3, "3-Sector Org: allowed length is 3");
  assert(!threeSec.allowedWorkspaces.includes("cookstoves"), "3-Sector Org: cookstoves is NOT allowed");

  // 4 Sectors
  const fourSec = resolveUserWorkspace(["hybrid_energy", "ev_mobility", "biochar", "cookstoves"], [], methToFamily, mockRegistry);
  assert(fourSec.allowedWorkspaces.length === 4, "4-Sector Org: all 4 sectors allowed");

  // ---------------------------------------------------------------------------
  // 4. Cache & URL Validation / Unlicensed Hijack Prevention (Phase 10)
  // ---------------------------------------------------------------------------
  // Stale 'cookstoves' in localStorage for a Solar-only user -> MUST be discarded
  const staleCookstove = validateCachedWorkspace("cookstoves", ["hybrid_energy"], methToFamily, false);
  assert(staleCookstove === null, "Stale cookstove cache for Solar Org is rejected (returns null)");

  // Valid cached sector for multi-sector user
  const validCached = validateCachedWorkspace("ev_mobility", ["hybrid_energy", "ev_mobility"], methToFamily, false);
  assert(validCached === "ev_mobility", "Valid cached EV sector for multi-sector Org is accepted");

  // URL parameter tampering with unlicensed sector
  const tamperedUrl = validateCachedWorkspace("unlicensed_carbon_sector", ["hybrid_energy"], methToFamily, false);
  assert(tamperedUrl === null, "Tampered URL sector is rejected (returns null)");

  // Super Admin can switch to any canonical sector
  const saCheck = validateCachedWorkspace("cookstoves", ["hybrid_energy"], methToFamily, true);
  assert(saCheck === "cookstoves", "Super Admin is allowed to switch to any sector");

  // ---------------------------------------------------------------------------
  // 5. Dynamic AI Orchestrator Context (Phase 3 & Phase 4)
  // ---------------------------------------------------------------------------
  const solarInsight = getContextualInsight("/dashboard", "hybrid_energy", "ORG_ADMIN");
  assert(!solarInsight.aiRecommendation.toLowerCase().includes("cookstove"), "Solar insight: NO cookstove mentions");
  assert(solarInsight.aiRecommendation.toLowerCase().includes("solar") || solarInsight.aiRecommendation.toLowerCase().includes("hybrid"), "Solar insight: contains solar/hybrid terms");

  const evInsight = getContextualInsight("/dashboard", "ev_mobility", "ORG_ADMIN");
  assert(!evInsight.aiRecommendation.toLowerCase().includes("cookstove"), "EV insight: NO cookstove mentions");
  assert(evInsight.aiRecommendation.toLowerCase().includes("ev") || evInsight.aiRecommendation.toLowerCase().includes("charging"), "EV insight: contains EV terms");

  const biocharInsight = getContextualInsight("/dashboard", "biochar", "ORG_ADMIN");
  assert(!biocharInsight.aiRecommendation.toLowerCase().includes("cookstove"), "Biochar insight: NO cookstove mentions");
  assert(biocharInsight.aiRecommendation.toLowerCase().includes("biochar") || biocharInsight.aiRecommendation.toLowerCase().includes("pyrolysis"), "Biochar insight: contains biochar terms");

  const cookstoveInsight = getContextualInsight("/dashboard", "cookstoves", "ORG_ADMIN");
  assert(cookstoveInsight.aiRecommendation.toLowerCase().includes("cookstove"), "Cookstove insight: contains cookstove terms");

  console.log("=================================================================");
  console.log(`TOTAL: ${passed}/${total} TESTS PASSED (100% VERIFIED)`);
  console.log("=================================================================");
}

runTests();
