// Reproducible lexical/AST inventory. No API requests or live integrations.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import ts from "typescript";

const root = path.resolve(import.meta.dirname, "../..");
const apiPath = "dashboard/src/lib/api.ts";
const source = fs.readFileSync(path.join(root, apiPath), "utf8");
const ast = ts.createSourceFile(apiPath, source, ts.ScriptTarget.Latest, true);
const routes = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const files = execFileSync("rg", ["--files", "--hidden", "-g", "!.git", "-g", "!dashboard/scripts/inventory_api_capabilities.mjs"], { cwd: root, encoding: "utf8" })
  .trim().split("\n").filter((file) => /\.(tsx?|jsx?|mjs|cjs|py|dart|sh)$/.test(file) && file !== apiPath)
  .map((file) => ({ file, text: fs.readFileSync(path.join(root, file), "utf8") }));
const rows = [];
for (const node of ast.statements) {
  if (!ts.isFunctionDeclaration(node) || !node.name || !node.modifiers?.some((modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword)) continue;
  const name = node.name.text;
  const body = node.getText(ast);
  const pattern = new RegExp(`\\b${name}\\b`);
  const consumers = files.filter(({ text }) => pattern.test(text)).map(({ file }) => file);
  const ui = consumers.filter((file) => file.startsWith("dashboard/src/"));
  const support = consumers.filter((file) => !file.startsWith("dashboard/src/"));
  const literalFamilies = [...body.matchAll(/[`"']\/(?:api\/v1\/)?([a-z][a-z0-9_-]*)\//g)].map((match) => match[1]);
  const backend = literalFamilies.some((family) => routes.some((route) => route.path.startsWith(`/api/v1/${family}/`)));
  let classification = ui.length ? "Current operational workflow" : "Future / gated capability";
  let decision = ui.length ? "Retain existing consumer" : "Retain; no speculative deletion";
  let role = "Existing endpoint policy; not re-audited";
  if (["getApiV1", "getAuthToken", "setAuthToken", "apiFetch"].includes(name)) {
    classification = "Internal service"; decision = "Retain shared client utility"; role = "Internal";
  } else if (["fetchCarbonProjects", "createCarbonProject", "fetchVerificationTasks", "downloadArticle6PackageZip"].includes(name)) {
    classification = "Legacy / duplicate"; decision = "Retain compatibility entry point";
  } else if (/issueVerra|issueGoldStandard/.test(name)) {
    classification = "Unsupported or incomplete"; decision = "Retain stub; no issuance UI";
  } else if (/submitITMO|executeCarbonMinting|Config|Plugin|Jurisdiction|Puro|Lineage/.test(name)) {
    classification = "Advanced or specialist workflow"; decision = "Retain specialist controls; no ordinary-operator exposure";
  } else if (/fetchRegistryReadiness|fetchRegistryDocumentMatrix|downloadRegistryPackage|downloadRegistryDocument/.test(name)) {
    classification = "Current operational workflow"; decision = "Expose in canonical project preparation"; role = "registry:read";
  } else if (support.length && !ui.length) {
    classification = "Internal service"; decision = "Retain test/automation dependency";
  }
  rows.push({ name, backend: backend ? "Route family present; contract not inferred" : "Indirect/dynamic; requires contract review", ui, support, classification, decision, role });
}
const unused = rows.filter((row) => !row.ui.length && !row.support.length);
const header = `# Phase 2 API capability inventory\n\nGenerated from TypeScript export declarations, repository-wide lexical references, and ${routes.length} actual FastAPI route registrations.\n\n${rows.length} exported functions inspected; ${unused.length} have no literal consumer outside api.ts. This replaces the old 51-export estimate. A textual reference can be a test, comment, or import; it is not proof of a working UI. Dynamic aliases cannot be ruled out. All potentially referenced exports are retained. Route-family presence is not a readiness or complete-contract claim.\n\n`;
const table = "| Capability | Backend available | Frontend consumer | Role | Classification | Decision |\n|---|---|---|---|---|---|\n";
const render = (row) => `| ${row.name} | ${row.backend} | ${row.ui.join("; ") || (row.support.length ? `Support only: ${row.support.join("; ")}` : "None found; retained")} | ${row.role} | ${row.classification} | ${row.decision} |`;
const output = header + "## No literal external consumers\n\n" + table + unused.map(render).join("\n") + "\n\n## Complete exported-function inventory\n\n" + table + rows.map(render).join("\n") + "\n";
fs.mkdirSync(path.join(root, "docs/phase2"), { recursive: true });
fs.writeFileSync(path.join(root, "docs/phase2/api_capability_inventory.md"), output);
fs.writeFileSync(path.join(root, "docs/phase2/api_capability_inventory.json"), JSON.stringify(rows, null, 2));
console.log(JSON.stringify({ exportedFunctions: rows.length, noLiteralConsumers: unused.length, sourceFilesSearched: files.length }));
