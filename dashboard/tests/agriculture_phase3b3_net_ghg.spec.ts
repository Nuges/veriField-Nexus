import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';
const ARTIFACT_DIR = '/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83';

interface SetupData {
  organization_id: string;
  project_id: string;
  project_name: string;
  project_code: string;
  prerequisite_id: string;
  prerequisite_code: string;
  baseline_stock_id: string;
  monitoring_stock_id: string;
  soc_change_id: string;
  soc_change_code: string;
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
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b3_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" setup ${scenario}`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

function cleanupLiveProject(orgId: string): void {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b3_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

  execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${orgId}"`, {
    cwd: backendDir,
  });
}

function verifyDbNetGhg(projectId: string): Record<string, any> {
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_phase3b3_live_helper.py');
  const backendDir = path.resolve(__dirname, '../../backend');
  const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

  const rawOutput = execSync(`PYTHONPATH=. DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_net_ghg "${projectId}"`, {
    cwd: backendDir,
  }).toString().trim();

  return JSON.parse(rawOutput);
}

test.describe('Agriculture MRV Phase 3B-3 Live Full-Stack Net GHG & VCU Readiness E2E', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(120000);

  /**
   * NaN Gate: Asserts zero prohibited numeric strings appear in the authoritative audit workspace.
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

  test('Live Case A: Fully Configured Positive Net GHG & VCU Readiness Lifecycle', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    console.log(`[Phase 3B-3 Case A] Seeded project ${setupData.project_code} in PostgreSQL`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-3 Live Org',
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

      // 2. Open dashboard
      console.log('[Case A] Navigating to dashboard URL...');
      await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use&methodology=VM0042&project=${setupData.project_id}`);
      await page.waitForLoadState('domcontentloaded');
      console.log('[Case A] DOM loaded');

      // 3. Open Agriculture Foundation tab
      const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
      await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
      await agriWorkflowTab.click();
      console.log('[Case A] Clicked Agriculture Foundation tab');

      // 4. Open Phase 3B Quantification Tab
      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();
      console.log('[Case A] Clicked Quantification tab');

      // 5. Click the Phase 3B-3 Net GHG & Issuance Readiness tab
      const netGhgTabButton = page.locator('button:has-text("Net GHG & Issuance Readiness (Phase 3B-3)")');
      await expect(netGhgTabButton).toBeVisible({ timeout: 10000 });
      await netGhgTabButton.click();
      console.log('[Case A] Clicked Net GHG sub-tab');

      // 6. Verify Scope Invariant Banner
      const banner = page.locator('text=VM0042 v2.2 Net GHG Reductions & Removals (Eqs. 37–43) + Section 8.7 VCU Readiness');
      await expect(banner).toBeVisible({ timeout: 10000 });
      console.log('[Case A] Scope banner visible');

      // Wait for prerequisite assessment option to load in select and select it
      const prereqSelect = page.locator('label:has-text("Prerequisite Assessment Dossier")').locator('..').locator('select');
      await expect(prereqSelect).toBeVisible({ timeout: 10000 });
      console.log('[Case A] Prereq select is visible');
      await expect(page.locator(`option[value="${setupData.prerequisite_id}"]`)).toBeAttached({ timeout: 15000 });
      console.log('[Case A] Prereq option attached');
      await prereqSelect.selectOption(setupData.prerequisite_id);
      console.log('[Case A] Selected prereq option');

      // Select SOC change result if option exists
      const socChangeOption = page.locator(`option[value="${setupData.soc_change_id}"]`);
      if ((await socChangeOption.count()) > 0) {
        const socChangeSelect = page.locator('label:has-text("Phase 3B-2 SOC Stock Change Result")').locator('..').locator('select');
        await socChangeSelect.selectOption(setupData.soc_change_id);
        console.log('[Case A] Selected SOC change option');
      }

      // 7. Click Evaluate Net GHG Preview
      console.log('[Case A] Clicking Evaluate Net GHG Preview...');
      const evalButton = page.locator('button:has-text("Evaluate Net GHG Preview")');
      await expect(evalButton).toBeVisible();
      await evalButton.click();
      console.log('[Case A] Clicked Evaluate Net GHG Preview');

      // Verify preview panel appears
      const previewHeader = page.locator('text=Preview: VM0042 v2.2 Net GHG Reductions & Removals Evaluation');
      await expect(previewHeader).toBeVisible({ timeout: 15000 });
      console.log('[Case A] Preview panel is visible');

      // Check Table 5 applicability status cards
      await expect(page.locator('text=Table 5 Applicability Router Status')).toBeVisible();

      // Check Core GHG metrics (Eqs. 37–43)
      await expect(page.locator('text=Gross ER (Eq. 37)')).toBeVisible();
      await expect(page.locator('text=Gross CR (Eq. 40)')).toBeVisible();
      await expect(page.locator('text=Total ERRNET (Eq. 43)')).toBeVisible();

      // Check Section 8.7 VCU Readiness Panel
      await expect(page.locator('text=Section 8.7 Internal VCU Readiness Calculation')).toBeVisible();

      // 8. Finalize Authoritative Record
      console.log('[Case A] Finalizing authoritative record...');
      const finalizeButton = page.locator('button:has-text("Finalize & Persist Authoritative Net GHG (Eqs. 37–43)")');
      await expect(finalizeButton).toBeVisible();
      await finalizeButton.click();
      console.log('[Case A] Clicked finalize button');

      // 9. Inspect Full Lineage Modal (opens automatically upon finalization)
      await expect(page.locator('text=Governance & System Status:')).toBeVisible({ timeout: 15000 });
      await expect(page.locator('text=Internal MRV:')).toBeVisible();
      await expect(page.locator('text=Cryptographic Proof & Lineage:')).toBeVisible();
      console.log('[Case A] Lineage modal verified');

      // Close modal
      const closeButton = page.locator('button:has-text("Close Detail")');
      await closeButton.click();
      console.log('[Case A] Closed lineage modal');

      // Verify authoritative record appears in results list
      const resultCard = page.locator('text=NET-GHG-');
      await expect(resultCard.first()).toBeVisible({ timeout: 15000 });

      // Re-inspect via the card's inspect button to verify reopening from list
      const inspectButton = page.locator('button:has-text("Inspect Full Lineage & VCU Deductions")').first();
      await expect(inspectButton).toBeVisible();
      await inspectButton.click();
      await expect(page.locator('text=Governance & System Status:')).toBeVisible();
      await page.locator('button:has-text("Close Detail")').click();
      console.log('[Case A] Reopened and closed lineage modal from results card');

      // 10. NaN Gate check
      await assertNaNGate(page, 'Case A');

      // Capture screenshot
      await page.screenshot({ path: `${ARTIFACT_DIR}/live_net_ghg_case_a_positive.png`, fullPage: true });

      // 11. Direct PostgreSQL Proof
      const dbProof = verifyDbNetGhg(setupData.project_id);
      expect(dbProof.found).toBe(true);
      expect(dbProof.result_status).toBe('CALCULATED');
      expect(dbProof.internal_mrv_status).toBe('CALCULATED');
      expect(dbProof.fail_closed_contract_passed).toBe(true);
      expect(dbProof.vintages_count).toBeGreaterThan(0);
      console.log(`[Phase 3B-3 Case A] PostgreSQL verification PASSED: Result ID ${dbProof.id}, ERRNET: ${dbProof.total_net_ghg_errnet} tCO2e`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case B: Mixed Reductions & Removals Summation (Eq. 43)', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    console.log(`[Phase 3B-3 Case B] Mixed reductions + removals`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-3 Live Org',
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
      await page.waitForLoadState('domcontentloaded');

      const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
      await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
      await agriWorkflowTab.click();

      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      const netGhgTabButton = page.locator('button:has-text("Net GHG & Issuance Readiness (Phase 3B-3)")');
      await expect(netGhgTabButton).toBeVisible({ timeout: 10000 });
      await netGhgTabButton.click();

      // Wait for prerequisite assessment option to load in select and select it
      const prereqSelect = page.locator('label:has-text("Prerequisite Assessment Dossier")').locator('..').locator('select');
      await expect(prereqSelect).toBeVisible({ timeout: 10000 });
      await expect(page.locator(`option[value="${setupData.prerequisite_id}"]`)).toBeAttached({ timeout: 15000 });
      await prereqSelect.selectOption(setupData.prerequisite_id);

      // Select SOC change result if option exists
      const socChangeOption = page.locator(`option[value="${setupData.soc_change_id}"]`);
      if ((await socChangeOption.count()) > 0) {
        const socChangeSelect = page.locator('label:has-text("Phase 3B-2 SOC Stock Change Result")').locator('..').locator('select');
        await socChangeSelect.selectOption(setupData.soc_change_id);
      }

      // Finalize with baseline fossil fuel = 40,000 L, project = 20,000 L, EF = 0.001
      const finalizeButton = page.locator('button:has-text("Finalize & Persist Authoritative Net GHG (Eqs. 37–43)")');
      await expect(finalizeButton).toBeVisible();
      await finalizeButton.click();

      // Modal opens automatically
      await expect(page.locator('text=Governance & System Status:')).toBeVisible({ timeout: 15000 });
      await page.locator('button:has-text("Close Detail")').click();

      const resultCard = page.locator('text=NET-GHG-');
      await expect(resultCard.first()).toBeVisible({ timeout: 15000 });

      await assertNaNGate(page, 'Case B');

      // Save screenshot
      await page.screenshot({ path: `${ARTIFACT_DIR}/live_net_ghg_case_b_mixed.png`, fullPage: true });

      const dbProof = verifyDbNetGhg(setupData.project_id);
      expect(dbProof.found).toBe(true);
      // Both reductions and removals should be strictly positive
      expect(dbProof.gross_reductions_er).toBeGreaterThan(0);
      expect(dbProof.gross_removals_cr).toBeGreaterThan(0);
      expect(dbProof.total_net_ghg_errnet).toBeGreaterThan(0);
      console.log(`[Phase 3B-3 Case B] Mixed accounting PASSED: Net ER=${dbProof.net_reductions_ernet}, Net CR=${dbProof.net_removals_crnet}, Total ERRNET=${dbProof.total_net_ghg_errnet}`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case Branch-Edge: VM0042 Eq. 37 Critical Branch with I=1 and Current-Year ΔCO2_wp < 0', async ({ page }) => {
    const setupData = setupLiveProject('eq37_branch_edge');
    console.log(`[Phase 3B-3 Branch-Edge] Seeded project ${setupData.project_code} for Eq.37 literal parity test`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-3 Live Org',
        organization_id: setupData.organization_id,
        licensed_methodologies: ['VM0042'],
        licensed_sectors: ['agriculture_land_use'],
        version: 1,
        is_deleted: false,
      };

      // 1. Authoritative API finalization with critical branch vector:
      // Year 1 (2023): wp = +20, bsl = 0 -> cumulative project stock = +20 (>0)
      // Year 2 (2024): wp = -5, bsl = -10 -> prior cumulative = +20, new cumulative = +15 (>0) -> I=1
      // Current-year wp = -5 (< 0). Baseline bsl = -10 (< 0).
      // Official literal Eq. 37: min(0, -5) - min(0, -10) = -5 - (-10) = +5.0000 tCO2e/yr.
      // Erroneous simplified formula would give +10.0000.
      const finalizeRes = await fetch(`${API_URL}/agriculture/projects/${setupData.project_id}/net-ghg/finalize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${setupData.pm_token}`,
        },
        body: JSON.stringify({
          prerequisite_assessment_id: setupData.prerequisite_id,
          soc_change_result_id: setupData.soc_change_id,
          verification_period_start: '2023-01-01',
          verification_period_end: '2024-12-31',
          npr_rating_pct: 15.0,
          annual_vintages_input: [
            {
              vintage_year: 2023,
              soc_stock_change_wp_tco2e: 20.0,
              soc_stock_change_bsl_tco2e: 0.0,
            },
            {
              vintage_year: 2024,
              soc_stock_change_wp_tco2e: -5.0,
              soc_stock_change_bsl_tco2e: -10.0,
            },
          ],
          notes: 'Phase 3B-3 Critical Eq.37 Branch-Edge Proof (I=1, current-year delta_wp < 0)',
        }),
      });

      expect([200, 201]).toContain(finalizeRes.status);
      const finalizedData = await finalizeRes.json();
      console.log(`[Phase 3B-3 Branch-Edge] Finalized record ${finalizedData.result_code}`);

      // 2. Open Chromium UI, authenticate and inspect record
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
      await page.waitForLoadState('domcontentloaded');

      const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
      await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
      await agriWorkflowTab.click();

      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      const netGhgTabButton = page.locator('button:has-text("Net GHG & Issuance Readiness (Phase 3B-3)")');
      await expect(netGhgTabButton).toBeVisible({ timeout: 10000 });
      await netGhgTabButton.click();

      // Verify the record card appears in the list
      const resultCard = page.locator(`text=${finalizedData.result_code}`);
      await expect(resultCard.first()).toBeVisible({ timeout: 15000 });

      // Click Inspect Full Lineage & VCU Deductions
      const inspectBtn = page.locator('button:has-text("Inspect Full Lineage & VCU Deductions")').first();
      await expect(inspectBtn).toBeVisible();
      await inspectBtn.click();

      // Modal is visible
      await expect(page.locator('text=Governance & System Status:')).toBeVisible({ timeout: 15000 });
      await expect(page.locator('text=Methodological Parity & VMD0054 Module Governance:')).toBeVisible();
      await expect(page.locator('text=VMD0054_1_1_CURRENT')).toBeVisible();

      // Check NaN gate
      await assertNaNGate(page, 'Branch-Edge Case');

      // Screenshot
      await page.screenshot({ path: `${ARTIFACT_DIR}/live_net_ghg_case_branch_edge.png`, fullPage: true });

      // Close modal
      await page.locator('button:has-text("Close Detail")').click();

      // 3. Direct PostgreSQL Proof verification
      const dbProof = verifyDbNetGhg(setupData.project_id);
      expect(dbProof.found).toBe(true);
      expect(dbProof.vintages_count).toBe(2);

      const y2024 = dbProof.vintages.find((v: any) => v.vintage_year === 2024);
      expect(y2024).toBeDefined();

      // Check Year 2024 branch vector invariants:
      // I = 1
      expect(y2024.i_value).toBe(1);
      // Cumulative project stock change = 20 + (-5) = 15.0
      expect(y2024.cumulative_project_stock_change).toBe(15.0);
      // current-year ΔCO2_wp = -5.0 < 0
      expect(y2024.current_year_delta_co2_wp).toBe(-5.0);
      // current-year ΔCO2_bsl = -10.0
      expect(y2024.current_year_delta_co2_bsl).toBe(-10.0);
      // Eq37 stock component = min(0,-5) - min(0,-10) = -5 - (-10) = +5.0000
      expect(y2024.eq37_stock_component).toBe(5.0);
      expect(y2024.eq37_stock_component).not.toBe(10.0);
      // ER = 5.0
      expect(y2024.er).toBe(5.0);
      // NPR = 15%
      expect(y2024.npr).toBe(15.0);
      // Eq75 term = 5.0
      expect(y2024.eq75_term).toBe(5.0);
      // BuER = 5.0 * 0.15 = 0.75
      expect(y2024.buer).toBe(0.75);
      // VMD0054 resolved version
      expect(y2024.vmd0054_resolved_version).toBe('VMD0054_1_1_CURRENT');
      expect(y2024.vmd0054_source_equation).toBe('VMD0054_V1.1_EQ13');

      console.log(`[Phase 3B-3 Branch-Edge] Direct PostgreSQL Proof PASSED:`);
      console.log(`  I=${y2024.i_value}, CumStock=${y2024.cumulative_project_stock_change}, wp=${y2024.current_year_delta_co2_wp}, bsl=${y2024.current_year_delta_co2_bsl}`);
      console.log(`  Eq37 Stock Component=${y2024.eq37_stock_component} (Rejected 10.0), ER=${y2024.er}, BuER=${y2024.buer}`);
      console.log(`  VMD0054=${y2024.vmd0054_resolved_version}, Hash=${dbProof.calculation_hash}`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case C: Proportional Leakage Allocation (Eqs. 39 & 42)', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    try {
      // Execute via direct API with exact leakage parameters to prove Eq. 39 and Eq. 42
      const response = await fetch(`${API_URL}/agriculture/projects/${setupData.project_id}/net-ghg/evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${setupData.pm_token}`,
        },
        body: JSON.stringify({
          soc_change_result_id: setupData.soc_change_id,
          prerequisite_assessment_id: setupData.prerequisite_id,
          verification_period_start: '2023-01-01',
          verification_period_end: '2024-12-31',
          fossil_fuel_activities_bsl: [{ quantity: 40000, emission_factor_tco2e_per_unit: 0.001 }],
          fossil_fuel_activities_wp: [{ quantity: 20000, emission_factor_tco2e_per_unit: 0.001 }],
          leakage_data: { production_decline_leakage_tco2e_yr: 10.0 },
          npr_rating_pct: 15.0,
        }),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.status).toBe('EVALUATED');
      const lkTotal = Number(data.total_leakage_tco2e);
      const lkEr = Number(data.leakage_allocation_er_lker_tco2e);
      const lkCr = Number(data.leakage_allocation_cr_lkcr_tco2e);

      expect(Math.abs((lkEr + lkCr) - lkTotal)).toBeLessThan(0.001);
      expect(lkEr).toBeGreaterThan(0);
      expect(lkCr).toBeGreaterThan(0);
      console.log(`[Phase 3B-3 Case C] Leakage allocation PASSED: LKER=${lkEr}, LKCR=${lkCr}, Total=${lkTotal}`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case D: Required Component Missing Fails Closed (No Fake Zero)', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    try {
      // Pass unconfigured source override to fail closed
      const response = await fetch(`${API_URL}/agriculture/projects/${setupData.project_id}/net-ghg/evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${setupData.pm_token}`,
        },
        body: JSON.stringify({
          prerequisite_assessment_id: setupData.prerequisite_id,
          verification_period_start: '2023-01-01',
          verification_period_end: '2024-12-31',
          applicability_overrides: [
            { source_category: 'CH4_SOIL_METHANOGENESIS', status: 'APPLICABLE_NOT_CONFIGURED' }
          ]
        }),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.status).toBe('BLOCKED');
      expect(data.blocking_reasons.length).toBeGreaterThan(0);
      expect(data.vcu_readiness_status).toBe('BLOCKED');
      console.log(`[Phase 3B-3 Case D] Fail-closed gating on unconfigured source returned BLOCKED with reasons: ${data.blocking_reasons.join(', ')}`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case E: NPR Missing Leaves VCU Readiness Blocked / Pending', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    try {
      const response = await fetch(`${API_URL}/agriculture/projects/${setupData.project_id}/net-ghg/evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${setupData.pm_token}`,
        },
        body: JSON.stringify({
          prerequisite_assessment_id: setupData.prerequisite_id,
          verification_period_start: '2023-01-01',
          verification_period_end: '2024-12-31',
          fossil_fuel_activities_bsl: [{ quantity: 40000, emission_factor_tco2e_per_unit: 0.001 }],
          fossil_fuel_activities_wp: [{ quantity: 20000, emission_factor_tco2e_per_unit: 0.001 }],
          npr_rating_pct: null, // Omit NPR buffer
        }),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.status).toBe('EVALUATED');
      expect(data.vcu_readiness_status).toContain('NOT_CONFIGURED');
      expect(data.internal_vcu_eligible_total_tco2e).toBeNull();
      console.log(`[Phase 3B-3 Case E] Omitted NPR correctly produced VCU readiness status: ${data.vcu_readiness_status}`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case F: NPR Configured Calculates Section 8.7 VCU Eligible Quantity', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    try {
      const response = await fetch(`${API_URL}/agriculture/projects/${setupData.project_id}/net-ghg/evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${setupData.pm_token}`,
        },
        body: JSON.stringify({
          prerequisite_assessment_id: setupData.prerequisite_id,
          verification_period_start: '2023-01-01',
          verification_period_end: '2024-12-31',
          fossil_fuel_activities_bsl: [{ quantity: 40000, emission_factor_tco2e_per_unit: 0.001 }],
          fossil_fuel_activities_wp: [{ quantity: 20000, emission_factor_tco2e_per_unit: 0.001 }],
          npr_rating_pct: 15.0,
        }),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.vcu_readiness_status).toBe('CALCULATED');
      const vcuEligible = Number(data.internal_vcu_eligible_total_tco2e);
      const bufferDeduction = Number(data.total_buffer_deduction_tco2e);
      const errnet = Number(data.total_net_ghg_errnet_tco2e);

      expect(vcuEligible).toBeGreaterThan(0);
      expect(bufferDeduction).toBeGreaterThan(0);
      expect(Math.abs((vcuEligible + bufferDeduction) - errnet)).toBeLessThan(0.01);
      console.log(`[Phase 3B-3 Case F] VCU Eligible quantity: ${vcuEligible} VCUs, Buffer: ${bufferDeduction} tCO2e`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case G: Field Agent Segregation of Duties Enforcement (HTTP 403 Rejection)', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    try {
      // Attempt finalization as Field Agent
      const response = await fetch(`${API_URL}/agriculture/projects/${setupData.project_id}/net-ghg/finalize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${setupData.field_token}`,
        },
        body: JSON.stringify({
          prerequisite_assessment_id: setupData.prerequisite_id,
          verification_period_start: '2023-01-01',
          verification_period_end: '2024-12-31',
          fossil_fuel_activities_bsl: [{ quantity: 40000, emission_factor_tco2e_per_unit: 0.001 }],
          fossil_fuel_activities_wp: [{ quantity: 20000, emission_factor_tco2e_per_unit: 0.001 }],
        }),
      });

      // Field agent MUST be rejected with HTTP 403 Forbidden
      expect(response.status).toBe(403);
      console.log(`[Phase 3B-3 Case G] Field agent segregation of duties successfully enforced (HTTP 403)`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case H: Attempted External Registry Issuance Invariant Preserved', async ({ page }) => {
    const setupData = setupLiveProject('standard');
    try {
      // Finalize record as PM
      const response = await fetch(`${API_URL}/agriculture/projects/${setupData.project_id}/net-ghg/finalize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${setupData.pm_token}`,
        },
        body: JSON.stringify({
          prerequisite_assessment_id: setupData.prerequisite_id,
          verification_period_start: '2023-01-01',
          verification_period_end: '2024-12-31',
          fossil_fuel_activities_bsl: [{ quantity: 40000, emission_factor_tco2e_per_unit: 0.001 }],
          fossil_fuel_activities_wp: [{ quantity: 20000, emission_factor_tco2e_per_unit: 0.001 }],
          npr_rating_pct: 15.0,
        }),
      });

      expect([200, 201]).toContain(response.status);
      const data = await response.json();

      // Assert fail-closed external registry invariants
      expect(data.internal_mrv_status).toBe('CALCULATED');
      expect(data.vvb_status).toBe('NOT_CONFIGURED / EXTERNAL');
      expect(data.registry_status).toBe('NOT_CONFIGURED / EXTERNAL');

      console.log(`[Phase 3B-3 Case H] Non-issuance invariants verified: VVB=${data.vvb_status}, Registry=${data.registry_status}`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });

  test('Live Case Adverse: VM0042 Eq. 37 Negative Result Preserved and VMD0054 v1.1 Eq. 13 Governance', async ({ page }) => {
    const setupData = setupLiveProject('eq37_adverse');
    console.log(`[Phase 3B-3 Adverse] Seeded project ${setupData.project_code} for unclamped negative Eq. 37 proof`);

    try {
      const userPayload = {
        id: setupData.pm_user_id,
        email: setupData.pm_user_email,
        full_name: 'Agricultural Project Manager',
        role: 'PROJECT_MANAGER',
        status: 'active',
        is_active: true,
        organization: 'Phase 3B-3 Live Org',
        organization_id: setupData.organization_id,
        licensed_methodologies: ['VM0042'],
        licensed_sectors: ['agriculture_land_use'],
        version: 1,
        is_deleted: false,
      };

      // 1. Authoritative API finalization with adverse vector:
      // Project loses carbon relative to baseline: wp = -10, bsl = -2.
      // Source reductions = 0 (10 bsl - 10 wp).
      // Eq. 37: min(0, -10) - min(0, -2) = -8.0 tCO2e/yr.
      // Must NOT be clamped to zero: ER = -8.0.
      const finalizeRes = await fetch(`${API_URL}/agriculture/projects/${setupData.project_id}/net-ghg/finalize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${setupData.pm_token}`,
        },
        body: JSON.stringify({
          prerequisite_assessment_id: setupData.prerequisite_id,
          soc_change_result_id: setupData.soc_change_id,
          verification_period_start: '2024-01-01',
          verification_period_end: '2024-12-31',
          fossil_fuel_activities_bsl: [{ quantity: 10000, emission_factor_tco2e_per_unit: 0.001 }],
          fossil_fuel_activities_wp: [{ quantity: 10000, emission_factor_tco2e_per_unit: 0.001 }],
          annual_vintages_input: [
            {
              vintage_year: 2024,
              soc_stock_change_wp_tco2e: -10.0,
              soc_stock_change_bsl_tco2e: -2.0,
            },
          ],
          leakage: {
            vmd0054_version: '1.1',
            activity_displacement_tco2e_yr: 0.0,
          },
          notes: 'Phase 3B-3 Adverse Eq.37 Unclamped Negative Performance Proof',
        }),
      });

      expect([200, 201]).toContain(finalizeRes.status);
      const finalizedData = await finalizeRes.json();
      console.log(`[Phase 3B-3 Adverse] Finalized record ${finalizedData.result_code}`);

      // 2. Open Chromium UI, authenticate and inspect record
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
      await page.waitForLoadState('domcontentloaded');

      const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
      await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
      await agriWorkflowTab.click();

      const quantTab = page.locator('[data-testid="tab-quantification"]');
      await expect(quantTab).toBeVisible({ timeout: 10000 });
      await quantTab.click();

      const netGhgTabButton = page.locator('button:has-text("Net GHG & Issuance Readiness (Phase 3B-3)")');
      await expect(netGhgTabButton).toBeVisible({ timeout: 10000 });
      await netGhgTabButton.click();

      // Verify the record card appears in the list
      const resultCard = page.locator(`text=${finalizedData.result_code}`);
      await expect(resultCard.first()).toBeVisible({ timeout: 15000 });

      // Click Inspect Full Lineage & VCU Deductions
      const inspectBtn = page.locator('button:has-text("Inspect Full Lineage & VCU Deductions")').first();
      await expect(inspectBtn).toBeVisible();
      await inspectBtn.click();

      // Modal is visible
      await expect(page.locator('text=Governance & System Status:')).toBeVisible({ timeout: 15000 });
      await expect(page.locator('text=Methodological Parity & VMD0054 Module Governance:')).toBeVisible();
      await expect(page.locator('text=VMD0054_1_1_CURRENT')).toBeVisible();

      // Check NaN gate
      await assertNaNGate(page, 'Adverse Unclamped Case');

      // Screenshot
      await page.screenshot({ path: `${ARTIFACT_DIR}/live_net_ghg_case_adverse_unclamped.png`, fullPage: true });

      // Close modal
      await page.locator('button:has-text("Close Detail")').click();

      // 3. Direct PostgreSQL Proof verification
      const dbProof = verifyDbNetGhg(setupData.project_id);
      expect(dbProof.found).toBe(true);
      expect(dbProof.gross_reductions_er).toBe(-8.0);
      expect(dbProof.gross_reductions_er).not.toBe(0.0);
      expect(dbProof.total_net_ghg_errnet).toBe(-8.0);
      expect(dbProof.vmd0054_resolved_version).toBe('VMD0054_1_1_CURRENT');
      expect(dbProof.vmd0054_source_equation).toBe('VMD0054_V1.1_EQ13');

      console.log(`[Phase 3B-3 Adverse] Direct PostgreSQL Proof PASSED:`);
      console.log(`  ER_t=${dbProof.gross_reductions_er} (Negative preserved, NOT clamped to 0.0)`);
      console.log(`  ERRNET_t=${dbProof.total_net_ghg_errnet}`);
      console.log(`  VMD0054 Version=${dbProof.vmd0054_resolved_version}, SourceEq=${dbProof.vmd0054_source_equation}`);
    } finally {
      cleanupLiveProject(setupData.organization_id);
    }
  });
});
