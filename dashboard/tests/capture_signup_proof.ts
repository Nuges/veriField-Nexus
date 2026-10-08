import { chromium } from "playwright";
import fs from "fs";
import path from "path";

async function main() {
  const artifactDir = "/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83";
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  console.log("Navigating to http://localhost:3005/signup...");
  await page.goto("http://localhost:3005/signup", { waitUntil: "networkidle" });

  // 1. Initial State: No sector selected
  const sectorSelect = page.locator("#primary-operating-sector");
  const methSelect = page.locator("#primary-operating-methodology");

  const isMethDisabledInitial = await methSelect.isDisabled();
  const initialMethOptions = await methSelect.locator("option").allTextContents();
  console.log("Initial methodology disabled:", isMethDisabledInitial);
  console.log("Initial methodology options:", initialMethOptions);

  if (!isMethDisabledInitial || initialMethOptions[0] !== "Select a sector first") {
    throw new Error("Initial state assertion failed: methodology dropdown should be disabled with 'Select a sector first'");
  }

  const p1 = path.join(artifactDir, "live_signup_01_initial_state.png");
  await page.screenshot({ path: p1, fullPage: false });
  console.log("Saved screenshot 1 to:", p1);

  // 2. Select "Agriculture & Land Use"
  console.log("Selecting Agriculture & Land Use...");
  await sectorSelect.selectOption("AGRICULTURE_LAND_USE");
  await page.waitForTimeout(300);

  const isMethDisabledAgri = await methSelect.isDisabled();
  const agriMethOptions = await methSelect.locator("option").allTextContents();
  console.log("Agriculture methodology disabled:", isMethDisabledAgri);
  console.log("Agriculture methodology options:", agriMethOptions);

  if (isMethDisabledAgri) {
    throw new Error("Agriculture state assertion failed: methodology dropdown should be enabled");
  }

  // Check that options contain ONLY "Select a methodology..." and "VM0042 — Improved Agricultural Land Management"
  const nonPromptOptions = agriMethOptions.filter(o => !o.includes("Select a methodology"));
  console.log("Agriculture non-prompt options:", nonPromptOptions);

  if (nonPromptOptions.length !== 1 || !nonPromptOptions[0].includes("VM0042")) {
    throw new Error(`Agriculture scoping failed! Expected only VM0042, got: ${JSON.stringify(nonPromptOptions)}`);
  }

  // Select VM0042
  await methSelect.selectOption({ label: nonPromptOptions[0] });
  await page.waitForTimeout(300);

  const p2 = path.join(artifactDir, "live_signup_02_agriculture_vm0042.png");
  await page.screenshot({ path: p2, fullPage: false });
  console.log("Saved screenshot 2 to:", p2);

  // 3. Switch sector to "Biochar Carbon Removal"
  console.log("Switching to Biochar Carbon Removal...");
  await sectorSelect.selectOption("BIOCHAR");
  await page.waitForTimeout(300);

  const biocharValue = await methSelect.inputValue();
  console.log("Methodology selection after sector switch (should be empty):", `"${biocharValue}"`);
  if (biocharValue !== "") {
    throw new Error("Sector switch assertion failed: methodology selection was not cleared");
  }

  const biocharOptions = await methSelect.locator("option").allTextContents();
  console.log("Biochar methodology options:", biocharOptions);

  const biocharNonPrompt = biocharOptions.filter(o => !o.includes("Select a methodology"));
  if (biocharNonPrompt.some(o => o.includes("VM0042"))) {
    throw new Error("Cross-sector leakage detected: VM0042 present in Biochar options!");
  }

  const p3 = path.join(artifactDir, "live_signup_03_biochar_switched.png");
  await page.screenshot({ path: p3, fullPage: false });
  console.log("Saved screenshot 3 to:", p3);

  // 4. Switch to "Hybrid Energy & Mini-grids"
  console.log("Switching to Hybrid Energy & Mini-grids...");
  await sectorSelect.selectOption("HYBRID_ENERGY");
  await page.waitForTimeout(300);

  const hybridOptions = await methSelect.locator("option").allTextContents();
  console.log("Hybrid energy methodology options:", hybridOptions);

  const p4 = path.join(artifactDir, "live_signup_04_hybrid_switched.png");
  await page.screenshot({ path: p4, fullPage: false });
  console.log("Saved screenshot 4 to:", p4);

  await browser.close();
  console.log("Visual verification completed successfully with 4 screenshots captured!");
}

main().catch((err) => {
  console.error("Visual proof execution error:", err);
  process.exit(1);
});
