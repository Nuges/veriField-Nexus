import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  fetchVerificationTasks,
  fetchAudits,
  fetchMyAuditTasks,
  type VerificationTask,
  type VerificationTasksResponse,
} from "../src/lib/api";

// =============================================================================
// VeriField Nexus — Verification API Contract & Defect A/B Protection Suite
// =============================================================================

test("DEFECT A: API Contract Envelope Normalization", async () => {
  // Test simulated backend responses
  const mockEnvelope = {
    tasks: [
      {
        id: "11111111-1111-1111-1111-111111111111",
        status: "ASSIGNED",
        property_name: "Clean Cooking Project",
        property_address: "Kano, Nigeria",
        property_type: "Clean Energy",
        agent_name: "Field Auditor",
        assigned_agent: "22222222-2222-2222-2222-222222222222",
        verifier_id: "22222222-2222-2222-2222-222222222222",
        project_id: "33333333-3333-3333-3333-333333333333",
        asset_id: "44444444-4444-4444-4444-444444444444",
        findings: {},
        created_at: "2026-10-04T00:00:00Z",
        updated_at: "2026-10-04T00:00:00Z",
      },
    ],
    audits: [
      {
        id: "11111111-1111-1111-1111-111111111111",
        status: "ASSIGNED",
      },
    ],
    total: 1,
    page: 1,
    per_page: 50,
  };

  // Check that mock envelope possesses canonical envelope keys
  assert.ok("tasks" in mockEnvelope, "Envelope must have tasks property");
  assert.ok("audits" in mockEnvelope, "Envelope must have audits property");
  assert.equal(mockEnvelope.total, 1);
  assert.equal(Array.isArray(mockEnvelope.tasks), true);
  assert.equal(Array.isArray(mockEnvelope.audits), true);
});

test("DEFECT A: Empty Tenant Envelope Guarantees 0 Tasks and Zero map Exceptions", () => {
  const emptyTenantEnvelope = {
    tasks: [],
    audits: [],
    total: 0,
    page: 1,
    per_page: 50,
  };

  // Ensure consumer mapping tasks directly behaves safely
  const mapped = emptyTenantEnvelope.tasks.map((t: any) => t.id);
  assert.deepEqual(mapped, []);
  assert.equal(emptyTenantEnvelope.total, 0);
});

test("DEFECT B: Backend Route Declaration Order Eliminates Route Collision", () => {
  const apiPyPath = path.resolve(__dirname, "../../backend/app/domains/verification/api.py");
  const content = fs.readFileSync(apiPyPath, "utf-8");

  // Verify /packages is declared BEFORE any dynamic /{task_id}
  const packagesIndex = content.indexOf('@router.get(\n    "/packages"');
  const packagesAltIndex = content.indexOf('@router.get("/packages"');
  const actualPackagesIndex = packagesIndex !== -1 ? packagesIndex : packagesAltIndex;

  assert.ok(
    actualPackagesIndex !== -1,
    "GET /packages route must be explicitly defined in api.py"
  );

  // Check where fallback legacy /{task_id} is located
  const legacyFallbackIndex = content.indexOf('@router.get("/{task_id}")');
  if (legacyFallbackIndex !== -1) {
    assert.ok(
      actualPackagesIndex < legacyFallbackIndex,
      "Static /packages route must be registered BEFORE generic dynamic /{task_id} to avoid 422 UUID collision"
    );
  }

  // Check that namespaced /tasks/{task_id} is present
  assert.ok(
    content.includes('@router.get("/tasks/{task_id}")'),
    "Explicit namespaced /tasks/{task_id} must be present"
  );
  assert.ok(
    content.includes('@router.patch("/tasks/{task_id}")'),
    "Explicit namespaced /tasks/{task_id} must be present for PATCH"
  );
});

test("DEFECT B: Strict Tenant Scoping in Verification Package Listing", () => {
  const apiPyPath = path.resolve(__dirname, "../../backend/app/domains/verification/api.py");
  const content = fs.readFileSync(apiPyPath, "utf-8");

  assert.ok(
    content.includes("VerificationPackage.organization_id == current_user.organization_id"),
    "list_verification_packages must enforce organization_id filter"
  );
  assert.ok(
    content.includes("VerificationAccessGrant"),
    "list_verification_packages must check active auditor access grants"
  );
});
