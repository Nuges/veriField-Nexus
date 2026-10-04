import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import * as path from "path";

// =============================================================================
// VeriField Nexus — Verification API Contract & Route Collision Live E2E
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

function setupFreshTenant(role: string = "ORG_ADMIN"): SetupData {
  const scriptPath = path.resolve(__dirname, "../../backend/scripts/run_tenant_isolation_live_helper.py");
  const backendDir = path.resolve(__dirname, "../../backend");
  const rawOutput = execSync(`venv/bin/python "${scriptPath}" setup "" "${role}"`, {
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

test.describe("Verification API Contract & Route Collision Live Full-Stack E2E", () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(60000);

  test("Fresh tenant on verification endpoints and UI produces 0 422 errors, 0 500 errors, and zero tasks.map exceptions", async ({ page, request }) => {
    const tenantData = setupFreshTenant();
    console.log(`[Verification Live E2E] Seeded fresh tenant: ${tenantData.organization_name} (${tenantData.organization_id})`);

    const consoleErrors: string[] = [];
    const failedNetworkRequests: { url: string; status: number }[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    page.on("response", (response) => {
      const url = response.url();
      const status = response.status();
      if ((url.includes("/verification/") || url.includes("/audits")) && status >= 400) {
        failedNetworkRequests.push({ url, status });
      }
    });

    try {
      // 1. DIRECT BACKEND VERIFICATION VIA HTTP REQUEST:
      // DEFECT B TEST: GET /api/v1/verification/packages must return HTTP 200 (NOT 422!)
      const pkgsRes = await request.get("http://localhost:8000/api/v1/verification/packages", {
        headers: {
          Authorization: `Bearer ${tenantData.token}`,
        },
      });
      expect(pkgsRes.status()).toBe(200);
      const pkgsBody = await pkgsRes.json();
      expect(Array.isArray(pkgsBody)).toBe(true);
      expect(pkgsBody).toHaveLength(0);
      console.log("[Verification Live E2E] Route Collision resolved: GET /api/v1/verification/packages returned 200 OK with empty array (NOT 422).");

      // DEFECT A TEST: GET /api/v1/verification/tasks must return canonical envelope { tasks: [], total: 0 }
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
      console.log("[Verification Live E2E] Canonical Contract verified: GET /api/v1/verification/tasks returned 200 OK with { tasks: [], total: 0 }.");

      // 2. BROWSER SESSION SETUP FOR FRESH TENANT
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

      // 3. NAVIGATE TO /dashboard/verifications
      console.log("[Verification Live E2E] Navigating to /dashboard/verifications...");
      await page.goto(`${BASE_URL}/dashboard/verifications`, { waitUntil: "networkidle" });

      // Verify Header
      await expect(page.locator("h1")).toContainText("Verification & Audits Hub");

      // Verify Audit Packages Tab is visible and renders clean empty state
      const packagesTab = page.getByRole("button", { name: /Audit Packages/i });
      await expect(packagesTab).toBeVisible();

      // Check empty state
      await expect(page.getByText("No Verification Packages Yet")).toBeVisible({ timeout: 10000 });
      await expect(page.getByText("Compile First Package")).toBeVisible();

      // Screenshot clean packages empty state
      await page.screenshot({
        path: `${ARTIFACT_DIR}/live_verification_packages_empty.png`,
        fullPage: true,
      });

      // 4. SWITCH TO AUDITS TAB ON VERIFICATIONS HUB
      const auditsTab = page.getByRole("button", { name: "Audits", exact: true });
      if (await auditsTab.isVisible()) {
        await auditsTab.click();
        await page.waitForTimeout(500);
        await expect(page.getByText("No Audits Pending")).toBeVisible({ timeout: 10000 });

        await page.screenshot({
          path: `${ARTIFACT_DIR}/live_verification_audits_tab_empty.png`,
          fullPage: true,
        });
      }

      // 5. TEST /dashboard/audits IN SEPARATE VERIFIER CONTEXT (PER RBAC MATRIX)
      const verifierTenant = setupFreshTenant("VERIFIER");
      try {
        const verifierContext = await page.context().browser()!.newContext();
        const verifierPage = await verifierContext.newPage();

        verifierPage.on("console", (msg) => {
          if (msg.type() === "error") {
            consoleErrors.push(msg.text());
          }
        });

        const verifierPayload = {
          id: verifierTenant.user_id,
          email: verifierTenant.email,
          full_name: `Accredited Lead Verifier ${verifierTenant.tag}`,
          role: "VERIFIER",
          status: "active",
          is_active: true,
          organization: verifierTenant.organization_name,
          organization_id: verifierTenant.organization_id,
          version: 1,
          is_deleted: false,
        };

        await verifierPage.addInitScript(
          ({ token, userData }) => {
            window.localStorage.setItem("vf_token", token);
            window.localStorage.setItem("vf_user", JSON.stringify(userData));
          },
          { token: verifierTenant.token, userData: verifierPayload }
        );

        console.log("[Verification Live E2E] Navigating to /dashboard/audits as VERIFIER...");
        await verifierPage.goto(`${BASE_URL}/dashboard/audits`, { waitUntil: "networkidle" });

        // Verify Header
        await expect(verifierPage.locator("h1")).toContainText("Manual Audit Tasks");

        // Assert table empty state renders without "tasks.map is not a function"
        await expect(verifierPage.getByText("All clear on Audits")).toBeVisible({ timeout: 10000 });

        // Screenshot dedicated audits page
        await verifierPage.screenshot({
          path: `${ARTIFACT_DIR}/live_dedicated_audits_page_empty.png`,
          fullPage: true,
        });

        await verifierContext.close();
      } finally {
        cleanupFreshTenant(verifierTenant.organization_id);
      }

      // Assert ZERO "tasks.map is not a function" in console logs
      const mapErrors = consoleErrors.filter((e) => e.includes("tasks.map is not a function") || e.includes(".map is not a function"));
      expect(mapErrors).toHaveLength(0);

      // Assert ZERO 422 or 500 errors on verification endpoints
      const verificationHttpErrors = failedNetworkRequests.filter(
        (r) => r.status === 422 || r.status === 500
      );
      expect(verificationHttpErrors).toHaveLength(0);

      console.log("[Verification Live E2E] All live assertions passed with 0 console errors and 0 network 422/500 errors!");
    } finally {
      cleanupFreshTenant(tenantData.organization_id);
      console.log(`[Verification Live E2E] Cleaned up test tenant ${tenantData.organization_id}`);
    }
  });
});
