import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('Biochar Automatic Audit Package Compiler & Auditor Workspace E2E', () => {
  const mockAuditorUser = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'auditor@thirdparty-vcf.org',
    full_name: 'Dr. Elena Vance (Lead Auditor)',
    role: 'AUDITOR',
    status: 'active',
    is_active: true,
    organization: 'EarthCheck VCF Validation Services',
    organization_id: '00000000-0000-0000-0000-000000000001',
    licensed_methodologies: ['VM0044', 'PURO_BIOCHAR_2025_V2'],
    licensed_sectors: ['biochar'],
    version: 2,
    is_deleted: false,
  };

  const mockDeveloperUser = {
    id: '00000000-0000-0000-0000-000000000002',
    email: 'developer@nordic-biochar.org',
    full_name: 'Sven Lindqvist (Project Developer)',
    role: 'PROJECT_DEVELOPER',
    status: 'active',
    is_active: true,
    organization: 'Nordic Agro-Biochar AB',
    organization_id: '00000000-0000-0000-0000-000000000002',
    licensed_methodologies: ['PURO_BIOCHAR_2025_V2'],
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
      completeness: {
        score: 100,
        completed_requirements: 5,
        total_requirements: 5,
        blocker_reasons: [],
      },
      project: {
        id: 'proj-biochar-001',
        name: 'Nordic Agro-Biochar Project Alpha',
        code: 'BIO-ND-001',
        organization_id: '00000000-0000-0000-0000-000000000001',
        organization_name: 'Nordic Agro-Biochar AB',
      },
      summary_quantification: {
        net_removals_tco2e: 989.10,
        c_stored_tco2e: 1250.40,
        c_baseline_tco2e: 0.00,
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
          formula: 'CORCs = C_stored - C_baseline - C_loss - E_project - E_leakage',
          input_variables: {
            c_stored_tco2e: 1250.40,
            c_baseline_tco2e: 0.00,
            c_loss_tco2e: 215.10,
            e_project_tco2e: 45.20,
            e_leakage_tco2e: 0.00,
            deductible_uncertainty_tco2e: 0.00,
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
        c_baseline: {
          title: 'Baseline Carbon Removal (C_baseline)',
          value: 0.00,
          unit: 'tCO2e',
          formula: 'C_baseline = Historical baseline char storage (0.0 for New Facility per Section 3.3)',
          input_variables: {
            scenario: 'NEW_FACILITY',
            c_baseline_tco2e: 0.00,
          },
          evidence_refs: [],
        },
      },
      value_chain_graph: {
        sources: [
          { id: 'src-1', source_name: 'Nordic Forestry', biomass_type: 'Wood Waste', sustainability_status: 'FSC' },
        ],
        feedstock_lots: [
          {
            id: 'lot-1',
            lot_number: 'LOT-01',
            feedstock_type: 'Wood Waste',
            source_name: 'Nordic Forestry',
            mass_received_tonnes: 600,
            moisture_content_pct: 20,
            dry_mass_tonnes: 480,
            evidence_hash: 'evhash-lot-01',
          },
        ],
        production_runs: [
          {
            id: 'run-1',
            run_number: 'RUN-01',
            total_feedstock_input_tonnes: 600,
            total_feedstock_dry_tonnes: 480,
            avg_pyrolysis_temp_celsius: 650,
            residence_time_minutes: 45,
            output_biochar_mass_tonnes: 250,
            qa_status: 'PASSED',
          },
        ],
        batches: [
          {
            id: 'batch-1',
            batch_number: 'BATCH-01',
            biochar_yield_tonnes: 250,
            dry_mass_tonnes: 250,
            fixed_carbon_pct: 82.5,
            ash_content_pct: 3.2,
            molar_h_c_ratio: 0.32,
            lab_analyses: [
              { molar_h_c_ratio: 0.32, accreditation_standard: 'ISO 17025' },
            ],
          },
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
        transports: [
          {
            id: 'tr-1',
            carrier_name: 'Nordic Freight',
            material_type: 'BIOCHAR',
            mass_transported_tonnes: 250,
            distance_km: 45,
            status: 'DELIVERED',
          },
        ],
        end_uses: [
          {
            id: 'end-1',
            end_use_type: 'AGRICULTURAL_SOIL',
            applied_quantity_tonnes: 250,
            verification_status: 'CONFIRMED',
          },
        ],
        qc_checks: [
          { id: 'qc-1', check_type: 'LAB_VERIFICATION', conducted_by: 'ISO Inspector', passed: true },
        ],
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

  let mockFindings: Array<{
    id: string;
    package_id: string;
    finding_number: string;
    finding_type: string;
    severity: string;
    title: string;
    description: string;
    target_domain: string;
    status: string;
    created_at: string;
    project_response?: string;
    resolution_notes?: string;
  }> = [];

  const setupRoutes = async (page: any, activeUser: any, initialFindings?: any[]) => {
    mockFindings = initialFindings ? [...initialFindings] : [
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

    page.on('dialog', async (dialog: any) => {
      try {
        await dialog.accept();
      } catch (_) {
        // Dialog already handled
      }
    });

    await page.route('**/api/v1/**', async (route: any) => {
      const url = route.request().url().toLowerCase();
      const method = route.request().method();

      if (url.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(activeUser),
        });
      }

      // Package Scoped Access Denial Mock
      if (url.includes('pkg-forbidden-403')) {
        return route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Access denied. You do not have an active verification grant for this package.',
          }),
        });
      }

      // Raw Evidence Content Download Mock
      if (url.includes('/evidence/ev-001/content')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/pdf',
          headers: {
            'Content-Disposition': 'attachment; filename="eurofins_coa_b2026_01.pdf"',
          },
          body: Buffer.from('%PDF-1.4 Mock Canonical Biochar COA Evidence Content'),
        });
      }

      // Export Archive ZIP Mock
      if (url.includes('/export/archive')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/zip',
          headers: {
            'Content-Disposition': 'attachment; filename="puro-biochar-2026-archive.zip"',
          },
          body: Buffer.from('PK\x03\x04MockZipArchiveBytes'),
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

      // Findings CRUD
      if (url.includes('/verification/findings/find-001/respond') && method === 'POST') {
        const postData = JSON.parse(route.request().postData() || '{}');
        const finding = mockFindings.find((f) => f.id === 'find-001');
        if (finding) {
          finding.project_response = postData.project_response;
          finding.status = 'RESPONSE_SUBMITTED';
        }
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(finding),
        });
      }

      if (url.includes('/verification/findings/find-001/resolve') && method === 'POST') {
        const postData = JSON.parse(route.request().postData() || '{}');
        const finding = mockFindings.find((f) => f.id === 'find-001');
        if (finding) {
          finding.resolution_notes = postData.resolution_notes;
          finding.status = 'RESOLVED';
        }
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(finding),
        });
      }

      if (url.includes('/verification/packages/pkg-biochar-2026/findings') && method === 'POST') {
        const postData = JSON.parse(route.request().postData() || '{}');
        const newFinding = {
          id: `find-00${mockFindings.length + 1}`,
          package_id: 'pkg-biochar-2026',
          finding_number: `CAR-0${mockFindings.length + 1}`,
          finding_type: postData.finding_type || 'CAR',
          severity: postData.severity || 'MAJOR',
          title: postData.title || 'New Finding',
          description: postData.description || '',
          target_domain: postData.target_domain || 'BIOCHAR',
          status: 'OPEN',
          created_at: new Date().toISOString(),
        };
        mockFindings.unshift(newFinding);
        return route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(newFinding),
        });
      }

      if (url.includes('/verification/packages/pkg-biochar-2026/findings')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockFindings),
        });
      }

      if (url.includes('/verification/packages/pkg-biochar-2026/decision') && method === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ...mockPackageDetail,
            package_status: 'VERIFIED',
          }),
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
      { userData: activeUser }
    );
  };

  test('Hub renders Verification Packages tab and navigation to Auditor Workspace', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications`);

    // Verify page title
    await expect(page.locator('h1')).toContainText('Verification & Audits Hub');

    // Verify "Audit Packages" tab button exists
    const packagesTab = page.getByRole('button', { name: /Audit Packages/i });
    await expect(packagesTab).toBeVisible();

    // Verify banner and compile button
    await expect(page.locator('text=Automatic Verification Packages')).toBeVisible();
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

  test('Auditor Workspace renders header, ledger seal, completeness ratio, and role authorization', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // Verify Package Name & Version Badge
    await expect(page.locator('h1')).toContainText('Puro Biochar 2026 Annual Audit Package');
    await expect(page.locator('h1')).toContainText('v1');

    // Verify Auditor Workspace badge
    await expect(page.locator('text=Auditor Workspace')).toBeVisible();

    // Verify RSA-PSS Ledger Seal badge
    await expect(page.locator('text=RSA-PSS Verified')).toBeVisible();

    // Verify Manifest Hash is displayed
    await expect(page.locator('text=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')).toBeVisible();

    // Verify Completeness Score with exact numerator/denominator
    await expect(page.locator('text=100% (5/5 requirements)')).toBeVisible();

    // Verify Production UI has NO client-side role simulator toggle buttons
    await expect(page.getByRole('button', { name: 'Auditor View' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Developer View' })).not.toBeVisible();

    // In AUDITOR session: Record Decision button is visible, Manage Grants is NOT visible
    await expect(page.getByRole('button', { name: 'Record Decision' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Manage Grants' })).not.toBeVisible();

    // Export Archive (ZIP) button is visible
    await expect(page.getByRole('button', { name: /Export Archive \(ZIP\)/i })).toBeVisible();
  });

  test('Segregation of Duties (SoD) UI behavior when authenticated as Project Developer', async ({ page }) => {
    await setupRoutes(page, mockDeveloperUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // In DEVELOPER session:
    // "Record Decision" button MUST NOT be visible
    await expect(page.getByRole('button', { name: 'Record Decision' })).not.toBeVisible();

    // Developer sees "Manage Grants"
    await expect(page.getByRole('button', { name: 'Manage Grants' })).toBeVisible();

    // Switch to Findings tab
    const findingsTab = page.getByRole('button', { name: /Findings/i });
    await findingsTab.click();

    // Developer should see "Submit Developer Response" on OPEN findings
    const submitResponseBtn = page.getByRole('button', { name: /Submit Developer Response/i });
    await expect(submitResponseBtn).toBeVisible();

    // Developer CANNOT see "Log New Finding" button
    await expect(page.getByRole('button', { name: /Log New Finding/i })).not.toBeVisible();
  });

  test('Lineage Value Chain Graph Traversal across all stages', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // 1. Overview tab shows Value Chain inventory counts
    await expect(page.locator('text=Feedstock Sources')).toBeVisible();
    await expect(page.locator('text=Pyrolysis Runs')).toBeVisible();
    await expect(page.locator('text=Biochar Batches')).toBeVisible();

    // 2. Feedstock Tab
    const feedstockTab = page.getByRole('button', { name: /Feedstock/i });
    await feedstockTab.click();
    await expect(page.locator('text=Sourced Biomass Feedstock Lots')).toBeVisible();
    await expect(page.getByRole('cell', { name: 'LOT-01', exact: true })).toBeVisible();
    await expect(page.locator('text=Wood Waste').first()).toBeVisible();

    // 3. Production Runs Tab
    const productionTab = page.getByRole('button', { name: /Production Runs/i });
    await productionTab.click();
    await expect(page.locator('text=Pyrolysis Thermochemical Production Runs')).toBeVisible();
    await expect(page.getByRole('cell', { name: 'RUN-01', exact: true })).toBeVisible();
    await expect(page.locator('text=650°C')).toBeVisible();

    // 4. Biochar & Lab COA Tab
    const biocharTab = page.getByRole('button', { name: /Biochar & Lab COA/i });
    await biocharTab.click();
    await expect(page.getByRole('cell', { name: 'BATCH-01', exact: true })).toBeVisible();
    await expect(page.locator('text=0.32').first()).toBeVisible();

    // 5. Products & Blend Tab
    const productsTab = page.getByRole('button', { name: /Products & Blend/i });
    await productsTab.click();
    await expect(page.locator('text=TerraBio Soil Amendment Plus')).toBeVisible();
    await expect(page.locator('text=TBSA-PLUS')).toBeVisible();

    // 6. Custody & Logistics Tab
    const custodyTab = page.getByRole('button', { name: /Custody & Logistics/i });
    await custodyTab.click();
    await expect(page.locator('text=Nordic Freight')).toBeVisible();

    // 7. Terminal End Use Tab
    const endUseTab = page.getByRole('button', { name: /Terminal End Use/i });
    await endUseTab.click();
    await expect(page.locator('text=AGRICULTURAL_SOIL')).toBeVisible();
  });

  test('LCA Carbon Quantification and Number-to-Evidence Drill-Down', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    const lcaTab = page.getByRole('button', { name: /LCA & Drill-Down/i });
    await expect(lcaTab).toBeVisible();
    await lcaTab.click();

    // Verify carbon figures
    await expect(page.locator('text=Net Removals (CORCs)')).toBeVisible();
    await expect(page.locator('text=989.1')).toBeVisible();
    await expect(page.locator('text=Carbon Stored (C_stored)')).toBeVisible();
    await expect(page.locator('text=1250.4')).toBeVisible();

    // Click on Net Removals to open Number-to-Evidence Drill-Down Modal
    const netCorcsCard = page.getByRole('button', { name: /Net Removals \(CORCs\)/i });
    await netCorcsCard.click();

    // Verify Drill-Down Modal content
    await expect(page.locator('text=NET REMOVALS CORCS DRILL-DOWN')).toBeVisible();
    await expect(page.locator('text=CORCs = C_stored - C_baseline - C_loss - E_project - E_leakage')).toBeVisible();
    await expect(page.locator('text=Input Variables')).toBeVisible();

    // Close drill-down modal
    const closeDrillDownBtn = page.getByRole('button', { name: '✕' });
    await closeDrillDownBtn.click();
    await expect(page.locator('text=NET REMOVALS CORCS DRILL-DOWN')).not.toBeVisible();
  });

  test('Original Raw Evidence Access, SHA-256 validation and Archive Export', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // Evidence Index Tab
    const evidenceTab = page.getByRole('button', { name: /Evidence Index/i });
    await evidenceTab.click();

    await expect(page.locator('text=Eurofins Lab COA #EUR-2026-8821')).toBeVisible();
    await expect(page.locator('text=eurofins_coa_b2026_01.pdf')).toBeVisible();
    await expect(page.locator('text=VERIFIED').first()).toBeVisible();

    // Verify individual raw evidence download button exists
    const downloadEvidenceBtn = page.getByRole('button', { name: /Download/i }).first();
    await expect(downloadEvidenceBtn).toBeVisible();

    // Verify Archive Export (ZIP) button exists
    const exportArchiveBtn = page.getByRole('button', { name: /Export Archive \(ZIP\)/i });
    await expect(exportArchiveBtn).toBeVisible();

    // Trigger Verify All Evidence Files
    const verifyAllBtn = page.getByRole('button', { name: /Verify All Evidence Files/i });
    await expect(verifyAllBtn).toBeVisible();
    await verifyAllBtn.click();

    // Verify banner appears
    await expect(page.locator('text=All Cryptographic Hashes Match Canonical Evidence')).toBeVisible();
  });

  test('Auditor logs new finding with formal categorization', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    const findingsTab = page.getByRole('button', { name: /Findings/i });
    await findingsTab.click();

    // Auditor clicks Log New Finding
    const logFindingBtn = page.getByRole('button', { name: /Log New Finding/i });
    await expect(logFindingBtn).toBeVisible();
    await logFindingBtn.click();

    // Fill new finding modal
    await expect(page.locator('text=Log Assurance Finding')).toBeVisible();
    await page.locator('input[placeholder*="Provide accredited"]').fill('Pyrolysis Temperature Sensor Thermocouple Drift');
    await page.locator('textarea[placeholder*="Reference standard clause"]').fill('Thermocouple TC-04 calibrated 14 months ago; standard requires annual calibration.');
    await page.getByRole('button', { name: 'Save Finding' }).click();

    // Verify newly created finding appears in list
    await expect(page.locator('text=Pyrolysis Temperature Sensor Thermocouple Drift')).toBeVisible();
  });

  test('Developer responds to open finding with corrective action plan', async ({ page }) => {
    await setupRoutes(page, mockDeveloperUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    const devFindingsTab = page.getByRole('button', { name: /Findings/i });
    await devFindingsTab.click();

    const respondBtn = page.getByRole('button', { name: /Submit Developer Response/i }).first();
    await expect(respondBtn).toBeVisible();
    await respondBtn.click();

    await page.locator('textarea[placeholder*="Describe corrective steps"]').fill('Recalibration performed on Sept 15, 2026. Attached certificate CAL-2026-99.');
    await page.getByRole('button', { name: 'Submit', exact: true }).click();
  });

  test('Auditor verifies developer response and resolves finding', async ({ page }) => {
    const findingUnderReview = [
      {
        id: 'find-001',
        package_id: 'pkg-biochar-2026',
        finding_number: 'CAR-01',
        finding_type: 'CAR',
        severity: 'MAJOR',
        title: 'Laboratory COA Heavy Metals Signature Missing',
        description: 'The ICP-MS heavy metals analysis scan for Batch B-2026-02 is missing the accredited laboratory stamp.',
        target_domain: 'BIOCHAR',
        status: 'RESPONSE_SUBMITTED',
        project_response: 'Recalibration performed on Sept 15, 2026. Attached certificate CAL-2026-99.',
        created_at: '2026-09-16T18:30:00Z',
      },
    ];
    await setupRoutes(page, mockAuditorUser, findingUnderReview);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    const auditorFindingsTab = page.getByRole('button', { name: /Findings/i });
    await auditorFindingsTab.click();

    const resolveBtn = page.getByRole('button', { name: /Verify & Resolve Finding/i }).first();
    await expect(resolveBtn).toBeVisible();
    await resolveBtn.click();

    await page.locator('textarea[placeholder*="State audit resolution opinion"]').fill('Recalibration certificate inspected and verified conformant.');
    await page.getByRole('button', { name: 'Submit', exact: true }).click();

    // Verify finding is now marked RESOLVED
    await expect(page.locator('text=RESOLVED').first()).toBeVisible();
  });

  test('Package-Scoped Access Denial (403 Unauthorized)', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-forbidden-403`);

    // Verify error boundary card is displayed
    await expect(page.locator('text=Access Denied or Package Not Found')).toBeVisible();
    await expect(page.getByRole('link', { name: /Return to Verifications/i })).toBeVisible();
  });

  test('Responsive viewports verification', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // Desktop
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(page.locator('h1')).toContainText('Puro Biochar 2026 Annual Audit Package');
    await expect(page.locator('text=Completeness')).toBeVisible();

    // Tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('h1')).toContainText('Puro Biochar 2026 Annual Audit Package');

    // Mobile
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator('h1')).toContainText('Puro Biochar 2026 Annual Audit Package');
  });

  test('Accessibility and keyboard navigation across tabs', async ({ page }) => {
    await setupRoutes(page, mockAuditorUser);
    await page.goto(`${BASE_URL}/dashboard/verifications/pkg-biochar-2026`);

    // Verify landmark heading
    const mainHeading = page.locator('h1');
    await expect(mainHeading).toBeVisible();

    // Verify overview tab button has focus or can be focused
    const overviewTab = page.getByRole('button', { name: 'Overview' });
    await overviewTab.focus();
    await expect(overviewTab).toBeFocused();

    // Press Tab to move to next tab and press Enter
    await page.keyboard.press('Tab');
    const projectTab = page.getByRole('button', { name: /Project & Standard/i });
    await projectTab.focus();
    await page.keyboard.press('Enter');

    // Verify Project baseline section appears
    await expect(page.locator('text=Project Baseline & Normative Standard Registration')).toBeVisible();
  });
});
