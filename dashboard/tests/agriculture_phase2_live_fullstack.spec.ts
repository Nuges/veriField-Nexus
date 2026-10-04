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
  land_unit_id: string;
  land_unit_name: string;
  stratum_id?: string;
  stratum_name?: string;
  collector_id: string;
  collector_email: string;
  collector_token: string;
  qa_user_id: string;
  qa_user_email: string;
  qa_user_token: string;
  tag: string;
}

test.describe('Agriculture MRV Phase 2 Live Full-Stack E2E Verification', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(120000);

  let envData: SetupData;

  test.beforeAll(async () => {
    // 1. Initialize real synthetic test entities directly in PostgreSQL 18
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_live_fullstack_helper.py');
    const backendDir = path.resolve(__dirname, '../../backend');
    const rawOutput = execSync(`PYTHONPATH=. venv/bin/python "${scriptPath}" setup`, {
      cwd: backendDir,
      env: { ...process.env, DATABASE_URL: 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test' },
    }).toString().trim();

    envData = JSON.parse(rawOutput);
  });

  test.afterAll(async () => {
    // Teardown real synthetic test entities from PostgreSQL 18
    if (envData?.organization_id) {
      const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_live_fullstack_helper.py');
      const backendDir = path.resolve(__dirname, '../../backend');
      execSync(`PYTHONPATH=. venv/bin/python "${scriptPath}" cleanup "${envData.organization_id}"`, {
        cwd: backendDir,
        env: { ...process.env, DATABASE_URL: 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test' },
      });
    }
  });

  test('Live Full-Stack Execution: Campaign, Plan Lock, Sampling, Assays, Revision, QA, and PostGIS Verification', async ({ page, request }) => {
    const userPayload = {
      id: envData.qa_user_id,
      email: envData.qa_user_email,
      full_name: 'Lead MRV QA Officer',
      role: 'SUPER_ADMIN',
      status: 'active',
      is_active: true,
      organization: 'Live Test Agriculture Org',
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
      { token: envData.qa_user_token, userData: userPayload, projectId: envData.project_id }
    );

    // 2. Open AGRICULTURE_LAND_USE project on dashboard
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use&methodology=VM0042&project=${envData.project_id}`);
    await page.waitForLoadState('networkidle');

    // Open Agriculture Foundation tab
    const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
    await agriWorkflowTab.click();

    // Open Phase 2 Ground Evidence Console
    const groundEvidenceTab = page.locator('[data-testid="tab-ground_evidence"]');
    await expect(groundEvidenceTab).toBeVisible({ timeout: 10000 });
    await groundEvidenceTab.click();

    // 3. Create Sampling Campaign via browser UI
    const campSubTab = page.locator('[data-testid="tab-ground-campaigns"]');
    await expect(campSubTab).toBeVisible();
    await campSubTab.click();

    const newCampBtn = page.locator('[data-testid="btn-create-campaign"]');
    await expect(newCampBtn).toBeVisible({ timeout: 10000 });
    await newCampBtn.click();

    const campCodeInput = page.locator('input[placeholder*="CAMP-2025"]');
    await expect(campCodeInput).toBeVisible();
    const campCodeVal = `CAM-${envData.tag}`.toUpperCase();
    await campCodeInput.fill(campCodeVal);

    const campNameInput = page.locator('input[placeholder*="Baseline Ground"]');
    await campNameInput.fill(`Live Soil Campaign ${envData.tag}`);

    await page.locator('button:has-text("Create Campaign")').click();

    // Verify campaign is created in the UI and active
    const campCard = page.getByText(campCodeVal, { exact: true });
    await expect(campCard).toBeVisible({ timeout: 10000 });
    await campCard.click();

    // Ensure Version 1 is loaded and visible
    await expect(page.getByText('Version 1', { exact: true })).toBeVisible({ timeout: 10000 });

    // 4. Create Planned Sampling Point via browser UI
    const addPointBtn = page.locator('[data-testid="btn-add-points"]');
    await expect(addPointBtn).toBeVisible({ timeout: 10000 });
    await addPointBtn.click();

    const ptCodeVal = `P-${envData.tag.substring(0, 4)}`.toUpperCase();
    await page.locator('input[placeholder="e.g. P-01"]').fill(ptCodeVal);
    await page.locator('[data-testid="select-point-land-unit"]').selectOption(envData.land_unit_id);
    if (envData.stratum_id) {
      await page.locator('[data-testid="select-point-stratum"]').selectOption(envData.stratum_id);
    }
    await page.locator('input[step="0.00001"]').first().fill('28.5200');
    await page.locator('input[step="0.00001"]').nth(1).fill('77.1200');

    await page.locator('button:has-text("Add Point")').click();
    await expect(page.locator('button:has-text("Add Point")')).not.toBeVisible({ timeout: 10000 });

    // Verify sampling point exists in the table
    await expect(page.getByRole('cell', { name: ptCodeVal.toUpperCase(), exact: true })).toBeVisible({ timeout: 10000 });

    // 5. Lock Sampling Plan Version via browser UI
    const lockBtn = page.locator('[data-testid="btn-lock-plan"]');
    await expect(lockBtn).toBeVisible({ timeout: 10000 });
    await lockBtn.click();

    const notesInput = page.locator('textarea[placeholder*="stratification guidelines"]');
    await expect(notesInput).toBeVisible();
    await notesInput.fill('Live execution lock confirmation for baseline fieldwork.');

    const confirmLockBtn = page.locator('button:has-text("Confirm & Lock")');
    await expect(confirmLockBtn).toBeVisible();
    await confirmLockBtn.click();

    // Verify plan is now LOCKED
    await expect(page.locator('[data-testid="plan-locked-badge"]')).toBeVisible({ timeout: 10000 });

    // Fetch plan versions and points via real API to retrieve IDs
    const planResp = await request.get(
      `${API_URL}/api/v1/agriculture/projects/${envData.project_id}/sampling-campaigns`,
      { headers: { Authorization: `Bearer ${envData.qa_user_token}` } }
    );
    expect(planResp.ok()).toBeTruthy();
    const campaignsList = await planResp.json();
    const liveCampaign = campaignsList.find((c: any) => c.campaign_code === campCodeVal);
    expect(liveCampaign).toBeDefined();

    const pvResp = await request.get(
      `${API_URL}/api/v1/agriculture/projects/${envData.project_id}/sampling-campaigns/${liveCampaign.id}/plan-versions`,
      { headers: { Authorization: `Bearer ${envData.qa_user_token}` } }
    );
    expect(pvResp.ok()).toBeTruthy();
    const planVersions = await pvResp.json();
    const lockedPlan = planVersions[0];
    expect(lockedPlan.is_locked).toBe(true);

    // 6. Verify Locked-Point Mutation is Rejected by Real FastAPI Backend
    const mutateAttempt = await request.post(
      `${API_URL}/api/v1/agriculture/projects/${envData.project_id}/sampling-campaigns/${liveCampaign.id}/plan-versions/${lockedPlan.id}/points`,
      {
        headers: { Authorization: `Bearer ${envData.qa_user_token}` },
        data: {
          points: [
            {
              point_code: 'P-ILLEGAL-MUTATION',
              land_unit_id: envData.land_unit_id,
              planned_lat: 28.525,
              planned_lon: 77.125,
              depth_from_cm: 0,
              depth_to_cm: 30,
            },
          ],
        },
      }
    );
    expect(mutateAttempt.status()).toBe(400);
    const mutateErr = await mutateAttempt.json();
    expect(mutateErr.detail).toContain('Plan is immutable');

    // 7. Verify PhysicalSample Created and Record Actual Field Collection
    const samplesResp = await request.get(
      `${API_URL}/api/v1/agriculture/projects/${envData.project_id}/physical-samples`,
      { headers: { Authorization: `Bearer ${envData.qa_user_token}` } }
    );
    expect(samplesResp.ok()).toBeTruthy();
    const samplesList = await samplesResp.json();
    const activeSample = samplesList[0];
    expect(activeSample).toBeDefined();
    expect(activeSample.status).toBe('PLANNED');

    // Record Actual Field Collection via real API with collector token
    const collectResp = await request.post(
      `${API_URL}/api/v1/agriculture/projects/${envData.project_id}/physical-samples/${activeSample.id}/collection`,
      {
        headers: { Authorization: `Bearer ${envData.collector_token}` },
        data: {
          actual_lat: 28.52008,
          actual_lon: 77.12010,
          actual_depth_from_cm: 0.0,
          actual_depth_to_cm: 30.0,
          collection_timestamp: new Date().toISOString(),
          sample_condition: 'GOOD',
          collector_name: 'Tariq Field Agent',
          device_metadata: { device_model: 'Trimble R2 GNSS', accuracy_m: 0.02 },
        },
      }
    );
    expect(collectResp.ok()).toBeTruthy();
    const collectionEvent = await collectResp.json();
    expect(collectionEvent.deviation_distance_m).toBeGreaterThan(0);

    // 8. Record Chain of Custody via real API
    const custodyResp = await request.post(
      `${API_URL}/api/v1/agriculture/projects/${envData.project_id}/physical-samples/${activeSample.id}/custody-events`,
      {
        headers: { Authorization: `Bearer ${envData.collector_token}` },
        data: {
          event_type: 'TRANSFER',
          event_timestamp: new Date().toISOString(),
          custodian_name: 'Eurofins Logistics Courier',
          custodian_organization: 'Eurofins Logistics Ltd',
          from_location: 'Farm Field Plot A',
          to_location: 'Eurofins Analytical Laboratory',
          seal_identifier: `SEAL-${envData.tag}`,
          seal_intact: true,
          condition: 'INTACT',
          notes: 'Temperature-controlled cooler container with calibrated data logger.',
        },
      }
    );
    expect(custodyResp.ok()).toBeTruthy();

    // 9. Refresh UI state and switch to Physical Samples tab in Browser UI
    await page.locator('[data-testid="ground-evidence-readiness-card"]').getByRole('button', { name: 'Refresh State' }).click();

    const samplesSubTab = page.locator('[data-testid="tab-ground-samples"]');
    await expect(samplesSubTab).toBeVisible();
    await samplesSubTab.click();

    // Verify sample is displayed with IN TRANSIT status
    await expect(page.locator(`text=${activeSample.sample_code}`)).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('cell', { name: 'IN TRANSIT', exact: true })).toBeVisible({ timeout: 10000 });

    // 10. Record Laboratory Intake Receipt via Browser UI
    const intakeBtn = page.locator('[data-testid="btn-record-receipt"]');
    await expect(intakeBtn).toBeVisible({ timeout: 10000 });
    await intakeBtn.click();

    await page.locator('button:has-text("Submit Receipt")').click();
    await expect(page.locator('button:has-text("Submit Receipt")')).not.toBeVisible({ timeout: 10000 });

    // Verify sample status transitions to RECEIVED BY LAB
    await expect(page.getByRole('cell', { name: 'RECEIVED BY LAB', exact: true })).toBeVisible({ timeout: 10000 });

    // 11. Record Laboratory Assay & SOC_CONCENTRATION Result via Browser UI
    const assayBtn = page.locator('[data-testid="btn-record-analysis"]');
    await expect(assayBtn).toBeVisible({ timeout: 10000 });
    await assayBtn.click();

    await page.locator('input[type="number"][step="0.01"]').fill('1.85');
    await page.locator('form').getByRole('button', { name: 'Record Assay' }).click();
    await expect(page.locator('button:has-text("Record Assay")')).not.toBeVisible({ timeout: 10000 });

    // Verify sample status transitions to ANALYZED and raw value 1.8500% is visible
    await expect(page.getByRole('cell', { name: 'ANALYZED', exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('cell', { name: /1\.85/ })).toBeVisible({ timeout: 10000 });

    // 12. Open Lineage Drawer and Revise Laboratory Result via Browser UI
    const lineageBtn = page.locator('[data-testid="btn-view-lineage"]');
    await expect(lineageBtn).toBeVisible({ timeout: 10000 });
    await lineageBtn.click();

    const drawer = page.locator('[data-testid="sample-lineage-drawer"]');
    await expect(drawer).toBeVisible({ timeout: 10000 });

    // Verify Lineage Drawer Stages
    await expect(drawer.locator('text=1. Planned Sample Point & Stratum')).toBeVisible();
    await expect(drawer.locator('text=2. Field Collection Event')).toBeVisible();
    await expect(drawer.locator('text=3. Unbroken Chain of Custody')).toBeVisible();
    await expect(drawer.locator('text=4. Laboratory Receipt & Analytical Assays')).toBeVisible();

    // Click Revise Result
    const reviseBtn = drawer.locator('[data-testid="btn-revise-result"]');
    await expect(reviseBtn).toBeVisible({ timeout: 10000 });
    await reviseBtn.click();

    // Fill revision form
    await page.locator('input[step="0.0001"]').fill('1.90');
    await page.locator('textarea[placeholder*="recalibration"]').fill('Duplicate analysis verification calibration correction');
    await page.locator('button:has-text("Submit Revision")').click();
    await expect(page.locator('button:has-text("Submit Revision")')).not.toBeVisible({ timeout: 10000 });

    // Wait for revision toast/confirmation
    await expect(page.locator('text=Result revised')).toBeVisible({ timeout: 10000 });

    // Close Lineage Drawer
    await page.locator('[data-testid="btn-close-lineage"]').click();
    await expect(drawer).not.toBeVisible();

    // 13. Sign Off as QA_OFFICER via Browser UI
    const qaBtn = page.locator('[data-testid="btn-record-qa"]');
    await expect(qaBtn).toBeVisible({ timeout: 10000 });
    await qaBtn.click();

    await page.locator('button:has-text("Sign & Accept")').click();
    await expect(page.locator('button:has-text("Sign & Accept")')).not.toBeVisible({ timeout: 10000 });

    // 14. Verify Ground Evidence Readiness transitions to COMPLETE
    const readinessTab = page.locator('[data-testid="tab-ground-readiness"]');
    await readinessTab.click();

    await page.locator('[data-testid="ground-evidence-readiness-card"]').getByRole('button', { name: 'Refresh State' }).click();

    const overallBadge = page.locator('[data-testid="ground-readiness-overall"]');
    await expect(overallBadge).toContainText('COMPLETE', { timeout: 15000 });

    // 15. Verify all 9 Categorical Readiness Components
    const expectedComponents = [
      'sampling_campaign',
      'sampling_plan',
      'stratum_coverage',
      'sampling_points',
      'field_collection',
      'chain_of_custody',
      'lab_receipt',
      'required_assays',
      'qa_review',
    ];
    for (const comp of expectedComponents) {
      await expect(page.locator(`[data-testid="ground-comp-${comp}"]`)).toBeVisible();
    }

    // 16. Query REAL PostgreSQL 18 Catalog to Verify Exact Generated Records
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_live_fullstack_helper.py');
    const backendDir = path.resolve(__dirname, '../../backend');
    const verifyOutput = execSync(`PYTHONPATH=. venv/bin/python "${scriptPath}" verify "${envData.project_id}"`, {
      cwd: backendDir,
      env: { ...process.env, DATABASE_URL: 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test' },
    }).toString().trim();

    const records = JSON.parse(verifyOutput);
    console.log('=== REAL POSTGRESQL 18 DIRECT CATALOG PERSISTENCE VERIFICATION ===');
    console.log(JSON.stringify(records, null, 2));

    // Assert exact persistence across all 10 tables in PostgreSQL
    expect(records.sampling_campaigns.length).toBeGreaterThanOrEqual(1);
    expect(records.sampling_plan_versions.length).toBeGreaterThanOrEqual(1);
    expect(records.sampling_points.length).toBeGreaterThanOrEqual(1);
    expect(records.sample_collection_events.length).toBeGreaterThanOrEqual(1);
    expect(records.physical_samples.length).toBeGreaterThanOrEqual(1);
    expect(records.chain_of_custody_events.length).toBeGreaterThanOrEqual(1);
    expect(records.laboratory_receipts.length).toBeGreaterThanOrEqual(1);
    expect(records.laboratory_analyses.length).toBeGreaterThanOrEqual(1);
    expect(records.laboratory_results.length).toBeGreaterThanOrEqual(2); // Original + Superseding
    expect(records.sample_qa_reviews.length).toBeGreaterThanOrEqual(1);

    // Verify acyclic revision lineage in database
    const supersededResult = records.laboratory_results.find((r: any) => r.is_superseded === true);
    const activeResult = records.laboratory_results.find((r: any) => r.is_superseded === false);
    expect(supersededResult).toBeDefined();
    expect(activeResult).toBeDefined();
    expect(activeResult.supersedes_id).toBe(supersededResult.id);

    // Verify SOC Canonical Unit Normalization (1% -> 10 g/kg)
    expect(supersededResult.raw_unit).toBe('%');
    expect(supersededResult.normalized_value).toBe(18.5);
    expect(supersededResult.normalized_unit).toBe('g/kg');
    expect(supersededResult.normalization_method).toBe('LINEAR_SCALING:VAL*10');

    expect(activeResult.raw_unit).toBe('%');
    expect(activeResult.normalized_value).toBe(19.0);
    expect(activeResult.normalized_unit).toBe('g/kg');
    expect(activeResult.normalization_method).toBe('LINEAR_SCALING:VAL*10');

    // Verify Laboratory Analysis QA Status synchronized to VERIFIED
    const activeAnalysis = records.laboratory_analyses[0];
    expect(activeAnalysis).toBeDefined();
    expect(activeAnalysis.qa_status).toBe('VERIFIED');

    // Verify PostGIS geodesic distance calculation
    const collectionRecord = records.sample_collection_events[0];
    expect(collectionRecord.dev_m).toBeGreaterThan(0);
  });
});
