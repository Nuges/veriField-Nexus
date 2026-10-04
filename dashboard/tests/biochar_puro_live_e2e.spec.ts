import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';

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

test.describe('Puro Biochar Edition 2025 V2 Live Full-Stack E2E Verification', () => {
  test.use({ viewport: { width: 1440, height: 1100 } });
  test.setTimeout(120000);

  let envData: SetupData;

  test.beforeAll(async () => {
    // 1. Initialize real synthetic test entities directly in PostgreSQL 18.1
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_dual_pathway_live_helper.py');
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
      const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_dual_pathway_live_helper.py');
      const backendDir = path.resolve(__dirname, '../../backend');
      const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test';

      execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${envData.organization_id}"`, {
        cwd: backendDir,
      });
    }
  });

  test('Live Full-Stack: Puro 2025 V2 Authoritative Quantification and PostgreSQL Lineage', async ({ page }) => {
    const userPayload = {
      id: envData.user_id,
      email: envData.user_email,
      full_name: 'Biochar Verification Lead',
      role: 'ORG_ADMIN',
      status: 'active',
      is_active: true,
      organization: 'Dual-Pathway Live Verification Org',
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
    await page.goto(`${BASE_URL}/dashboard?workspace=biochar&methodology=PURO_BIOCHAR_2025_V2&project=${envData.project_id}`);
    await page.waitForLoadState('domcontentloaded');

    // 3. Open Biochar Value Chain Tab if not already active
    const biocharTab = page.locator('[data-testid="analytics-tab-biochar_value_chain"]');
    if (await biocharTab.isVisible()) {
      await biocharTab.click();
    }

    // 4. Click Puro 2025 V2 Sub-navigation Tab
    const puroTab = page.locator('button:has-text("Puro 2025 V2")');
    await expect(puroTab).toBeVisible({ timeout: 15000 });
    await puroTab.click();

    // 5. Verify Puro Methodology Header Elements
    await expect(page.locator('text=Puro.earth Biochar Edition 2025 V2')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Deterministic CORC Quantification Console')).toBeVisible();
    await expect(page.locator('text=Engine v2.0.0')).toBeVisible();

    // 6. Select Batch in Authoritative Mode
    const batchSelect = page.locator('[data-testid="puro-batch-select"]');
    await expect(batchSelect).toBeVisible({ timeout: 10000 });
    await batchSelect.selectOption(envData.batch_id);

    // Verify Dry Mass and Molar H/C pass badge
    await expect(page.locator('text=PASS <0.70')).toBeVisible({ timeout: 10000 });

    // 7. Click Authoritative Quantification Execution
    const execBtn = page.locator('[data-testid="puro-btn-execute-quantification"]');
    await expect(execBtn).toBeVisible({ timeout: 10000 });
    await execBtn.click();

    // 8. Verify Deterministic Quantification Results
    await expect(page.locator('text=Net Quantified Carbon Removal')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('CORC200+', { exact: true })).toBeVisible();
    await expect(page.getByText('SUCCESS', { exact: true })).toBeVisible();
    await expect(page.locator('text=Point of Creation:')).toBeVisible();
    await expect(page.locator('text=Calculation Hash (SHA-256):')).toBeVisible();

    // 9. Direct PostgreSQL Verification
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_dual_pathway_live_helper.py');
    const backendDir = path.resolve(__dirname, '../../backend');
    const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test';

    const verifyOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_puro "${envData.batch_id}"`, {
      cwd: backendDir,
    }).toString().trim();

    const dbProof = JSON.parse(verifyOutput);
    expect(dbProof.verified).toBe(true);
    expect(dbProof.calculation_status).toBe('SUCCESS');
    expect(dbProof.calculation_mode).toBe('AUTHORITATIVE');
    expect(dbProof.durability_class).toBe('CORC200+');
    expect(dbProof.calculation_hash).toHaveLength(64);
  });
});
