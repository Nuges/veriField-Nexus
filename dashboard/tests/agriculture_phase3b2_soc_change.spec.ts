import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000';
const ARTIFACT_DIR = '/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83';

interface SetupData {
  organization_id: string;
  project_id: string;
  project_name: string;
  project_code: string;
  prerequisite_id: string;
  prerequisite_code: string;
  baseline_stock_id: string;
  baseline_stock_code: string;
  monitoring_stock_id: string;
  monitoring_stock_code: string;
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

function setupLiveProject(scenario: string = 'standard'): SetupData {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b2_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" setup ${scenario}`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

function cleanupLiveProject(orgId: string): void {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b2_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

  execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${orgId}"`, {
    cwd: backendDir,
  });
}

function verifyDbSocChange(projectId: string): Record<string, any> {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b2_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_soc_change "${projectId}"`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

test.describe('Agriculture MRV Phase 3B-2 Live Full-Stack SOC Stock Change & Uncertainty Engine E2E', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(120000);

  /**
   * NaN Gate: Asserts zero prohibited numeric strings appear in the authoritative audit workspace.
   * Must be called on every successful E2E case with a visible page.
   */
  async function assertNaNGate(page: import('@playwright/test').Page, caseLabel: string) {
    const bodyText = await page.locator('body').innerText();
    const nanCount = (bodyText.match(/\bNaN\b/g) || []).length;
    const infCount = (bodyText.match(/\bInfinity\b/g) || []).length;
    const negInfCount = (bodyText.match(/-Infinity\b/g) || []).length;
    expect(nanCount, `[${caseLabel}] NaN gate: found ${nanCount} visible "NaN"`).toBe(0);
    expect(infCount, `[${caseLabel}] NaN gate: found ${infCount} visible "Infinity"`).toBe(0);
    expect(negInfCount, `[${caseLabel}] NaN gate: found ${negInfCount} visible "-Infinity"`).toBe(0);
    console.log(`[${caseLabel}] NaN gate PASSED — 0 NaN, 0 Infinity, 0 -Infinity`);
  }

  test('Live Case 1: Standard ΔSOC, 44/12 Stoichiometry & Eq. (74) Uncertainty Deduction Lifecycle', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    console.log(`[Phase 3B-2 E2E Case 1] Seeded project ${setupData.project_code} in PostgreSQL`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-2 Live Org',
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

      // 4. Open Phase 3B Quantification Tab
      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      // 5. Click the Phase 3B-2 SOC Stock Change & Uncertainty tab
      const socChangeTabButton = page.locator('button:has-text("SOC Stock Change & Uncertainty (Phase 3B-2)")');
      await expect(socChangeTabButton).toBeVisible({ timeout: 10000 });
      await socChangeTabButton.click();

      // 6. Verify Scope Invariant Banner is prominent
      const invariantBanner = page.locator('text=METHODOLOGY MAPPING & SCOPE BOUNDARY:');
      await expect(invariantBanner).toBeVisible({ timeout: 10000 });

      // 7. Click Evaluate Preview
      const previewButton = page.locator('button:has-text("Evaluate Preview")');
      await expect(previewButton).toBeVisible();
      await previewButton.click();

      // Verify preview result appears
      const previewHeader = page.locator('text=ΔSOC & Uncertainty Preview Evaluation');
      await expect(previewHeader).toBeVisible({ timeout: 15000 });

      // Verify key metric cards are visible with correct VM0042 nomenclature
      const projectEq47Card = page.locator('text=Project SOC Change (Eq. 47)');
      await expect(projectEq47Card.first()).toBeVisible();

      const baselineEq46Card = page.locator('text=Baseline SOC Change (Eq. 46)');
      await expect(baselineEq46Card.first()).toBeVisible();

      const qa2NetSocCard = page.locator('text=QA2 Net SOC Effect');
      await expect(qa2NetSocCard.first()).toBeVisible();

      const uncertaintyCard = page.locator('text=Sampling Uncertainty (U%)');
      await expect(uncertaintyCard.first()).toBeVisible();

      const deductionCard = page.locator('text=Eq. (74) Deduction (0% Deadband)');
      await expect(deductionCard.first()).toBeVisible();

      const signIndicatorCard = page.locator('text=Sign Indicator I(ΔCO₂)');
      await expect(signIndicatorCard.first()).toBeVisible();

      // 8. Submit Authoritative Calculation & Finalization
      const finalizeButton = page.locator('button:has-text("Finalize & Persist Authoritative ΔSOC")');
      await expect(finalizeButton).toBeVisible();
      await finalizeButton.click();

      // Wait for persistent card to appear in results list
      const persistentSection = page.locator('text=Persisted Authoritative SOC Stock Change Results');
      await expect(persistentSection).toBeVisible({ timeout: 15000 });

      const changeResultCode = page.locator('text=SOC-CHG-');
      await expect(changeResultCode.first()).toBeVisible({ timeout: 15000 });

      // 9. Inspect Full Lineage & VM0042 Uncertainty Breakdown
      const inspectButton = page.locator('button:has-text("Inspect Full Lineage & VM0042 Uncertainty Breakdown")').first();
      await expect(inspectButton).toBeVisible();
      await inspectButton.click();

      // Verify modal opens with scientific breakdown
      const modalHeader = page.locator('text=VM0042 Equations & Uncertainty Quantification Audit Trail');
      await expect(modalHeader).toBeVisible({ timeout: 10000 });

      // Verify ledger protection alert in modal
      const ledgerAlert = page.locator('text=BLOCKED_FOR_AGRICULTURE');
      await expect(ledgerAlert.first()).toBeVisible();

      // Verify cryptographic SHA-256 proof in modal
      const shaProof = page.locator('text=Calculation SHA-256:');
      await expect(shaProof).toBeVisible();

      // Capture screenshot of authoritative result modal
      const screenshotPath = path.join(ARTIFACT_DIR, 'live_soc_change_e2e.png');
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`[Phase 3B-2 E2E Case 1] Saved live screenshot to ${screenshotPath}`);

      // 10. Direct PostgreSQL verification
      const dbProof = verifyDbSocChange(setupData.project_id);
      expect(dbProof.result_code).toBeTruthy();
      expect(dbProof.delta_soc_net_t_c_ha_yr).toBeGreaterThan(0);
      expect(dbProof.total_net_delta_co2_tco2e_yr).toBeGreaterThan(0);
      expect(dbProof.adjusted_net_delta_co2_tco2e_yr).toBeGreaterThan(0);
      expect(dbProof.baseline_soc_change_tco2e_yr).not.toBeNull();
      expect(dbProof.project_soc_change_tco2e_yr).toBeGreaterThan(0);
      expect(dbProof.qa2_net_soc_effect_tco2e_yr).toBeGreaterThan(0);
      expect(dbProof.uncertainty_adjusted_soc_effect_tco2e_yr).toBeGreaterThan(0);
      expect(dbProof.sign_indicator).toBe(1);
      expect(dbProof.eq44_eq45_status).toBe('PARTIALLY_CONFIGURED_SOC_ONLY');
      expect(dbProof.df_estimator).toBe('DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR');
      expect(dbProof.carbon_accounting_status).toBe('NOT_CONFIGURED');
      expect(['BLOCKED_FOR_AGRICULTURE', 'REJECTED_CARBON_MINTING_NOT_SUPPORTED_FOR_SOC_CHANGE']).toContain(dbProof.ledger_status);
      expect(dbProof.fail_closed_contract_passed).toBe(true);

      // NaN Gate Assertion
      await assertNaNGate(page, 'Case 1: Standard ΔSOC');

    } finally {
      cleanupLiveProject(setupData.organization_id);
      console.log(`[Phase 3B-2 E2E Case 1] Cleaned up test org ${setupData.organization_id}`);
    }
  });

  test('Live Case 2: Unfavorable Scenario (I = -1, monitoring < baseline) Conservative Loss Behavior', async ({ page }) => {
    const setupData = setupLiveProject('unfavorable');
    console.log(`[Phase 3B-2 E2E Case 2] Seeded unfavorable project ${setupData.project_code} in PostgreSQL`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-2 Live Org',
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

      const socChangeTabButton = page.locator('button:has-text("SOC Stock Change & Uncertainty (Phase 3B-2)")');
      await expect(socChangeTabButton).toBeVisible({ timeout: 10000 });
      await socChangeTabButton.click();

      // Click Evaluate Preview
      const previewButton = page.locator('button:has-text("Evaluate Preview")');
      await expect(previewButton).toBeVisible();
      await previewButton.click();

      const previewHeader = page.locator('text=ΔSOC & Uncertainty Preview Evaluation');
      await expect(previewHeader).toBeVisible({ timeout: 15000 });

      // In unfavorable scenario, sign indicator I should be -1
      const signText = page.locator('text=I = -1');
      await expect(signText.first()).toBeVisible({ timeout: 10000 });

      // Finalize and persist
      const finalizeButton = page.locator('button:has-text("Finalize & Persist Authoritative ΔSOC")');
      await expect(finalizeButton).toBeVisible();
      await finalizeButton.click();

      const persistentSection = page.locator('text=Persisted Authoritative SOC Stock Change Results');
      await expect(persistentSection).toBeVisible({ timeout: 15000 });

      // Screenshot unfavorable scenario
      const screenshotPath = path.join(ARTIFACT_DIR, 'live_soc_change_unfavorable_e2e.png');
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`[Phase 3B-2 E2E Case 2] Saved unfavorable screenshot to ${screenshotPath}`);

      // Verify PostgreSQL persistence proves conservative scaling
      const dbProof = verifyDbSocChange(setupData.project_id);
      expect(dbProof.sign_indicator).toBe(-1);
      expect(dbProof.qa2_net_soc_effect_tco2e_yr).toBeLessThan(0);
      expect(dbProof.uncertainty_adjusted_soc_effect_tco2e_yr).toBeLessThan(dbProof.qa2_net_soc_effect_tco2e_yr);
      console.log(`[Phase 3B-2 E2E Case 2] Verified conservative loss expansion: raw=${dbProof.qa2_net_soc_effect_tco2e_yr}, adjusted=${dbProof.uncertainty_adjusted_soc_effect_tco2e_yr}`);

      // NaN Gate Assertion
      await assertNaNGate(page, 'Case 2: Unfavorable Scenario');

    } finally {
      cleanupLiveProject(setupData.organization_id);
      console.log(`[Phase 3B-2 E2E Case 2] Cleaned up test org ${setupData.organization_id}`);
    }
  });

  test('Live Case 3: Scientific Block Gate (Unverified Laboratory Proficiency Fails Closed)', async ({ page, request }) => {
    const setupData = setupLiveProject('standard');
    console.log(`[Phase 3B-2 E2E Case 3] Testing Scientific Block Gate on ${setupData.project_code}`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-2 Live Org',
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

      const socChangeTabButton = page.locator('button:has-text("SOC Stock Change & Uncertainty (Phase 3B-2)")');
      await expect(socChangeTabButton).toBeVisible({ timeout: 10000 });
      await socChangeTabButton.click();

      // Uncheck "Active Lab Proficiency Program Certificate on File"
      const proficiencyCheckbox = page.locator('input[type="checkbox"]').nth(1);
      await proficiencyCheckbox.uncheck();

      // Click Evaluate Preview
      const previewButton = page.locator('button:has-text("Evaluate Preview")');
      await previewButton.click();

      // Expect diagnostic error alert in UI
      const errorAlert = page.locator('[data-testid="soc-change-error-alert"]');
      await expect(errorAlert).toBeVisible({ timeout: 10000 });
      await expect(errorAlert).toContainText('Laboratory analysis lacks demonstrated proficiency');

      // Screenshot blocked state
      const screenshotPath = path.join(ARTIFACT_DIR, 'live_soc_change_unverified_lab_blocked.png');
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`[Phase 3B-2 E2E Case 3] Saved blocked screenshot to ${screenshotPath}`);

      // Direct backend API verification: must reject with HTTP 400 Bad Request
      const evalRes = await request.post(`${API_URL}/api/v1/agriculture/projects/${setupData.project_id}/soc-change/evaluate`, {
        headers: {
          Authorization: `Bearer ${setupData.pm_token}`,
          'Content-Type': 'application/json',
        },
        data: {
          baseline_stock_result_id: setupData.baseline_stock_id,
          monitoring_stock_result_id: setupData.monitoring_stock_id,
          prerequisite_assessment_id: setupData.prerequisite_id,
          laboratory_method: 'DRY_COMBUSTION',
          lab_qa_verified: true,
          active_lab_proficiency: false,
        },
      });
      expect(evalRes.status()).toBe(400);
      const errBody = await evalRes.json();
      expect(JSON.stringify(errBody)).toContain('Laboratory analysis lacks demonstrated proficiency');
      console.log(`[Phase 3B-2 E2E Case 3] Backend correctly failed closed with HTTP 400 LAB_PROFICIENCY_EVIDENCE_INCOMPLETE`);

      // NaN Gate Assertion
      await assertNaNGate(page, 'Case 3: Scientific Block');

    } finally {
      cleanupLiveProject(setupData.organization_id);
      console.log(`[Phase 3B-2 E2E Case 3] Cleaned up test org ${setupData.organization_id}`);
    }
  });

  test('Live Case 4: Segregation of Duties Enforcement (Field Agent Blocked)', async ({ page, request }) => {
    const setupData = setupLiveProject('standard');
    console.log(`[Phase 3B-2 E2E Case 4] Testing Segregation of Duties for Field Agent on ${setupData.project_code}`);

    try {
      const fieldUserPayload = {
        id: setupData.field_agent_id,
        email: setupData.field_agent_email,
        full_name: 'Tariq Field Agent',
        role: 'FIELD_AGENT',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-2 Live Org',
        organization_id: setupData.organization_id,
        licensed_methodologies: ['VM0042'],
        licensed_sectors: ['agriculture_land_use'],
        version: 1,
        is_deleted: false,
      };

      // 1. Authenticate with Field Agent token
      await page.addInitScript(
        ({ token, userData, projectId }) => {
          window.localStorage.setItem('vf_token', token);
          window.localStorage.setItem('vf_user', JSON.stringify(userData));
          window.localStorage.setItem('vf_active_project_id', projectId);
          window.localStorage.setItem('vf_active_sector', 'agriculture_land_use');
        },
        { token: setupData.field_token, userData: fieldUserPayload, projectId: setupData.project_id }
      );

      // 2. Open dashboard
      await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use&methodology=VM0042&project=${setupData.project_id}`);
      await page.waitForLoadState('networkidle');

      // 3. Open Agriculture Foundation & Quantification Tab
      const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
      await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
      await agriWorkflowTab.click();

      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      const socChangeTabButton = page.locator('button:has-text("SOC Stock Change & Uncertainty (Phase 3B-2)")');
      await expect(socChangeTabButton).toBeVisible({ timeout: 10000 });
      await socChangeTabButton.click();

      // 4. Verify Field Agent Segregation of Duties Warning is visible
      const sodWarning = page.locator('text=Field Agents are restricted to preview only (Segregation of Duties).');
      await expect(sodWarning).toBeVisible({ timeout: 10000 });

      // 5. Verify Finalize button is disabled
      const finalizeButton = page.locator('button:has-text("Finalize & Persist Authoritative ΔSOC")');
      await expect(finalizeButton).toBeDisabled();

      // 6. Verify Field Agent can still evaluate preview
      const previewButton = page.locator('button:has-text("Evaluate Preview")');
      await expect(previewButton).toBeEnabled();
      await previewButton.click();

      const previewHeader = page.locator('text=ΔSOC & Uncertainty Preview Evaluation');
      await expect(previewHeader).toBeVisible({ timeout: 15000 });

      // 7. Verify direct backend API mutation is blocked with HTTP 403 Forbidden
      const finalizeRes = await request.post(`${API_URL}/api/v1/agriculture/projects/${setupData.project_id}/soc-change/finalize`, {
        headers: {
          Authorization: `Bearer ${setupData.field_token}`,
          'Content-Type': 'application/json',
        },
        data: {
          baseline_stock_result_id: setupData.baseline_stock_id,
          monitoring_stock_result_id: setupData.monitoring_stock_id,
          prerequisite_assessment_id: setupData.prerequisite_id,
        },
      });
      expect(finalizeRes.status()).toBe(403);
      console.log(`[Phase 3B-2 E2E Case 4] Backend correctly returned HTTP 403 Forbidden for Field Agent`);

      // Screenshot SoD state
      const screenshotPath = path.join(ARTIFACT_DIR, 'live_soc_change_field_agent_sod.png');
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`[Phase 3B-2 E2E Case 4] Saved SoD screenshot to ${screenshotPath}`);

      // NaN Gate Assertion
      await assertNaNGate(page, 'Case 4: Field Agent SoD');

    } finally {
      cleanupLiveProject(setupData.organization_id);
      console.log(`[Phase 3B-2 E2E Case 4] Cleaned up test org ${setupData.organization_id}`);
    }
  });

  test('Live Case 5: Carbon Ledger Minting Rejection Contract Verification', async ({ request }) => {
    const setupData = setupLiveProject('standard');
    console.log(`[Phase 3B-2 E2E Case 5] Testing Ledger Fail-Closed Rejection on ${setupData.project_code}`);

    try {
      // 1. Finalize an authoritative SOC Change result via API with PM token
      const finalizeRes = await request.post(`${API_URL}/api/v1/agriculture/projects/${setupData.project_id}/soc-change/finalize`, {
        headers: {
          Authorization: `Bearer ${setupData.pm_token}`,
          'Content-Type': 'application/json',
        },
        data: {
          baseline_stock_result_id: setupData.baseline_stock_id,
          monitoring_stock_result_id: setupData.monitoring_stock_id,
          prerequisite_assessment_id: setupData.prerequisite_id,
          notes: 'Testing ledger rejection invariant',
        },
      });
      expect([200, 201]).toContain(finalizeRes.status());
      const changeResult = await finalizeRes.json();
      expect(changeResult.id).toBeTruthy();
      expect(['BLOCKED_FOR_AGRICULTURE', 'REJECTED_CARBON_MINTING_NOT_SUPPORTED_FOR_SOC_CHANGE']).toContain(changeResult.ledger_status);

      // 2. Attempt to mint carbon credits using this result ID on /ledger/mint
      const mintRes = await request.post(`${API_URL}/api/v1/ledger/mint`, {
        headers: {
          Authorization: `Bearer ${setupData.pm_token}`,
          'Content-Type': 'application/json',
        },
        data: {
          calculation_id: changeResult.id,
          idempotency_key: `IDEMP-3B2-${setupData.tag}`,
        },
      });

      // Must be rejected (HTTP 400, 403, 404, or 422 because AgricultureSOCChangeResult is not a mintable CarbonCalculation)
      expect([400, 403, 404, 422]).toContain(mintRes.status());
      console.log(`[Phase 3B-2 E2E Case 5] Ledger correctly rejected minting request with HTTP ${mintRes.status()}`);

    } finally {
      cleanupLiveProject(setupData.organization_id);
      console.log(`[Phase 3B-2 E2E Case 5] Cleaned up test org ${setupData.organization_id}`);
    }
  });
});
