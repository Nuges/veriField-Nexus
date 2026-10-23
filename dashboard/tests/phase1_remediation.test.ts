// =============================================================================
// VeriField Nexus — Phase 1 Remediation Unit & Integration Verification Suite
// =============================================================================

import test, { type TestContext } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { resolveProjectMethodology } from "../src/lib/projectMethodology";
import { downloadLaboratoryImportTemplate, getLaboratoryImportTemplateUrl, setAuthToken } from "../src/lib/api";

function setTestApiBase(t: TestContext, base: string | undefined) {
  const previous = process.env.NEXT_PUBLIC_API_URL;
  if (base === undefined) delete process.env.NEXT_PUBLIC_API_URL;
  else process.env.NEXT_PUBLIC_API_URL = base;
  t.after(() => {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = previous;
    setAuthToken(null);
  });
}

function mockDownloadBrowser(t: TestContext, hostname = "app.verifield.test") {
  const anchor = { href: "", download: "", click() {}, remove() {} };
  const previous = new Map<string, PropertyDescriptor | undefined>();
  for (const [key, value] of Object.entries({
    window: { location: { hostname } },
    document: { createElement: () => anchor, body: { appendChild() {} } },
  })) {
    previous.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { value, writable: true, configurable: true });
  }
  t.after(() => {
    for (const [key, descriptor] of previous) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else Reflect.deleteProperty(globalThis, key);
    }
  });
  const click = t.mock.method(anchor, "click");
  const remove = t.mock.method(anchor, "remove");
  const createUrl = t.mock.method(URL, "createObjectURL", () => "blob:lab-template-test");
  const revokeUrl = t.mock.method(URL, "revokeObjectURL", () => {});
  return { anchor, click, remove, createUrl, revokeUrl };
}

for (const base of ["https://api.example.test", "https://api.example.test/", "https://api.example.test/api/v1", "https://api.example.test/api/v1/"]) {
  test(`Lab template uses exactly one API prefix for ${base}`, (t) => {
    setTestApiBase(t, base);
    assert.equal(getLaboratoryImportTemplateUrl("project-1", "xlsx"),
      "https://api.example.test/api/v1/agriculture/projects/project-1/laboratory-import/template?format=xlsx");
  });
}

test("Hosted template download defaults to production rather than the user's localhost", (t) => {
  setTestApiBase(t, undefined);
  mockDownloadBrowser(t);
  assert.equal(new URL(getLaboratoryImportTemplateUrl("project-1")).origin, "https://verifield-nexus.onrender.com");
});

test("Local development template uses the local backend", (t) => {
  setTestApiBase(t, undefined);
  mockDownloadBrowser(t, "localhost");
  assert.equal(new URL(getLaboratoryImportTemplateUrl("project-1")).origin, "http://localhost:8000");
});

test("Template download sends the active bearer token and saves the returned file", async (t) => {
  setTestApiBase(t, "https://api.example.test/api/v1/");
  const browser = mockDownloadBrowser(t);
  setAuthToken("test-lab-download-token");
  t.mock.method(globalThis, "fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    assert.equal(String(input), getLaboratoryImportTemplateUrl("project-1", "xlsx"));
    assert.equal(new Headers(init?.headers).get("Authorization"), "Bearer test-lab-download-token");
    return new Response("workbook-bytes", { headers: { "Content-Disposition": 'attachment; filename="laboratory.xlsx"; size=14' } });
  });
  await downloadLaboratoryImportTemplate("project-1", "xlsx");
  assert.equal(browser.anchor.download, "laboratory.xlsx");
  assert.equal(browser.click.mock.callCount(), 1);
  assert.equal(browser.remove.mock.callCount(), 1);
  assert.equal(browser.revokeUrl.mock.calls[0].arguments[0], "blob:lab-template-test");
});

for (const status of [401, 403]) {
  test(`Template HTTP ${status} remains an error and never saves an error response as a file`, async (t) => {
    setTestApiBase(t, "https://api.example.test");
    const browser = mockDownloadBrowser(t);
    setAuthToken("invalid-test-token");
    t.mock.method(globalThis, "fetch", async () => new Response(JSON.stringify({ detail: "Access denied" }), { status }));
    await assert.rejects(downloadLaboratoryImportTemplate("project-1"), /Access denied/);
    assert.equal(browser.click.mock.callCount(), 0);
    assert.equal(browser.createUrl.mock.callCount(), 0);
  });
}

test("Phase 1 Verification — Case A: Deepak unassigned project resolves to 'Under Assessment' without VM0032 or VM0042", () => {
  const deepakFarmProject = {
    id: "5688bb11-a431-4f53-b5da-2064436c3aef",
    name: "Deepak Farm Soil Sensor Pilot",
    country: "Nigeria",
    organization_id: "3008978d-3d24-49c4-ac0c-aeed69c59a7f",
    methodology_id: null,
    methodology_code: null,
    baseline_parameters: {
      purpose: "Wokwi ESP32 soil moisture and temperature telemetry pilot",
      environment: "local/test only",
    },
  };

  const resolved = resolveProjectMethodology(deepakFarmProject);

  assert.equal(resolved.isAssigned, false);
  assert.equal(resolved.code, "Under Assessment");
  assert.notEqual(resolved.code, "VM0032", "VM0032 must never be used as a methodology fallback");
  assert.notEqual(resolved.code, "VM0042", "VM0042 must never be used as a methodology fallback");
});

test("Phase 1 Verification — Case B: Assigned project resolves actual methodology code", () => {
  const assignedProject = {
    id: "proj-assigned-vm0047",
    name: "Afforestation Pilot",
    methodology_id: "meth-uuid-1",
    methodology_code: "VM0047",
    baseline_parameters: {},
  };

  const resolved = resolveProjectMethodology(assignedProject);

  assert.equal(resolved.isAssigned, true);
  assert.equal(resolved.code, "VM0047");
  assert.notEqual(resolved.code, "Under Assessment");
});

test("Phase 1 Lab Template — URL generator produces canonical backend endpoint and formats", () => {
  const projectId = "5688bb11-a431-4f53-b5da-2064436c3aef";

  const csvUrl = getLaboratoryImportTemplateUrl(projectId, "csv");
  assert.match(csvUrl, /\/api\/v1\/agriculture\/projects\/5688bb11-a431-4f53-b5da-2064436c3aef\/laboratory-import\/template\?format=csv/);

  const xlsxUrl = getLaboratoryImportTemplateUrl(projectId, "xlsx");
  assert.match(xlsxUrl, /\/api\/v1\/agriculture\/projects\/5688bb11-a431-4f53-b5da-2064436c3aef\/laboratory-import\/template\?format=xlsx/);
});

test("Phase 1 Static Source Audit — VM0032 is completely removed from Verification page", () => {
  const verificationsPagePath = path.resolve(__dirname, "../src/app/dashboard/verifications/page.tsx");
  const content = fs.readFileSync(verificationsPagePath, "utf-8");

  assert.doesNotMatch(
    content,
    /["']VM0032["']/,
    "verifications/page.tsx must not contain hardcoded VM0032"
  );
  assert.match(
    content,
    /resolveProjectMethodology/,
    "verifications/page.tsx must import and use resolveProjectMethodology"
  );
});

test("Phase 1 navigation destinations remain in the shared navigation model", () => {
  const content = fs.readFileSync(path.resolve(__dirname, "../src/lib/navigation.ts"), "utf-8");
  for (const destination of ["sensors", "assets", "command-center", "settings", "verifications"]) {
    assert.ok(content.includes(`/dashboard/${destination}`));
  }
  assert.doesNotMatch(content, /"Global Mission Control"|"Enterprise Spatial Command Center"/);
});
