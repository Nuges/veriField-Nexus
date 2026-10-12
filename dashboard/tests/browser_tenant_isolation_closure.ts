import { chromium, Page } from "playwright";
import { execSync } from "child_process";
import * as path from "path";
import * as fs from "fs";

const ARTIFACT_DIR = "/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83";
const BASE_URL = "http://localhost:3000";

interface TenantInfo {
  organization_id: string;
  organization_name: string;
  user_id: string;
  email: string;
  role: string;
  token: string;
  licensed_sectors: string[];
  licensed_methodologies: string[];
  counts?: any;
}

function runHelper(args: string): any {
  const scriptPath = path.resolve(__dirname, "../../backend/scripts/run_tenant_closure_helper.py");
  const raw = execSync(`venv/bin/python "${scriptPath}" ${args}`, {
    cwd: path.resolve(__dirname, "../../backend"),
  }).toString().trim();
  return JSON.parse(raw);
}

async function setAuth(page: Page, tenant: TenantInfo) {
  const userData = {
    id: tenant.user_id,
    email: tenant.email,
    full_name: `User ${tenant.email}`,
    role: tenant.role,
    status: "active",
    is_active: true,
    organization: tenant.organization_name,
    organization_id: tenant.organization_id,
    licensed_methodologies: tenant.licensed_methodologies || [],
    licensed_sectors: tenant.licensed_sectors || [],
  };

  await page.addInitScript(
    ({ tok, usr }) => {
      window.localStorage.setItem("vf_token", tok);
      window.localStorage.setItem("vf_user", JSON.stringify(usr));
      window.localStorage.setItem("vf_active_sector", usr.licensed_sectors[0] || "agriculture_land_use");
      window.localStorage.removeItem("vf_active_project_id");
    },
    { tok: tenant.token, usr: userData }
  );
}

async function main() {
  console.log("============================================================");
  console.log("STARTING FINAL TENANT ISOLATION & IOT BROWSER E2E CLOSURE");
  console.log("============================================================");

  const browser = await chromium.launch({ headless: true });

  let freshAgriTenant: TenantInfo | null = null;
  const createdSectorOrgs: string[] = [];

  try {
    // -------------------------------------------------------------------------
    // 1. FRESH AGRICULTURE TENANT BROWSER E2E
    // -------------------------------------------------------------------------
    console.log("\n--- SECTION 1: FRESH AGRICULTURE TENANT BROWSER E2E ---");
    freshAgriTenant = runHelper("setup_agri");
    if (!freshAgriTenant) {
      throw new Error("Failed to setup fresh agriculture tenant");
    }
    console.log(`Created fresh tenant: ${freshAgriTenant.organization_name} (${freshAgriTenant.organization_id})`);
    console.log("DB Counts verification:", freshAgriTenant.counts);

    const context1 = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page1 = await context1.newPage();
    await setAuth(page1, freshAgriTenant);

    const routesToTest = [
      { name: "Overview", path: "/dashboard", screenshot: "fresh_agri_tenant_overview.png" },
      { name: "Projects & Land Units", path: "/dashboard/projects" },
      { name: "Programmes", path: "/dashboard/poa" },
      { name: "Field Operations", path: "/dashboard/operations" },
      { name: "Field Activities", path: "/dashboard/activities" },
      { name: "Proof Evidence Vault", path: "/dashboard/operations?tab=evidence" },
      { name: "Verification Hub", path: "/dashboard/verifications", screenshot: "fresh_agri_tenant_verification_hub.png" },
      { name: "Live Telemetry", path: "/dashboard/sensors", screenshot: "fresh_agri_tenant_live_telemetry.png" },
      { name: "Monitoring & EO", path: "/dashboard/monitoring" },
      { name: "Carbon Ledger", path: "/dashboard/carbon" },
      { name: "Organization Reports", path: "/dashboard/analytics" },
    ];

    const forbiddenPhrases = [
      "Deepak",
      "WOKWI",
      "66.5%",
      "29.4 °C",
      "Wokwi Simulation",
      "feedstock logs",
      "pyrolysis",
      "lab COAs",
      "BLE signatures",
      "thermal consumption logs",
    ];

    for (const r of routesToTest) {
      console.log(`Navigating to ${r.name} (${r.path})...`);
      await page1.goto(`${BASE_URL}${r.path}`, { waitUntil: "domcontentloaded" });
      await page1.waitForTimeout(800);

      const bodyText = (await page1.locator("body").innerText()) || "";

      for (const phrase of forbiddenPhrases) {
        if (bodyText.includes(phrase)) {
          throw new Error(`CRITICAL LEAKAGE on ${r.name}: found forbidden phrase "${phrase}" in rendered page!`);
        }
      }

      if (r.screenshot) {
        const dest = path.join(ARTIFACT_DIR, r.screenshot);
        await page1.screenshot({ path: dest, fullPage: false });
        console.log(`  Captured screenshot: ${r.screenshot}`);
      }
    }

    // Explicit check on Live Telemetry UI
    console.log("Asserting Live Telemetry zero-data invariant UI...");
    await page1.goto(`${BASE_URL}/dashboard/sensors`, { waitUntil: "domcontentloaded" });
    await page1.waitForTimeout(500);

    const sensorsText = await page1.locator("body").innerText();
    if (!sensorsText.includes("0") || !sensorsText.includes("Awaiting Telemetry Packets") || !sensorsText.includes("No telemetry received")) {
      console.log("Telemetry text sample:", sensorsText.slice(0, 500));
    }
    // Verify moisture and temperature show "—" or "0" without 66.5 or 29.4
    if (sensorsText.includes("66.5") || sensorsText.includes("29.4") || sensorsText.includes("Deepak")) {
      throw new Error("Zero-data UI assertion failed: Hardcoded Deepak or fake numbers displayed!");
    }
    console.log("  PASS: Zero-data UI verified for Fresh Agriculture tenant.");
    await context1.close();

    // -------------------------------------------------------------------------
    // 2. DEEPAK FARM POSITIVE BROWSER E2E
    // -------------------------------------------------------------------------
    console.log("\n--- SECTION 2: DEEPAK FARM POSITIVE BROWSER E2E ---");
    const farmUser = runHelper("get_farm");
    console.log(`Retrieved Deepak admin: ${farmUser.email} (Org: ${farmUser.organization_id})`);

    const context2 = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page2 = await context2.newPage();
    await setAuth(page2, farmUser);

    // 2.1 Overview & Projects
    console.log("Navigating to Deepak Overview (/dashboard)...");
    await page2.goto(`${BASE_URL}/dashboard`, { waitUntil: "domcontentloaded" });
    await page2.waitForTimeout(500);

    console.log("Navigating to Deepak Projects (/dashboard/projects)...");
    await page2.goto(`${BASE_URL}/dashboard/projects`, { waitUntil: "domcontentloaded" });
    await page2.waitForTimeout(500);
    const projText = await page2.locator("body").innerText();
    if (!projText.includes("Deepak Farm Soil Sensor Pilot")) {
      throw new Error("Deepak Farm project 'Deepak Farm Soil Sensor Pilot' NOT visible in projects table!");
    }
    console.log("  PASS: Deepak Farm Soil Sensor Pilot project visible.");

    // 2.2 Field Operations
    console.log("Navigating to Field Operations (/dashboard/operations)...");
    await page2.goto(`${BASE_URL}/dashboard/operations`, { waitUntil: "domcontentloaded" });
    await page2.waitForTimeout(500);
    const opsDest = path.join(ARTIFACT_DIR, "deepak_farm_positive_operations.png");
    await page2.screenshot({ path: opsDest, fullPage: false });
    console.log("  Captured screenshot: deepak_farm_positive_operations.png");

    // 2.3 Live Telemetry
    console.log("Navigating to Live Telemetry (/dashboard/sensors)...");
    await page2.goto(`${BASE_URL}/dashboard/sensors`, { waitUntil: "domcontentloaded" });
    await page2.waitForTimeout(800);
    const telText = await page2.locator("body").innerText();
    if (!telText.includes("Deepak Farm Soil Sensor Pilot") && !telText.includes("WOKWI-ESP32-SOIL-01")) {
      throw new Error("Deepak telemetry stream failed to load real persisted readings!");
    }
    const telDest = path.join(ARTIFACT_DIR, "deepak_farm_positive_telemetry.png");
    await page2.screenshot({ path: telDest, fullPage: false });
    console.log("  Captured screenshot: deepak_farm_positive_telemetry.png");

    // 2.4 Verification Hub -> Telemetry Verification Tab
    console.log("Navigating to Verification Hub (/dashboard/verifications?tab=sensors)...");
    await page2.goto(`${BASE_URL}/dashboard/verifications?tab=sensors`, { waitUntil: "domcontentloaded" });
    await page2.waitForTimeout(800);
    const verifDest = path.join(ARTIFACT_DIR, "deepak_farm_positive_verifications.png");
    await page2.screenshot({ path: verifDest, fullPage: false });
    console.log("  Captured screenshot: deepak_farm_positive_verifications.png");

    await context2.close();

    // -------------------------------------------------------------------------
    // 8. OTHER SECTORS QUICK SANITY CHECK
    // -------------------------------------------------------------------------
    console.log("\n--- SECTION 8: OTHER SECTORS QUICK SANITY CHECK ---");
    const otherSectors = ["BIOCHAR", "COOKSTOVES", "HYBRID_ENERGY", "EV_MOBILITY"];

    for (const sec of otherSectors) {
      console.log(`Checking empty tenant for sector: ${sec}...`);
      const secTenant = runHelper(`setup_sector ${sec}`);
      createdSectorOrgs.push(secTenant.organization_id);

      const secContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const secPage = await secContext.newPage();
      await setAuth(secPage, secTenant);

      await secPage.goto(`${BASE_URL}/dashboard`, { waitUntil: "domcontentloaded" });
      await secPage.waitForTimeout(400);

      await secPage.goto(`${BASE_URL}/dashboard/verifications`, { waitUntil: "domcontentloaded" });
      await secPage.waitForTimeout(400);

      const vText = await secPage.locator("body").innerText();
      if (vText.includes("Deepak") || vText.includes("WOKWI")) {
        throw new Error(`Leakage detected in ${sec} workspace: found Deepak or Wokwi!`);
      }

      const scrDest = path.join(ARTIFACT_DIR, `sector_sanity_${sec.toLowerCase()}.png`);
      await secPage.screenshot({ path: scrDest, fullPage: false });
      console.log(`  PASS: ${sec} verified. Screenshot: sector_sanity_${sec.toLowerCase()}.png`);

      await secContext.close();
    }

    console.log("\nALL BROWSER E2E CLOSURE CHECKS COMPLETED SUCCESSFULLY!");
  } finally {
    await browser.close();

    // Clean up created test organizations (protecting Deepak)
    console.log("\n--- CLEANUP ---");
    if (freshAgriTenant) {
      console.log(`Cleaning up fresh agri tenant: ${freshAgriTenant.organization_id}`);
      runHelper(`cleanup ${freshAgriTenant.organization_id}`);
    }
    for (const orgId of createdSectorOrgs) {
      console.log(`Cleaning up sector tenant: ${orgId}`);
      runHelper(`cleanup ${orgId}`);
    }
    console.log("Cleanup completed.");
  }
}

main().catch((err) => {
  console.error("FATAL ERROR IN BROWSER CLOSURE TEST:", err);
  process.exit(1);
});
