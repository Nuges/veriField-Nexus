import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('Biochar Automatic Audit Package Compiler & Auditor Workspace E2E', () => {
  const mockUser = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'auditor@thirdparty-vcf.org',
    full_name: 'Dr. Elena Vance (Lead Auditor)',
    role: 'SUPER_ADMIN',
    status: 'active',
    is_active: true,
    organization: 'EarthCheck VCF Validation Services',
    organization_id: '00000000-0000-0000-0000-000000000001',
    licensed_methodologies: ['VM0044', 'PURO_BIOCHAR_2025_V2'],
    licensed_sectors: ['biochar'],
    version: 2,
    is_deleted: false,
  };

  const mockProject = {
    id: 'proj-biochar-001',
    name: 'Nordic Agro-Biochar Project Alpha',
    project_code: 'BIO-ND-001',
    sector_id: 'biochar',
    status: 'ACTIVE',
  };

  const mockPackageDetail = {
    id: 'pkg-biochar-2026',
    project_id: 'proj-biochar-001',
    organization_id: '00000000-0000-0000-0000-000000000001',
    package_name: 'Puro Biochar 2026 Annual Audit Package',
    package_version: 1,
    package_status: 'SEALED',
    registry_target: 'PURO_EARTH',
    audit_type: 'ANNUAL_VERIFICATION',
    monitoring_period_start: '2026-01-01T00:00:00Z',
    monitoring_period_end: '2026-06-30T23:59:59Z',
    manifest_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    ledger_signature_id: 'sig-rsa-2026-001',
    sealed_at: '2026-09-16T18:00:00Z',
    sealed_by_user_id: '00000000-0000-0000-0000-000000000001',
    completeness_score: 100,
    blocker_reasons: [],
    created_at: '2026-09-16T17:30:00Z',
    updated_at: '2026-09-16T18:00:00Z',
    manifest_json: {
      summary_quantification: {
        net_removals_tco2e: 989.10,
        c_stored_tco2e: 1250.40,
        c_loss_tco2e: 215.10,
        e_project_tco2e: 45.20,
        e_leakage_tco2e: 0.00,
        uncertainty_pct: 5.0,
      },
      trace_trees: {
        net_removals_corcs: {
          title: 'Net CO2e Removals (CORCs)',
          value: 989.10,
          unit: 'tCO2e',
          formula: 'CORCs = C_stored - C_loss - E_project - E_leakage - Uncertainty',
          input_variables: {
            c_stored_tco2e: 1250.40,
            c_loss_tco2e: 215.10,
            e_project_tco2e: 45.20,
            e_leakage_tco2e: 0.00,
            uncertainty_deduction_tco2e: 1.00,
          },
          evidence_refs: [
            { type: 'LAB_COA', hash: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0' },
          ],
        },
        c_stored: {
          title: 'Carbon Stored (C_stored)',
          value: 1250.40,
          unit: 'tCO2e',
          formula: 'C_stored = M_dry * C_org * (44/12) * PF_100',
          input_variables: {
            dry_mass_tonnes: 500.0,
            organic_carbon_pct: 85.2,
            permanence_factor: 0.80,
          },
          evidence_refs: [
            { type: 'BIOCHAR_BATCH', hash: 'b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01' },
          ],
        },
      },
      value_chain_graph: {
        feedstock_sources: [
          { id: 'src-1', source_name: 'Nordic Forestry', biomass_type: 'Wood Waste', sustainability_status: 'FSC' },
        ],
        feedstock_lots: [
          { id: 'lot-1', lot_number: 'LOT-01', wet_weight_tonnes: 600, dry_weight_tonnes: 480, biomass_type: 'Wood Waste' },
        ],
        production_runs: [
          { id: 'run-1', run_number: 'RUN-01', pyrolysis_temperature_celsius: 650, biochar_yield_tonnes: 250 },
        ],
        batches: [
          { id: 'batch-1', batch_number: 'BATCH-01', dry_mass_tonnes: 250, quality_grade: 'PREMIUM_CORC200', organic_carbon_pct: 85.2 },
        ],
        lab_analyses: [
          { id: 'lab-1', lab_name: 'Eurofins', molar_h_c: 0.32, organic_carbon_pct: 85.2, ebc_compliant: true },
        ],
        formulations: [
          {
            id: 'form-1',
            product_name: 'TerraBio Soil Amendment Plus',
            product_code: 'TBSA-PLUS',
            target_sector: 'AGRICULTURE',
            biochar_target_ratio: 0.75,
          },
        ],
        transports: [],
        end_use_records: [
          { id: 'end-1', application_type: 'AGRICULTURAL_SOIL', applied_quantity_tonnes: 400, permanence_verified: true },
        ],
        qc_checks: [],
      },
      evidence_index: [
        {
          id: 'ev-001',
          package_id: 'pkg-biochar-2026',
          evidence_category: 'LAB_COA',
          reference_domain: 'BIOCHAR_BATCH',
          reference_id: 'batch-001',
          title: 'Eurofins Lab COA #EUR-2026-8821',
          file_name: 'eurofins_coa_b2026_01.pdf',
          file_uri: 's3://verifield-evidence/coa/eurofins_coa_b2026_01.pdf',
          file_size_bytes: 428190,
          sha256_hash: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
          verified_hash: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
          integrity_status: 'VERIFIED',
          created_at: '2026-09-16T17:00:00Z',
        },
      ],
    },
    diff_summary_json: {},
  };

  const mockFindings = [
    {
      id: 'find-001',
      package_id: 'pkg-biochar-2026',
      finding_number: 'CAR-01',
      finding_type: 'CAR',
      severity: 'MAJOR',
      title: 'Laboratory COA Heavy Metals Signature Missing',
      description: 'The ICP-MS heavy metals analysis scan for Batch B-2026-02 is missing the accredited laboratory stamp.',
      target_domain: 'BIOCHAR',
      status: 'OPEN',
      created_at: '2026-09-16T18:30:00Z',
    },
  ];

  test.beforeEach(async ({ page }) => {
    // Intercept API calls
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url().toLowerCase();

      if (url.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockUser),
        });
      }

      if (url.includes('/verification/packages/pkg-biochar-2026/evidence/verify-all')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            total_evidence_items: 1,
            verified_count: 1,
            mismatch_count: 0,
            all_passed: true,
          }),
        });
      }

      if (url.includes('/verification/packages/pkg-biochar-2026/evidence')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockPackageDetail.manifest_json.evidence_index),
        });
      }

      if (url.includes('/verification/packages/pkg-biochar-2026/findings')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockFindings),
        });
      }

      if (url.includes('/verification/packages/pkg-biochar-2026/grants')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'grant-001',
              package_id: 'pkg-biochar-2026',
              auditor_email: 'auditor@thirdparty-vcf.org',
              auditor_organization: 'EarthCheck VCF Validation Services',
              grantee_role: 'LEAD_AUDITOR',
              is_active: true,
              created_at: '2026-09-16T18:00:00Z',
            },
          ]),
        });
      }

      if (url.includes('/verification/packages/pkg-biochar-2026')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockPackageDetail),
        });
      }

      if (url.includes('/verification/packages')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([mockPackageDetail]),
        });
      }

      if (url.includes('/projects')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [mockProject], total: 1 }),
        });
      }

      if (url.includes('/audits/my-tasks') || url.includes('/audits')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      }

      if (url.includes('/activities')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ activities: [] }),
        });
      }

      if (url.includes('/properties')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ properties: [] }),
        });
      }

      if (url.includes('/community')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ posts: [] }),
        });
      }

      if (url.includes('/sensors')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ devices: [] }),
        });
      }

      if (url.includes('/agents')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ agents: [] }),
        });
      }

      // Default fallback for any other api calls
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.addInitScript(
      ({ userData }: { userData: Record<string, unknown> }) => {
        window.localStorage.setItem('vf_token', 'valid-mock-token');
        window.localStorage.setItem('vf_user', JSON.stringify(userData));
        window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'biochar');
      },
      { userData: mockUser }
    );
  });

  test('Hub renders Verification Packages tab and navigation to Auditor Workspace', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/verifications`);

    // Verify page title
    await expect(page.locator('h1')).toContainText('Verification & Audits Hub');

    // Verify "Audit Packages (CIOS)" tab button exists
    const packagesTab = page.getByRole('button', { name: /Audit Packages \(CIOS\)/i });
    await expect(packagesTab).toBeVisible();

    // Verify banner and compile button
    await expect(page.locator('text=Automatic Verification Packages (CIOS Level 5)')).toBeVisible();
    await expect(page.getByRole('button', { name: /Compile Audit Package/i })).toBeVisible();

    // Verify Package Card is rendered
    await expect(page.locator('text=Puro Biochar 2026 Annual Audit Package')).toBeVisible();
    await expect(page.locator('text=v1.0')).toBeVisible();
    await expect(page.locator('text=PURO_EARTH')).toBeVisible();
    await expect(page.getByText('SEALED', { exact: true })).toBeVisible();

    // Verify Open Auditor Workspace button exists
    const workspaceLink = page.getByRole('link', { name: /Open Auditor Workspace/i });
    await expect(workspaceLink).toBeVisible();
  });

  test('Auditor Workspace renders header, ledger seal, and metric cards', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // Verify Package Name & Version Badge
    await expect(page.locator('h1')).toContainText('Puro Biochar 2026 Annual Audit Package');
    await expect(page.locator('h1')).toContainText('v1');

    // Verify RSA-PSS Ledger Seal badge
    await expect(page.locator('text=RSA-PSS Verified')).toBeVisible();

    // Verify Manifest Hash is displayed
    await expect(page.locator('text=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')).toBeVisible();

    // Verify Completeness Score is displayed
    await expect(page.locator('text=Completeness')).toBeVisible();
    await expect(page.locator('text=100%').first()).toBeVisible();

    // Verify Role Simulator is present
    await expect(page.getByRole('button', { name: 'Auditor View' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Developer View' })).toBeVisible();
  });

  test('Auditor Workspace tabs and number-to-evidence drill-down', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // 1. Check LCA & Drill-Down Tab
    const lcaTab = page.getByRole('button', { name: /LCA & Drill-Down/i });
    await expect(lcaTab).toBeVisible();
    await lcaTab.click();

    // Verify headline carbon figures are visible
    await expect(page.locator('text=Net Removals (CORCs)')).toBeVisible();
    await expect(page.locator('text=989.1')).toBeVisible();
    await expect(page.locator('text=Carbon Stored (C_stored)')).toBeVisible();
    await expect(page.locator('text=1250.4')).toBeVisible();

    // Click on Net Removals to open Number-to-Evidence Drill-Down Modal
    const netCorcsCard = page.getByRole('button', { name: /Net Removals \(CORCs\)/i });
    await netCorcsCard.click();

    // Verify Drill-Down Modal opened
    await expect(page.locator('text=NET REMOVALS CORCS DRILL-DOWN')).toBeVisible();
    await expect(page.locator('text=CORCs = C_stored - C_loss - E_project - E_leakage - Uncertainty')).toBeVisible();
    await expect(page.locator('text=Input Variables')).toBeVisible();

    // Close drill-down modal
    const closeDrillDownBtn = page.getByRole('button', { name: 'Close Trace Tree' });
    await closeDrillDownBtn.click();
    await expect(page.locator('text=NET REMOVALS CORCS DRILL-DOWN')).not.toBeVisible();

    // 2. Check Products & Blend Tab
    const productsTab = page.getByRole('button', { name: /Products & Blend/i });
    await expect(productsTab).toBeVisible();
    await productsTab.click();

    await expect(page.locator('text=TerraBio Soil Amendment Plus')).toBeVisible();
    await expect(page.locator('text=TBSA-PLUS')).toBeVisible();
    await expect(page.locator('text=75%')).toBeVisible();

    // 3. Check Evidence Index Tab & Integrity Check
    const evidenceTab = page.getByRole('button', { name: /Evidence Index/i });
    await expect(evidenceTab).toBeVisible();
    await evidenceTab.click();

    await expect(page.locator('text=Eurofins Lab COA #EUR-2026-8821')).toBeVisible();
    await expect(page.locator('text=eurofins_coa_b2026_01.pdf')).toBeVisible();
    await expect(page.locator('text=VERIFIED').first()).toBeVisible();

    // Click Verify All Evidence Files
    const verifyAllBtn = page.getByRole('button', { name: /Verify All Evidence Files/i });
    await expect(verifyAllBtn).toBeVisible();
    await verifyAllBtn.click();

    // Verify banner appears
    await expect(page.locator('text=All Cryptographic Hashes Match Canonical Evidence')).toBeVisible();

    // 4. Check Findings Tab
    const findingsTab = page.getByRole('button', { name: /Findings/i });
    await expect(findingsTab).toBeVisible();
    await findingsTab.click();

    await expect(page.locator('text=CAR-01')).toBeVisible();
    await expect(page.locator('text=Laboratory COA Heavy Metals Signature Missing')).toBeVisible();
    await expect(page.locator('text=MAJOR')).toBeVisible();
  });

  test('Segregation of Duties (SoD) UI behavior between Auditor and Developer', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // In AUDITOR mode:
    // "Record Decision" button is visible
    const decisionBtn = page.getByRole('button', { name: 'Record Decision' });
    await expect(decisionBtn).toBeVisible();

    // Switch role simulator to DEVELOPER
    const devRoleBtn = page.getByRole('button', { name: 'Developer View' });
    await devRoleBtn.click();

    // In DEVELOPER mode:
    // "Record Decision" button is not visible for developer (SoD protection)
    await expect(page.getByRole('button', { name: 'Record Decision' })).not.toBeVisible();
    // Instead "Manage Grants" is available
    await expect(page.getByRole('button', { name: 'Manage Grants' })).toBeVisible();

    // Switch to Findings tab
    const findingsTab = page.getByRole('button', { name: /Findings/i });
    await findingsTab.click();

    // Developer should see "Submit Developer Response" button on OPEN findings
    const submitResponseBtn = page.getByRole('button', { name: /Submit Developer Response/i });
    await expect(submitResponseBtn).toBeVisible();

    // Switch back to AUDITOR role
    const auditorRoleBtn = page.getByRole('button', { name: 'Auditor View' });
    await auditorRoleBtn.click();

    // Auditor should see "Log New Finding" button
    const raiseFindingBtn = page.getByRole('button', { name: /Log New Finding/i });
    await expect(raiseFindingBtn).toBeVisible();
  });
});
