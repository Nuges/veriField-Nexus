import { chromium } from "playwright";
import { execSync } from "child_process";
import * as path from "path";
import * as fs from "fs";

const ARTIFACT_DIR = "/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83";
const BASE_URL = "http://localhost:3000";
const API_URL = "http://localhost:8000/api/v1";

interface TenantInfo {
  organization_id: string;
  organization_name: string;
  user_id: string;
  email: string;
  role: string;
  token: string;
  licensed_sectors: string[];
  licensed_methodologies: string[];
  tag: string;
}

function setupTenant(): TenantInfo {
  const scriptPath = path.resolve(__dirname, "../../backend/scripts/run_release_persistence_helper.py");
  const raw = execSync(`venv/bin/python "${scriptPath}" setup`, {
    cwd: path.resolve(__dirname, "../../backend"),
  }).toString().trim();
  return JSON.parse(raw);
}

function cleanupTenant(orgId: string): void {
  const scriptPath = path.resolve(__dirname, "../../backend/scripts/run_release_persistence_helper.py");
  execSync(`venv/bin/python "${scriptPath}" cleanup "${orgId}"`, {
    cwd: path.resolve(__dirname, "../../backend"),
  });
}

interface PathwayResult {
  sector: string;
  methodology: string;
  version: string;
  createdInUI: boolean;
  persistedInUI: boolean;
  persistedInAPI: boolean;
  calculationEngineEnabled: boolean;
  projectCode?: string;
  projectId?: string;
  error?: string;
}

async function runReleaseProjectPersistenceAudit() {
  console.log("=== STARTING RELEASE PROJECT PERSISTENCE AUDIT ===");
  const tenant = setupTenant();
  console.log(`[SETUP] Seeded isolated tenant: ${tenant.organization_name} (${tenant.organization_id})`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const auditResults: Record<string, PathwayResult> = {};
  const secondaryCheckResults: Record<string, string[]> = {};

  try {
    // Inject auth into browser session
    const userData = {
      id: tenant.user_id,
      email: tenant.email,
      full_name: `Release Tester ${tenant.tag}`,
      role: tenant.role,
      status: "active",
      is_active: true,
      organization: tenant.organization_name,
      organization_id: tenant.organization_id,
      licensed_methodologies: tenant.licensed_methodologies,
      licensed_sectors: tenant.licensed_sectors,
    };

    await page.addInitScript(
      ({ tok, usr }) => {
        window.localStorage.setItem("vf_token", tok);
        window.localStorage.setItem("vf_user", JSON.stringify(usr));
      },
      { tok: tenant.token, usr: userData }
    );

    // List of 5 Pathways to test
    const pathways = [
      {
        sectorKey: "agriculture_land_use",
        sectorCode: "AGRICULTURE_LAND_USE",
        targetMethodologyCode: "VM0042",
        targetVersion: "2.2",
        expectedGated: false,
        projectName: "Live-Release-Agriculture-VM0042",
        screenshotName: "release_check_agriculture_project.png",
        secondaryCodes: ["VM0051", "VM0047", "VM0032"],
      },
      {
        sectorKey: "biochar",
        sectorCode: "BIOCHAR",
        targetMethodologyCode: "VM0044",
        targetVersion: "1.2",
        expectedGated: false,
        projectName: "Live-Release-Biochar-VM0044",
        screenshotName: "release_check_biochar_project.png",
        secondaryCodes: ["PURO_BIOCHAR_2025", "BIOCHAR_C_SINK"],
      },
      {
        sectorKey: "cookstoves",
        sectorCode: "COOKSTOVES",
        targetMethodologyCode: "AMS_II_G",
        targetVersion: "14.0",
        expectedGated: true,
        projectName: "Live-Release-Cookstoves-AMSIIG",
        screenshotName: "release_check_cookstoves_project.png",
        secondaryCodes: ["GS_MECD", "VM0050"],
      },
      {
        sectorKey: "hybrid_energy",
        sectorCode: "HYBRID_ENERGY",
        targetMethodologyCode: "AMS_I_F",
        targetVersion: "5.0",
        expectedGated: true,
        projectName: "Live-Release-Hybrid-AMSIF",
        screenshotName: "release_check_hybrid_project.png",
        secondaryCodes: ["AMS_I_L", "ACM0002"],
      },
      {
        sectorKey: "ev_mobility",
        sectorCode: "EV_MOBILITY",
        targetMethodologyCode: "VM0038",
        targetVersion: "1.1",
        expectedGated: true,
        projectName: "Live-Release-EV-VM0038",
        screenshotName: "release_check_ev_project.png",
        secondaryCodes: ["AMS_III_C"],
      },
    ];

    for (const pw of pathways) {
      console.log(`\n=======================================================`);
      console.log(`[PATHWAY AUDIT] ${pw.sectorCode} -> ${pw.targetMethodologyCode} v${pw.targetVersion}`);
      console.log(`=======================================================`);

      const targetUrl = `${BASE_URL}/dashboard/projects?workspace=${pw.sectorKey}`;
      await page.goto(targetUrl, { waitUntil: "domcontentloaded" });
      await page.evaluate(({ sec }) => {
        window.localStorage.setItem("vf_active_sector", sec);
      }, { sec: pw.sectorKey });
      await page.waitForTimeout(600);

      // 2. Click "Create New Project"
      const createBtn = page.locator("button", { hasText: "Create New Project" });
      await createBtn.waitFor({ state: "visible", timeout: 8000 });
      await createBtn.click();
      await page.waitForTimeout(400);

      // 3. Inspect Methodology dropdown options
      const methSelect = page.locator("#modal-project-methodology-select");
      await methSelect.waitFor({ state: "visible", timeout: 8000 });
      const optionsText = await methSelect.locator("option").allTextContents();
      console.log(`  Modal methodology options in ${pw.sectorCode}:`, optionsText);

      // Verify secondary methodology codes are present
      secondaryCheckResults[pw.sectorCode] = optionsText;
      for (const secCode of pw.secondaryCodes) {
        const foundSec = optionsText.some(opt => opt.includes(secCode) || opt.includes(secCode.replace(/_/g, "-")));
        console.log(`  Secondary methodology check: ${secCode} present? ${foundSec}`);
        if (!foundSec) {
          throw new Error(`Secondary methodology ${secCode} missing in sector ${pw.sectorCode}`);
        }
      }

      // 4. Find option corresponding to target methodology
      const targetOption = optionsText.find(opt => opt.includes(pw.targetMethodologyCode) || opt.includes(pw.targetMethodologyCode.replace(/_/g, "-")));
      if (!targetOption) {
        throw new Error(`Target methodology ${pw.targetMethodologyCode} not found in options for ${pw.sectorCode}`);
      }

      // Select target option
      await methSelect.selectOption({ label: targetOption });
      await page.waitForTimeout(400);

      // 5. If version select is available, select target version
      const versionSelect = page.locator("#modal-project-version-select");
      if (await versionSelect.isVisible()) {
        try {
          await versionSelect.selectOption(pw.targetVersion);
          console.log(`  Selected explicit version ${pw.targetVersion}`);
        } catch {
          // Version might already be selected
        }
      }

      // 6. Verify Gated Notice display
      const modalText = await page.locator("div.fixed.inset-0").innerText();
      if (pw.expectedGated) {
        const hasGatedNotice = modalText.includes("VeriField calculation engine for this methodology is not yet enabled");
        console.log(`  Gated notice displayed correctly in modal: ${hasGatedNotice}`);
        if (!hasGatedNotice) {
          throw new Error(`Expected calculation gate notice missing in modal for ${pw.targetMethodologyCode}`);
        }
      }

      // 7. Fill Project Name
      const nameInput = page.locator("input[placeholder*='e.g.']").first();
      await nameInput.fill(pw.projectName);

      // 8. Submit modal
      const submitBtn = page.locator("#modal-register-project-btn");
      await submitBtn.waitFor({ state: "visible", timeout: 8000 });
      await submitBtn.click();
      await page.waitForTimeout(1500);

      // 9. Verify project appears in Registered Climate Projects table
      const projectTableText = await page.locator("table").innerText();
      const projectInTable = projectTableText.includes(pw.projectName);
      console.log(`  Project rendered in table immediately: ${projectInTable}`);

      // 10. Refresh browser page (reload) and verify persistence in UI
      console.log(`  Refreshing browser page to confirm UI persistence...`);
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(800);

      const refreshedTableText = await page.locator("table").innerText();
      const projectPersistedInTable = refreshedTableText.includes(pw.projectName);
      console.log(`  Project persists in table after reload: ${projectPersistedInTable}`);

      // Capture screenshot
      const shotPath = path.join(ARTIFACT_DIR, pw.screenshotName);
      await page.screenshot({ path: shotPath, fullPage: false });
      console.log(`  Saved screenshot: ${shotPath}`);

      // 11. Fetch project via API directly to verify database persistence & invariants
      const apiRes = await fetch(`${API_URL}/projects`, {
        headers: { Authorization: `Bearer ${tenant.token}` },
      });
      const apiData = await apiRes.json();
      const projectList = Array.isArray(apiData) ? apiData : (apiData.items || []);
      const savedProject = projectList.find((p: any) => p.name === pw.projectName);

      if (!savedProject) {
        throw new Error(`Project ${pw.projectName} not found in GET /api/v1/projects`);
      }

      const bp = savedProject.baseline_parameters || {};
      const persistedMeth = bp.methodology_code;
      const persistedVer = bp.methodology_version;
      const calcEnabled = bp.calculation_engine_enabled;

      console.log(`  API Persistence Verified:`);
      console.log(`    Project Code:             ${savedProject.project_code}`);
      console.log(`    Persisted Methodology:    ${persistedMeth}`);
      console.log(`    Persisted Version:        ${persistedVer}`);
      console.log(`    Calculation Enabled:      ${calcEnabled}`);

      const methMatches = persistedMeth === pw.targetMethodologyCode || persistedMeth === pw.targetMethodologyCode.replace(/_/g, "-");
      const verMatches = persistedVer === pw.targetVersion;
      const gatePreserved = pw.expectedGated ? (calcEnabled === false) : (calcEnabled === true);

      if (!methMatches) {
        throw new Error(`Methodology mismatch in DB: expected ${pw.targetMethodologyCode}, got ${persistedMeth}`);
      }
      if (!verMatches) {
        throw new Error(`Version mismatch in DB: expected ${pw.targetVersion}, got ${persistedVer}`);
      }
      if (!gatePreserved) {
        throw new Error(`Calculation gate breach: expected calcEnabled=${!pw.expectedGated}, got ${calcEnabled}`);
      }

      auditResults[pw.sectorCode] = {
        sector: pw.sectorCode,
        methodology: persistedMeth,
        version: persistedVer,
        createdInUI: projectInTable,
        persistedInUI: projectPersistedInTable,
        persistedInAPI: true,
        calculationEngineEnabled: calcEnabled,
        projectCode: savedProject.project_code,
        projectId: savedProject.id,
      };
    }

    console.log("\n=======================================================");
    console.log("=== ALL 5 PROJECT PATHWAYS VERIFIED SUCCESSFULLY ===");
    console.log("=======================================================");
    console.log(JSON.stringify(auditResults, null, 2));

  } finally {
    await browser.close();
    // Clean up isolated test organization
    console.log(`\n[CLEANUP] Cleaning up test tenant ${tenant.organization_id}...`);
    cleanupTenant(tenant.organization_id);
    console.log(`[CLEANUP] Cleaned up test tenant successfully.`);
  }
}

runReleaseProjectPersistenceAudit().catch(err => {
  console.error("FATAL PERSISTENCE TEST ERROR:", err);
  process.exit(1);
});
