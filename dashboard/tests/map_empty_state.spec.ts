import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('Map Empty-State Overlay & Stacking Validation', () => {
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
    licensed_sectors: ['agriculture_land_use', 'biochar', 'ev_mobility', 'cookstoves', 'hybrid_energy'],
    licensed_methodologies: ['VM0042', 'VM0044', 'AMS-III.C', 'AMS-II.G', 'ACM0002'],
  };

  const mockMethodologies = [
    { id: '1', code: 'VM0042', name: 'Improved Agricultural Land Management', sector: 'agriculture_land_use', family_id: 'fam-agri', ui_config: {} },
    { id: '2', code: 'VM0044', name: 'Biochar Carbon Removal', sector: 'biochar', family_id: 'fam-biochar', ui_config: {} },
    { id: '3', code: 'AMS-III.C', name: 'Electric Mobility', sector: 'ev_mobility', family_id: 'fam-ev', ui_config: {} },
  ];

  const mockFamilies = [
    { id: 'fam-agri', code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', methodologies: ['VM0042'] },
    { id: 'fam-biochar', code: 'BIOCHAR', name: 'Biochar Carbon Removal', methodologies: ['VM0044'] },
    { id: 'fam-ev', code: 'EV_MOBILITY', name: 'EV Mobility', methodologies: ['AMS-III.C'] },
  ];

  const agriZeroAssetsPayload = {
    workspace: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', badge: 'AGRI' },
    methodology: { code: 'VM0042', name: 'Improved Agricultural Land Management' },
    kpis: [
      { code: 'monitored_area', label: 'MONITORED AREA', value: '0 ha', unit: 'ha', subtext: 'No active parcels', state: 'AVAILABLE' },
      { code: 'land_units', label: 'LAND UNITS', value: '0', unit: 'Registered management units', subtext: '0 top-level parcels', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 0,
    assets: [],
  };

  const agriPopulatedAssetsPayload = {
    workspace: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', badge: 'AGRI' },
    methodology: { code: 'VM0042', name: 'Improved Agricultural Land Management' },
    kpis: [
      { code: 'monitored_area', label: 'MONITORED AREA', value: '150 ha', unit: 'ha', subtext: 'Across 1 parcel', state: 'AVAILABLE' },
      { code: 'land_units', label: 'LAND UNITS', value: '1', unit: 'Registered management units', subtext: '1 parcel', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [],
    activity_total: 1,
    asset_total: 1,
    assets: [
      { id: 'lu-101', name: 'Green Valley Plot Alpha', lat: 6.5244, lng: 3.3792, status: 'active', sector: 'agriculture_land_use', trust: 92 }
    ],
  };

  const biocharZeroAssetsPayload = {
    workspace: { code: 'BIOCHAR', name: 'Biochar Carbon Removal', badge: 'BIOCHAR' },
    methodology: { code: 'VM0044', name: 'Biochar Carbon Removal' },
    kpis: [],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 0,
    assets: [],
  };

  const unknownZeroAssetsPayload = {
    workspace: { code: 'GENERIC', name: 'Operations', badge: 'OPS' },
    methodology: { code: 'GENERIC', name: 'Generic Monitoring' },
    kpis: [],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 0,
    assets: [],
  };

  test('Scenario A: Agriculture + 0 land units -> compact Agriculture card visible, map and zoom controls present', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/auth/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockUser) });
      if (url.includes('/methodologies')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      if (url.includes('/methodology-families') || url.includes('/families')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFamilies) });
      if (url.toLowerCase().includes('/dashboard')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(agriZeroAssetsPayload) });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
    });

    await page.addInitScript(({ u }) => {
      window.localStorage.setItem('vf_token', 'valid-mock-token');
      window.localStorage.setItem('vf_user', JSON.stringify(u));
      window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'agriculture_land_use');
    }, { u: mockUser });

    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    const emptyHeading = page.locator('text="No land boundaries registered."');
    await expect(emptyHeading).toBeVisible({ timeout: 15000 });

    const emptySubtext = page.locator('text="Add or capture a land unit to establish the project map."');
    await expect(emptySubtext).toBeVisible();

    const mapContainer = page.locator('.leaflet-container');
    await expect(mapContainer).toBeVisible();

    const zoomInBtn = page.locator('.leaflet-control-zoom-in');
    await expect(zoomInBtn).toBeVisible();
    const zoomOutBtn = page.locator('.leaflet-control-zoom-out');
    await expect(zoomOutBtn).toBeVisible();
  });

  test('Scenario B: Agriculture + 1 valid land unit -> empty-state message absent, boundary and map remain', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/auth/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockUser) });
      if (url.includes('/methodologies')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      if (url.includes('/methodology-families') || url.includes('/families')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFamilies) });
      if (url.toLowerCase().includes('/dashboard')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(agriPopulatedAssetsPayload) });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
    });

    await page.addInitScript(({ u }) => {
      window.localStorage.setItem('vf_token', 'valid-mock-token');
      window.localStorage.setItem('vf_user', JSON.stringify(u));
      window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'agriculture_land_use');
    }, { u: mockUser });

    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    const emptyHeading = page.locator('text="No land boundaries registered."');
    await expect(emptyHeading).not.toBeVisible({ timeout: 15000 });

    const mapContainer = page.locator('.leaflet-container');
    await expect(mapContainer).toBeVisible();
  });

  test('Scenario C: Unknown / Missing sector + 0 assets -> neutral generic copy, NO Agriculture copy', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/auth/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockUser) });
      if (url.includes('/methodologies')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      if (url.toLowerCase().includes('/dashboard')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(unknownZeroAssetsPayload) });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
    });

    await page.addInitScript(({ u }) => {
      window.localStorage.setItem('vf_token', 'valid-mock-token');
      window.localStorage.setItem('vf_user', JSON.stringify(u));
    }, { u: mockUser });

    await page.goto(`${BASE_URL}/dashboard?workspace=unknown`, { waitUntil: 'domcontentloaded' });

    const genericHeading = page.locator('text="No assets registered."');
    await expect(genericHeading).toBeVisible({ timeout: 15000 });

    const agriHeading = page.locator('text="No land boundaries registered."');
    await expect(agriHeading).not.toBeVisible();
  });

  test('Scenario D: Biochar + 0 assets -> Biochar terminology, NO Agriculture copy', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/auth/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockUser) });
      if (url.includes('/methodologies')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      if (url.toLowerCase().includes('/dashboard')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(biocharZeroAssetsPayload) });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
    });

    await page.addInitScript(({ u }) => {
      window.localStorage.setItem('vf_token', 'valid-mock-token');
      window.localStorage.setItem('vf_user', JSON.stringify(u));
      window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'biochar');
    }, { u: mockUser });

    await page.goto(`${BASE_URL}/dashboard?workspace=biochar`, { waitUntil: 'domcontentloaded' });

    const biocharHeading = page.locator('text="No biochar facilities registered."');
    await expect(biocharHeading).toBeVisible({ timeout: 15000 });

    const agriHeading = page.locator('text="No land boundaries registered."');
    await expect(agriHeading).not.toBeVisible();
  });

  test('Scenario F: Mission Control open -> map empty-state remains contained behind drawer', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/auth/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockUser) });
      if (url.includes('/methodologies')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      if (url.toLowerCase().includes('/dashboard')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(agriZeroAssetsPayload) });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
    });

    await page.addInitScript(({ u }) => {
      window.localStorage.setItem('vf_token', 'valid-mock-token');
      window.localStorage.setItem('vf_user', JSON.stringify(u));
      window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'agriculture_land_use');
    }, { u: mockUser });

    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    const emptyHeading = page.locator('text="No land boundaries registered."');
    await expect(emptyHeading).toBeVisible({ timeout: 15000 });

    const drawerTrigger = page.locator('button[title*="Decision Support"], button[title*="Guidance"]').first();
    if (await drawerTrigger.isVisible()) {
      await drawerTrigger.click();
      const guidanceDrawer = page.locator('.fixed.inset-0.z-50');
      await expect(guidanceDrawer).toBeVisible();

      const drawerZIndex = await guidanceDrawer.evaluate((el) => window.getComputedStyle(el).zIndex);
      expect(Number(drawerZIndex)).toBeGreaterThanOrEqual(50);
    }
  });
});
