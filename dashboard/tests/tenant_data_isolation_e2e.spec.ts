import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import * as path from "path";
import * as fs from "fs";

// =============================================================================
// VeriField Nexus — Tenant Data Isolation & Zero Cross-Contamination E2E Test
// =============================================================================

const BASE_URL = process.env.BASE_URL || "http://localhost:3000";
const ARTIFACT_DIR = "/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83";

interface SetupData {
  organization_id: string;
  organization_name: string;
  user_id: string;
  email: string;
  role: string;
  token: string;
  sector: string;
  tag: string;
}

function setupFreshTenant(): SetupData {
  const scriptPath = path.resolve(__dirname, "../../backend/scripts/run_tenant_isolation_live_helper.py");
  const backendDir = path.resolve(__dirname, "../../backend");
  const rawOutput = execSync(`venv/bin/python "${scriptPath}" setup`, {
    cwd: backendDir,
  }).toString().trim();
  return JSON.parse(rawOutput);
}

function cleanupFreshTenant(orgId: string): void {
  const scriptPath = path.resolve(__dirname, "../../backend/scripts/run_tenant_isolation_live_helper.py");
  const backendDir = path.resolve(__dirname, "../../backend");
  execSync(`venv/bin/python "${scriptPath}" cleanup "${orgId}"`, {
    cwd: backendDir,
  });
}

test.describe("Fresh Tenant Data Isolation & Verification Tasks 500 Fix", () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(90000);

  test("Fresh ORG_ADMIN in AGRICULTURE_LAND_USE shows 0 projects, 0 activities, 0 anomalies, no cross-sector leaks, and verification/tasks returns 200", async ({ page, request }) => {
    const tenantData = setupFreshTenant();
    console.log(`[Tenant Isolation Test] Seeded fresh tenant: ${tenantData.organization_name} (${tenantData.organization_id})`);

    try {
      // 1. Verify backend API directly with fresh tenant token: GET /api/v1/verification/tasks
      console.log("[Tenant Isolation Test] Verifying GET /api/v1/verification/tasks endpoint...");
      const tasksRes = await request.get("http://localhost:8000/api/v1/verification/tasks", {
        headers: {
          Authorization: `Bearer ${tenantData.token}`,
        },
      });
      expect(tasksRes.status()).toBe(200);
      const tasksBody = await tasksRes.json();
      expect(tasksBody.tasks).toEqual([]);
      expect(tasksBody.audits).toEqual([]);
      expect(tasksBody.total).toBe(0);
      console.log("[Tenant Isolation Test] GET /api/v1/verification/tasks returned 200 OK with empty tasks list (No 500 error)");

      // 2. Set up authenticated browser session for fresh ORG_ADMIN
      const userPayload = {
        id: tenantData.user_id,
        email: tenantData.email,
        full_name: `Fresh Agriculture Admin ${tenantData.tag}`,
        role: "ORG_ADMIN",
        status: "active",
        is_active: true,
        organization: tenantData.organization_name,
        organization_id: tenantData.organization_id,
        licensed_methodologies: ["VM0042"],
        licensed_sectors: ["agriculture_land_use"],
        version: 1,
        is_deleted: false,
      };

      await page.addInitScript(
        ({ token, userData }) => {
          window.localStorage.setItem("vf_token", token);
          window.localStorage.setItem("vf_user", JSON.stringify(userData));
          window.localStorage.setItem("vf_active_sector", "agriculture_land_use");
          window.localStorage.setItem("vf_active_methodology", "VM0042");
        },
        { token: tenantData.token, userData: userPayload }
      );

      // 3. Navigate to Main Dashboard
      console.log("[Tenant Isolation Test] Navigating to /dashboard...");
      await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use&methodology=VM0042`, {
        waitUntil: "networkidle",
      });

      // Assert Sector and Engine Header
      await expect(page.locator("body")).toContainText("Agriculture & Land Use");

      // Assert Agriculture KPI Cards
      // MONITORED AREA: "—" (Awaiting registration)
      await expect(page.getByText("MONITORED AREA", { exact: true })).toBeVisible();
      await expect(page.getByText("Awaiting land unit registration")).toBeVisible();

      // LAND UNITS: 0
      await expect(page.getByText("LAND UNITS", { exact: true })).toBeVisible();
      await expect(page.getByText("No management units registered")).toBeVisible();

      // FIELD ACTIVITIES: 0
      await expect(page.getByText("FIELD ACTIVITIES", { exact: true })).toBeVisible();
      await expect(page.getByText("Recorded field observations")).toBeVisible();

      // OPEN QA FINDINGS: "—" (NO_DATA, NEVER 23!)
      await expect(page.getByText("OPEN QA FINDINGS", { exact: true })).toBeVisible();
      await expect(page.getByText("No QA aggregate available")).toBeVisible();
      await expect(page.locator("body")).not.toContainText("23 open QA findings");
      await expect(page.locator("body")).not.toContainText("23 active flags");

      // Assert Operational status & summary
      await expect(page.locator("body")).toContainText("0 field activities submitted for Agriculture & Land Use. Awaiting field data capture.");

      // Assert Action required & Activity timeline empty states
      await expect(page.locator("body")).toContainText("No pending actions.");
      await expect(page.locator("body")).toContainText("No recent activity.");

      // Assert absolute zero cross-sector leakage on Dashboard body
      const dashboardText = await page.locator("body").innerText();
      expect(dashboardText).not.toContain("684.1");
      expect(dashboardText).not.toContain("Kano Solar");
      expect(dashboardText).not.toContain("Lekki EV");
      expect(dashboardText).not.toContain("Clean Stove");
      expect(dashboardText).not.toContain("CS-892");
      expect(dashboardText).not.toContain("Biochar Kiln");
      expect(dashboardText).not.toContain("Northern Nigeria Solar");
      expect(dashboardText).not.toContain("Oyo Sustainable Biochar");

      // Capture screenshot of main dashboard
      const screenshotDir = path.resolve(__dirname, "screenshots");
      if (!fs.existsSync(screenshotDir)) {
        fs.mkdirSync(screenshotDir, { recursive: true });
      }
      const dashScreenshotPath = path.join(screenshotDir, "live_tenant_data_isolation_dashboard.png");
      await page.screenshot({ path: dashScreenshotPath, fullPage: true });
      console.log(`[Tenant Isolation Test] Saved dashboard screenshot to ${dashScreenshotPath}`);

      if (fs.existsSync(ARTIFACT_DIR)) {
        fs.copyFileSync(dashScreenshotPath, path.join(ARTIFACT_DIR, "live_tenant_data_isolation_dashboard.png"));
      }

      // 4. Navigate to Monitoring & Historian Console
      console.log("[Tenant Isolation Test] Navigating to /dashboard/monitoring?tab=historian...");
      await page.goto(`${BASE_URL}/dashboard/monitoring?tab=historian`, {
        waitUntil: "networkidle",
      });

      // Assert Telemetry Historian empty state
      await expect(page.locator("body")).toContainText("No historical telemetry recorded for this workspace");
      await expect(page.locator("body")).toContainText("0 kg");
      await expect(page.locator("body")).toContainText("0 kWh");
      await expect(page.locator("body")).toContainText("0 hrs");
      await expect(page.locator("body")).toContainText("N/A");

      // Assert Data Quality Event Stream empty state
      await expect(page.locator("body")).toContainText("No Matching Events Found");

      // Assert absolute zero synthetic / demo leakage on Monitoring body
      const monitoringText = await page.locator("body").innerText();
      expect(monitoringText).not.toContain("684.1");
      expect(monitoringText).not.toContain("96% Verified");
      expect(monitoringText).not.toContain("Kano Solar Array Inverter 04");
      expect(monitoringText).not.toContain("Northern Nigeria Solar Mini-Grid");
      expect(monitoringText).not.toContain("Clean Stove Device CS-892");
      expect(monitoringText).not.toContain("Kano Clean Cooking Expansion");
      expect(monitoringText).not.toContain("Lekki EV Fast Charger");
      expect(monitoringText).not.toContain("Lagos Urban EV Corridor");
      expect(monitoringText).not.toContain("Biochar Kiln Temperature Sensor");
      expect(monitoringText).not.toContain("Oyo Sustainable Biochar Removal");

      // Capture screenshot of monitoring page
      const monScreenshotPath = path.join(screenshotDir, "live_tenant_data_isolation_monitoring.png");
      await page.screenshot({ path: monScreenshotPath, fullPage: true });
      console.log(`[Tenant Isolation Test] Saved monitoring screenshot to ${monScreenshotPath}`);

      if (fs.existsSync(ARTIFACT_DIR)) {
        fs.copyFileSync(monScreenshotPath, path.join(ARTIFACT_DIR, "live_tenant_data_isolation_monitoring.png"));
      }

      console.log("[Tenant Isolation Test] All isolation assertions verified successfully!");
    } finally {
      cleanupFreshTenant(tenantData.organization_id);
      console.log(`[Tenant Isolation Test] Cleaned up test tenant: ${tenantData.organization_id}`);
    }
  });
});
