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

test.describe('Dual-Pathway Cross-Methodology Conflict Prevention E2E', () => {
  test.use({ viewport: { width: 1440, height: 1100 } });
  test.setTimeout(120000);

  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_dual_pathway_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test';

  test('Conflict Direction 1: Puro Authoritative Claim Blocks VM0044 Authoritative Claim in UI', async ({ page }) => {
    // 1. Setup fresh shared batch
    const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" setup`, {
      cwd: backendDir,
    }).toString().trim();
    const envData: SetupData = JSON.parse(rawOutput);

    try {
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

      await page.addInitScript(
        ({ token, userData, projectId }) => {
          window.localStorage.setItem('vf_token', token);
          window.localStorage.setItem('vf_user', JSON.stringify(userData));
          window.localStorage.setItem('vf_active_project_id', projectId);
          window.localStorage.setItem('vf_active_sector', 'biochar');
        },
        { token: envData.token, userData: userPayload, projectId: envData.project_id }
      );

      // 2. Open Puro tab and execute Authoritative Quantification
      await page.goto(`${BASE_URL}/dashboard?workspace=biochar&methodology=PURO_BIOCHAR_2025_V2&project=${envData.project_id}`);
      await page.waitForLoadState('domcontentloaded');

      const biocharTab = page.locator('[data-testid="analytics-tab-biochar_value_chain"]');
      if (await biocharTab.isVisible()) {
        await biocharTab.click();
      }

      const puroTab = page.locator('button:has-text("Puro 2025 V2")');
      await expect(puroTab).toBeVisible({ timeout: 15000 });
      await puroTab.click();

      // Ensure batch is selected and execute Puro
      const batchSelect = page.locator('[data-testid="puro-batch-select"]');
      await expect(batchSelect).toBeVisible({ timeout: 10000 });
      await batchSelect.selectOption(envData.batch_id);

      const puroExecBtn = page.locator('[data-testid="puro-btn-execute-quantification"]');
      await expect(puroExecBtn).toBeVisible({ timeout: 10000 });
      await puroExecBtn.click();

      await expect(page.getByText('SUCCESS', { exact: true })).toBeVisible({ timeout: 15000 });

      // 3. Switch to Verra VM0044 v1.2 tab on the SAME batch
      const vm44Tab = page.locator('[data-testid="tab-vm0044"]');
      await expect(vm44Tab).toBeVisible();
      await vm44Tab.click();

      // Go to calculator subtab
      const calcSubtab = page.locator('[data-testid="vm0044-subtab-calculator"]');
      await expect(calcSubtab).toBeVisible();
      await calcSubtab.click();

      // Attempt Authoritative Execution on VM0044
      const vm44ExecBtn = page.locator('[data-testid="vm0044-btn-execute-authoritative"]');
      await expect(vm44ExecBtn).toBeVisible();
      await vm44ExecBtn.click();

      // 4. Verify deterministic DOUBLE_COUNTING_CONFLICT in UI
      const errorBanner = page.locator('text=DOUBLE_COUNTING_CONFLICT');
      await expect(errorBanner).toBeVisible({ timeout: 15000 });
      await expect(page.locator('text=already claimed under Puro.earth Standard')).toBeVisible();

      // 5. Query PostgreSQL: prove exactly 1 authoritative claim exists (Puro=yes, VM0044=no)
      const conflictOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_conflict "${envData.batch_id}"`, {
        cwd: backendDir,
      }).toString().trim();
      const conflictProof = JSON.parse(conflictOutput);

      expect(conflictProof.conflict_verified).toBe(true);
      expect(conflictProof.total_authoritative_claims).toBe(1);
      expect(conflictProof.puro_claimed).toBe(true);
      expect(conflictProof.vm0044_claimed).toBe(false);

    } finally {
      // Cleanup
      execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${envData.organization_id}"`, {
        cwd: backendDir,
      });
    }
  });

  test('Conflict Direction 2: VM0044 Authoritative Claim Blocks Puro Authoritative Claim in UI', async ({ page }) => {
    // 1. Setup fresh shared batch
    const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" setup`, {
      cwd: backendDir,
    }).toString().trim();
    const envData: SetupData = JSON.parse(rawOutput);

    try {
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

      await page.addInitScript(
        ({ token, userData, projectId }) => {
          window.localStorage.setItem('vf_token', token);
          window.localStorage.setItem('vf_user', JSON.stringify(userData));
          window.localStorage.setItem('vf_active_project_id', projectId);
          window.localStorage.setItem('vf_active_sector', 'biochar');
        },
        { token: envData.token, userData: userPayload, projectId: envData.project_id }
      );

      // 2. Open VM0044 tab and execute Authoritative Quantification
      await page.goto(`${BASE_URL}/dashboard?workspace=biochar&methodology=VM0044&project=${envData.project_id}`);
      await page.waitForLoadState('domcontentloaded');

      const biocharTab = page.locator('[data-testid="analytics-tab-biochar_value_chain"]');
      if (await biocharTab.isVisible()) {
        await biocharTab.click();
      }

      const vm44Tab = page.locator('[data-testid="tab-vm0044"]');
      await expect(vm44Tab).toBeVisible({ timeout: 15000 });
      await vm44Tab.click();

      const calcSubtab = page.locator('[data-testid="vm0044-subtab-calculator"]');
      await expect(calcSubtab).toBeVisible();
      await calcSubtab.click();

      const vm44ExecBtn = page.locator('[data-testid="vm0044-btn-execute-authoritative"]');
      await expect(vm44ExecBtn).toBeVisible();
      await vm44ExecBtn.click();

      await expect(page.locator('[data-testid="vm0044-results-container"]')).toBeVisible({ timeout: 15000 });

      // 3. Switch to Puro 2025 V2 tab on the SAME batch
      const puroTab = page.locator('button:has-text("Puro 2025 V2")');
      await expect(puroTab).toBeVisible();
      await puroTab.click();

      // Ensure batch is selected and click Authoritative Quantification
      const batchSelect = page.locator('[data-testid="puro-batch-select"]');
      await expect(batchSelect).toBeVisible({ timeout: 10000 });
      await batchSelect.selectOption(envData.batch_id);

      const puroExecBtn = page.locator('[data-testid="puro-btn-execute-quantification"]');
      await expect(puroExecBtn).toBeVisible({ timeout: 10000 });
      await puroExecBtn.click();

      // 4. Verify deterministic DOUBLE_COUNTING_CONFLICT in UI
      await expect(page.getByText('DOUBLE_COUNTING_CONFLICT', { exact: false })).toBeVisible({ timeout: 15000 });

      // 5. Query PostgreSQL: prove exactly 1 authoritative claim exists (VM0044=yes, Puro=no)
      const conflictOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_conflict "${envData.batch_id}"`, {
        cwd: backendDir,
      }).toString().trim();
      const conflictProof = JSON.parse(conflictOutput);

      expect(conflictProof.conflict_verified).toBe(true);
      expect(conflictProof.total_authoritative_claims).toBe(1);
      expect(conflictProof.vm0044_claimed).toBe(true);
      expect(conflictProof.puro_claimed).toBe(false);

    } finally {
      // Cleanup
      execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${envData.organization_id}"`, {
        cwd: backendDir,
      });
    }
  });
});
