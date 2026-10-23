import test, { type TestContext } from "node:test";
import assert from "node:assert/strict";
import { CANONICAL_ROLES } from "../src/lib/roles";
import { canReadRegistry, registryExportBlockReason, registryPreparationLabel, type RegistryReadiness } from "../src/lib/registryWorkflow";
import { fetchRegistryReadiness, fetchRegistryDocumentMatrix, downloadRegistryPackage, downloadArticle6PackageZip, downloadRegistryDocument, submitITMOAuthorization, setAuthToken, apiConfig } from "../src/lib/api";
import type { Project } from "../src/lib/types";

const project: Project = { id: "project-a", name: "Isolated review fixture", registry_id: null, created_at: "2026-01-01", methodology_code: "VM0047", baseline_parameters: {}, sector: "AGRICULTURE_LAND_USE" };
const ready: RegistryReadiness = { project_id: project.id, target_standard: "VERRA", readiness_status: "SUBMISSION_READY", blocking_items: [], missing_requirements: [] };

function setup(t: TestContext) {
  const base = process.env.NEXT_PUBLIC_API_URL;
  const retries = apiConfig.maxRetries;
  process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
  apiConfig.maxRetries = 0;
  setAuthToken("isolated-test-token");
  t.after(() => {
    if (base === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = base;
    apiConfig.maxRetries = retries;
    setAuthToken(null);
  });
  t.mock.method(console, "error", () => {});
}

test("All 13 roles match existing backend registry-read access without granting new roles", () => {
  const allowed = new Set(["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "COMPLIANCE_ADMIN", "REGISTRY_ADMIN"]);
  for (const role of Object.values(CANONICAL_ROLES)) assert.equal(canReadRegistry(role), allowed.has(role), role);
  assert.equal(canReadRegistry("admin"), true);
  assert.equal(canReadRegistry("unknown"), false);
});

test("An unassigned pilot stays Under Assessment even if a readiness response claims ready", () => {
  assert.match(registryExportBlockReason({ ...project, methodology_code: null, methodology_id: null }, ready, "VERRA")!, /Under Assessment/);
});

test("Registry exports require the same project and standard, no blockers, and explicit ready status", () => {
  assert.equal(registryExportBlockReason(project, ready, "VERRA"), null);
  for (const response of [null, { ...ready, project_id: "other-project" }, { ...ready, target_standard: "GOLD_STANDARD" }, { ...ready, blocking_items: ["MISSING_EVIDENCE"] }, { ...ready, readiness_status: "UNRECOGNIZED" }, { ...ready, blocking_items: undefined }]) {
    assert.notEqual(registryExportBlockReason(project, response, "VERRA"), null);
  }
});

test("Pilot/test and cookstove modules cannot use preparation state to enable exports", () => {
  assert.match(registryExportBlockReason({ ...project, baseline_parameters: { purpose: "Wokwi telemetry pilot" } }, ready, "VERRA")!, /Pilot/);
  assert.match(registryExportBlockReason({ ...project, sector: "COOKSTOVES" }, ready, "VERRA")!, /gated/);
});

test("Internal preparation labels never invent submission or issued-credit states", () => {
  assert.equal(registryPreparationLabel(null), "Not Started");
  assert.equal(registryPreparationLabel({ ...ready, readiness_status: "BLOCKED" }), "Missing Requirements");
  assert.equal(registryPreparationLabel(ready), "Ready for Review");
  assert.equal(registryPreparationLabel({ ...ready, readiness_status: "SUBMITTED" }), "In Preparation");
});

test("Canonical readiness client sends project, target registry and bearer token", async (t) => {
  setup(t);
  t.mock.method(globalThis, "fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    assert.equal(url.pathname, "/api/v1/registry/readiness/project-a");
    assert.equal(url.searchParams.get("target_standard"), "GOLD_STANDARD");
    assert.equal(new Headers(init?.headers).get("Authorization"), "Bearer isolated-test-token");
    return new Response(JSON.stringify({ ...ready, target_standard: "GOLD_STANDARD" }));
  });
  assert.equal((await fetchRegistryReadiness(project.id, "GOLD_STANDARD")).project_id, project.id);
});

test("JSON registry fallback is restricted to HTTP 404 and retains authentication", async (t) => {
  setup(t);
  const paths: string[] = [];
  t.mock.method(globalThis, "fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    paths.push(new URL(String(input)).pathname);
    assert.equal(new Headers(init?.headers).get("Authorization"), "Bearer isolated-test-token");
    return paths.length === 1 ? new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 }) : new Response(JSON.stringify({ version: "test", authorities: [] }));
  });
  await fetchRegistryDocumentMatrix();
  assert.deepEqual(paths, ["/api/v1/registry/document-matrix", "/api/v1/registry-integrations/document-matrix"]);
});

test("Existing authorization client preserves POST payload and 404 compatibility without a live integration", async (t) => {
  setup(t);
  const payload = { project_id: project.id, acquiring_party: "Test party", authorization_reference: "fixture", authorized_use_scope: "fixture", cooperative_approach_id: "fixture", authorized_at: "2026-01-01", dossier: {} };
  const paths: string[] = [];
  t.mock.method(globalThis, "fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    paths.push(new URL(String(input)).pathname);
    assert.equal(init?.method, "POST");
    assert.deepEqual(JSON.parse(String(init?.body)), payload);
    assert.equal(new Headers(init?.headers).get("Authorization"), "Bearer isolated-test-token");
    return paths.length === 1 ? new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 }) : new Response(JSON.stringify({ status: "FIXTURE_ONLY" }));
  });
  assert.equal((await submitITMOAuthorization(payload)).status, "FIXTURE_ONLY");
  assert.deepEqual(paths, ["/api/v1/registry/itmo/authorize", "/api/v1/registry-integrations/itmo/authorize"]);
});

for (const status of [401, 403, 500]) {
  test(`JSON HTTP ${status} never falls back to a legacy route`, async (t) => {
    setup(t);
    const mocked = t.mock.method(globalThis, "fetch", async () => new Response(JSON.stringify({ detail: "Denied" }), { status }));
    await assert.rejects(fetchRegistryDocumentMatrix(), /Denied/);
    assert.equal(mocked.mock.callCount(), 1);
  });
}

test("All-project registry requests are rejected before any request", async (t) => {
  setup(t);
  const mocked = t.mock.method(globalThis, "fetch", async () => { throw new Error("must not fetch"); });
  await assert.rejects(fetchRegistryReadiness("all"), /specific project/);
  await assert.rejects(downloadRegistryPackage("VERRA", ""), /specific project/);
  assert.equal(mocked.mock.callCount(), 0);
});

test("Existing package alias uses the canonical authenticated download and 404 fallback", async (t) => {
  setup(t);
  const previous = Object.getOwnPropertyDescriptor(globalThis, "document");
  const anchor = { href: "", download: "", click() {}, remove() {} };
  Object.defineProperty(globalThis, "document", { configurable: true, value: { createElement: () => anchor, body: { appendChild() {} } } });
  t.after(() => { if (previous) Object.defineProperty(globalThis, "document", previous); else Reflect.deleteProperty(globalThis, "document"); });
  t.mock.method(URL, "createObjectURL", () => "blob:registry-fixture");
  const revoke = t.mock.method(URL, "revokeObjectURL", () => {});
  const click = t.mock.method(anchor, "click");
  const paths: string[] = [];
  t.mock.method(globalThis, "fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    paths.push(new URL(String(input)).pathname);
    assert.equal(new Headers(init?.headers).get("Authorization"), "Bearer isolated-test-token");
    return paths.length === 1 ? new Response("missing", { status: 404 }) : new Response("isolated-package-bytes");
  });
  await downloadArticle6PackageZip("VERRA", project.id);
  assert.deepEqual(paths, ["/api/v1/registry/package-download/VERRA/project-a", "/api/v1/registry-integrations/package-download/VERRA/project-a"]);
  assert.equal(click.mock.callCount(), 1);
  assert.equal(revoke.mock.callCount(), 1);
});

for (const status of [401, 403, 500]) {
  test(`Download HTTP ${status} never retries via a legacy prefix or reports success`, async (t) => {
    setup(t);
    const mocked = t.mock.method(globalThis, "fetch", async () => new Response("Denied", { status }));
    await assert.rejects(downloadRegistryPackage("VERRA", project.id), new RegExp(`HTTP ${status}`));
    await assert.rejects(downloadRegistryDocument("VERRA", project.id, "DOC"), new RegExp(`HTTP ${status}`));
    assert.equal(mocked.mock.callCount(), 2);
  });
}
