import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('Agriculture & Land Use Dashboard Metric Correctness & Terminology E2E', () => {
  test.setTimeout(60000);

  const mockUser = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'segunoluwole22@gmail.com',
    full_name: 'Segun Oluwole',
    role: 'SUPER_ADMIN',
    status: 'active',
    is_active: true,
    organization: 'VeriField Nexus',
    organization_id: '00000000-0000-0000-0000-000000000001',
    licensed_sectors: ['agriculture_land_use', 'ev_mobility', 'cookstoves', 'hybrid_energy', 'biochar'],
    licensed_methodologies: ['VM0042', 'VM0047', 'VM0051', 'AMS-II.G', 'AMS-III.C'],
  };

  const mockMethodologies = [
    { id: '1', code: 'VM0042', name: 'Improved Agricultural Land Management', sector: 'agriculture_land_use', family_id: 'fam-agri', ui_config: {} },
    { id: '2', code: 'AMS-III.C', name: 'Electric Mobility', sector: 'ev_mobility', family_id: 'fam-ev', ui_config: {} },
    { id: '3', code: 'ACM0002', name: 'Grid-connected Electricity Generation', sector: 'hybrid_energy', family_id: 'fam-hybrid', ui_config: {} },
    { id: '4', code: 'VM0044', name: 'Biochar Carbon Removal', sector: 'biochar', family_id: 'fam-biochar', ui_config: {} },
    { id: '5', code: 'AMS-II.G', name: 'Clean Cooking', sector: 'cookstoves', family_id: 'fam-cookstoves', ui_config: {} },
  ];

  const mockFamilies = [
    { id: 'fam-agri', code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', methodologies: ['VM0042'] },
    { id: 'fam-ev', code: 'EV_MOBILITY', name: 'EV Mobility', methodologies: ['AMS-III.C'] },
    { id: 'fam-hybrid', code: 'HYBRID_ENERGY', name: 'Hybrid Energy & Mini-grids', methodologies: ['ACM0002'] },
    { id: 'fam-biochar', code: 'BIOCHAR', name: 'Biochar Carbon Removal', methodologies: ['VM0044'] },
    { id: 'fam-cookstoves', code: 'COOKSTOVES', name: 'Clean Cookstoves', methodologies: ['AMS-II.G'] },
  ];

  const agriDashboardPayload = {
    workspace: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', badge: 'AGRI' },
    methodology: { code: 'VM0042', name: 'Improved Agricultural Land Management' },
    kpis: [
      { code: 'monitored_area', label: 'MONITORED AREA', value: '150 ha', unit: 'ha', subtext: 'Across 2 top-level parcels', state: 'AVAILABLE' },
      { code: 'land_units', label: 'LAND UNITS', value: '2', unit: 'Registered management units', subtext: '2 top-level parcels', state: 'AVAILABLE' },
      { code: 'field_activities', label: 'FIELD ACTIVITIES', value: '3', unit: 'Submitted field records', subtext: 'Recorded field observations', state: 'AVAILABLE' },
      { code: 'qa_findings', label: 'OPEN QA FINDINGS', value: '0', unit: 'Active quality flags', subtext: 'All checks clear', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [
      { id: 'act-1', type: 'soil_sample', label: 'Soil Sample #1', timestamp: '2026-09-15T12:00:00Z', confidence: '98%', status: 'verified', pipeline_stage: 'ai_verified' }
    ],
    activity_total: 1,
    asset_total: 2,
    assets: [
      { id: 'lu-1', name: 'North Parcel', lat: 28.65, lng: 77.15, status: 'active', sector: 'agriculture_land_use' }
    ],
  };

  const evDashboardPayload = {
    workspace: { code: 'EV_MOBILITY', name: 'EV Mobility', badge: 'EV' },
    methodology: { code: 'AMS-III.C', name: 'Electric and Hybrid Vehicles' },
    kpis: [
      { code: 'co2_displaced', label: 'CO₂ DISPLACED', value: '120 tCO₂e', unit: 'ICE vehicle emissions avoided', state: 'AVAILABLE' },
      { code: 'charging_sessions', label: 'CHARGING SESSIONS', value: '800', unit: 'Completed fast charges', state: 'AVAILABLE' },
      { code: 'kwh_delivered', label: 'ELECTRICITY DELIVERED', value: '420 MWh', unit: 'Total grid power delivered', state: 'AVAILABLE' },
      { code: 'fleet_util', label: 'FLEET UTILISATION', value: '74%', unit: 'Active charging uptime', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 20,
    assets: [],
  };

  const hybridDashboardPayload = {
    workspace: { code: 'HYBRID_ENERGY', name: 'Hybrid Energy & Mini-grids', badge: 'HYBRID' },
    methodology: { code: 'ACM0002', name: 'Grid-connected Electricity Generation' },
    kpis: [
      { code: 'co2_displaced', label: 'TOTAL CO₂ DISPLACED', value: '450 tCO₂e', unit: 'Diesel & grid offset', state: 'AVAILABLE' },
      { code: 'energy_gen', label: 'ENERGY GENERATED', value: '562 MWh', unit: 'Clean solar PV', state: 'AVAILABLE' },
      { code: 'diesel_avoided', label: 'TOTAL DIESEL AVOIDED', value: '166,500 Liters', unit: 'Avoided diesel', state: 'AVAILABLE' },
      { code: 'active_sites', label: 'ACTIVE SITES', value: '12', unit: 'Verified operational systems', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 12,
    assets: [],
  };

  const biocharDashboardPayload = {
    workspace: { code: 'BIOCHAR', name: 'Biochar Carbon Removal', badge: 'BIOCHAR' },
    methodology: { code: 'VM0042', name: 'Biochar Carbon Removal' },
    kpis: [
      { code: 'carbon_removed', label: 'CARBON REMOVED', value: '250 tCO₂e', unit: 'Permanently sequestered carbon', state: 'AVAILABLE' },
      { code: 'biochar_produced', label: 'BIOCHAR PRODUCED', value: '175 Tons', unit: 'Pyrolyzed biomass output', state: 'AVAILABLE' },
      { code: 'permanence', label: 'CARBON PERMANENCE', value: '100 Yrs', unit: 'Soil sink durability', state: 'AVAILABLE' },
      { code: 'credit_value', label: 'CREDIT VALUE', value: '$6,250', unit: 'At baseline price', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 4,
    assets: [],
  };

  const cookstovesDashboardPayload = {
    workspace: { code: 'COOKSTOVES', name: 'Clean Cookstoves', badge: 'COOKSTOVES' },
    methodology: { code: 'AMS-II.G', name: 'Clean Cooking' },
    kpis: [
      { code: 'co2_reduced', label: 'TOTAL CO₂ REDUCED', value: '88 tCO₂e', unit: 'Verified offset credits', state: 'AVAILABLE' },
      { code: 'households', label: 'HOUSEHOLDS REACHED', value: '1,450', unit: 'Stoves deployed', state: 'AVAILABLE' },
      { code: 'usage_rate', label: 'STOVE USAGE RATE', value: '82%', unit: 'Mean daily utilization', state: 'AVAILABLE' },
      { code: 'credit_value', label: 'PORTFOLIO CREDIT VALUE', value: '$1,320', unit: 'At baseline price', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 1450,
    assets: [],
  };

  test.beforeEach(async ({ page }) => {
    // Intercept all API routes to prevent 401s and provide deterministic data
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url();

      if (url.includes('/auth/me')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockUser) });
      }
      if (url.includes('/methodologies/families') || url.includes('/methodology-families')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFamilies) });
      }
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      }
      if (url.includes('/users')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([mockUser]) });
      }
      const lowerUrl = url.toLowerCase();
      if (lowerUrl.includes('/properties/current/dashboard') || lowerUrl.includes('/dashboard')) {
        if (lowerUrl.includes('ev_mobility') || lowerUrl.includes('ams_iii_c') || lowerUrl.includes('ams-iii.c')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(evDashboardPayload) });
        }
        if (lowerUrl.includes('hybrid_energy') || lowerUrl.includes('acm0002')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(hybridDashboardPayload) });
        }
        if (lowerUrl.includes('biochar') || lowerUrl.includes('vm0044')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(biocharDashboardPayload) });
        }
        if (lowerUrl.includes('cookstoves') || lowerUrl.includes('ams_ii_g') || lowerUrl.includes('ams-ii.g')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(cookstovesDashboardPayload) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(agriDashboardPayload) });
      }
      if (url.includes('/projects')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/notifications')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }

      // Default safe empty response for any other API route
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
    });

    await page.addInitScript(
      ({ u }) => {
        window.localStorage.setItem('vf_token', 'valid-mock-token');
        window.localStorage.setItem('vf_user', JSON.stringify(u));
        window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'agriculture_land_use');
      },
      { u: mockUser }
    );
  });

  test('1. Agriculture dashboard renders correct Agriculture KPIs and zero EV metrics', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    // Wait for the loader to clear and the main dashboard heading / UI to stabilize
    await expect(page.locator('text=Connecting to VeriField Mission Control Engine')).toHaveCount(0, { timeout: 20000 });
    await expect(page.getByText('MONITORED AREA', { exact: true })).toBeVisible({ timeout: 15000 });

    const bodyText = await page.innerText('body');

    // 1. Assert ABSENCE of EV metrics
    expect(bodyText).not.toContain('CHARGING SESSIONS');
    expect(bodyText).not.toContain('ELECTRICITY DELIVERED');
    expect(bodyText).not.toContain('FLEET UTILISATION');
    expect(bodyText).not.toContain('Fleet Utilisation');

    // 2. Assert ABSENCE of "AI Verified"
    expect(bodyText).not.toContain('AI Verified');

    // 3. Assert PRESENCE of Agriculture KPI labels
    expect(bodyText).toContain('MONITORED AREA');
    expect(bodyText).toContain('LAND UNITS');
    expect(bodyText).toContain('FIELD ACTIVITIES');
    expect(bodyText).toContain('OPEN QA FINDINGS');

    // 4. Assert Spatial Module terminology
    expect(bodyText).toContain('land units');

    // 5. Assert Terminology updates in pipeline
    expect(bodyText).toContain('Checks Passed');
  });

  test('2. Exhaustive 9-step sector switching cache test: Agriculture <-> EV <-> Hybrid <-> Biochar <-> Cookstoves', async ({ page }) => {
    // Step 1: Agriculture
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=MONITORED AREA').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=150 ha').first()).toBeVisible({ timeout: 15000 });
    let txt = await page.innerText('body');
    expect(txt).not.toContain('CHARGING SESSIONS');

    // Step 2: EV Mobility
    await page.goto(`${BASE_URL}/dashboard?workspace=ev_mobility`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=CHARGING SESSIONS').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=800').first()).toBeVisible({ timeout: 15000 });
    txt = await page.innerText('body');
    expect(txt).not.toContain('MONITORED AREA');

    // Step 3: Back to Agriculture
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=MONITORED AREA').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=150 ha').first()).toBeVisible({ timeout: 15000 });
    txt = await page.innerText('body');
    expect(txt).not.toContain('CHARGING SESSIONS');

    // Step 4: Hybrid Energy
    await page.goto(`${BASE_URL}/dashboard?workspace=hybrid_energy`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=TOTAL DIESEL AVOIDED').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=166,500 Liters').first()).toBeVisible({ timeout: 15000 });
    txt = await page.innerText('body');
    expect(txt).not.toContain('MONITORED AREA');

    // Step 5: Back to Agriculture
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=MONITORED AREA').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=150 ha').first()).toBeVisible({ timeout: 15000 });
    txt = await page.innerText('body');
    expect(txt).not.toContain('TOTAL DIESEL AVOIDED');

    // Step 6: Biochar
    await page.goto(`${BASE_URL}/dashboard?workspace=biochar`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=BIOCHAR PRODUCED').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=175 Tons').first()).toBeVisible({ timeout: 15000 });
    txt = await page.innerText('body');
    expect(txt).not.toContain('MONITORED AREA');

    // Step 7: Back to Agriculture
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=MONITORED AREA').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=150 ha').first()).toBeVisible({ timeout: 15000 });
    txt = await page.innerText('body');
    expect(txt).not.toContain('BIOCHAR PRODUCED');

    // Step 8: Clean Cookstoves
    await page.goto(`${BASE_URL}/dashboard?workspace=cookstoves`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=HOUSEHOLDS REACHED').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=1,450').first()).toBeVisible({ timeout: 15000 });
    txt = await page.innerText('body');
    expect(txt).not.toContain('MONITORED AREA');

    // Step 9: Back to Agriculture
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=MONITORED AREA').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=150 ha').first()).toBeVisible({ timeout: 15000 });
    txt = await page.innerText('body');
    expect(txt).toContain('LAND UNITS');
    expect(txt).not.toContain('HOUSEHOLDS REACHED');
    expect(txt).not.toContain('CHARGING SESSIONS');
  });

  test('3. Verification Pipeline renders Checks Passed and handles empty state cleanly', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    // The Verification Pipeline Stage should show "Checks Passed"
    const checksPassedStage = page.locator('text=Checks Passed');
    await expect(checksPassedStage.first()).toBeVisible({ timeout: 15000 });

    // Verify no "AI Verified" stage
    const aiVerifiedStage = page.locator('text=AI Verified');
    await expect(aiVerifiedStage).toHaveCount(0);
  });
});
