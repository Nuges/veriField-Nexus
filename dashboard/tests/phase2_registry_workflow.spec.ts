import { test, expect, type Page } from "@playwright/test";

// All backend responses are isolated fixtures; outbound production requests are blocked.
const first = "00000000-0000-4000-8000-000000000001";
const second = "00000000-0000-4000-8000-000000000002";
const org = "00000000-0000-4000-8000-000000000003";
const projects = [
  { id: first, name: "Telemetry pilot fixture", organization_id: org, methodology_id: null, methodology_code: null, registry_id: null, country: "India", baseline_parameters: {}, created_at: "2026-01-01" },
  { id: second, name: "Review project fixture", organization_id: org, methodology_code: "VM0047", registry_id: null, country: "India", baseline_parameters: {}, created_at: "2026-01-01" },
];

async function fixtures(page: Page, role = "ORG_ADMIN", deniedDownload = false) {
  const user = { id: "phase2-user", email: "operator@example.test", full_name: "Test operator", role, organization_id: org, status: "active", is_active: true, licensed_sectors: ["AGRICULTURE_LAND_USE"], licensed_methodologies: [] };
  const registryRequests: string[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (!["localhost", "127.0.0.1"].includes(url.hostname)) return route.abort();
    if (!url.pathname.startsWith("/api/v1/")) return route.continue();
    const resource = url.pathname.slice("/api/v1".length);
    if (resource.startsWith("/registry")) {
      registryRequests.push(resource);
      expect(route.request().headers().authorization).toBe("Bearer phase2-fixture-token");
    }
    if (resource === "/auth/login") return route.fulfill({ json: { access_token: "phase2-fixture-token", user } });
    if (resource === "/auth/me") return route.fulfill({ json: user });
    if (resource === "/projects") return route.fulfill({ json: projects });
    if (resource.startsWith("/registry/readiness/")) {
      const id = resource.split("/").pop();
      return route.fulfill({ json: { project_id: id, target_standard: url.searchParams.get("target_standard"), readiness_status: id === first ? "BLOCKED" : "SUBMISSION_READY", blocking_items: id === first ? ["METHODOLOGY_UNLINKED"] : [], missing_requirements: [], document_readiness: [] } });
    }
    if (resource === "/registry/document-matrix") return route.fulfill({ json: { version: "fixture", authorities: [] } });
    if (resource.includes("/package-download/")) return route.fulfill(deniedDownload ? { status: 403, json: { detail: "Denied" } } : { contentType: "application/zip", body: "fixture package", headers: { "Content-Disposition": "attachment; filename=review.zip" } });
    if (resource.includes("/laboratory-import/template")) return route.fulfill({ contentType: "text/csv", body: "sample_code,analyte,raw_value,raw_unit\n", headers: { "Content-Disposition": "attachment; filename=template.csv" } });
    const selected = projects.find((item) => resource === `/projects/${item.id}`);
    if (selected) return route.fulfill({ json: selected });
    if (resource.includes("verification/tasks") || resource === "/audits") return route.fulfill({ json: { tasks: [], audits: [], total: 0 } });
    if (resource.startsWith("/activities")) return route.fulfill({ json: { activities: [], total: 0 } });
    if (resource.includes("/auth/sso/providers")) return route.fulfill({ json: { providers: [] } });
    return route.fulfill({ json: [] });
  });
  await page.addInitScript(({ user, first }) => {
    localStorage.setItem("vf_token", "phase2-fixture-token");
    localStorage.setItem("vf_user", JSON.stringify(user));
    localStorage.setItem("vf_active_project_id", first);
    localStorage.setItem("vf_active_sector", "agriculture_land_use");
  }, { user, first });
  return registryRequests;
}

test("Selected unassigned pilot remains Under Assessment and cannot export", async ({ page }) => {
  await fixtures(page);
  await page.goto("/dashboard/registry");
  await expect(page.getByRole("heading", { name: "Registry Preparation", exact: true })).toBeVisible();
  await expect(page.getByTestId("registry-preparation-state")).toHaveText("Missing Requirements");
  await expect(page.getByText(/remains Under Assessment/)).toBeVisible();
  await expect(page.getByTestId("registry-download-package")).toBeDisabled();
});

test("Project change loads its own readiness and confirmed download feedback", async ({ page }) => {
  const requests = await fixtures(page);
  await page.goto("/dashboard/registry");
  await page.getByLabel("Registry project", { exact: true }).selectOption(second);
  await expect(page.getByTestId("registry-preparation-state")).toHaveText("Ready for Review");
  const download = page.waitForEvent("download");
  await page.getByTestId("registry-download-package").click();
  await download;
  await expect(page.getByText(/Export Available/)).toBeVisible();
  expect(requests.some((value) => value === `/registry/package-download/VERRA/${second}`)).toBeTruthy();
  expect(requests.some((value) => value.includes(`/package-download/VERRA/${first}`))).toBeFalsy();
});

test("A viewer has no registry action and sends no registry request", async ({ page }) => {
  const requests = await fixtures(page, "VIEWER");
  await page.goto("/dashboard/registry");
  await expect(page.getByText(/does not have registry-read access/)).toBeVisible();
  expect(requests).toEqual([]);
});

test("Denied download shows failure with no legacy authorization fallback", async ({ page }) => {
  const requests = await fixtures(page, "ORG_ADMIN", true);
  await page.goto("/dashboard/registry");
  await page.getByLabel("Registry project", { exact: true }).selectOption(second);
  await expect(page.getByTestId("registry-download-package")).toBeEnabled();
  await page.getByTestId("registry-download-package").click();
  await expect(page.getByRole("alert").filter({ hasText: "Registry download failed" })).toContainText("HTTP 403");
  expect(requests.filter((value) => value.includes("package-download"))).toHaveLength(1);
  await expect(page.getByText(/Export Available/)).toHaveCount(0);
});

test("Project laboratory template remains reachable without registry submission", async ({ page }) => {
  await fixtures(page);
  await page.goto(`/dashboard/projects/${first}?tab=laboratory`);
  await expect(page.getByTestId("btn-download-csv-template")).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByTestId("btn-download-csv-template").click();
  await download;
});
