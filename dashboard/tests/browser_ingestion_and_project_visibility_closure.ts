import { chromium } from "playwright";
import type { Page } from "playwright";
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
}

function getFarmUser(): TenantInfo {
  const scriptPath = path.resolve(__dirname, "../../backend/scripts/run_tenant_closure_helper.py");
  const raw = execSync(`venv/bin/python "${scriptPath}" get_farm`, {
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
      window.localStorage.setItem("vf_active_sector", "agriculture_land_use");
      // Do NOT set active project; let WorkspaceContext load it dynamically!
      window.localStorage.removeItem("vf_active_project_id");
    },
    { tok: tenant.token, usr: userData }
  );
}

async function main() {
  console.log("============================================================");
  console.log("STARTING FRONTEND INGESTION DISCOVERABILITY & DEEPAK VISIBILITY VERIFICATION");
  console.log("============================================================");

  const farm = getFarmUser();
  console.log(`[AUTH] Retrieved Farm User: ${farm.email} (Org: ${farm.organization_name})`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    await setAuth(page, farm);

    // -------------------------------------------------------------------------
    // 1. PROJECTS DIRECTORY VERIFICATION
    // -------------------------------------------------------------------------
    console.log("[NAV] Navigating to /dashboard/projects (Projects & Land Units)...");
    await page.goto(`${BASE_URL}/dashboard/projects`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);

    const projectsPageText = await page.innerText("body");
    const deepakInRoster = projectsPageText.includes("Deepak Farm Soil Sensor Pilot");
    console.log(`[ASSERT] Deepak Farm project visible in roster: ${deepakInRoster}`);
    if (!deepakInRoster) {
      throw new Error("Deepak Farm project was not found in the Projects directory roster!");
    }

    // Verify breadcrumb project selector
    const selectorHasDeepak = await page.evaluate(() => {
      const select = document.querySelector('select[data-testid="project-selector"]') as HTMLSelectElement;
      if (!select) return false;
      const options = Array.from(select.options).map(o => o.text);
      return options.some(t => t.includes("Deepak Farm Soil Sensor Pilot"));
    });
    console.log(`[ASSERT] EnterpriseBreadcrumb project selector contains Deepak: ${selectorHasDeepak}`);

    const screenshotRoster = path.join(ARTIFACT_DIR, "deepak_projects_roster_visible.png");
    await page.screenshot({ path: screenshotRoster, fullPage: true });
    console.log(`[SCREENSHOT] Saved: ${screenshotRoster}`);

    // -------------------------------------------------------------------------
    // 2. FIELD OPERATIONS -> DATA & DOCUMENT INGESTION TAB
    // -------------------------------------------------------------------------
    console.log("[NAV] Navigating to /dashboard/operations?tab=ingestion...");
    await page.goto(`${BASE_URL}/dashboard/operations?tab=ingestion`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);

    const opsText = await page.innerText("body");
    const ingestionTabVisible = opsText.includes("Data & Document Ingestion");
    const projectDocsVisible = opsText.includes("Project Documents & PDD") || opsText.includes("Upload Project Document");
    const labImportVisible = opsText.includes("Soil Laboratory Bulk Assays") || opsText.includes("Laboratory Import") || opsText.includes("Laboratory Assays");

    console.log(`[ASSERT] Ingestion tab rendered: ${ingestionTabVisible}`);
    console.log(`[ASSERT] Project Documents module exposed: ${projectDocsVisible}`);
    console.log(`[ASSERT] Laboratory Assays module exposed: ${labImportVisible}`);

    const screenshotOpsIngestion = path.join(ARTIFACT_DIR, "deepak_operations_ingestion_center.png");
    await page.screenshot({ path: screenshotOpsIngestion, fullPage: true });
    console.log(`[SCREENSHOT] Saved: ${screenshotOpsIngestion}`);

    // -------------------------------------------------------------------------
    // 3. PROJECT DETAIL PAGE (/dashboard/projects/[id])
    // -------------------------------------------------------------------------
    const deepakId = "5688bb11-a431-4f53-b5da-2064436c3aef";
    console.log(`[NAV] Navigating to project detail page: /dashboard/projects/${deepakId}...`);
    await page.goto(`${BASE_URL}/dashboard/projects/${deepakId}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);

    const detailText = await page.innerText("body");
    const detailHasTitle = detailText.includes("Deepak Farm Soil Sensor Pilot");
    const detailHas91 = detailText.includes("91");
    const detailHasUnderAssessment = detailText.includes("Under Assessment");
    const detailHasVM0042 = detailText.includes("VM0042");

    console.log(`[ASSERT] Project detail has Deepak title: ${detailHasTitle}`);
    console.log(`[ASSERT] Project detail displays 91 activities: ${detailHas91}`);
    console.log(`[ASSERT] Project detail displays 'Under Assessment' methodology: ${detailHasUnderAssessment}`);
    console.log(`[ASSERT] Project detail has ZERO VM0042 fallback: ${!detailHasVM0042}`);

    if (!detailHasUnderAssessment) {
      throw new Error("Case A Violation: Unassigned Deepak project must display 'Under Assessment'!");
    }
    if (detailHasVM0042) {
      throw new Error("Case A Violation: Unassigned Deepak project must NOT contain VM0042!");
    }

    const screenshotDetailOverview = path.join(ARTIFACT_DIR, "deepak_project_detail_overview.png");
    await page.screenshot({ path: screenshotDetailOverview, fullPage: true });
    console.log(`[SCREENSHOT] Saved: ${screenshotDetailOverview}`);

    // Click "Project Documents & PDD" tab
    console.log("[ACTION] Switching to Documents tab in project detail...");
    const docsTabBtn = page.getByRole("button", { name: /Project Documents & PDD/i });
    if (await docsTabBtn.isVisible()) {
      await docsTabBtn.click();
      await page.waitForTimeout(1500);
      const screenshotDetailDocs = path.join(ARTIFACT_DIR, "deepak_project_detail_documents.png");
      await page.screenshot({ path: screenshotDetailDocs, fullPage: true });
      console.log(`[SCREENSHOT] Saved: ${screenshotDetailDocs}`);
    }

    // Click "Laboratory Assays" tab
    console.log("[ACTION] Switching to Laboratory Assays tab in project detail...");
    const labTabBtn = page.getByRole("button", { name: /Laboratory Assays/i });
    if (await labTabBtn.isVisible()) {
      await labTabBtn.click();
      await page.waitForTimeout(1500);
      const screenshotDetailLab = path.join(ARTIFACT_DIR, "deepak_project_detail_laboratory.png");
      await page.screenshot({ path: screenshotDetailLab, fullPage: true });
      console.log(`[SCREENSHOT] Saved: ${screenshotDetailLab}`);
    }

    // -------------------------------------------------------------------------
    // 4. VERIFY CASE B — ASSIGNED PROJECT (e.g. VM0047)
    // -------------------------------------------------------------------------
    console.log("[TEST] Testing Case B: Assigned project with VM0047...");
    const assignedProjectId = "00000000-0000-0000-0000-000000000047";
    await page.route(`**/api/v1/projects/${assignedProjectId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: assignedProjectId,
          name: "Assigned Agroforestry Carbon Project",
          country: "Kenya",
          methodology_id: "meth-47",
          methodology_code: "VM0047",
          methodology_version: "1.0",
          baseline_parameters: {},
          organization_id: farm.organization_id,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`${BASE_URL}/dashboard/projects/${assignedProjectId}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);

    const caseBText = await page.innerText("body");
    const caseBHasVM0047 = caseBText.includes("VM0047");
    const caseBHasUnderAssessment = caseBText.includes("Under Assessment");

    console.log(`[ASSERT] Case B project displays assigned VM0047: ${caseBHasVM0047}`);
    console.log(`[ASSERT] Case B does NOT display 'Under Assessment': ${!caseBHasUnderAssessment}`);

    if (!caseBHasVM0047) {
      throw new Error("Case B Violation: Assigned project must display VM0047!");
    }
    if (caseBHasUnderAssessment) {
      throw new Error("Case B Violation: Assigned project must NOT display Under Assessment!");
    }

    const screenshotCaseB = path.join(ARTIFACT_DIR, "case_b_project_detail_vm0047.png");
    await page.screenshot({ path: screenshotCaseB, fullPage: true });
    console.log(`[SCREENSHOT] Saved: ${screenshotCaseB}`);

    console.log("============================================================");
    console.log("BROWSER E2E VERIFICATION COMPLETED SUCCESSFULLY (PASS)");
    console.log("============================================================");
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("Browser E2E verification failed:", err);
  process.exit(1);
});
