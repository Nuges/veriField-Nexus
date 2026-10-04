import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

interface SetupData {
  organization_id: string;
  project_id: string;
  project_name: string;
  project_code: string;
  user_id: string;
  user_email: string;
  token: string;
  facility_id: string;
  source_id: string;
  lot_id: string;
  batch_id: string;
  batch_number: string;
  lab_id: string;
  end_use_id: string;
  tag: string;
}

test.describe('Verra VM0044 v1.2 Live Full-Stack E2E Verification', () => {
  test.use({ viewport: { width: 1440, height: 1100 } });
  test.setTimeout(120000);

  let envData: SetupData;

  test.beforeAll(async () => {
    // 1. Initialize real synthetic test entities directly in PostgreSQL 18.1
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_vm0044_live_helper.py');
    const backendDir = path.resolve(__dirname, '../../backend');
    const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test';

    const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" setup`, {
      cwd: backendDir,
    }).toString().trim();

    envData = JSON.parse(rawOutput);
  });

  test.afterAll(async () => {
    // Teardown real synthetic test entities from PostgreSQL 18.1
    if (envData?.organization_id) {
      const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_vm0044_live_helper.py');
      const backendDir = path.resolve(__dirname, '../../backend');
      const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test';

      execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${envData.organization_id}"`, {
        cwd: backendDir,
      });
    }
  });

  test('Live Full-Stack: Dual Gates (Section 4 & 7), High-Tech Quantification (Eqs 1-15), and Cryptographic Audit Lineage', async ({ page }) => {
    const userPayload = {
      id: envData.user_id,
      email: envData.user_email,
      full_name: 'Verra Project Lead',
      role: 'ORG_ADMIN',
      status: 'active',
      is_active: true,
      organization: 'VM0044 Live Verification Org',
      organization_id: envData.organization_id,
      licensed_methodologies: ['VM0044', 'PURO_BIOCHAR_2025_V2'],
      licensed_sectors: ['biochar'],
      version: 1,
      is_deleted: false,
    };

    // 1. Authenticate with real token and active project in localStorage
    await page.addInitScript(
      ({ token, userData, projectId }) => {
        window.localStorage.setItem('vf_token', token);
        window.localStorage.setItem('vf_user', JSON.stringify(userData));
        window.localStorage.setItem('vf_active_project_id', projectId);
        window.localStorage.setItem('vf_active_sector', 'biochar');
      },
      { token: envData.token, userData: userPayload, projectId: envData.project_id }
    );

    // 2. Open Biochar project on dashboard
    await page.goto(`${BASE_URL}/dashboard?workspace=biochar&methodology=VM0044&project=${envData.project_id}`);
    await page.waitForLoadState('networkidle');

    // 3. Open Biochar Value Chain Tab if not already active
    const biocharTab = page.locator('[data-testid="analytics-tab-biochar_value_chain"]');
    if (await biocharTab.isVisible()) {
      await biocharTab.click();
    }

    // 4. Click Verra VM0044 v1.2 Sub-navigation Tab
    const vm44Tab = page.locator('[data-testid="tab-vm0044"]');
    await expect(vm44Tab).toBeVisible({ timeout: 15000 });
    await vm44Tab.click();

    // 5. Verify Locked Methodology Header Elements
    await expect(page.locator('text=VERRA VCS METHODOLOGY')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=CCP-ELIGIBLE')).toBeVisible();
    await expect(page.locator('text=SCOPE 13 WASTE')).toBeVisible();
    await expect(page.locator('text=FROZEN SPECIFICATION')).toBeVisible();
    await expect(page.getByText('VM0044 v1.2', { exact: true })).toBeVisible();

    // 6. Test Dual-Gate Eligibility View (Section 4 & 7)
    const eligibilitySubtab = page.locator('[data-testid="vm0044-subtab-eligibility"]');
    await expect(eligibilitySubtab).toBeVisible();
    await eligibilitySubtab.click();

    // Run Section 4 Applicability Audit
    const evalAppBtn = page.locator('[data-testid="vm0044-btn-evaluate-applicability"]');
    await expect(evalAppBtn).toBeVisible();
    await evalAppBtn.click();
    await expect(page.getByText('ELIGIBLE', { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=1. Production Facility (Greenfield)')).toBeVisible();

    // Run Section 7 Additionality Assessment (VT0008)
    const evalAddBtn = page.locator('[data-testid="vm0044-btn-evaluate-additionality"]');
    await expect(evalAddBtn).toBeVisible();
    await evalAddBtn.click();
    await expect(page.getByText('COMPLETE', { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Step 1: Regulatory Surplus')).toBeVisible();
    await expect(page.locator('text=Step 2: Positive List (Section 4)')).toBeVisible();

    // 7. Test Quantification Engine Execution
    const calcSubtab = page.locator('[data-testid="vm0044-subtab-calculator"]');
    await expect(calcSubtab).toBeVisible();
    await calcSubtab.click();

    // Click Authoritative Execute
    const execBtn = page.locator('[data-testid="vm0044-btn-execute-authoritative"]');
    await expect(execBtn).toBeVisible();
    await execBtn.click();

    // Verify Results Container and Net Removals
    const resultsContainer = page.locator('[data-testid="vm0044-results-container"]');
    await expect(resultsContainer).toBeVisible({ timeout: 15000 });

    const netRemovals = page.locator('[data-testid="vm0044-net-removals-val"]');
    await expect(netRemovals).toBeVisible();
    const netRemovalsText = await netRemovals.textContent();
    expect(netRemovalsText).toContain('80.2062');

    // Verify Mathematical Lineage and Cryptographic Audit Signatures
    await expect(page.locator('text=Mathematical Expression Lineage:')).toBeVisible();
    await expect(page.locator('text=Canonical Snapshot Hash:')).toBeVisible();
    await expect(page.locator('text=Execution Audit Hash:')).toBeVisible();

    // 8. Capture Full-Page Screenshot Proof
    const screenshotDir = path.resolve(__dirname, 'screenshots');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    const screenshotPath = path.join(screenshotDir, 'vm0044_v12_live_fullstack_proof.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });

    // Copy to evidence directories
    const evidenceDir = '/tmp/verifield_vm0044_v12_evidence';
    if (!fs.existsSync(evidenceDir)) {
      fs.mkdirSync(evidenceDir, { recursive: true });
    }
    fs.copyFileSync(screenshotPath, path.join(evidenceDir, 'vm0044_v12_live_fullstack_proof.png'));

    const brainArtifactDir = '/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83';
    if (fs.existsSync(brainArtifactDir)) {
      fs.copyFileSync(screenshotPath, path.join(brainArtifactDir, 'vm0044_v12_live_fullstack_proof.png'));
    }
  });
});
