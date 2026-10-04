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

function setupLiveProject(caseName: 'case_a' | 'case_b'): SetupData {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b0_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres:postgres@localhost:5432/verifield_postgis_test';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" setup ${caseName}`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

function cleanupLiveProject(orgId: string): void {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b0_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres:postgres@localhost:5432/verifield_postgis_test';

  execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${orgId}"`, {
    cwd: backendDir,
  });
}

function queryDbAssessment(projectId: string): Record<string, unknown> {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b0_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres:postgres@localhost:5432/verifield_postgis_test';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_assessment "${projectId}"`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

function queryDbZeroCarbon(projectId: string): Record<string, unknown> {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b0_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://postgres:postgres@localhost:5432/verifield_postgis_test';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_zero_carbon "${projectId}"`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

test.describe('Agriculture MRV Phase 3B-0 Live VCS Transition Full-Stack E2E', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(120000);

  test('Case A: Pre-2027 Request without Early Adoption (VCS Standard v4.7 / Template v4.4 / Carbon Null)', async ({ page, request }) => {
    const envData = setupLiveProject('case_a');
    const closureDir = '/tmp/verifield_agri_3b0_runtime_closure';
    if (!fs.existsSync(closureDir)) {
      fs.mkdirSync(closureDir, { recursive: true });
    }

    try {
      const userPayload = {
        id: envData.pm_user_id,
        email: envData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-0 Live Org',
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

      // 4. Open Phase 3B Quantification Readiness / Prerequisites Tab
      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      // 5. Verify Authoritative Methodology Lock Card
      await expect(page.getByText('Authoritative Methodology', { exact: true })).toBeVisible({ timeout: 10000 });
      await expect(page.getByText('VM0042', { exact: true })).toBeVisible();
      await expect(page.getByText('v2.2', { exact: true })).toBeVisible();
      await expect(page.locator('text=VM0042_V2_2_CC_2026_06_11')).toBeVisible();

      // 6. Verify VCS Program Governance Card — Case A: VCS Standard v4.7, VCS_PROJECT_DESCRIPTION_V4.4, Variant NONE
      await expect(page.getByText('VCS Program Governance', { exact: true })).toBeVisible();
      await expect(page.getByText('VCS Standard v4.7').first()).toBeVisible();
      await expect(page.getByText('VCS_PROJECT_DESCRIPTION_V4.4').first()).toBeVisible();
      await expect(page.getByText('NONE').first()).toBeVisible();

      // 7. Verify Authoritative Carbon Quantification Status (Phase 3B-0 Strict Null Contract)
      const carbonStatusLocator = page.locator('[data-testid="authoritative-carbon-status"]');
      await expect(carbonStatusLocator).toBeVisible();
      await expect(carbonStatusLocator).toHaveText('NOT_CONFIGURED');

      const netRemovalsVal = page.locator('[data-testid="net-removals-val"]');
      await expect(netRemovalsVal).toBeVisible();
      await expect(netRemovalsVal).toContainText('—');
      await expect(netRemovalsVal).toContainText('(Not configured)');

      const totalNetVal = page.locator('[data-testid="total-net-tco2e-val"]');
      await expect(totalNetVal).toBeVisible();
      await expect(totalNetVal).toContainText('—');
      await expect(totalNetVal).toContainText('(Not configured)');

      // 8. Segregation of Duties (SoD) API Gate Verification:
      const blockedRes = await request.post(`${API_URL}/api/v1/agriculture/projects/${envData.project_id}/prerequisites/lock`, {
        headers: {
          Authorization: `Bearer ${envData.field_token}`,
          'Content-Type': 'application/json',
        },
        data: {
          snapshot_id: envData.snapshot_id,
          notes: 'Unauthorized field agent prerequisite lock attempt',
        },
      });
      expect(blockedRes.status()).toBe(403);

      const auditorRes = await request.get(`${API_URL}/api/v1/agriculture/projects/${envData.project_id}/prerequisites/assessments`, {
        headers: {
          Authorization: `Bearer ${envData.auditor_token}`,
        },
      });
      expect(auditorRes.status()).toBe(200);

      // 9. Lock Official Prerequisite Assessment Dossier as PM via UI
      const prereqTabBtn = page.locator('button:has-text("Methodology Prerequisites (Phase 3B-0)")');
      await prereqTabBtn.click();

      const lockPrereqBtn = page.locator('button:has-text("Lock Prerequisite Dossier")');
      await expect(lockPrereqBtn).toBeVisible();
      await lockPrereqBtn.click();

      await expect(page.locator('text=Attach Phase 3A Input Snapshot (Optional)')).toBeVisible({ timeout: 5000 });
      const notesTextarea = page.locator('textarea[placeholder*="crediting cycle"]');
      await notesTextarea.fill('Authoritative VM0042 v2.2 Case A prerequisite evaluation locked via live Playwright E2E.');

      const confirmLockBtn = page.locator('form button[type="submit"]:has-text("Lock Prerequisite Dossier")');
      await confirmLockBtn.click();

      // Automatically navigates to Locked Assessments Tab
      await expect(page.locator('text=Prerequisite Dossiers (1)')).toBeVisible({ timeout: 15000 });
      await expect(page.getByText('LOCKED', { exact: true })).toBeVisible();

      const assessmentHashLocator = page.locator('[data-testid="assessment-hash-value"]');
      await expect(assessmentHashLocator).toBeVisible();
      const displayedAssessmentHash = await assessmentHashLocator.innerText();
      expect(displayedAssessmentHash).toHaveLength(64);

      // 10. Direct PostgreSQL Verification for Case A
      const dbVerification = queryDbAssessment(envData.project_id);
      fs.writeFileSync(path.join(closureDir, '13_live_postgres_case_a.txt'), JSON.stringify(dbVerification, null, 2));

      expect(dbVerification.is_locked).toBe(true);
      expect(dbVerification.assessment_status).toBe('LOCKED');
      expect(dbVerification.assessment_hash).toBe(displayedAssessmentHash);
      expect(dbVerification.governing_vcs_standard).toBe('VCS_4_7');
      expect(dbVerification.v5_template_variant).toBe('NONE');
      expect(dbVerification.project_description_template).toBe('VCS_PROJECT_DESCRIPTION_V4.4');
      expect(dbVerification.early_adoption_mode).toBe('NONE');
      expect(dbVerification.delayed_requirement_ids).toEqual([]);
      expect(dbVerification.carbon_status).toBe('NOT_CONFIGURED');
      expect(dbVerification.tco2e_yield).toBeNull();
      expect(dbVerification.tco2e_generated).toBeNull();
      expect(dbVerification.total_carbon_calculations_count).toBe(0);

      const zeroCarbon = queryDbZeroCarbon(envData.project_id);
      expect(zeroCarbon.fail_closed_contract_passed).toBe(true);

      // Screenshot proof
      await page.screenshot({ path: path.join(closureDir, 'live_case_a.png'), fullPage: true });
    } finally {
      cleanupLiveProject(envData.organization_id);
    }
  });

  test('Case B: Post-2027 Request for Pre-2027 Start Project (VCS Standard v5.0 / Template v5.0A / Delayed Updates / Carbon Null)', async ({ page }) => {
    const envData = setupLiveProject('case_b');
    const closureDir = '/tmp/verifield_agri_3b0_runtime_closure';
    if (!fs.existsSync(closureDir)) {
      fs.mkdirSync(closureDir, { recursive: true });
    }

    try {
      const userPayload = {
        id: envData.pm_user_id,
        email: envData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-0 Live Org Case B',
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

      // 4. Open Phase 3B Quantification Readiness / Prerequisites Tab
      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      // 5. Verify Authoritative Methodology Lock Card
      await expect(page.getByText('Authoritative Methodology', { exact: true })).toBeVisible({ timeout: 10000 });
      await expect(page.getByText('VM0042', { exact: true })).toBeVisible();
      await expect(page.getByText('v2.2', { exact: true })).toBeVisible();

      // 6. Verify VCS Program Governance Card — Case B: VCS Standard v5.0, VCS_PROJECT_DESCRIPTION_V5.0A, Variant V5_0A, 5 active delayed updates
      await expect(page.getByText('VCS Program Governance', { exact: true })).toBeVisible();
      await expect(page.getByText('VCS Standard v5.0').first()).toBeVisible();
      await expect(page.getByText('VCS_PROJECT_DESCRIPTION_V5.0A').first()).toBeVisible();
      await expect(page.getByText('V5_0A').first()).toBeVisible();
      await expect(page.locator('text=Delayed V5 Updates: 5 active')).toBeVisible();

      // 7. Verify Authoritative Carbon Quantification Status (Phase 3B-0 Strict Null Contract)
      const carbonStatusLocator = page.locator('[data-testid="authoritative-carbon-status"]');
      await expect(carbonStatusLocator).toBeVisible();
      await expect(carbonStatusLocator).toHaveText('NOT_CONFIGURED');

      const netRemovalsVal = page.locator('[data-testid="net-removals-val"]');
      await expect(netRemovalsVal).toBeVisible();
      await expect(netRemovalsVal).toContainText('—');
      await expect(netRemovalsVal).toContainText('(Not configured)');

      const totalNetVal = page.locator('[data-testid="total-net-tco2e-val"]');
      await expect(totalNetVal).toBeVisible();
      await expect(totalNetVal).toContainText('—');
      await expect(totalNetVal).toContainText('(Not configured)');

      // 8. Lock Official Prerequisite Assessment Dossier as PM via UI
      const prereqTabBtn = page.locator('button:has-text("Methodology Prerequisites (Phase 3B-0)")');
      await prereqTabBtn.click();

      const lockPrereqBtn = page.locator('button:has-text("Lock Prerequisite Dossier")');
      await expect(lockPrereqBtn).toBeVisible();
      await lockPrereqBtn.click();

      await expect(page.locator('text=Attach Phase 3A Input Snapshot (Optional)')).toBeVisible({ timeout: 5000 });
      const notesTextarea = page.locator('textarea[placeholder*="crediting cycle"]');
      await notesTextarea.fill('Authoritative VM0042 v2.2 Case B prerequisite evaluation locked via live Playwright E2E.');

      const confirmLockBtn = page.locator('form button[type="submit"]:has-text("Lock Prerequisite Dossier")');
      await confirmLockBtn.click();

      // Automatically navigates to Locked Assessments Tab
      await expect(page.locator('text=Prerequisite Dossiers (1)')).toBeVisible({ timeout: 15000 });
      await expect(page.getByText('LOCKED', { exact: true })).toBeVisible();

      const assessmentHashLocator = page.locator('[data-testid="assessment-hash-value"]');
      await expect(assessmentHashLocator).toBeVisible();
      const displayedAssessmentHash = await assessmentHashLocator.innerText();
      expect(displayedAssessmentHash).toHaveLength(64);

      // 9. Direct PostgreSQL Verification for Case B
      const dbVerification = queryDbAssessment(envData.project_id);
      fs.writeFileSync(path.join(closureDir, '14_live_postgres_case_b.txt'), JSON.stringify(dbVerification, null, 2));

      expect(dbVerification.is_locked).toBe(true);
      expect(dbVerification.assessment_status).toBe('LOCKED');
      expect(dbVerification.assessment_hash).toBe(displayedAssessmentHash);
      expect(dbVerification.governing_vcs_standard).toBe('VCS_5_0');
      expect(dbVerification.v5_template_variant).toBe('V5_0A');
      expect(dbVerification.project_description_template).toBe('VCS_PROJECT_DESCRIPTION_V5.0A');
      expect(dbVerification.early_adoption_mode).toBe('NONE');
      expect((dbVerification.delayed_requirement_ids as string[]).slice().sort()).toEqual(['V5#14', 'V5#16', 'V5#17', 'V5#23', 'V5#58'].sort());
      expect(dbVerification.carbon_status).toBe('NOT_CONFIGURED');
      expect(dbVerification.tco2e_yield).toBeNull();
      expect(dbVerification.tco2e_generated).toBeNull();
      expect(dbVerification.total_carbon_calculations_count).toBe(0);

      const zeroCarbon = queryDbZeroCarbon(envData.project_id);
      expect(zeroCarbon.fail_closed_contract_passed).toBe(true);

      // Screenshot proof
      await page.screenshot({ path: path.join(closureDir, 'live_case_b.png'), fullPage: true });
    } finally {
      cleanupLiveProject(envData.organization_id);
    }
  });
});
