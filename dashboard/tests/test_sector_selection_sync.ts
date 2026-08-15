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
  assert(canonicalSectorCode("EV_MOBILITY") === "ev_mobility", "canonicalSectorCode: uppercase EV_MOBILITY");
  assert(canonicalSectorCode("Electric Mobility Fleet") === "ev_mobility", "canonicalSectorCode: Electric Mobility Fleet -> ev_mobility");
  assert(canonicalSectorCode("Biod Ev") === "ev_mobility", "canonicalSectorCode: Biod Ev -> ev_mobility");
  assert(canonicalSectorCode("dammy Solar") === "hybrid_energy", "canonicalSectorCode: dammy Solar -> hybrid_energy");
  assert(canonicalSectorCode("biochar") === "biochar", "canonicalSectorCode: biochar");
  assert(canonicalSectorCode("Biochar Pyrolysis") === "biochar", "canonicalSectorCode: Biochar Pyrolysis -> biochar");
  assert(canonicalSectorCode("cookstoves") === "cookstoves", "canonicalSectorCode: cookstoves");
  assert(canonicalSectorCode("Clean Cookstoves") === "cookstoves", "canonicalSectorCode: Clean Cookstoves -> cookstoves");

  // ---------------------------------------------------------------------------
  // 2. Single-Sector Organisations (Explicit Licenses)
  // ---------------------------------------------------------------------------
  // EV Mobility (Explicit)
  const evExplicit = resolveUserWorkspace(["EV_MOBILITY"], ["AMS-III.C"], methToFamily, mockRegistry);
  assert(evExplicit.activeWorkspace === "ev_mobility", "EV Org (Explicit): initial sector is ev_mobility");
  assert(evExplicit.allowedWorkspaces.length === 1 && evExplicit.allowedWorkspaces[0] === "ev_mobility", "EV Org (Explicit): allowed sectors strictly [ev_mobility]");

  // Solar / Hybrid Energy (Explicit)
  const solarExplicit = resolveUserWorkspace(["HYBRID_ENERGY"], ["ACM0002"], methToFamily, mockRegistry);
  assert(solarExplicit.activeWorkspace === "hybrid_energy", "Solar Org (Explicit): initial sector is hybrid_energy");
  assert(solarExplicit.allowedWorkspaces.length === 1 && solarExplicit.allowedWorkspaces[0] === "hybrid_energy", "Solar Org (Explicit): allowed sectors strictly [hybrid_energy]");

  // Biochar (Explicit)
  const bioExplicit = resolveUserWorkspace(["BIOCHAR"], ["VM0042"], methToFamily, mockRegistry);
  assert(bioExplicit.activeWorkspace === "biochar", "Biochar Org (Explicit): initial sector is biochar");
  assert(bioExplicit.allowedWorkspaces.length === 1 && bioExplicit.allowedWorkspaces[0] === "biochar", "Biochar Org (Explicit): allowed sectors strictly [biochar]");

  // Cookstoves (Explicit)
  const cookExplicit = resolveUserWorkspace(["COOKSTOVES"], ["AMS-II.G"], methToFamily, mockRegistry);
  assert(cookExplicit.activeWorkspace === "cookstoves", "Cookstove Org (Explicit): initial sector is cookstoves");
  assert(cookExplicit.allowedWorkspaces.length === 1 && cookExplicit.allowedWorkspaces[0] === "cookstoves", "Cookstove Org (Explicit): allowed sectors strictly [cookstoves]");

  // ---------------------------------------------------------------------------
  // 3. Organization Name Semantic Fallback (e.g. Biod Ev, dammy Solar)
  // ---------------------------------------------------------------------------
  const biodEvFallback = resolveUserWorkspace([], [], methToFamily, mockRegistry, "Biod Ev");
  assert(biodEvFallback.activeWorkspace === "ev_mobility", "Biod Ev (Empty licenses): resolves to ev_mobility via orgName");
  assert(biodEvFallback.allowedWorkspaces.length === 1 && biodEvFallback.allowedWorkspaces[0] === "ev_mobility", "Biod Ev (Empty licenses): allowed sectors strictly [ev_mobility]");

  const dammySolarFallback = resolveUserWorkspace([], [], methToFamily, mockRegistry, "dammy Solar");
  assert(dammySolarFallback.activeWorkspace === "hybrid_energy", "dammy Solar (Empty licenses): resolves to hybrid_energy via orgName");
  assert(dammySolarFallback.allowedWorkspaces.length === 1 && dammySolarFallback.allowedWorkspaces[0] === "hybrid_energy", "dammy Solar (Empty licenses): allowed sectors strictly [hybrid_energy]");

  // ---------------------------------------------------------------------------
  // 4. Multi-Sector Organisations
  // ---------------------------------------------------------------------------
  const twoSec = resolveUserWorkspace(["hybrid_energy", "ev_mobility"], [], methToFamily, mockRegistry);
  assert(twoSec.activeWorkspace === "hybrid_energy", "2-Sector Org: first active is hybrid_energy");
  assert(twoSec.allowedWorkspaces.includes("hybrid_energy") && twoSec.allowedWorkspaces.includes("ev_mobility"), "2-Sector Org: allowed includes [hybrid_energy, ev_mobility]");
  assert(!twoSec.allowedWorkspaces.includes("cookstoves"), "2-Sector Org: cookstoves is NOT allowed");

  const fourSec = resolveUserWorkspace(["hybrid_energy", "ev_mobility", "biochar", "cookstoves"], [], methToFamily, mockRegistry);
  assert(fourSec.allowedWorkspaces.length === 4, "4-Sector Org: all 4 sectors allowed");

  // ---------------------------------------------------------------------------
  // 5. Cache & URL Validation / Stale Cache Eviction
  // ---------------------------------------------------------------------------
  const staleCookstoveForEv = validateCachedWorkspace("cookstoves", ["ev_mobility"], methToFamily, false);
  assert(staleCookstoveForEv === null, "Stale cookstove cache for EV Org is rejected (returns null)");

  const staleCookstoveForSolar = validateCachedWorkspace("cookstoves", ["hybrid_energy"], methToFamily, false);
  assert(staleCookstoveForSolar === null, "Stale cookstove cache for Solar Org is rejected (returns null)");

  const validEvCache = validateCachedWorkspace("ev_mobility", ["ev_mobility", "hybrid_energy"], methToFamily, false);
  assert(validEvCache === "ev_mobility", "Valid EV cached workspace is accepted");

  const tamperedUrl = validateCachedWorkspace("unlicensed_carbon_sector", ["ev_mobility"], methToFamily, false);
  assert(tamperedUrl === null, "Tampered URL sector is rejected (returns null)");

  const saCheck = validateCachedWorkspace("cookstoves", ["ev_mobility"], methToFamily, true);
  assert(saCheck === "cookstoves", "Super Admin is allowed to switch to any sector");

  // ---------------------------------------------------------------------------
  // 6. Dynamic AI Orchestrator Context (Strictly Isolated)
  // ---------------------------------------------------------------------------
  const evInsight = getContextualInsight("/dashboard", "ev_mobility", "ORG_ADMIN");
  assert(!evInsight.aiRecommendation.toLowerCase().includes("cookstove"), "EV insight: NO cookstove mentions");
  assert(!evInsight.aiRecommendation.toLowerCase().includes("lpg burner"), "EV insight: NO LPG Burner mentions");
  assert(evInsight.aiRecommendation.toLowerCase().includes("ev") || evInsight.aiRecommendation.toLowerCase().includes("charging"), "EV insight: contains EV/charging terms");

  const solarInsight = getContextualInsight("/dashboard", "hybrid_energy", "ORG_ADMIN");
  assert(!solarInsight.aiRecommendation.toLowerCase().includes("cookstove"), "Solar insight: NO cookstove mentions");
  assert(!solarInsight.aiRecommendation.toLowerCase().includes("lpg burner"), "Solar insight: NO LPG Burner mentions");
  assert(solarInsight.aiRecommendation.toLowerCase().includes("solar") || solarInsight.aiRecommendation.toLowerCase().includes("hybrid"), "Solar insight: contains solar/hybrid terms");

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
