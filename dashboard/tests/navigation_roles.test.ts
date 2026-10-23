import { test } from "node:test";
import assert from "node:assert/strict";
import { CANONICAL_ROLES, canPerformAction, isRouteAuthorized, isDashboardRoleAllowed } from "../src/lib/roles";
import { getNavigationGroups } from "../src/lib/navigation";
import { CAPTURE_FIELDS, captureQueueKey, projectCaptureSector, validateCapture } from "../src/lib/fieldCapture";
import type { Project } from "../src/lib/types";

for (const role of Object.values(CANONICAL_ROLES)) {
  test(`${role}: navigation has unique destinations and direct access agrees`, () => {
    const items = getNavigationGroups(role).flatMap(g => g.items);
    assert.ok(items.length > 0);
    assert.equal(new Set(items.map(i => i.href)).size, items.length);
    assert.equal(new Set(items.map(i => i.label)).size, items.length);
    for (const item of items) {
      assert.ok(isRouteAuthorized(item.href, role), `${role} ${item.href}`);
      assert.doesNotMatch(item.label, /\bAI\b|intelligence|command|ledger nodes/i);
    }
  });
}
test("unknown roles and unregistered paths fail closed", () => {
  for (const role of [undefined, "", "invented_admin"]) {
    assert.equal(isDashboardRoleAllowed(role), false);
    assert.equal(isRouteAuthorized("/dashboard", role), false);
    assert.equal(canPerformAction("project:create", role), false);
  }
  assert.equal(isRouteAuthorized("/dashboard/new-admin-tool", "VIEWER"), false);
  assert.equal(isRouteAuthorized("/dashboard/people", "vvb"), false);
});
test("administrators oversee independent verification without performing it", () => {
  for (const role of ["SUPER_ADMIN", "ORG_ADMIN", "admin", "FIELD_SUPERVISOR", "QA_OFFICER"]) {
    assert.equal(canPerformAction("activity:verify", role), false);
    assert.equal(canPerformAction("audit:sign", role), false);
  }
  for (const role of ["VERIFIER", "AUDITOR", "vvb", "vvb_auditor"]) {
    assert.equal(canPerformAction("audit:sign", role), true);
    assert.equal(canPerformAction("project:create", role), false);
    assert.equal(canPerformAction("users:manage", role), false);
    assert.equal(isRouteAuthorized("/capture", role), false);
  }
});
test("super admin retains field and administration oversight", () => {
  const destinations = getNavigationGroups("SUPER_ADMIN").flatMap(g => g.items.map(i => i.href));
  for (const path of ["/super-admin", "/dashboard/people", "/dashboard/projects", "/dashboard/assets", "/dashboard/sensors", "/dashboard/operations", "/dashboard/agents", "/dashboard/verifications"]) assert.ok(destinations.includes(path), path);
});
for (const sector of Object.keys(CAPTURE_FIELDS)) {
  test(`${sector}: capture resolves from project, requires access and real coordinates`, () => {
    const p = { id: "project", sector, baseline_parameters: {} } as Project;
    assert.equal(projectCaptureSector(p), sector);
    assert.equal(validateCapture(p, [sector], "4", 0, 0), null);
    assert.ok(validateCapture(p, [], "4", 0, 0));
    assert.ok(validateCapture(p, [sector], "0", 0, 0));
    assert.ok(validateCapture(p, [sector], "4", null, null));
  });
}
test("capture never assigns a sector to an unconfigured project; queues are account scoped", () => {
  assert.equal(projectCaptureSector({ baseline_parameters: {} } as Project), null);
  assert.notEqual(captureQueueKey("one", "org"), captureQueueKey("two", "org"));
  assert.notEqual(captureQueueKey("one", "org"), captureQueueKey("one", "other"));
});
