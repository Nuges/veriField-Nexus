import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000';

interface SetupData {
  organization_id: string;
  project_id: string;
  project_name: string;
  project_code: string;
  prerequisite_id: string;
  prerequisite_code: string;
  snapshot_id: string;
  pm_user_id: string;
  pm_user_email: string;
  pm_token: string;
  field_agent_id: string;
  field_agent_email: string;
  field_token: string;
  auditor_id: string;
  auditor_email: string;
  auditor_token: string;
  tag: string;
}

function setupLiveProject(divergentBd: boolean = false): SetupData {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b1_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';
  const flag = divergentBd ? ' --divergent-bd' : '';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" setup${flag}`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

function cleanupLiveProject(orgId: string): void {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b1_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

  execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${orgId}"`, {
    cwd: backendDir,
  });
}

function verifyDbSocStock(projectId: string): Record<string, unknown> {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b1_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_soc_stock "${projectId}"`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

test.describe('Agriculture MRV Phase 3B-1 Live Full-Stack SOC Stock & ESM Engine E2E', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(120000);

  test('Live Case 1: Standard SOC Stock & ESM Normalization Lifecycle', async ({ page, request }) => {
    const setupData = setupLiveProject(false);
    console.log(`[E2E Case 1] Seeded project ${setupData.project_code} in PostgreSQL`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-1 Live Org',
        organization_id: setupData.organization_id,
        licensed_methodologies: ['VM0042'],
        licensed_sectors: ['agriculture_land_use'],
        version: 1,
        is_deleted: false,
      };

      // 1. Authenticate with real token and active project in localStorage
      await page.addInitScript(
        ({ token, userData, projectId }) => {
          window.localStorage.setItem('vf_token', token);
          window.localStorage.setItem('vf_user', JSON.stringify(userData));
          window.localStorage.setItem('vf_active_project_id', projectId);
          window.localStorage.setItem('vf_active_sector', 'agriculture_land_use');
        },
        { token: setupData.pm_token, userData: userPayload, projectId: setupData.project_id }
      );

      // 2. Open AGRICULTURE_LAND_USE project on dashboard
      await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use&methodology=VM0042&project=${setupData.project_id}`);
      await page.waitForLoadState('networkidle');

      // 3. Open Agriculture Foundation tab
      const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
      await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
      await agriWorkflowTab.click();

      // 4. Open Phase 3B Quantification Readiness / Prerequisites Tab
      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      // 5. Click the SOC Stock & ESM (Phase 3B-1) tab
      const socTabButton = page.locator('button:has-text("SOC Stock & ESM (Phase 3B-1)")');
      await expect(socTabButton).toBeVisible({ timeout: 10000 });
      await socTabButton.click();

      // 6. Verify Carbon Policy Lock Invariant Banner
      const policyBanner = page.locator('text=Authoritative Carbon Quantification: NOT_CONFIGURED');
      await expect(policyBanner).toBeVisible({ timeout: 10000 });

      // 7. Evaluate Preview
      const previewButton = page.locator('button:has-text("Evaluate Preview")');
      await expect(previewButton).toBeVisible();
      await previewButton.click();

      // Verify preview result appears
      const previewHeader = page.locator('text=Evaluation Preview Result');
      await expect(previewHeader).toBeVisible({ timeout: 15000 });

      // Verify Project SOC Stock metric card is visible
      const stockCard = page.locator('text=Project SOC Stock (ESM)');
      await expect(stockCard).toBeVisible();

      // 8. Submit Authoritative Calculation
      const calculateButton = page.locator('button:has-text("Calculate & Persist Authoritative Stock")');
      await expect(calculateButton).toBeVisible();
      await calculateButton.click();

      // Wait for persistent card to appear in results list
      const persistentSection = page.locator('text=Persisted Authoritative SOC Stock Results');
      await expect(persistentSection).toBeVisible({ timeout: 15000 });

      const stockResultCode = page.locator('text=SOC-PT-');
      await expect(stockResultCode.first()).toBeVisible({ timeout: 15000 });

      // 9. Click Inspect Component Profile & Layer Breakdown
      const inspectButton = page.locator('button:has-text("Inspect Component Profile & Layer Breakdown")').first();
      await expect(inspectButton).toBeVisible();
      await inspectButton.click();

      // Verify modal opens with layer breakdown table
      const layerArithmeticHeader = page.locator('text=Layer-by-Layer Fine Soil Mass & SOC Arithmetic');
      await expect(layerArithmeticHeader).toBeVisible({ timeout: 10000 });

      // Verify cryptographic SHA-256 proof in modal
      const shaProof = page.locator('text=Calculation SHA-256:');
      await expect(shaProof).toBeVisible();

      // Capture screenshot
      const artifactDir = '/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83';
      const screenshotPath = path.join(artifactDir, 'live_soc_stock_e2e.png');
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`[E2E Case 1] Saved live screenshot to ${screenshotPath}`);

      // 10. Direct PostgreSQL verification
      const dbProof = verifyDbSocStock(setupData.project_id);
      expect(dbProof.result_code).toBeTruthy();
      expect(dbProof.soc_stock_t_c_per_ha).toBeGreaterThan(0);
      expect(dbProof.reference_soil_mass_t_ha).toBeGreaterThan(0);
      expect(dbProof.tco2e_yield).toBeNull();
      expect(dbProof.ledger_mint_count).toBe(0);
      expect(dbProof.fail_closed_contract_passed).toBe(true);

    } finally {
      cleanupLiveProject(setupData.organization_id);
      console.log(`[E2E Case 1] Cleaned up test org ${setupData.organization_id}`);
    }
  });

  test('Live Case 2: ESM Normalization with Divergent Bulk Density', async ({ page }) => {
    const setupData = setupLiveProject(true);
    console.log(`[E2E Case 2] Seeded divergent bulk density project ${setupData.project_code}`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-1 Live Org',
        organization_id: setupData.organization_id,
        licensed_methodologies: ['VM0042'],
        licensed_sectors: ['agriculture_land_use'],
        version: 1,
        is_deleted: false,
      };

      await page.addInitScript(
        ({ token, userData, projectId }) => {
          window.localStorage.setItem('vf_token', token);
          window.localStorage.setItem('vf_user', JSON.stringify(userData));
          window.localStorage.setItem('vf_active_project_id', projectId);
          window.localStorage.setItem('vf_active_sector', 'agriculture_land_use');
        },
        { token: setupData.pm_token, userData: userPayload, projectId: setupData.project_id }
      );

      await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use&methodology=VM0042&project=${setupData.project_id}`);
      await page.waitForLoadState('networkidle');

      const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
      await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
      await agriWorkflowTab.click();

      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      const socTabButton = page.locator('button:has-text("SOC Stock & ESM (Phase 3B-1)")');
      await expect(socTabButton).toBeVisible({ timeout: 10000 });
      await socTabButton.click();

      // Set Reference Soil Mass to baseline 3822.0 t/ha to demonstrate ESM depth adjustment for divergent BD
      const refMassInput = page.locator('input[placeholder*="Auto-derived"]');
      await refMassInput.fill('3822.00');

      // Click Evaluate Preview
      const previewButton = page.locator('button:has-text("Evaluate Preview")');
      await expect(previewButton).toBeVisible();
      await previewButton.click();

      const previewHeader = page.locator('text=Evaluation Preview Result');
      await expect(previewHeader).toBeVisible({ timeout: 15000 });

      // Calculate authoritative stock
      const calculateButton = page.locator('button:has-text("Calculate & Persist Authoritative Stock")');
      await calculateButton.click();

      const stockResultCode = page.locator('text=SOC-PT-');
      await expect(stockResultCode.first()).toBeVisible({ timeout: 15000 });

      // Capture screenshot
      const artifactDir = '/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83';
      const screenshotPath = path.join(artifactDir, 'live_esm_divergent_bd_e2e.png');
      await page.screenshot({ path: screenshotPath, fullPage: true });

      // Direct DB proof
      const dbProof = verifyDbSocStock(setupData.project_id);
      expect(dbProof.soc_stock_t_c_per_ha).toBeGreaterThan(0);
      expect(dbProof.equivalent_depth_cm).toBeLessThan(30.0);
      expect(dbProof.fail_closed_contract_passed).toBe(true);

    } finally {
      cleanupLiveProject(setupData.organization_id);
      console.log(`[E2E Case 2] Cleaned up test org ${setupData.organization_id}`);
    }
  });

  test('Live Case 3: Blocked / Fail-Closed & Segregation of Duties', async ({ page }) => {
    const setupData = setupLiveProject(false);
    console.log(`[E2E Case 3] Testing Segregation of Duties with field agent ${setupData.field_agent_email}`);

    try {
      const fieldPayload = {
        id: setupData.field_agent_id,
        email: setupData.field_agent_email,
        full_name: 'Tariq Field Agent',
        role: 'FIELD_AGENT',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-1 Live Org',
        organization_id: setupData.organization_id,
        licensed_methodologies: ['VM0042'],
        licensed_sectors: ['agriculture_land_use'],
        version: 1,
        is_deleted: false,
      };

      await page.addInitScript(
        ({ token, userData, projectId }) => {
          window.localStorage.setItem('vf_token', token);
          window.localStorage.setItem('vf_user', JSON.stringify(userData));
          window.localStorage.setItem('vf_active_project_id', projectId);
          window.localStorage.setItem('vf_active_sector', 'agriculture_land_use');
        },
        { token: setupData.field_token, userData: fieldPayload, projectId: setupData.project_id }
      );

      await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use&methodology=VM0042&project=${setupData.project_id}`);
      await page.waitForLoadState('networkidle');

      const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
      await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
      await agriWorkflowTab.click();

      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      const socTabButton = page.locator('button:has-text("SOC Stock & ESM (Phase 3B-1)")');
      await expect(socTabButton).toBeVisible({ timeout: 10000 });
      await socTabButton.click();

      // Field Agent sees SoD notice and Calculate button is disabled
      const sodNotice = page.locator('text=Field Agents are restricted to preview only (Segregation of Duties)');
      await expect(sodNotice).toBeVisible();

      const calculateButton = page.locator('button:has-text("Calculate & Persist Authoritative Stock")');
      await expect(calculateButton).toBeDisabled();

      // Field Agent can still evaluate preview
      const previewButton = page.locator('button:has-text("Evaluate Preview")');
      await expect(previewButton).toBeEnabled();

      // Capture screenshot
      const artifactDir = '/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83';
      const screenshotPath = path.join(artifactDir, 'live_soc_stock_blocked_e2e.png');
      await page.screenshot({ path: screenshotPath, fullPage: true });

    } finally {
      cleanupLiveProject(setupData.organization_id);
      console.log(`[E2E Case 3] Cleaned up test org ${setupData.organization_id}`);
    }
  });
});
