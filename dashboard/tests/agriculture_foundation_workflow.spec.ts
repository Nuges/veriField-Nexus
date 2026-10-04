import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Agriculture MRV Phase 1 Foundation E2E Workflow', () => {
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
    licensed_sectors: ['agriculture_land_use', 'biochar', 'cookstoves'],
    licensed_methodologies: ['VM0042', 'VM0044', 'AMS-II.G'],
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
    licensed_sectors: ['agriculture_land_use', 'biochar'],
    licensed_methodologies: ['VM0042', 'VM0044'],
  };

  const mockFieldAgent = {
    id: '00000000-0000-0000-0000-000000000003',
    email: 'field@verifield.com',
    full_name: 'Daniel Kiprop (Field Agent)',
    role: 'FIELD_AGENT',
    status: 'active',
    is_active: true,
    organization: 'VeriField Agro-Carbon',
    organization_id: '00000000-0000-0000-0000-000000000001',
    licensed_sectors: ['agriculture_land_use'],
    licensed_methodologies: ['VM0042'],
  };

  // ---------------------------------------------------------------------------
  // Methodology & Registry Catalogs
  // ---------------------------------------------------------------------------
  const mockMethodologies = [
    { id: '1', code: 'VM0042', name: 'Improved Agricultural Land Management', version: '2.2', sector: 'agriculture_land_use', family_id: 'fam-agri', ui_config: {} },
    { id: '2', code: 'VM0044', name: 'Biochar Utilization', version: '1.0', sector: 'biochar', family_id: 'fam-biochar', ui_config: {} },
    { id: '3', code: 'AMS-II.G', name: 'Clean Cooking Solutions', version: '4.0', sector: 'cookstoves', family_id: 'fam-cook', ui_config: {} },
  ];

  const mockFamilies = [
    { id: 'fam-agri', code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', methodologies: ['VM0042'] },
    { id: 'fam-biochar', code: 'BIOCHAR', name: 'Biochar Carbon Removal', methodologies: ['VM0044'] },
    { id: 'fam-cook', code: 'COOKSTOVES', name: 'Clean Cooking Solutions', methodologies: ['AMS-II.G'] },
  ];

  // Projects
  const mockProjects = [
    { id: 'proj-agri-001', name: 'Demonstration Plot Alpha', code: 'AGRI-KE-001', sector: 'agriculture_land_use', area_ha: 124.50 },
    { id: 'proj-agri-002', name: 'Savannah Regenerative Farm', code: 'AGRI-KE-002', sector: 'agriculture_land_use', area_ha: 50.25 },
    { id: 'proj-biochar-001', name: 'Biochar Pyrolysis Kiln 1', code: 'BIO-KE-001', sector: 'biochar' },
  ];

  // ---------------------------------------------------------------------------
  // Route Setup Helper with Mutable State
  // ---------------------------------------------------------------------------
  const setupMocks = async (page: any, activeUser: any) => {
    // Dynamic mutable state for Project 1 (Alpha)
    const state = {
      project1: {
        foundation: {
          project_id: 'proj-agri-001',
          project_name: 'Demonstration Plot Alpha',
          project_code: 'AGRI-KE-001',
          crediting_period: { start: '2024-01-01', end: '2034-12-31' },
          methodology_lock_status: 'UNLOCKED',
          methodology: { code: 'VM0042', version: '2.2', name: 'Improved Agricultural Land Management' },
          sector: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use' },
          locked_methodology_snapshot: null as any,
          active_boundary: { id: 'bnd-001', version_number: 1, area_ha: 124.50, is_active: true },
        },
        readiness: {
          overall_status: 'INCOMPLETE',
          overall_message: 'Project configuration in progress.',
          components: {
            project_configuration: { status: 'COMPLETE', message: 'Project foundation configured with crediting period.' },
            methodology_lock: { status: 'NEEDS_REVIEW', message: 'Methodology unlocked. Baseline parameters require locking.' },
            authoritative_boundary: { status: 'COMPLETE', message: 'Authoritative spatial boundary established.' },
            land_units: { status: 'COMPLETE', message: '2 land units registered with computed geodesic area.' },
            stratification: { status: 'INCOMPLETE', message: 'Stratum delineation required.' },
            management_baseline: { status: 'INCOMPLETE', message: 'Historical management practice documentation required.' },
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
          {
            id: 'lu-002',
            project_id: 'proj-agri-001',
            name: 'South Field Parcel B',
            code: 'LU-02',
            unit_type: 'PARCEL',
            land_use_category: 'CROPLAND',
            soil_type: 'CLAY_LOAM',
            area_ha: 50.00,
            boundary_source: 'POSTGIS_GEOMETRY',
            status: 'ACTIVE',
          },
        ],
        strata: [] as any[],
        managementRecords: [] as any[],
      },
      project2: {
        foundation: {
          project_id: 'proj-agri-002',
          project_name: 'Savannah Regenerative Farm',
          project_code: 'AGRI-KE-002',
          crediting_period: { start: '2025-01-01', end: '2035-12-31' },
          methodology_lock_status: 'UNLOCKED',
          methodology: { code: 'VM0042', version: '2.2', name: 'Improved Agricultural Land Management' },
          sector: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use' },
          locked_methodology_snapshot: null,
          active_boundary: { id: 'bnd-002', version_number: 1, area_ha: 50.25, is_active: true },
        },
        readiness: {
          overall_status: 'INCOMPLETE',
          overall_message: 'Savannah project initial setup.',
          components: {
            project_configuration: { status: 'COMPLETE', message: 'Project configuration active.' },
            methodology_lock: { status: 'NEEDS_REVIEW', message: 'Unlocked.' },
            authoritative_boundary: { status: 'COMPLETE', message: 'Boundary active.' },
            land_units: { status: 'COMPLETE', message: '1 unit registered.' },
            stratification: { status: 'INCOMPLETE', message: 'No strata.' },
            management_baseline: { status: 'INCOMPLETE', message: 'No records.' },
          },
        },
        landUnits: [
          {
            id: 'lu-sav-001',
            project_id: 'proj-agri-002',
            name: 'Savannah Agroforestry Block 1',
            code: 'SAV-01',
            unit_type: 'FIELD',
            land_use_category: 'AGROFORESTRY',
            soil_type: 'SANDY_LOAM',
            area_ha: 50.25,
            boundary_source: 'POSTGIS_GEOMETRY',
            status: 'ACTIVE',
          },
        ],
        strata: [] as any[],
        managementRecords: [] as any[],
      },
    };

    // Dialog handler to auto-accept confirm popups
    page.on('dialog', async (dialog: any) => {
      try {
        await dialog.accept();
      } catch {
        // Dialog already handled
      }
    });

    await page.route('**/api/v1/**', async (route: any) => {
      const url = route.request().url();
      const method = route.request().method();

      // Auth
      if (url.includes('/auth/me')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(activeUser) });
      }

      // Metadata Catalogs
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      }
      if (url.includes('/methodology-families') || url.includes('/families')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFamilies) });
      }

      // Assets endpoint (used by fetchProperties to populate project selector)
      if (url.includes('/assets')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            assets: mockProjects.map((p) => ({
              id: p.id,
              name: p.name,
              attributes: { sector: p.sector },
              asset_type: 'project',
            })),
            total: mockProjects.length,
          }),
        });
      }

      // Properties / Projects list
      if (url.includes('/properties') && !url.includes('/dashboard')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ properties: mockProjects, total: mockProjects.length }),
        });
      }
      if (url.includes('/projects') && !url.includes('/agriculture')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: mockProjects, total: mockProjects.length }),
        });
      }

      // Dashboard Payload
      if (url.includes('/dashboard')) {
        const isBiochar = url.includes('biochar') || url.includes('workspace_id=biochar');
        if (isBiochar) {
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              workspace: { code: 'BIOCHAR', name: 'Biochar Carbon Removal', badge: 'BIO' },
              methodology: { code: 'VM0044', name: 'Biochar Utilization' },
              project: { id: 'proj-biochar-001', name: 'Biochar Pyrolysis Kiln 1' },
              kpis: [],
              charts: [],
              activities: [],
              activity_total: 0,
              asset_total: 0,
              assets: [],
            }),
          });
        }

        const isProj2 = url.includes('proj-agri-002');
        const proj = isProj2 ? mockProjects[1] : mockProjects[0];
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            workspace: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', badge: 'AGRI' },
            methodology: { code: 'VM0042', name: 'Improved Agricultural Land Management' },
            project: { id: proj.id, name: proj.name },
            kpis: [
              { code: 'monitored_area', label: 'MONITORED AREA', value: `${proj.area_ha} ha`, unit: 'ha', state: 'AVAILABLE' },
              { code: 'land_units', label: 'LAND UNITS', value: isProj2 ? '1' : '2', unit: 'Registered management units', state: 'AVAILABLE' },
            ],
            charts: [],
            activities: [],
            activity_total: 0,
            asset_total: 0,
            assets: [],
          }),
        });
      }

      // Agriculture APIs: Readiness (MUST BE EVALUATED BEFORE /foundation to avoid partial matching)
      if (url.includes('/agriculture/projects/proj-agri-001/foundation-readiness')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project1.readiness) });
      }
      if (url.includes('/agriculture/projects/proj-agri-002/foundation-readiness')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project2.readiness) });
      }

      // Agriculture APIs: Foundation
      if (url.includes('/agriculture/projects/proj-agri-001/foundation')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project1.foundation) });
      }
      if (url.includes('/agriculture/projects/proj-agri-002/foundation')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project2.foundation) });
      }

      // Lock Methodology
      if (url.includes('/agriculture/projects/proj-agri-001/lock-methodology') && method === 'POST') {
        const body = route.request().postDataJSON ? route.request().postDataJSON() : {};
        state.project1.foundation.methodology_lock_status = 'LOCKED';
        state.project1.foundation.locked_methodology_snapshot = {
          methodology_code: 'VM0042',
          version: '2.2',
          locked_at: new Date().toISOString(),
          notes: body?.notes || 'Locked via E2E test',
        };
        state.project1.readiness.components.methodology_lock = {
          status: 'COMPLETE',
          message: 'Methodology parameters locked and immutable.',
        };
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project1.foundation) });
      }

      // Land Units
      if (url.includes('/agriculture/land-units')) {
        if (url.includes('proj-agri-002')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project2.landUnits) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project1.landUnits) });
      }

      // Strata: Create Stratum (POST)
      if (url.includes('/agriculture/projects/proj-agri-001/strata') && method === 'POST' && !url.includes('/members')) {
        const postData = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const newStratum = {
          id: `strat-${Date.now()}`,
          project_id: 'proj-agri-001',
          code: postData.code || 'STRAT-01',
          name: postData.name || 'Analytical Stratum',
          stratum_type: postData.stratum_type || 'MANAGEMENT_PRACTICE',
          description: postData.description || '',
          member_count: 0,
          area_ha: 0.0,
          land_unit_ids: [],
          status: 'ACTIVE',
        };
        state.project1.strata.push(newStratum);
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(newStratum) });
      }

      // Strata: Assign Members (POST)
      if (url.includes('/agriculture/projects/proj-agri-001/strata/') && url.includes('/members') && method === 'POST') {
        const postData = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const memberships = postData.memberships || [];
        const unitIds = memberships.map((m: any) => m.land_unit_id);
        const stratum = state.project1.strata[0];
        if (stratum) {
          stratum.land_unit_ids = unitIds;
          stratum.member_count = unitIds.length;
          let totalArea = 0;
          for (const uid of unitIds) {
            const lu = state.project1.landUnits.find((u) => u.id === uid);
            if (lu) totalArea += lu.area_ha;
          }
          stratum.area_ha = totalArea;
        }
        state.project1.readiness.components.stratification = {
          status: 'COMPLETE',
          message: 'Analytical strata configured and land units assigned.',
        };
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(stratum) });
      }

      // Strata: Get Strata (GET)
      if (url.includes('/agriculture/projects/proj-agri-001/strata')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project1.strata) });
      }
      if (url.includes('/agriculture/projects/proj-agri-002/strata')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project2.strata) });
      }

      // Management Records: Create (POST)
      if (url.includes('/agriculture/projects/proj-agri-001/management-records') && method === 'POST') {
        const postData = route.request().postDataJSON ? route.request().postDataJSON() : {};
        const newRecord = {
          id: `mgmt-${Date.now()}`,
          project_id: 'proj-agri-001',
          land_unit_id: postData.land_unit_id || null,
          practice_category: postData.practice_category || 'BASELINE',
          record_type: postData.record_type || 'TILLAGE',
          event_date: postData.event_date || '2024-03-15',
          data_source: postData.data_source || 'FIELD_INTERVIEW',
          details: postData.details || {},
          qa_status: 'VERIFIED',
        };
        state.project1.managementRecords.push(newRecord);
        state.project1.readiness.components.management_baseline = {
          status: 'COMPLETE',
          message: 'Management practices documented with valid provenance.',
        };
        // Check if all core components complete -> promote overall to COMPLETE
        if (state.project1.foundation.methodology_lock_status === 'LOCKED' && state.project1.strata.length > 0) {
          state.project1.readiness.overall_status = 'COMPLETE';
          state.project1.readiness.overall_message = 'Phase 1 foundation fully configured and verified.';
        }
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(newRecord) });
      }

      // Management Records: Get (GET)
      if (url.includes('/agriculture/projects/proj-agri-001/management-records')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project1.managementRecords) });
      }
      if (url.includes('/agriculture/projects/proj-agri-002/management-records')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.project2.managementRecords) });
      }

      // Default fallback
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    // Populate initial localStorage
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
  // TEST 1: Full Foundation Lifecycle: Readiness -> Lock -> Units -> Strata -> Management -> Complete
  // ---------------------------------------------------------------------------
  test('1. Full End-to-End Foundation Workflow: PM Locks Methodology, Creates Strata, Assigns Units, Logs Management, and Achieves COMPLETE Status', async ({ page }) => {
    await setupMocks(page, mockProjectManager);

    await page.goto(`${BASE_URL}/dashboard`);

    // Ensure Dashboard renders and Agriculture tab is active
    const agriTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriTab).toBeVisible({ timeout: 15000 });
    await agriTab.click();

    // 1. Initial Readiness State Verification
    const overallBadge = page.locator('[data-testid="agri-readiness-overall"]');
    await expect(overallBadge).toContainText('INCOMPLETE');

    const methCompBadge = page.locator('[data-testid="readiness-comp-methodology_lock"]');
    await expect(methCompBadge).toContainText('NEEDS REVIEW');

    // 2. Methodology Lock Workflow
    await page.locator('[data-testid="tab-methodology"]').click();
    await expect(page.locator('h3:has-text("Methodology Version Lock")')).toBeVisible();

    const lockNotesInput = page.locator('[data-testid="input-lock-notes"]');
    await expect(lockNotesInput).toBeVisible();
    await lockNotesInput.fill('Phase 1 Baseline Lock for VM0042 v2.2');

    const lockBtn = page.locator('[data-testid="btn-lock-methodology"]');
    await expect(lockBtn).toBeVisible();
    await lockBtn.click();

    // Immutable badge must appear, and the lock button must be eliminated
    const lockedBadge = page.locator('[data-testid="locked-methodology-badge"]');
    await expect(lockedBadge).toBeVisible();
    await expect(lockedBadge).toContainText('LOCKED');
    await expect(page.locator('[data-testid="btn-lock-methodology"]')).not.toBeVisible();

    // 3. Land Management Units Inspection & Geodesic Area
    await page.locator('[data-testid="tab-land_structure"]').click();
    await expect(page.locator('text=Land Management Units (2)')).toBeVisible();
    await expect(page.locator('text=North Field Parcel A')).toBeVisible();
    await expect(page.locator('text=74.50')).toBeVisible();
    await expect(page.locator('text=South Field Parcel B')).toBeVisible();
    await expect(page.locator('text=50.00')).toBeVisible();
    await expect(page.locator('text=POSTGIS_GEOMETRY').first()).toBeVisible();

    // 4. Stratum Creation & Land Unit Assignment
    await page.locator('[data-testid="tab-strata"]').click();
    await expect(page.locator('text=Analytical Strata (0)')).toBeVisible();

    const createStratumBtn = page.locator('[data-testid="btn-create-stratum"]');
    await expect(createStratumBtn).toBeVisible();
    await createStratumBtn.click();

    const stratumModal = page.locator('[data-testid="modal-create-stratum"]');
    await expect(stratumModal).toBeVisible();

    await page.locator('[data-testid="input-stratum-code"]').fill('STRAT-TILL-01');
    await page.locator('[data-testid="input-stratum-name"]').fill('Reduced Tillage Loam');
    await page.locator('[data-testid="select-stratum-type"]').selectOption('MANAGEMENT_PRACTICE');
    await page.locator('[data-testid="input-stratum-desc"]').fill('Silt and clay loam plots under reduced tillage regime');
    await page.locator('[data-testid="btn-submit-stratum"]').click();

    // Verify Stratum Card is displayed
    const stratumCard = page.locator('[data-testid="stratum-card-STRAT-TILL-01"]');
    await expect(stratumCard).toBeVisible();
    await expect(stratumCard).toContainText('STRAT-TILL-01');
    await expect(stratumCard).toContainText('MANAGEMENT_PRACTICE');

    // Assign Land Units to Stratum
    const assignBtn = page.locator('[data-testid="btn-assign-units-STRAT-TILL-01"]');
    await expect(assignBtn).toBeVisible();
    await assignBtn.click();

    const assignModal = page.locator('[data-testid="modal-assign-units"]');
    await expect(assignModal).toBeVisible();

    // Select both units
    await page.locator('[data-testid="checkbox-unit-lu-001"] input[type="checkbox"]').check();
    await page.locator('[data-testid="checkbox-unit-lu-002"] input[type="checkbox"]').check();
    await page.locator('[data-testid="btn-save-assignments"]').click();

    // Verify aggregated area and member count
    await expect(page.locator('[data-testid="stratum-members-STRAT-TILL-01"]')).toContainText('2');
    await expect(page.locator('[data-testid="stratum-area-STRAT-TILL-01"]')).toContainText('124.50 ha');

    // 5. Baseline Management Record Logging
    await page.locator('[data-testid="tab-management"]').click();
    await expect(page.locator('text=Management Baseline & Practice History (0)')).toBeVisible();

    const logPracticeBtn = page.locator('[data-testid="btn-log-practice"]');
    await expect(logPracticeBtn).toBeVisible();
    await logPracticeBtn.click();

    const practiceModal = page.locator('[data-testid="modal-log-practice"]');
    await expect(practiceModal).toBeVisible();

    // Fill Record 1: TILLAGE, BASELINE, FIELD_INTERVIEW
    await page.locator('[data-testid="select-practice-category"]').selectOption('BASELINE');
    await page.locator('[data-testid="select-record-type"]').selectOption('TILLAGE');
    await page.locator('[data-testid="input-event-date"]').fill('2024-03-15');
    await page.locator('[data-testid="select-data-source"]').selectOption('FIELD_INTERVIEW');
    await page.locator('[data-testid="input-event-details"]').fill('{"tillage_depth_cm": 15, "equipment": "CHISEL_PLOW"}');
    await page.locator('[data-testid="btn-submit-practice"]').click();

    // Verify Record 1 in Table
    const tillageRow = page.locator('[data-testid="mgmt-row-TILLAGE"]');
    await expect(tillageRow).toBeVisible();
    await expect(tillageRow).toContainText('BASELINE');
    await expect(tillageRow).toContainText('FIELD_INTERVIEW');

    // Fill Record 2: COVER_CROP, BASELINE, REMOTE_SENSING_CORROBORATED
    await page.locator('[data-testid="btn-log-practice"]').click();
    await page.locator('[data-testid="select-practice-category"]').selectOption('BASELINE');
    await page.locator('[data-testid="select-record-type"]').selectOption('COVER_CROP');
    await page.locator('[data-testid="input-event-date"]').fill('2024-04-01');
    await page.locator('[data-testid="select-data-source"]').selectOption('REMOTE_SENSING_CORROBORATED');
    await page.locator('[data-testid="input-event-details"]').fill('{"species": "CLOVER", "corroboration": "NDVI > 0.65"}');
    await page.locator('[data-testid="btn-submit-practice"]').click();

    const coverCropRow = page.locator('[data-testid="mgmt-row-COVER_CROP"]');
    await expect(coverCropRow).toBeVisible();
    await expect(coverCropRow).toContainText('REMOTE_SENSING_CORROBORATED');

    // 6. Dynamic Readiness Update to COMPLETE
    await page.locator('[data-testid="tab-readiness"]').click();
    await expect(overallBadge).toContainText('COMPLETE');
    await expect(methCompBadge).toContainText('COMPLETE');
    await expect(page.locator('[data-testid="readiness-comp-stratification"]')).toContainText('COMPLETE');
    await expect(page.locator('[data-testid="readiness-comp-management_baseline"]')).toContainText('COMPLETE');
  });

  // ---------------------------------------------------------------------------
  // TEST 2: Project Switching Data Isolation
  // ---------------------------------------------------------------------------
  test('2. Project Switching Data Isolation: Switching from Project Alpha to Savannah Updates View Without Data Bleeding', async ({ page }) => {
    await setupMocks(page, mockProjectManager);

    await page.goto(`${BASE_URL}/dashboard`);

    const agriTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriTab).toBeVisible({ timeout: 15000 });
    await agriTab.click();

    // Initial project is Alpha
    await expect(page.locator('h2:has-text("Demonstration Plot Alpha")')).toBeVisible();
    await page.locator('[data-testid="tab-land_structure"]').click();
    await expect(page.locator('text=North Field Parcel A')).toBeVisible();
    await expect(page.locator('text=74.50')).toBeVisible();

    // Switch Project Selector to Savannah
    const projectSelector = page.locator('[data-testid="project-selector"]');
    await expect(projectSelector).toBeVisible();
    await projectSelector.selectOption('proj-agri-002');

    // Verify Title and Code update to Savannah
    await expect(page.locator('h2:has-text("Savannah Regenerative Farm")')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=AGRI-KE-002')).toBeVisible();

    // Check Land Units: should show Savannah Agroforestry Block 1 (50.25 ha), NOT Alpha's 74.50 ha
    await page.locator('[data-testid="tab-land_structure"]').click();
    await expect(page.locator('text=Savannah Agroforestry Block 1')).toBeVisible();
    await expect(page.locator('text=50.25')).toBeVisible();
    await expect(page.locator('text=North Field Parcel A')).not.toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // TEST 3: Sector Switching Control Removal
  // ---------------------------------------------------------------------------
  test('3. Sector Switching: Switching to Biochar Removes Agriculture Controls and Replaces With Biochar Tab', async ({ page }) => {
    await setupMocks(page, mockProjectManager);

    await page.goto(`${BASE_URL}/dashboard`);

    // Initially in Agriculture
    const agriTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriTab).toBeVisible({ timeout: 15000 });

    // Switch Sector Selector to Biochar
    const sectorSelector = page.locator('[data-testid="sector-selector"]');
    await expect(sectorSelector).toBeVisible();
    await sectorSelector.selectOption('biochar');

    // Agriculture tab must disappear completely
    await expect(agriTab).not.toBeVisible({ timeout: 10000 });

    // Biochar tab must appear
    const biocharTab = page.locator('[data-testid="analytics-tab-biochar_value_chain"]');
    await expect(biocharTab).toBeVisible();

    // Switch back to Agriculture
    await sectorSelector.selectOption('agriculture_land_use');
    await expect(page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]')).toBeVisible({ timeout: 10000 });
  });

  // ---------------------------------------------------------------------------
  // TEST 4: RBAC & Separation of Duties (AUDITOR & FIELD_AGENT Restrictions)
  // ---------------------------------------------------------------------------
  test('4. RBAC Verification: AUDITOR is Strictly Read-Only; FIELD_AGENT Can Log Management but Cannot Lock Methodology', async ({ page }) => {
    // PART A: AUDITOR
    await setupMocks(page, mockAuditor);
    await page.goto(`${BASE_URL}/dashboard`);

    const agriTab = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriTab).toBeVisible({ timeout: 15000 });
    await agriTab.click();

    // Auditor in Methodology Tab: Cannot lock
    await page.locator('[data-testid="tab-methodology"]').click();
    await expect(page.locator('[data-testid="btn-lock-methodology"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="auditor-restricted-notice"]')).toBeVisible();
    await expect(page.locator('[data-testid="auditor-restricted-notice"]')).toContainText('AUDITOR is not authorized');

    // Auditor in Strata Tab: Cannot create or assign
    await page.locator('[data-testid="tab-strata"]').click();
    await expect(page.locator('[data-testid="btn-create-stratum"]')).not.toBeVisible();

    // Auditor in Management Tab: Cannot log practice
    await page.locator('[data-testid="tab-management"]').click();
    await expect(page.locator('[data-testid="btn-log-practice"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="auditor-management-notice"]')).toBeVisible();

    // PART B: FIELD_AGENT
    await setupMocks(page, mockFieldAgent);
    await page.goto(`${BASE_URL}/dashboard`);

    const agriTabFA = page.locator('[data-testid="analytics-tab-agri_foundation_workflow"]');
    await expect(agriTabFA).toBeVisible({ timeout: 15000 });
    await agriTabFA.click();

    // Field Agent in Methodology: Cannot lock
    await page.locator('[data-testid="tab-methodology"]').click();
    await expect(page.locator('[data-testid="btn-lock-methodology"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="auditor-restricted-notice"]')).toContainText('FIELD_AGENT is not authorized');

    // Field Agent in Management: CAN log practice
    await page.locator('[data-testid="tab-management"]').click();
    await expect(page.locator('[data-testid="btn-log-practice"]')).toBeVisible();
  });
});
