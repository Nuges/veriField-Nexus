import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

interface SetupData {
  organization_id: string;
  project_id: string;
  project_name: string;
  project_code: string;
  campaign_id: string;
  pm_user_id: string;
  pm_user_email: string;
  pm_token: string;
  field_agent_id: string;
  field_token: string;
  sample1_code: string;
  sample2_code: string;
  csv_path: string;
  tag: string;
}

test.describe('Agriculture MRV Laboratory Bulk Data Import Live Full-Stack Verification', () => {
  test.use({ viewport: { width: 1440, height: 1000 } });
  test.setTimeout(120000);

  let envData: SetupData;

  test.beforeAll(async () => {
    // 1. Initialize real synthetic test entities directly in PostgreSQL 18
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_laboratory_bulk_import_live_helper.py');
    const backendDir = path.resolve(__dirname, '../../backend');
    const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

    const rawOutput = execSync(`DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" setup`, {
      cwd: backendDir,
    }).toString().trim();

    envData = JSON.parse(rawOutput);
  });

  test.afterAll(async () => {
    // Teardown real synthetic test entities from PostgreSQL 18
    if (envData?.organization_id) {
      const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_laboratory_bulk_import_live_helper.py');
      const backendDir = path.resolve(__dirname, '../../backend');
      const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

      try {
        execSync(`DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" cleanup "${envData.organization_id}"`, {
          cwd: backendDir,
        });
      } catch (e) {
        console.warn("Cleanup encountered an error:", e);
      }
    }
  });

  test('Live Full-Stack: Upload CSV, Column Mapping, Scientific Validation, Unit Normalization, Preview, Commit & DB Verification', async ({ page }) => {
    const userPayload = {
      id: envData.pm_user_id,
      email: envData.pm_user_email,
      full_name: 'Agricultural Lab PM',
      role: 'PROJECT_MANAGER',
      status: 'active',
      is_active: true,
      organization: 'Lab Bulk Import Org',
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

    // 3. Open Agriculture Foundation / Workflow tab
    const agriWorkflowTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriWorkflowTab).toBeVisible({ timeout: 15000 });
    await agriWorkflowTab.click();

    // 4. Open Ground Evidence & Labs (Phase 2) section
    const groundEvidenceTab = page.locator('[data-testid="tab-ground_evidence"]');
    await expect(groundEvidenceTab).toBeVisible({ timeout: 15000 });
    await groundEvidenceTab.click();

    // 5. Open Laboratory Bulk Import tab
    const bulkImportTab = page.locator('[data-testid="tab-ground-bulk-import"]');
    await expect(bulkImportTab).toBeVisible({ timeout: 15000 });
    await bulkImportTab.click();

    // 6. Verify Header and Download Template Buttons
    await expect(page.locator('text=Laboratory Bulk Data Import')).toBeVisible({ timeout: 10000 });
    const csvTemplateBtn = page.locator('[data-testid="btn-download-csv-template"]');
    const xlsxTemplateBtn = page.locator('[data-testid="btn-download-xlsx-template"]');
    await expect(csvTemplateBtn).toBeVisible();
    await expect(xlsxTemplateBtn).toBeVisible();

    // 7. Select File and Upload
    const fileInput = page.locator('[data-testid="input-lab-import-file"]');
    await expect(fileInput).toBeVisible();
    await fileInput.setInputFiles(envData.csv_path);

    const uploadBtn = page.locator('[data-testid="btn-upload-lab-file"]');
    await expect(uploadBtn).toBeEnabled({ timeout: 5000 });
    await uploadBtn.click();

    // 8. Verify upload success and active batch detail panel
    const detailPanel = page.locator('[data-testid="active-batch-detail-panel"]');
    await expect(detailPanel).toBeVisible({ timeout: 20000 });

    // Verify metadata displayed: SHA-256 and original filename
    await expect(detailPanel.getByText(path.basename(envData.csv_path))).toBeVisible();
    await expect(detailPanel.getByText('Total Staged Rows')).toBeVisible();

    // 9. Re-Validate Staged Assays
    const revalidateBtn = page.locator('[data-testid="btn-revalidate-batch"]');
    await expect(revalidateBtn).toBeVisible();
    await revalidateBtn.click();

    // 10. Verify Staged Rows and Scientific Normalization
    // Sample 1: SOC 2.15% normalized to 21.5 g/kg
    await expect(page.locator(`text=${envData.sample1_code}`).first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=21.5 g/kg').first()).toBeVisible();

    // Sample 2: Bulk Density 1.32 g/cm3
    await expect(page.locator(`text=${envData.sample2_code}`).first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=1.32 g/cm3').first()).toBeVisible();

    // 11. Transactional Commit to Canonical Laboratory Ledger
    const commitBtn = page.locator('[data-testid="btn-commit-batch"]');
    await expect(commitBtn).toBeVisible();
    await expect(commitBtn).toBeEnabled();
    await commitBtn.click();

    // 12. Verify status badge updates to "IMPORTED"
    await expect(detailPanel.getByText('IMPORTED', { exact: true }).first()).toBeVisible({ timeout: 15000 });

    // 13. Direct PostgreSQL 18 Database Persistence Verification
    const scriptPath = path.resolve(__dirname, '../../backend/scripts/run_laboratory_bulk_import_live_helper.py');
    const backendDir = path.resolve(__dirname, '../../backend');
    const dbUrl = process.env.DATABASE_URL || 'postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test';

    const verifyOutput = execSync(`DATABASE_URL="${dbUrl}" venv/bin/python "${scriptPath}" verify_committed "${envData.project_id}"`, {
      cwd: backendDir,
    }).toString().trim();

    const dbVerification = JSON.parse(verifyOutput);
    expect(dbVerification.batch_status).toBe('IMPORTED');
    expect(dbVerification.imported_rows).toBe(2);
    expect(dbVerification.receipts_count).toBe(2);
    expect(dbVerification.analyses_count).toBe(2);
    // SoD Verification: imported analyses start with qa_status="PENDING"
    expect(dbVerification.analyses_qa_statuses).toEqual(['PENDING', 'PENDING']);
    expect(dbVerification.results_count).toBe(2);
    expect(dbVerification.soc_normalized_value).toBe(21.5);
    expect(dbVerification.soc_normalized_unit).toBe('g/kg');
    expect(dbVerification.bd_normalized_value).toBe(1.32);
    expect(dbVerification.bd_normalized_unit).toBe('g/cm³');

    // 14. Capture Full-Page Live Screenshot Proof
    const proofScreenshotPath = '/tmp/verifield_lab_import_evidence/08_lab_bulk_import_live_e2e_proof.png';
    const artifactScreenshotPath = '/Users/segun/.gemini/antigravity/brain/0dfbb0b4-c0b6-45f3-af9f-f74e23a0fe83/lab_bulk_import_live_e2e_proof.png';

    await page.screenshot({ path: proofScreenshotPath, fullPage: true });
    fs.copyFileSync(proofScreenshotPath, artifactScreenshotPath);
  });
});
