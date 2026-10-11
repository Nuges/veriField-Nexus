import { chromium } from "playwright";
import * as fs from "fs";
import * as path from "path";

const ARTIFACT_DIR = "/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-85ae371d66c97152".replace(
  "85ae371d66c97152",
  ""
).startsWith("/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-")
  ? "/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83"
  : "/tmp";

async function runBrowserEvidence() {
  console.log("=== STARTING OFFICIAL BROWSER VERIFICATION AUDIT ===");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  const results: Record<string, any> = {};

  // ---------------------------------------------------------------------------
  // 1. CLEAN COOKSTOVES (/signup)
  // ---------------------------------------------------------------------------
  console.log("\n[BROWSER AUDIT 1] Navigating to /signup for CLEAN COOKSTOVES...");
  await page.goto("http://localhost:3000/signup", { waitUntil: "networkidle" });
  await page.waitForSelector("#primary-operating-sector");

  await page.selectOption("#primary-operating-sector", "COOKSTOVES");
  await page.waitForTimeout(500);

  const cookstoveOptions = await page.locator("#primary-operating-methodology option").allTextContents();
  console.log("  Cookstoves Dropdown Options:", cookstoveOptions);

  const cookstoveAmsIIG = cookstoveOptions.find((opt) => opt.includes("AMS_II_G") || opt.includes("AMS-II.G"));
  console.log("  Cookstoves AMS-II.G entry:", cookstoveAmsIIG);

  const cookstoveScreenshot = path.join(ARTIFACT_DIR, "browser_evidence_cookstoves_signup.png");
  await page.screenshot({ path: cookstoveScreenshot, fullPage: false });
  console.log("  Saved screenshot:", cookstoveScreenshot);

  results.cookstoves = {
    sector: "COOKSTOVES",
    options: cookstoveOptions,
    ams_ii_g_displayed: !!cookstoveAmsIIG,
    entry: cookstoveAmsIIG,
    screenshot: cookstoveScreenshot,
  };

  // ---------------------------------------------------------------------------
  // 2. HYBRID ENERGY (/signup)
  // ---------------------------------------------------------------------------
  console.log("\n[BROWSER AUDIT 2] Selecting HYBRID_ENERGY on /signup...");
  await page.selectOption("#primary-operating-sector", "HYBRID_ENERGY");
  await page.waitForTimeout(500);

  const hybridOptions = await page.locator("#primary-operating-methodology option").allTextContents();
  console.log("  Hybrid Energy Dropdown Options:", hybridOptions);

  const hybridScreenshot = path.join(ARTIFACT_DIR, "browser_evidence_hybrid_signup.png");
  await page.screenshot({ path: hybridScreenshot, fullPage: false });
  console.log("  Saved screenshot:", hybridScreenshot);

  const amsIF = hybridOptions.find((opt) => opt.includes("AMS_I_F") || opt.includes("AMS-I.F"));
  const amsIL = hybridOptions.find((opt) => opt.includes("AMS_I_L") || opt.includes("AMS-I.L"));
  const acm0002 = hybridOptions.find((opt) => opt.includes("ACM0002"));

  results.hybrid_energy = {
    sector: "HYBRID_ENERGY",
    options: hybridOptions,
    ams_i_f_displayed: !!amsIF,
    ams_i_l_displayed: !!amsIL,
    acm0002_displayed: !!acm0002,
    screenshot: hybridScreenshot,
  };

  // ---------------------------------------------------------------------------
  // 3. EV MOBILITY (/signup)
  // ---------------------------------------------------------------------------
  console.log("\n[BROWSER AUDIT 3] Selecting EV_MOBILITY on /signup...");
  await page.selectOption("#primary-operating-sector", "EV_MOBILITY");
  await page.waitForTimeout(500);

  const evOptions = await page.locator("#primary-operating-methodology option").allTextContents();
  console.log("  EV Mobility Dropdown Options:", evOptions);

  const evScreenshot = path.join(ARTIFACT_DIR, "browser_evidence_ev_signup.png");
  await page.screenshot({ path: evScreenshot, fullPage: false });
  console.log("  Saved screenshot:", evScreenshot);

  const vm0038 = evOptions.find((opt) => opt.includes("VM0038"));
  const amsIIIC = evOptions.find((opt) => opt.includes("AMS_III_C") || opt.includes("AMS-III.C"));

  results.ev_mobility = {
    sector: "EV_MOBILITY",
    options: evOptions,
    vm0038_displayed: !!vm0038,
    ams_iii_c_displayed: !!amsIIIC,
    screenshot: evScreenshot,
  };

  // ---------------------------------------------------------------------------
  // 4. METHODOLOGY CALCULATION GATING EVIDENCE (/dashboard/methodologies)
  // ---------------------------------------------------------------------------
  console.log("\n[BROWSER AUDIT 4] Auditing calculation gate badges on /dashboard/methodologies...");

  const mockUser = {
    id: "00000000-0000-0000-0000-000000000001",
    email: "auditor@verifield.test",
    full_name: "Audit Officer",
    role: "ORG_ADMIN",
    status: "active",
    is_active: true,
    organization: "VeriField Internal Audit",
    organization_id: "00000000-0000-0000-0000-000000000002",
    licensed_methodologies: ["AMS_II_G", "AMS_I_F", "VM0038"],
    licensed_sectors: ["cookstoves", "hybrid_energy", "ev_mobility"],
  };

  // Test Cookstoves Gating
  await page.addInitScript(({ u }) => {
    window.localStorage.setItem("vf_token", "test_audit_token");
    window.localStorage.setItem("vf_user", JSON.stringify(u));
    window.localStorage.setItem("vf_active_sector", "cookstoves");
    window.localStorage.setItem("vf_active_methodology", "AMS_II_G");
  }, { u: mockUser });

  await page.goto("http://localhost:3000/dashboard/methodologies", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);

  const bodyTextCs = await page.locator("body").innerText();
  const hasGatedBadgeCs = bodyTextCs.includes("METHODOLOGY ENGINE GATED") || bodyTextCs.includes("SUPPORTED PILOT SECTOR");
  const hasClosedNoticeCs = bodyTextCs.includes("Official production quantification is not yet enabled") || bodyTextCs.includes("locked");
  const gatingCsScreenshot = path.join(ARTIFACT_DIR, "browser_evidence_cookstoves_gating.png");
  await page.screenshot({ path: gatingCsScreenshot, fullPage: false });

  results.cookstoves_gating = {
    sector: "cookstoves",
    methodology: "AMS_II_G",
    hasGatedBadge: hasGatedBadgeCs,
    hasClosedNotice: hasClosedNoticeCs,
    screenshot: gatingCsScreenshot,
  };
  console.log("  Cookstoves calculation gate closed:", hasGatedBadgeCs, hasClosedNoticeCs);

  // Test Hybrid Energy Gating
  await page.evaluate(() => {
    window.localStorage.setItem("vf_active_sector", "hybrid_energy");
    window.localStorage.setItem("vf_active_methodology", "AMS_I_F");
  });
  await page.goto("http://localhost:3000/dashboard/methodologies", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);

  const bodyTextHe = await page.locator("body").innerText();
  const hasGatedBadgeHe = bodyTextHe.includes("METHODOLOGY ENGINE GATED") || bodyTextHe.includes("SUPPORTED PILOT SECTOR");
  const gatingHeScreenshot = path.join(ARTIFACT_DIR, "browser_evidence_hybrid_gating.png");
  await page.screenshot({ path: gatingHeScreenshot, fullPage: false });

  results.hybrid_gating = {
    sector: "hybrid_energy",
    methodology: "AMS_I_F",
    hasGatedBadge: hasGatedBadgeHe,
    screenshot: gatingHeScreenshot,
  };
  console.log("  Hybrid Energy calculation gate closed:", hasGatedBadgeHe);

  // Test EV Mobility Gating
  await page.evaluate(() => {
    window.localStorage.setItem("vf_active_sector", "ev_mobility");
    window.localStorage.setItem("vf_active_methodology", "VM0038");
  });
  await page.goto("http://localhost:3000/dashboard/methodologies", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);

  const bodyTextEv = await page.locator("body").innerText();
  const hasGatedBadgeEv = bodyTextEv.includes("METHODOLOGY ENGINE GATED") || bodyTextEv.includes("SUPPORTED PILOT SECTOR");
  const gatingEvScreenshot = path.join(ARTIFACT_DIR, "browser_evidence_ev_gating.png");
  await page.screenshot({ path: gatingEvScreenshot, fullPage: false });

  results.ev_gating = {
    sector: "ev_mobility",
    methodology: "VM0038",
    hasGatedBadge: hasGatedBadgeEv,
    screenshot: gatingEvScreenshot,
  };
  console.log("  EV Mobility calculation gate closed:", hasGatedBadgeEv);

  await browser.close();

  console.log("\n=== BROWSER EVIDENCE AUDIT COMPLETE ===");
  console.log(JSON.stringify(results, null, 2));
}

runBrowserEvidence().catch((err) => {
  console.error("FATAL BROWSER AUDIT ERROR:", err);
  process.exit(1);
});
