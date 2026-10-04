import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Agriculture MRV Phase 2 Ground Evidence Workflow E2E', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(60000);

  // ---------------------------------------------------------------------------
  // User Personas & Roles
  // ---------------------------------------------------------------------------
  const mockProjectManager = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'pm@verifield.com',
    full_name: 'Sarah Mwangi (Project Manager)',
    role: 'PROJECT_MANAGER',
    status: 'active',
    is_active: true,
    organization: 'VeriField Agro-Carbon',
    organization_id: '00000000-0000-0000-0000-000000000001',
    licensed_sectors: ['agriculture_land_use'],
    licensed_methodologies: ['VM0042'],
  };

  const mockAuditor = {
    id: '00000000-0000-0000-0000-000000000002',
    email: 'auditor@vcf-cert.org',
    full_name: 'Dr. James Chen (Lead Auditor)',
    role: 'AUDITOR',
    status: 'active',
    is_active: true,
    organization: 'EarthCheck VCF Validation Services',
    organization_id: '00000000-0000-0000-0000-000000000002',
    licensed_sectors: ['agriculture_land_use'],
    licensed_methodologies: ['VM0042'],
  };

  // Base Project & Methodology Catalogs
  const mockMethodologies = [
    { id: '1', code: 'VM0042', name: 'Improved Agricultural Land Management', version: '2.2', sector: 'agriculture_land_use', family_id: 'fam-agri', ui_config: {} },
  ];

  const mockFamilies = [
    { id: 'fam-agri', code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', methodologies: ['VM0042'] },
  ];

  const mockProjects = [
    { id: 'proj-agri-001', name: 'Demonstration Plot Alpha', code: 'AGRI-KE-001', sector: 'agriculture_land_use', area_ha: 124.50 },
  ];

  // ---------------------------------------------------------------------------
  // Setup Mock Handlers with In-Memory Phase 2 State
  // ---------------------------------------------------------------------------
  const setupPhase2Mocks = async (page: any, activeUser: any) => {
    const state = {
      campaigns: [
        {
          id: 'camp-001',
          project_id: 'proj-agri-001',
          campaign_code: 'CAMP-2025-BASE',
          name: 'Baseline Soil Carbon Campaign 2025',
          status: 'ACTIVE',
          target_strata_ids: ['strat-001'],
          planned_start_date: '2025-01-10',
          planned_end_date: '2025-02-28',
          notes: 'Standard VM0042 depth 0-30cm baseline sampling',
          point_count: 2,
          sample_count: 2,
          created_at: '2025-01-10T10:00:00Z',
          updated_at: '2025-01-10T12:00:00Z',
        },
      ],
      plans: [
        {
          id: 'plan-001',
          campaign_id: 'camp-001',
          version_number: 1,
          effective_as_of_date: '2025-01-10',
          status: 'DRAFT',
          is_locked: false,
          strata_snapshot: { strata_count: 1, method: 'VM0042_STRATIFICATION' },
          locked_by_user_id: null as string | null,
          locked_at: null as string | null,
          approval_notes: null as string | null,
        },
      ],
      points: [
        {
          id: 'pt-001',
          campaign_id: 'camp-001',
          sampling_plan_version_id: 'plan-001',
          point_code: 'P-01',
          land_unit_id: 'lu-001',
          stratum_id: 'strat-001',
          planned_lat: 28.5050,
          planned_lon: 77.1050,
          target_depth_from_cm: 0,
          target_depth_to_cm: 30,
          status: 'COLLECTED',
        },
        {
          id: 'pt-002',
          campaign_id: 'camp-001',
          sampling_plan_version_id: 'plan-001',
          point_code: 'P-02',
          land_unit_id: 'lu-001',
          stratum_id: 'strat-001',
          planned_lat: 28.5060,
          planned_lon: 77.1060,
          target_depth_from_cm: 0,
          target_depth_to_cm: 30,
          status: 'PLANNED',
        },
      ],
      samples: [
        {
          id: 'samp-001',
          sampling_point_id: 'pt-001',
          project_id: 'proj-agri-001',
          sample_code: 'SMP-2025-001',
          depth_interval_from_cm: 0,
          depth_interval_to_cm: 30,
          sample_type: 'SOIL_CORE',
          status: 'COLLECTED',
          sampling_point: {
            id: 'pt-001',
            point_code: 'P-01',
            planned_lat: 28.5050,
            planned_lon: 77.1050,
            target_depth_from_cm: 0,
            target_depth_to_cm: 30,
          },
          collection_event: {
            id: 'col-001',
            actual_lat: 28.50505,
            actual_lon: 77.10502,
            deviation_distance_m: 6.2,
            deviation_reason: null,
            collected_at: '2025-01-15T09:30:00Z',
            collector_user_id: 'user-field-01',
            collection_method: 'CORE_SAMPLER',
            soil_condition: 'MOIST',
            photo_hashes: ['bafkreiapple12345678'],
          },
          custody_events: [
            {
              id: 'cust-001',
              event_timestamp: '2025-01-15T10:00:00Z',
              transferor_user_id: 'user-field-01',
              transferee_user_id: 'user-driver-01',
              custody_action: 'FIELD_STORAGE',
              tamper_evident_seal_id: 'SEAL-KE-8899',
              notes: 'Placed in temperature-controlled cooler box',
            },
          ],
          laboratory_receipt: null as any,
          laboratory_analyses: [] as any[],
          qa_review: null as any,
        },
      ],
      readiness: {
        overall_status: 'INCOMPLETE',
        overall_message: 'Ground sampling campaign in progress: 1 collected sample awaiting lab processing.',
        components: {
          sampling_campaign: { status: 'COMPLETE', message: 'Active campaign CAMP-2025-BASE configured.' },
          sampling_plan: { status: 'NEEDS_REVIEW', message: 'Sampling plan version 1 is in DRAFT state. Locking required.' },
          stratum_coverage: { status: 'COMPLETE', message: 'All active analytical strata covered.' },
          sampling_points: { status: 'COMPLETE', message: '2 planned points registered.' },
          field_collection: { status: 'COMPLETE', message: 'Field collection events registered with coordinate logs.' },
          chain_of_custody: { status: 'COMPLETE', message: 'Unbroken chain of custody verified.' },
          lab_receipt: { status: 'INCOMPLETE', message: 'Laboratory intake receipts pending for 1 collected sample.' },
          required_assays: { status: 'INCOMPLETE', message: 'Standard analytical assays (SOC, Bulk Density) pending.' },
          qa_review: { status: 'INCOMPLETE', message: 'Formal QA review and signoff pending.' },
        },
      },
      landUnits: [
        {
          id: 'lu-001',
          project_id: 'proj-agri-001',
          name: 'North Field Parcel A',
          code: 'LU-01',
          unit_type: 'FIELD',
          land_use_category: 'CROPLAND',
          soil_type: 'SILT_LOAM',
          area_ha: 74.50,
          boundary_source: 'POSTGIS_GEOMETRY',
          status: 'ACTIVE',
        },
      ],
      strata: [
        {
          id: 'strat-001',
          project_id: 'proj-agri-001',
          code: 'STRAT-01',
          name: 'Reduced Tillage Silt Loam',
          stratum_type: 'MANAGEMENT_PRACTICE',
          description: 'Baseline stratum',
          member_count: 1,
          area_ha: 74.50,
          land_unit_ids: ['lu-001'],
          status: 'ACTIVE',
        },
      ],
    };

    // Auto-accept confirmation dialogs
    page.on('dialog', async (dialog: any) => {
      try {
        await dialog.accept();
      } catch {
        // Handled
      }
    });

    await page.route('**/api/v1/**', async (route: any) => {
      const url = route.request().url();
      const method = route.request().method();

      // Auth
      if (url.includes('/auth/me')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(activeUser) });
      }

      // Metadata & Projects
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      }
      if (url.includes('/methodology-families') || url.includes('/families')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFamilies) });
      }
      if (url.includes('/assets')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            assets: mockProjects.map((p) => ({ id: p.id, name: p.name, attributes: { sector: p.sector }, asset_type: 'project' })),
            total: mockProjects.length,
          }),
        });
      }
      if (url.includes('/properties') && !url.includes('/dashboard')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ properties: mockProjects, total: 1 }) });
      }
      if (url.includes('/projects') && !url.includes('/agriculture')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: mockProjects, total: 1 }) });
      }
      if (url.includes('/dashboard')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            workspace: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', badge: 'AGRI' },
            methodology: { code: 'VM0042', name: 'Improved Agricultural Land Management' },
            project: { id: mockProjects[0].id, name: mockProjects[0].name },
            kpis: [],
            charts: [],
            activities: [],
            activity_total: 0,
            asset_total: 0,
            assets: [],
          }),
        });
      }

      // Phase 1 Foundations
      if (url.includes('/foundation-readiness')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            overall_status: 'COMPLETE',
            overall_message: 'Phase 1 foundation ready.',
            components: {
              project_configuration: { status: 'COMPLETE', message: 'Configured.' },
              methodology_lock: { status: 'COMPLETE', message: 'Locked.' },
              authoritative_boundary: { status: 'COMPLETE', message: 'Boundary active.' },
              land_units: { status: 'COMPLETE', message: 'Land units registered.' },
              stratification: { status: 'COMPLETE', message: 'Strata active.' },
              management_baseline: { status: 'COMPLETE', message: 'Practices logged.' },
            },
          }),
        });
      }
      if (url.includes('/foundation')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            project_id: 'proj-agri-001',
            project_name: 'Demonstration Plot Alpha',
            project_code: 'AGRI-KE-001',
            crediting_period: { start: '2024-01-01', end: '2034-12-31' },
            methodology_lock_status: 'LOCKED',
            methodology: { code: 'VM0042', version: '2.2', name: 'Improved Agricultural Land Management' },
            sector: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use' },
            locked_methodology_snapshot: { locked_at: '2025-01-01T00:00:00Z', notes: 'Locked' },
            active_boundary: { id: 'bnd-001', version_number: 1, area_ha: 124.50, is_active: true },
          }),
        });
      }
      if (url.includes('/agriculture/land-units')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.landUnits) });
      }
      if (url.includes('/agriculture/projects/proj-agri-001/strata')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.strata) });
      }
      if (url.includes('/agriculture/projects/proj-agri-001/management-records')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }

      // -----------------------------------------------------------------------
      // Phase 2 Ground Evidence Endpoints
      // -----------------------------------------------------------------------

      // Ground Evidence Readiness
      if (url.includes('/ground-evidence-readiness')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.readiness) });
      }

      // Lock Sampling Plan Version (Must be evaluated before general plan-versions/campaigns)
      if (url.includes('/lock') && method === 'POST') {
        const body = route.request().postDataJSON ? route.request().postDataJSON() : {};
        state.plans[0].status = 'LOCKED';
        state.plans[0].is_locked = true;
        state.plans[0].locked_by_user_id = activeUser.id;
        state.plans[0].locked_at = new Date().toISOString();
        state.plans[0].approval_notes = body.approval_notes || 'Locked via E2E';
        state.readiness.components.sampling_plan = {
          status: 'COMPLETE',
          message: 'Sampling plan version 1 locked and immutable.',
        };
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.plans[0]) });
      }

      // Sampling Plan Versions List
      if (url.includes('/plan-versions') && !url.includes('/lock') && !url.includes('/points') && method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.plans) });
      }

      // Sampling Campaigns (Root endpoints only)
      if (url.includes('/sampling-campaigns') && !url.includes('/plan-versions') && !url.includes('/points') && !url.includes('/lock') && method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.campaigns) });
      }
      if (url.includes('/sampling-campaigns') && !url.includes('/plan-versions') && !url.includes('/points') && !url.includes('/lock') && method === 'POST') {
        const body = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const newCamp = {
          id: `camp-${Date.now()}`,
          project_id: 'proj-agri-001',
          campaign_code: body.campaign_code || 'CAMP-NEW',
          name: body.name || 'New Campaign',
          status: 'ACTIVE',
          target_strata_ids: body.target_strata_ids || [],
          planned_start_date: body.planned_start_date || '2025-02-01',
          planned_end_date: body.planned_end_date || null,
          notes: body.notes || null,
          point_count: 0,
          sample_count: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        state.campaigns.push(newCamp);
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(newCamp) });
      }

      // Sampling Points
      if (url.includes('/points') && method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.points) });
      }
      if (url.includes('/points') && method === 'POST') {
        const body = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const pts = body.points || [];
        for (const p of pts) {
          const newPt = {
            id: `pt-${Date.now()}-${Math.random()}`,
            campaign_id: 'camp-001',
            sampling_plan_version_id: 'plan-001',
            point_code: p.point_code,
            land_unit_id: p.land_unit_id,
            stratum_id: p.stratum_id || null,
            planned_lat: p.planned_lat,
            planned_lon: p.planned_lon,
            target_depth_from_cm: p.target_depth_from_cm || 0,
            target_depth_to_cm: p.target_depth_to_cm || 30,
            status: 'PLANNED',
          };
          state.points.push(newPt);
        }
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(state.points) });
      }

      // Physical Sample (Single sample detail)
      if (url.match(/\/physical-samples\/[^\/?]+$/) && method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.samples[0]) });
      }

      // Physical Samples List
      if (url.includes('/physical-samples') && !url.includes('receipt') && !url.includes('analyses') && !url.includes('qa-review') && method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.samples) });
      }

      // Lab Receipt
      if (url.includes('receipt') && method === 'POST') {
        const body = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const receipt = {
          id: `rec-${Date.now()}`,
          physical_sample_id: state.samples[0].id,
          laboratory_name: body.laboratory_name || 'Eurofins Agri Testing',
          received_at: new Date().toISOString(),
          received_by_name: body.received_by_name || 'Lab Intake Officer',
          sample_condition_on_receipt: body.sample_condition_on_receipt || 'ACCEPTABLE',
          seal_intact: body.seal_intact ?? true,
          seal_status: body.seal_status || 'SEALED_INTACT',
          intake_status: body.intake_status || 'ACCEPTED',
          rejection_reason: body.rejection_reason || null,
        };
        state.samples[0].laboratory_receipt = receipt;
        state.samples[0].status = 'RECEIVED_BY_LAB';
        state.readiness.components.lab_receipt = {
          status: 'COMPLETE',
          message: 'All physical samples received and accepted by accredited lab.',
        };
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(receipt) });
      }

      // Lab Analysis & Results
      if (url.includes('analyses') && method === 'POST') {
        const body = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const analysis = {
          id: `ana-${Date.now()}`,
          physical_sample_id: state.samples[0].id,
          analyzed_at: new Date().toISOString(),
          analyst_name: body.analyst_name || 'Senior Chemist',
          analytical_method: body.analytical_method || 'DRY_COMBUSTION',
          instrument_id: 'ELEMENTAR-VARIO-MAX',
          results: (body.results || []).map((r: any, idx: number) => ({
            id: `res-${Date.now()}-${idx}`,
            analysis_id: `ana-001`,
            analyte: r.analyte || 'SOC_CONCENTRATION',
            raw_value: r.raw_value ?? 1.85,
            raw_unit: r.raw_unit || '%',
            standardized_value: r.raw_value ?? 1.85,
            standardized_unit: '%',
            detection_limit: 0.01,
            uncertainty_pct: 2.5,
            is_superseded: false,
            superseded_by_result_id: null,
            revision_reason: null,
          })),
        };
        state.samples[0].laboratory_analyses = [analysis];
        state.samples[0].status = 'ANALYZED';
        state.readiness.components.required_assays = {
          status: 'COMPLETE',
          message: 'Required assays (SOC concentration, bulk density) analyzed and recorded.',
        };
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(analysis) });
      }

      // Revise Result
      if (url.includes('revise') && method === 'POST') {
        const body = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const activeAna = state.samples[0].laboratory_analyses[0];
        const oldRes = activeAna.results[0];
        oldRes.is_superseded = true;
        const newRes = {
          id: `res-${Date.now()}-revised`,
          analysis_id: activeAna.id,
          analyte: oldRes.analyte,
          raw_value: body.new_raw_value || 1.90,
          raw_unit: oldRes.raw_unit,
          standardized_value: body.new_raw_value || 1.90,
          standardized_unit: oldRes.standardized_unit,
          detection_limit: 0.01,
          uncertainty_pct: 2.5,
          is_superseded: false,
          superseded_by_result_id: null,
          revision_reason: body.revision_reason || 'Re-run correction',
        };
        oldRes.superseded_by_result_id = newRes.id;
        activeAna.results.push(newRes);
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(newRes) });
      }

      // QA Review Signoff
      if (url.includes('/qa-review') && method === 'POST') {
        const body = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const qaReview = {
          id: `qa-${Date.now()}`,
          physical_sample_id: state.samples[0].id,
          reviewed_by_user_id: activeUser.id,
          reviewer_name: body.reviewer_name || activeUser.full_name,
          reviewed_at: new Date().toISOString(),
          overall_qa_status: body.overall_qa_status || 'ACCEPTED',
          location_verified: true,
          depth_verified: true,
          custody_verified: true,
          lab_receipt_verified: true,
          results_verified: true,
          notes: body.notes || 'Verified compliant',
        };
        state.samples[0].qa_review = qaReview;
        state.readiness.components.qa_review = {
          status: 'COMPLETE',
          message: 'All physical ground evidence formally QA reviewed and signed off.',
        };
        state.readiness.overall_status = 'COMPLETE';
        state.readiness.overall_message = 'Defensible ground evidence chain 100% verified complete.';
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(qaReview) });
      }

      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.addInitScript(
      ({ user, defaultSector }: { user: Record<string, unknown>; defaultSector: string }) => {
        window.localStorage.setItem('vf_token', 'valid-mock-jwt-token');
        window.localStorage.setItem('vf_user', JSON.stringify(user));
        window.localStorage.setItem(`vf_workspace_${user.id}`, defaultSector);
      },
      { user: activeUser, defaultSector: 'agriculture_land_use' }
    );

    return state;
  };

  // ---------------------------------------------------------------------------
  // TEST 1: Ground Evidence Readiness & 9 Categorical Components Rendering
  // ---------------------------------------------------------------------------
  test('1. Ground Evidence Readiness Dashboard displays 9 categorical components correctly', async ({ page }) => {
    await setupPhase2Mocks(page, mockProjectManager);

    await page.goto(`${BASE_URL}/dashboard`);

    // Navigate to Agriculture workflow
    const agriTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriTab).toBeVisible({ timeout: 15000 });
    await agriTab.click();

    // Click Phase 2 Ground Evidence & Labs sub-tab
    const phase2Tab = page.locator('[data-testid="tab-ground_evidence"]');
    await expect(phase2Tab).toBeVisible();
    await phase2Tab.click();

    // Verify Ground Evidence Readiness Card
    const readinessCard = page.locator('[data-testid="ground-evidence-readiness-card"]');
    await expect(readinessCard).toBeVisible();

    // Overall status is initially INCOMPLETE
    const overallBadge = page.locator('[data-testid="ground-readiness-overall"]');
    await expect(overallBadge).toContainText('INCOMPLETE');

    // Verify all 9 categorical components are rendered
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

    for (const compKey of expectedComponents) {
      const compCard = page.locator(`[data-testid="ground-comp-${compKey}"]`);
      await expect(compCard).toBeVisible();
    }

    // Check specific initial values:
    // sampling_plan is NEEDS_REVIEW
    await expect(page.locator('[data-testid="ground-comp-sampling_plan"]')).toContainText('NEEDS REVIEW');
    // lab_receipt is INCOMPLETE
    await expect(page.locator('[data-testid="ground-comp-lab_receipt"]')).toContainText('INCOMPLETE');
  });

  // ---------------------------------------------------------------------------
  // TEST 2: Campaign, Sampling Plan Version Lock & Adding Points
  // ---------------------------------------------------------------------------
  test('2. Campaign management: Lock sampling plan version and register planned points', async ({ page }) => {
    await setupPhase2Mocks(page, mockProjectManager);

    await page.goto(`${BASE_URL}/dashboard`);
    await page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]').click();
    await page.locator('[data-testid="tab-ground_evidence"]').click();

    // Switch to Campaigns & Points tab
    const campSubTab = page.locator('[data-testid="tab-ground-campaigns"]');
    await expect(campSubTab).toBeVisible();
    await campSubTab.click();

    // Check Campaign details rendered
    await expect(page.getByText('CAMP-2025-BASE', { exact: true })).toBeVisible();

    // Lock Sampling Plan Version
    const lockBtn = page.locator('[data-testid="btn-lock-plan"]');
    await expect(lockBtn).toBeVisible();
    await lockBtn.click();

    // Fill notes in modal and confirm
    const notesInput = page.locator('textarea[placeholder*="stratification guidelines"]');
    await expect(notesInput).toBeVisible();
    await notesInput.fill('Phase 2 Plan locked for baseline fieldwork.');

    const confirmLockBtn = page.locator('button:has-text("Confirm & Lock")');
    await expect(confirmLockBtn).toBeVisible();
    await confirmLockBtn.click();

    // Verify plan is now LOCKED
    await expect(page.locator('[data-testid="plan-locked-badge"]')).toBeVisible();

    // Add Planned Sampling Point
    const addPointBtn = page.locator('[data-testid="btn-add-points"]');
    await expect(addPointBtn).toBeVisible();
    await addPointBtn.click();

    // Fill point modal
    await page.locator('input[placeholder="e.g. P-01"]').fill('P-03');
    await page.locator('[data-testid="select-point-land-unit"]').selectOption('lu-001');
    await page.locator('button:has-text("Add Point")').click();

    // Verify point exists in the table
    await expect(page.locator('text=P-03')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // TEST 3: Physical Samples, Lab Intake Receipt, Lab Assay, Result Revision, QA Signoff
  // ---------------------------------------------------------------------------
  test('3. Physical sample lifecycle: Lab intake, analytical assay, immutable result revision, and QA signoff', async ({ page }) => {
    await setupPhase2Mocks(page, mockProjectManager);

    await page.goto(`${BASE_URL}/dashboard`);
    await page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]').click();
    await page.locator('[data-testid="tab-ground_evidence"]').click();

    // Switch to Physical Samples & Assays tab
    const samplesSubTab = page.locator('[data-testid="tab-ground-samples"]');
    await expect(samplesSubTab).toBeVisible();
    await samplesSubTab.click();

    // Verify sample SMP-2025-001 is listed
    await expect(page.locator('text=SMP-2025-001')).toBeVisible();
    await expect(page.getByRole('cell', { name: 'COLLECTED', exact: true })).toBeVisible();

    // 1. Record Lab Intake Receipt
    const intakeBtn = page.locator('[data-testid="btn-record-receipt"]');
    await expect(intakeBtn).toBeVisible();
    await intakeBtn.click();

    await page.locator('button:has-text("Submit Receipt")').click();

    // Status transitions to RECEIVED_BY_LAB
    await expect(page.getByRole('cell', { name: 'RECEIVED BY LAB', exact: true })).toBeVisible();

    // 2. Record Analytical Laboratory Assay
    const assayBtn = page.locator('[data-testid="btn-record-analysis"]');
    await expect(assayBtn).toBeVisible();
    await assayBtn.click();

    await page.locator('input[type="number"][step="0.01"]').fill('1.85');
    await page.locator('form').getByRole('button', { name: 'Record Assay' }).click();

    // Status transitions to ANALYZED and raw value 1.85% is shown
    await expect(page.getByRole('cell', { name: 'ANALYZED', exact: true })).toBeVisible();
    await expect(page.locator('text=1.85%')).toBeVisible();

    // 3. Open Lineage Drawer to Revise Result and Inspect Lineage
    const lineageBtn = page.locator('[data-testid="btn-view-lineage"]');
    await expect(lineageBtn).toBeVisible();
    await lineageBtn.click();

    // Verify Lineage Drawer is opened
    const drawer = page.locator('[data-testid="sample-lineage-drawer"]');
    await expect(drawer).toBeVisible();

    // Verify Lineage Stages:
    await expect(drawer.locator('text=1. Planned Sample Point & Stratum')).toBeVisible();
    await expect(drawer.locator('text=2. Field Collection Event')).toBeVisible();
    await expect(drawer.locator('text=3. Unbroken Chain of Custody')).toBeVisible();
    await expect(drawer.locator('text=4. Laboratory Receipt & Analytical Assays')).toBeVisible();
    await expect(drawer.locator('text=5. QA Review & Signoff')).toBeVisible();

    // Check Geodesic Deviation is shown in Stage 2
    await expect(drawer.getByText(/6\.2\s*m/)).toBeVisible();

    // Revise Result inside Lineage Drawer
    const reviseBtn = drawer.locator('[data-testid="btn-revise-result"]');
    await expect(reviseBtn).toBeVisible();
    await reviseBtn.click();

    // Fill revision modal
    await page.locator('input[step="0.0001"]').fill('1.90');
    await page.locator('textarea[placeholder*="recalibration"]').fill('Duplicate analysis verification calibration correction');
    await page.locator('button:has-text("Submit Revision")').click();

    // Wait for revision to complete and toast feedback to appear
    await expect(page.locator('text=Result revised')).toBeVisible();

    // Close Lineage Drawer
    await page.locator('[data-testid="btn-close-lineage"]').click();
    await expect(drawer).not.toBeVisible();

    // 4. QA Signoff
    const qaBtn = page.locator('[data-testid="btn-record-qa"]');
    await expect(qaBtn).toBeVisible();
    await qaBtn.click();

    // Verify QA criteria checklist is visible in the modal
    await expect(page.locator('text=Geodesic coordinate containment within land unit')).toBeVisible();
    await expect(page.locator('text=Unbroken chain of custody transfer log')).toBeVisible();

    await page.locator('button:has-text("Sign & Accept")').click();

    // Verify QA status is updated and readiness transitions to COMPLETE
    const readinessTab = page.locator('[data-testid="tab-ground-readiness"]');
    await readinessTab.click();

    const overallBadge = page.locator('[data-testid="ground-readiness-overall"]');
    await expect(overallBadge).toContainText('COMPLETE');
    await expect(page.locator('[data-testid="ground-comp-qa_review"]')).toContainText('COMPLETE');
  });

  // ---------------------------------------------------------------------------
  // TEST 4: RBAC & Separation of Duties for AUDITOR Persona
  // ---------------------------------------------------------------------------
  test('4. RBAC Verification: AUDITOR is strictly read-only and cannot lock plans, intake samples, record assays, or perform QA', async ({ page }) => {
    await setupPhase2Mocks(page, mockAuditor);

    await page.goto(`${BASE_URL}/dashboard`);
    await page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]').click();
    await page.locator('[data-testid="tab-ground_evidence"]').click();

    // Auditor can view Readiness
    await expect(page.locator('[data-testid="ground-evidence-readiness-card"]')).toBeVisible();

    // Campaigns tab: Auditor cannot create campaign or lock plan
    await page.locator('[data-testid="tab-ground-campaigns"]').click();
    await expect(page.locator('[data-testid="btn-create-campaign"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="btn-lock-plan"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="btn-add-points"]')).not.toBeVisible();

    // Samples tab: Auditor can view lineage but cannot intake, assay, or QA sign
    await page.locator('[data-testid="tab-ground-samples"]').click();
    await expect(page.locator('[data-testid="btn-view-lineage"]')).toBeVisible();
    await expect(page.locator('[data-testid="btn-record-receipt"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="btn-record-analysis"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="btn-record-qa"]')).not.toBeVisible();
  });
});
