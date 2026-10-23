import { test, expect, type Page } from "@playwright/test";
import { getNavigationGroups } from "../src/lib/navigation";
import { CANONICAL_ROLES } from "../src/lib/roles";
import { CAPTURE_FIELDS } from "../src/lib/fieldCapture";

const projectId = "00000000-0000-4000-8000-000000000001";
const sampleId = "00000000-0000-4000-8000-000000000002";
async function fixtures(page: Page, role = "ORG_ADMIN", sector = "AGRICULTURE_LAND_USE", deny = false) {
  const user = { id: "navigation-fixture-user", full_name: "Test operator", role, organization: "Deepak Farms", organization_id: "00000000-0000-4000-8000-000000000003", is_active: true, status: "active", licensed_sectors: [sector], licensed_methodologies: [] };
  const project = { id: projectId, name: "Test project", sector, organization_id: user.organization_id, baseline_parameters: { sector }, country: "India", status: "draft", created_at: "2026-01-01" };
  const writes: { path: string; body: any }[] = [];
  await page.route("**/*", async route => {
    const url = new URL(route.request().url());
    if (!["localhost", "127.0.0.1"].includes(url.hostname)) return route.abort();
    if (!url.pathname.startsWith("/api/v1/")) return route.continue();
    const path = url.pathname.slice(7);
    if (route.request().method() !== "GET") {
      const body = route.request().postDataJSON(); writes.push({ path, body });
      return route.fulfill(deny ? { status: 403, json: { detail: "Permission denied" } } : { json: { ...body, id: "fixture-record", status: "pending", collection_timestamp: body?.collection_timestamp } });
    }
    if (path === "/auth/me") return route.fulfill({ json: user });
    if (path === "/projects") return route.fulfill({ json: { items: [project], total: 1 } });
    if (path === `/projects/${projectId}`) return route.fulfill({ json: project });
    if (path === "/assets" || path === "/properties") return route.fulfill({ json: { items: [], assets: [], properties: [], total: 0 } });
    if (path.startsWith("/activities")) return route.fulfill({ json: { activities: [], total: 0 } });
    if (path.includes("/verification/packages")) return route.fulfill({ json: [] });
    if (path.includes("/anomalies")) return route.fulfill({ json: { anomalies: [], total: 0 } });
    if (path.includes("/verification/tasks")) return route.fulfill({ json: { tasks: [], total: 0 } });
    if (path.includes("/agents") || path.includes("agent-performance")) return route.fulfill({ json: { agents: [], total_agents: 0, suspicious_count: 0 } });
    if (path.includes("/registry/readiness")) return route.fulfill({ json: { project_id: projectId, readiness_status: "BLOCKED", blocking_items: ["METHODOLOGY_UNLINKED"], missing_requirements: [], document_readiness: [] } });
    if (path.includes("/registry/document-matrix")) return route.fulfill({ json: { authorities: [] } });
    if (path.includes("/carbon/ledger")) return route.fulfill({ json: { data: [] } });
    if (path.includes("/auth/sso/providers")) return route.fulfill({ json: { providers: [] } });
    return route.fulfill({ json: [] });
  });
  await page.addInitScript(({ user, sector }) => {
    localStorage.setItem("vf_token", "navigation-fixture-token");
    localStorage.setItem("vf_user", JSON.stringify(user));
    localStorage.setItem("vf_active_sector", sector.toLowerCase());
  }, { user, sector });
  return writes;
}

for (const role of Object.values(CANONICAL_ROLES)) {
  test(`${role}: every sidebar destination opens without a role denial or page crash`, async ({ page }) => {
    test.setTimeout(120000);
    await fixtures(page, role);
    const errors: string[] = [];
    page.on("pageerror", err => errors.push(err.message));
    const links = getNavigationGroups(role).flatMap(g => g.items);
    for (const item of links) {
      await page.goto(item.href);
      await expect(page.getByText("Access denied", { exact: true })).toHaveCount(0);
      await expect(page.getByText(/Application error: a client-side exception/)).toHaveCount(0);
      if (item.href.startsWith("/dashboard")) {
        await expect(page.getByRole("complementary", { name: "Main navigation" })).toBeVisible();
        await expect(page.getByRole("complementary").getByRole("link", { name: item.label, exact: true })).toHaveCount(1);
      }
    }
    expect(errors).toEqual([]);
  });
}

test("projects, assets and operations have one home for each action", async ({ page }) => {
  await fixtures(page);
  await page.goto("/dashboard/projects");
  await expect(page.getByRole("button", { name: "Create project", exact: true })).toHaveCount(1);
  await expect(page.getByText(/Manage Team|Privileges|Certified Gold Standard/)).toHaveCount(0);
  await page.goto("/dashboard/assets");
  await expect(page.getByRole("button", { name: /Create.*project/i })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Projects", exact: true })).toHaveCount(0);
  await expect(page.getByText(/verified MRV telemetry|Verification insight|Certified Gold Standard/i)).toHaveCount(0);
  await page.goto("/dashboard/operations");
  await expect(page.getByRole("navigation", { name: "Field operations" }).getByRole("link")).toHaveCount(2);
  await expect(page.getByText(/Provision Field Agent|LIVE DISPATCH|Spatial Command/)).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Capture data", exact: true })).toHaveAttribute("href", /\/capture/);
});

for (const [sector, fields] of Object.entries(CAPTURE_FIELDS)) {
  test(`${sector}: field agent submits the selected project and sector contract`, async ({ page }) => {
    const writes = await fixtures(page, "FIELD_AGENT", sector);
    await page.goto(`/capture?project=${projectId}`);
    await expect(page.getByTestId("capture-sector")).toHaveText(fields.label);
    await page.getByLabel(sector === "AGRICULTURE_LAND_USE" ? "Physical sample ID" : "Asset identifier", { exact: true }).fill(sector === "AGRICULTURE_LAND_USE" ? sampleId : "asset-001");
    await page.getByLabel(fields.metric, { exact: true }).fill("4");
    await page.getByLabel("Latitude", { exact: true }).fill("0");
    await page.getByLabel("Longitude", { exact: true }).fill("0");
    await page.getByRole("button", { name: "Submit record", exact: true }).click();
    await expect(page.getByRole("heading", { name: sector === "AGRICULTURE_LAND_USE" ? "Collection recorded" : "pending", exact: true })).toBeVisible();
    expect(writes).toHaveLength(1);
    if (sector === "AGRICULTURE_LAND_USE") {
      expect(writes[0].path).toBe(`/agriculture/projects/${projectId}/physical-samples/${sampleId}/collection`);
      expect(writes[0].body.actual_lat).toBe(0);
      expect(writes[0].body.actual_depth_to_cm).toBe(4);
    } else {
      expect(writes[0].body.project_id).toBe(projectId);
      expect(writes[0].body.activity_type).toBe(fields.type);
      expect(writes[0].body.activity_data[fields.key]).toBe(4);
      expect(writes[0].body.latitude).toBe(0);
      expect(writes[0].body.image_url).toBeUndefined();
    }
    await expect(page.getByText(/% Verified|95%|Submission Verified/)).toHaveCount(0);
  });
}

for (const role of ["ORG_ADMIN", "SUPER_ADMIN", "VERIFIER", "AUDITOR", "VIEWER"]) {
  test(`${role}: preparation and independent actions stay separated`, async ({ page }) => {
    await fixtures(page, role);
    await page.goto("/dashboard/verifications");
    if (["VERIFIER", "AUDITOR", "VIEWER"].includes(role)) await expect(page.getByRole("button", { name: "Prepare package", exact: true })).toHaveCount(0);
    if (["ORG_ADMIN", "SUPER_ADMIN"].includes(role)) {
      await page.getByRole("button", { name: "Audit queue", exact: true }).click();
      await expect(page.getByRole("button", { name: "Create audit assignment", exact: true })).toHaveCount(0);
    }
    await page.goto("/capture");
    if (["VERIFIER", "AUDITOR", "VIEWER"].includes(role)) await expect(page.getByRole("heading", { name: "Field capture unavailable" })).toBeVisible();
  });
}

test("legacy telemetry tab goes to Sensors", async ({ page }) => {
  await fixtures(page);
  await page.goto("/dashboard/operations?tab=telemetry");
  await expect(page).toHaveURL(/\/dashboard\/sensors$/);
});
test("mobile dashboard provides a usable navigation menu", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await fixtures(page);
  await page.goto("/dashboard/projects");
  await expect(page.getByRole("button", { name: "Create project", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(page.getByRole("complementary", { name: "Main navigation" })).toBeVisible();
  await page.getByRole("complementary").getByRole("link", { name: "Assets", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard\/assets$/);
  await expect(page.getByRole("button", { name: "Toggle navigation" })).toHaveAttribute("aria-expanded", "false");
});

test("a denied submission stays an error and is not silently queued", async ({ page }) => {
  await fixtures(page, "FIELD_AGENT", "HYBRID_ENERGY", true);
  await page.goto(`/capture?project=${projectId}`);
  await page.getByLabel("Asset identifier", { exact: true }).fill("meter-1");
  await page.getByLabel("Energy delivered (kWh)", { exact: true }).fill("12");
  await page.getByLabel("Latitude", { exact: true }).fill("0");
  await page.getByLabel("Longitude", { exact: true }).fill("0");
  await page.getByRole("button", { name: "Submit record", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Permission denied" })).toContainText("Permission denied");
  await expect(page.getByTestId("pwa-queue-banner")).toHaveCount(0);
});

test("offline records retain project and account context and sync once", async ({ page }) => {
  const writes = await fixtures(page, "FIELD_AGENT", "HYBRID_ENERGY");
  await page.goto(`/capture?project=${projectId}`);
  await page.getByLabel("Asset identifier", { exact: true }).fill("meter-1");
  await page.getByLabel("Energy delivered (kWh)", { exact: true }).fill("12");
  await page.getByLabel("Latitude", { exact: true }).fill("0");
  await page.getByLabel("Longitude", { exact: true }).fill("0");
  await page.evaluate(() => { Object.defineProperty(navigator, "onLine", { configurable: true, value: false }); window.dispatchEvent(new Event("offline")); });
  await page.getByRole("button", { name: "Save offline", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Saved offline — awaiting submission" })).toBeVisible();
  expect(writes).toHaveLength(0);
  const stored = await page.evaluate(() => Object.entries(localStorage).filter(([key]) => key.startsWith("verifield_capture_queue:")));
  expect(stored).toHaveLength(1);
  expect(stored[0][0]).toContain("navigation-fixture-user");
  expect(JSON.parse(stored[0][1])[0].projectId).toBe(projectId);
  await page.evaluate(() => { Object.defineProperty(navigator, "onLine", { configurable: true, value: true }); window.dispatchEvent(new Event("online")); });
  await page.getByTestId("pwa-sync-button").click();
  await expect(page.getByTestId("pwa-queue-banner")).toHaveCount(0);
  expect(writes).toHaveLength(1);
});

test("failed GPS does not create regional fallback coordinates", async ({ page, context }) => {
  await fixtures(page, "FIELD_AGENT", "HYBRID_ENERGY");
  await page.addInitScript(() => { navigator.geolocation.getCurrentPosition = (_success, fail) => fail?.({ code: 1, message: "Denied", PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 }); });
  await page.goto(`/capture?project=${projectId}`);
  await page.getByRole("button", { name: "Use current location", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Location could not be obtained" })).toContainText("Location could not be obtained");
  await expect(page.getByLabel("Latitude", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Longitude", { exact: true })).toHaveValue("");
});

for (const role of ["VIEWER", "INVESTOR", "VERIFIER", "AUDITOR", "FIELD_AGENT"]) {
  test(`${role}: direct administration URL is denied`, async ({ page }) => {
    await fixtures(page, role);
    await page.goto("/dashboard/people");
    await expect(page.getByRole("heading", { name: "Access denied", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /invite|provision|create user/i })).toHaveCount(0);
  });
}

test("capture uses plain mobile layout", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await fixtures(page, "FIELD_AGENT", "AGRICULTURE_LAND_USE");
  await page.goto(`/capture?project=${projectId}`);
  await expect(page.getByTestId("capture-sector")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: "test-results/capture-agriculture-mobile.png", fullPage: true });
});
