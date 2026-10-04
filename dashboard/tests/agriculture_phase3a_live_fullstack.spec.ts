import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000';

interface SetupData {
  organization_id: string;
  project_id: string;
  project_name: string;
  project_code: string;
  pm_user_id: string;
  pm_user_email: string;
  pm_token: string;
  field_agent_id: string;
  field_agent_email: string;
  field_token: string;
  sample1_code: string;
  sample2_code: string;
  tag: string;
}

test.describe('Agriculture MRV Phase 3A Live Full-Stack E2E Verification', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(120000);

  let envData: SetupData;

  test.beforeAll(async () => {
    // 1. Initialize real synthetic test entities directly in PostgreSQL 18.1
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3a_live_helper.py');
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
      const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3a_live_helper.py');
      const backendDir = path.resolve(__dirname, '../../backend');
      const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test';

      execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${envData.organization_id}"`, {
        cwd: backendDir,
      });
    }
  });

  test('Live Full-Stack: Readiness Dimensions, Eligible Sets, Exclusions, SoD Gate, and Snapshot Hash Proof', async ({ page, request }) => {
    const userPayload = {
      id: envData.pm_user_id,
      email: envData.pm_user_email,
      full_name: 'Agricultural Project Manager',
      role: 'PROJECT_MANAGER',
      status: 'active',
      is_active: true,
      organization: 'Phase 3A Live Org',
      organization_id: envData.organization_id,
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
      { token: envData.pm_token, userData: userPayload, projectId: envData.project_id }
    );

    // 2. Open AGRICULTURE_LAND_USE project on dashboard
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use&methodology=VM0042&project=${envData.project_id}`);
    await page.waitForLoadState('networkidle');

    // 3. Open Agriculture Foundation tab
    const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
    await agriWorkflowTab.click();

    // 4. Open Phase 3A Quantification Readiness Tab
    const quantTab = page.locator('[data-testid="tab-quantification"]');
    await expect(quantTab).toBeVisible({ timeout: 10000 });
    await quantTab.click();

    // 5. Verify Header and Rule Set
    await expect(page.locator('text=Quantification Readiness & Calculation Input Contract')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=VM0042_V2_2_RULES_V1.0')).toBeVisible();

    // Invariant: zero percentage scores or progress bars
    const progressBars = page.locator('div[role="progressbar"]');
    await expect(progressBars).toHaveCount(0);

    // Invariant: DESIGN_SUFFICIENCY status strictly NOT_CONFIGURED
    const designSufficiencyCard = page.locator('text=DESIGN_SUFFICIENCY').locator('..');
    await expect(designSufficiencyCard).toBeVisible();
    await expect(page.locator('text=Strictly unconfigured (future phase)')).toBeVisible();

    // 6. Navigate to Eligible Measurements Tab
    const eligibleSubTab = page.locator('button:has-text("Eligible Measurements")');
    await expect(eligibleSubTab).toBeVisible();
    await eligibleSubTab.click();

    // Verify Sample 1 is listed as eligible with canonical unit and depth match
    await expect(page.locator(`text=${envData.sample1_code}`)).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=18.5 g/kg')).toBeVisible();
    await expect(page.locator('text=MATCH (0-30cm)')).toBeVisible();
    await expect(page.locator('text=1.35 g/cm³')).toBeVisible();
    await expect(page.getByText('MEASURED', { exact: true })).toBeVisible();

    // 7. Navigate to Excluded Measurements Tab
    const excludedSubTab = page.locator('button:has-text("Excluded Measurements")');
    await expect(excludedSubTab).toBeVisible();
    await excludedSubTab.click();

    // Verify Sample 2 is listed as excluded with reason DEPTH_MISMATCH
    await expect(page.locator(`text=${envData.sample2_code}`)).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=DEPTH_MISMATCH')).toBeVisible();

    // 8. Segregation of Duties (SoD) API Gate Verification:
    // Attempting to create snapshot as FIELD_AGENT must return 403 Forbidden
    const blockedRes = await request.post(`${API_URL}/api/v1/agriculture/projects/${envData.project_id}/quantification-input-snapshots`, {
      headers: {
        Authorization: `Bearer ${envData.field_token}`,
        'Content-Type': 'application/json',
      },
      data: {
        context: 'BASELINE',
        notes: 'Unauthorized field agent snapshot attempt',
      },
    });
    expect(blockedRes.status()).toBe(403);

    // 9. Lock Quantification Input Snapshot via UI as PM
    const lockButton = page.locator('button:has-text("Lock Input Snapshot")');
    await expect(lockButton).toBeVisible();
    await lockButton.click();

    // Modal opens
    await expect(page.locator('text=Lock Quantification Snapshot')).toBeVisible();
    const notesTextarea = page.locator('textarea[placeholder*="baseline"]');
    await notesTextarea.fill('Official live baseline input snapshot verified via Playwright.');

    const confirmLockBtn = page.locator('form button[type="submit"]:has-text("Lock Snapshot")');
    await confirmLockBtn.click();

    // 10. Automatically switches to Snapshots tab and renders locked snapshot
    await expect(page.locator('text=Input Snapshots & Hashes (1)')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('LOCKED', { exact: true })).toBeVisible();

    // Verify 64-character SHA-256 hash rendered
    const hashLocator = page.locator('[data-testid="snapshot-hash-value"]');
    await expect(hashLocator).toBeVisible();
    const displayedHash = await hashLocator.innerText();
    expect(displayedHash).toHaveLength(64);

    // 11. Real Database Persistence Proof: verify directly in PostgreSQL 18.1
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3a_live_helper.py');
    const backendDir = path.resolve(__dirname, '../../backend');
    const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test';

    const verifyOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_snapshot "${envData.project_id}"`, {
      cwd: backendDir,
    }).toString().trim();

    const dbVerification = JSON.parse(verifyOutput);
    expect(dbVerification.is_locked).toBe(true);
    expect(dbVerification.snapshot_hash).toBe(displayedHash);
    expect(dbVerification.is_hash_valid).toBe(true);
    expect(dbVerification.total_eligible_measurements).toBe(1);
    expect(dbVerification.total_excluded_measurements).toBe(1);
    expect(dbVerification.context).toBe('BASELINE');
    expect(dbVerification.methodology_code).toBe('VM0042');

    // Take live screenshot proof
    await page.screenshot({ path: '/tmp/phase3a_live_fullstack_proof.png', fullPage: true });
  });
});
