import { test, expect } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";

// =============================================================================
// VeriField Nexus — Primary Operating Sector Live Browser Proof
// =============================================================================

test.describe("Primary Operating Sector Live E2E Verification", () => {
  test("Live Chromium proves exactly 5 canonical sector options, 0 duplicates, 0 test fixtures", async ({ page }) => {
    // 1. Navigate to live signup page
    await page.goto("http://localhost:3000/signup", { waitUntil: "networkidle" });

    // 2. Locate the Primary Operating Sector selector
    const sectorSelect = page.locator('select[data-testid="primary-operating-sector-select"]');
    await expect(sectorSelect).toBeVisible({ timeout: 10000 });

    // 3. Inspect all <option> elements
    const options = sectorSelect.locator("option");
    const optionCount = await options.count();

    // 1 placeholder + 5 canonical options = 6 total elements
    expect(optionCount).toBe(6);

    const optionValues: string[] = [];
    const optionTexts: string[] = [];

    for (let i = 0; i < optionCount; i++) {
      const val = await options.nth(i).getAttribute("value");
      const txt = (await options.nth(i).textContent())?.trim() || "";
      optionValues.push(val || "");
      optionTexts.push(txt);
    }

    console.log("All options discovered in live browser:", optionTexts);
    console.log("All option values:", optionValues);

    // Verify placeholder
    expect(optionValues[0]).toBe("");
    expect(optionTexts[0]).toBe("Select a sector...");

    // The 5 canonical selectable options
    const selectableValues = optionValues.slice(1);
    const selectableTexts = optionTexts.slice(1);

    expect(selectableValues.length).toBe(5);
    expect(selectableTexts.length).toBe(5);

    // Exact canonical codes
    expect(selectableValues).toEqual([
      "COOKSTOVES",
      "HYBRID_ENERGY",
      "BIOCHAR",
      "EV_MOBILITY",
      "AGRICULTURE_LAND_USE",
    ]);

    // Exact canonical labels
    expect(selectableTexts).toEqual([
      "Clean Cookstoves",
      "Hybrid Energy & Mini-grids",
      "Biochar Carbon Removal",
      "EV Mobility",
      "Agriculture & Land Use",
    ]);

    // Zero duplicates
    const uniqueValues = new Set(selectableValues);
    const uniqueTexts = new Set(selectableTexts);
    expect(uniqueValues.size).toBe(5);
    expect(uniqueTexts.size).toBe(5);

    // Strictly NO test fixtures or unauthorized families
    for (const text of selectableTexts) {
      expect(text).not.toContain("Test Family");
      expect(text).not.toContain("Biochar Removal Family");
      expect(text).not.toContain("FAM-");
    }

    // 4. Test interaction: Select each canonical option and verify state reactivity
    for (let i = 0; i < selectableValues.length; i++) {
      const code = selectableValues[i];
      const label = selectableTexts[i];
      await sectorSelect.selectOption(code);
      expect(await sectorSelect.inputValue()).toBe(code);
      console.log(`Verified live selection: ${code} -> ${label}`);
    }

    // Leave selected on 'BIOCHAR'
    await sectorSelect.selectOption("BIOCHAR");
    expect(await sectorSelect.inputValue()).toBe("BIOCHAR");

    // Wait briefly for UI reactivity
    await page.waitForTimeout(500);

    // Capture visual screenshot
    const artifactDir = "/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83";
    const artifactScreenshot = path.join(artifactDir, "live_primary_operating_sector_dropdown.png");
    const localScreenshotDir = path.resolve(__dirname, "screenshots");
    if (!fs.existsSync(localScreenshotDir)) {
      fs.mkdirSync(localScreenshotDir, { recursive: true });
    }
    const localScreenshot = path.join(localScreenshotDir, "live_primary_operating_sector_dropdown.png");

    await page.screenshot({ path: artifactScreenshot, fullPage: true });
    await page.screenshot({ path: localScreenshot, fullPage: true });

    console.log(`Screenshot captured successfully: ${artifactScreenshot}`);
  });
});
