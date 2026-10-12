// =============================================================================
// VeriField Nexus — Project Methodology Resolution & Fallback Defense Unit Tests
// =============================================================================

import test from "node:test";
import assert from "node:assert/strict";
import { resolveProjectMethodology } from "../src/lib/projectMethodology";

test("Project Methodology Resolution — Case A: Unassigned project renders 'Under Assessment'", () => {
  // Case A input:
  // methodology_id = null
  // methodology_code = null
  // baseline_parameters.methodology_code = absent
  const unassignedProject = {
    id: "proj-unassigned-001",
    name: "Unassigned Soil Pilot",
    methodology_id: null,
    methodology_code: null,
    baseline_parameters: {
      purpose: "Sensor moisture logging",
      environment: "test",
    },
  };

  const result = resolveProjectMethodology(unassignedProject);

  assert.equal(result.isAssigned, false);
  assert.equal(result.code, "Under Assessment");
  assert.notEqual(result.code, "VM0042");
  assert.equal(result.version, undefined);
});

test("Project Methodology Resolution — Case A (Deepak Canonical Invariant): Deepak Farm returns 'Under Assessment' without VM0042", () => {
  // Exact persisted DB representation of Deepak Farm Soil Sensor Pilot:
  const deepakProject = {
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

  const result = resolveProjectMethodology(deepakProject);

  assert.equal(result.isAssigned, false);
  assert.equal(result.code, "Under Assessment");
  assert.notEqual(result.code, "VM0042");
  assert.notEqual(result.code, "VM0042 / Agricultural MRV");
});

test("Project Methodology Resolution — Case B: Assigned project with direct methodology_code (VM0047)", () => {
  const assignedProject = {
    id: "proj-assigned-002",
    name: "Forestry Carbon Project",
    methodology_id: "some-uuid",
    methodology_code: "VM0047",
    methodology_version: "1.1",
    baseline_parameters: {},
  };

  const result = resolveProjectMethodology(assignedProject);

  assert.equal(result.isAssigned, true);
  assert.equal(result.code, "VM0047");
  assert.equal(result.version, "1.1");
  assert.notEqual(result.code, "Under Assessment");
});

test("Project Methodology Resolution — Case B: Assigned project via baseline_parameters contract (VM0042)", () => {
  const contractProject = {
    id: "proj-contract-003",
    name: "Validated Soil Carbon Project",
    methodology_id: null,
    baseline_parameters: {
      methodology_code: "VM0042",
      methodology_version: "2.2",
    },
  };

  const result = resolveProjectMethodology(contractProject);

  assert.equal(result.isAssigned, true);
  assert.equal(result.code, "VM0042");
  assert.equal(result.version, "2.2");
});

test("Project Methodology Resolution — Case B: Nested methodology object payload support", () => {
  const nestedProject = {
    id: "proj-nested-004",
    name: "Cookstoves Efficiency Project",
    methodology: {
      code: "GS_MECD",
      version: "3.0",
    },
  };

  const result = resolveProjectMethodology(nestedProject);

  assert.equal(result.isAssigned, true);
  assert.equal(result.code, "GS-MECD");
  assert.equal(result.version, "3.0");
});

test("Project Methodology Resolution — Null & undefined safety fallback", () => {
  assert.deepEqual(resolveProjectMethodology(null), {
    code: "Under Assessment",
    isAssigned: false,
    version: undefined,
  });

  assert.deepEqual(resolveProjectMethodology(undefined), {
    code: "Under Assessment",
    isAssigned: false,
    version: undefined,
  });

  assert.deepEqual(resolveProjectMethodology({}), {
    code: "Under Assessment",
    isAssigned: false,
    version: undefined,
  });
});
