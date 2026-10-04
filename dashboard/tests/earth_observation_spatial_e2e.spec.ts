import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

const FIXTURE_PATH = path.join(__dirname, 'fixtures', 'real_s2_thumbnail.jpg');
const REAL_SATELLITE_BYTES = fs.readFileSync(FIXTURE_PATH);

const ARTIFACT_DIR = process.env.ARTIFACT_DIR || path.join(__dirname, '..', 'test-results');
if (!fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

test.describe('Earth Observation & Spatial Map Runtime E2E', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(60000);

  const mockUser = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'test.superadmin@verifield.com',
    full_name: 'Test Super Admin',
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
    { id: '2', code: 'VM0044', name: 'Biochar Utilization', sector: 'biochar', family_id: 'fam-biochar', ui_config: {} },
    { id: '3', code: 'ACM0002', name: 'Grid-Connected Renewable Electricity', sector: 'hybrid_energy', family_id: 'fam-energy', ui_config: {} },
    { id: '4', code: 'AMS-III.C', name: 'Emission Reductions by Electric Vehicles', sector: 'ev_mobility', family_id: 'fam-ev', ui_config: {} },
    { id: '5', code: 'AMS-II.G', name: 'Energy Efficiency in Clean Cooking', sector: 'cookstoves', family_id: 'fam-cook', ui_config: {} },
  ];

  const mockFamilies = [
    { id: 'fam-agri', code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', methodologies: ['VM0042'] },
    { id: 'fam-biochar', code: 'BIOCHAR', name: 'Biochar Carbon Removal', methodologies: ['VM0044'] },
    { id: 'fam-energy', code: 'HYBRID_ENERGY', name: 'Hybrid Energy & Mini-grids', methodologies: ['ACM0002'] },
    { id: 'fam-ev', code: 'EV_MOBILITY', name: 'EV Mobility', methodologies: ['AMS-III.C'] },
    { id: 'fam-cook', code: 'COOKSTOVES', name: 'Clean Cooking Solutions', methodologies: ['AMS-II.G'] },
  ];

  const agriPayload = {
    workspace: { code: 'AGRICULTURE_LAND_USE', name: 'Agriculture & Land Use', badge: 'AGRI' },
    methodology: { code: 'VM0042', name: 'Improved Agricultural Land Management' },
    project: { id: '00000000-0000-0000-0000-000000000099', name: 'Demonstration Plot Alpha' },
    kpis: [
      { code: 'monitored_area', label: 'MONITORED AREA', value: '124.5 ha', unit: 'ha', state: 'AVAILABLE' },
      { code: 'land_units', label: 'LAND UNITS', value: '3', unit: 'Registered management units', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [],
    activity_total: 1,
    asset_total: 1,
    assets: [
      { id: 'field-01', name: 'Demonstration Plot Alpha', lat: -1.2921, lng: 36.8219, status: 'VERIFIED', trust: 95 },
    ],
  };

  const biocharPayload = {
    workspace: { code: 'BIOCHAR', name: 'Biochar Carbon Removal', badge: 'BIO' },
    methodology: { code: 'VM0044', name: 'Biochar Utilization' },
    project: { id: '00000000-0000-0000-0000-000000000098', name: 'Biochar Kiln Facility' },
    kpis: [],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 0,
    assets: [],
  };

  const hybridEnergyPayload = {
    workspace: { code: 'HYBRID_ENERGY', name: 'Hybrid Energy & Mini-grids', badge: 'ENG' },
    methodology: { code: 'ACM0002', name: 'Grid-Connected Renewable Electricity' },
    project: { id: '00000000-0000-0000-0000-000000000097', name: 'Solar PV Mini-grid Station' },
    kpis: [],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 0,
    assets: [],
  };

  const evMobilityPayload = {
    workspace: { code: 'EV_MOBILITY', name: 'EV Mobility', badge: 'EV' },
    methodology: { code: 'AMS-III.C', name: 'Emission Reductions by Electric Vehicles' },
    project: { id: '00000000-0000-0000-0000-000000000096', name: 'Nairobi Central Fast-Charging Depot' },
    kpis: [],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 0,
    assets: [],
  };

  const cookstovesPayload = {
    workspace: { code: 'COOKSTOVES', name: 'Clean Cooking Solutions', badge: 'CK' },
    methodology: { code: 'AMS-II.G', name: 'Energy Efficiency in Clean Cooking' },
    project: { id: '00000000-0000-0000-0000-000000000095', name: 'Rift Valley Household Stove Distribution' },
    kpis: [],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 0,
    assets: [],
  };

  const mockAOIResponse = {
    status: 'CONFIGURED',
    aoi: {
      id: 'aoi-001',
      project_id: '00000000-0000-0000-0000-000000000099',
      name: 'Demonstration AOI Nairobi',
      area_ha: 124.5,
      perimeter_m: 4460.2,
      geometry_geojson: {
        type: 'Polygon',
        coordinates: [
          [
            [36.8, -1.35],
            [37.0, -1.35],
            [37.0, -1.2],
            [36.8, -1.2],
            [36.8, -1.35],
          ],
        ],
      },
    },
  };

  const mockObservations = [
    {
      id: 'obs-s2-001',
      project_id: '00000000-0000-0000-0000-000000000099',
      scene_id: 'S2B_37MBU_20240227_0_L2A',
      platform: 'Sentinel-2B',
      sensor: 'MSI',
      product_code: 'S2_MSI_L2A',
      observation_type: 'OPTICAL_MULTISPECTRAL',
      acquisition_timestamp: '2024-02-27T10:00:00Z',
      cloud_cover_pct: 2.5,
      quality_status: 'USABLE',
      spatial_resolution_m: 10.0,
      provenance_hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b',
      geometry_geojson: {
        type: 'Polygon',
        coordinates: [
          [
            [36.8, -1.35],
            [37.0, -1.35],
            [37.0, -1.2],
            [36.8, -1.2],
            [36.8, -1.35],
          ],
        ],
      },
      raw_band_uris: {
        visual: 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/visual.tif',
        thumbnail: 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/thumbnail.jpg',
      },
      is_baseline: false,
    },
    {
      id: 'obs-landsat-001',
      project_id: '00000000-0000-0000-0000-000000000099',
      scene_id: 'LE07_L2SP_168061_20230331_02_T1',
      platform: 'Landsat-7',
      sensor: 'ETM+',
      product_code: 'LANDSAT_C2_L2',
      observation_type: 'OPTICAL_MULTISPECTRAL',
      acquisition_timestamp: '2023-03-31T05:47:59Z',
      cloud_cover_pct: 12.0,
      quality_status: 'USABLE',
      spatial_resolution_m: 30.0,
      provenance_hash: '7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9a8b',
      geometry_geojson: {
        type: 'Polygon',
        coordinates: [
          [
            [36.8, -1.35],
            [37.0, -1.35],
            [37.0, -1.2],
            [36.8, -1.2],
            [36.8, -1.35],
          ],
        ],
      },
      raw_band_uris: {
        visual: 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/37/M/BU/2024/2/S2B_37MBU_20240227_0_L2A/thumbnail.jpg',
        thumbnail: 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/37/M/BU/2024/2/S2B_37MBU_20240227_0_L2A/thumbnail.jpg',
      },
      is_baseline: true,
      baseline_notes: 'Historical pre-project MRV baseline observation (2023)',
    },
  ];

  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/auth/me')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockUser) });
      }
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      }
      if (url.includes('/methodology-families') || url.includes('/families')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFamilies) });
      }
      if (url.includes('/earth-observation/projects/') && url.includes('/aoi')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockAOIResponse) });
      }
      if (url.includes('/earth-observation/projects/') && url.includes('/observations') && !url.includes('/raster')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockObservations) });
      }
      if (url.includes('/earth-observation/projects/') && url.includes('/derived-layers')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/earth-observation/projects/') && url.includes('/spatial-anomalies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/raster')) {
        return route.fulfill({
          status: 200,
          contentType: 'image/jpeg',
          body: REAL_SATELLITE_BYTES,
          headers: {
            'Content-Type': 'image/jpeg',
            'X-EO-Raster-Origin': 'PROVIDER_THUMBNAIL',
            'X-Raster-Crop': 'FULL_SCENE',
            'X-Raster-CRS': 'EPSG:4326',
            'X-Visualization-Type': 'TRUE_COLOR',
            'X-Band-Mapping': 'R=B04,G=B03,B=B02',
            'X-Visualization-Version': 'S2_TRUE_COLOR_V1',
            'Cache-Control': 'public, max-age=86400',
          },
        });
      }
      if (url.includes('/activities')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/properties') && !url.includes('/dashboard')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ properties: [] }) });
      }
      if (url.toLowerCase().includes('/dashboard')) {
        if (url.includes('biochar')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(biocharPayload) });
        }
        if (url.includes('hybrid') || url.includes('energy')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(hybridEnergyPayload) });
        }
        if (url.includes('ev') || url.includes('mobility')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(evMobilityPayload) });
        }
        if (url.includes('cookstove')) {
          return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(cookstovesPayload) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(agriPayload) });
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
    });

    page.on('console', (msg) => {
      if (msg.type() === 'error' || msg.text().includes('Uncaught') || msg.text().includes('Failed')) {
        console.log('[BROWSER CONSOLE ERROR]', msg.text());
      }
    });
    page.on('pageerror', (err) => {
      console.log('[BROWSER UNCAUGHT PAGE ERROR]', err.message);
    });

    await page.addInitScript(({ u }) => {
      window.localStorage.setItem('vf_token', 'valid-mock-token');
      window.localStorage.setItem('vf_user', JSON.stringify(u));
      window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'agriculture_land_use');
    }, { u: mockUser });
  });

  test('01. Map renders with Leaflet container, zoom controls, and basemap switcher (Screenshots A & B)', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    // Leaflet container should be visible
    const leafletContainer = page.locator('.leaflet-container');
    await expect(leafletContainer).toBeVisible({ timeout: 15000 });

    // Zoom controls should exist
    const zoomIn = page.locator('.leaflet-control-zoom-in');
    const zoomOut = page.locator('.leaflet-control-zoom-out');
    await expect(zoomIn).toBeVisible();
    await expect(zoomOut).toBeVisible();

    // Basemap switch controls should exist with clean labels
    const mapBtn = page.locator('button[data-basemap="map"]');
    const satelliteBtn = page.locator('button[data-basemap="satellite"]');
    await expect(mapBtn).toBeVisible();
    await expect(satelliteBtn).toBeVisible();

    // Allow tiles to settle
    await page.waitForTimeout(1000);

    // Capture Screenshot A: Map basemap + project boundary
    const screenshotAPath = path.join(ARTIFACT_DIR, 'screenshot_a_map_boundary.png');
    await leafletContainer.screenshot({ path: screenshotAPath });

    // Switch to satellite context
    await satelliteBtn.click({ force: true });

    // Verify neutral disclaimer badge is rendered
    const contextNotice = page.locator('text=Geographic context only');
    await expect(contextNotice).toBeVisible();

    // Allow satellite tiles to settle
    await page.waitForTimeout(1200);

    // Capture Screenshot B: Satellite basemap + project boundary
    const screenshotBPath = path.join(ARTIFACT_DIR, 'screenshot_b_satellite_boundary.png');
    await leafletContainer.screenshot({ path: screenshotBPath });

    // Switch back to Map
    await mapBtn.click({ force: true });
    await expect(contextNotice).not.toBeVisible();
  });

  test('02. Real Sentinel-2 optical observation on Map and Satellite basemaps (Screenshots C & D)', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    const leafletContainer = page.locator('.leaflet-container');
    await expect(leafletContainer).toBeVisible({ timeout: 15000 });

    // Switch to EO & MRV tab
    const eoTabBtn = page.getByRole('button', { name: /EO & MRV/i });
    await expect(eoTabBtn).toBeVisible();
    await eoTabBtn.click({ force: true });

    // Verify observation table lists Sentinel-2 scene
    const sceneRow = page.locator('text=S2B_37MBU_20240227_0_L2A');
    await expect(sceneRow).toBeVisible({ timeout: 10000 });

    // Click scene row to inspect scene
    await sceneRow.click({ force: true });

    // Inspection panel with "View on Map" button should appear
    const viewOnMapBtn = page.getByRole('button', { name: /View on Map/i });
    await expect(viewOnMapBtn).toBeVisible();
    await viewOnMapBtn.click({ force: true });

    // Map container should receive data-eo-raster-active="true"
    const activeMap = page.locator('.leaflet-container[data-eo-raster-active="true"]');
    await expect(activeMap).toBeVisible({ timeout: 15000 });

    // Leaflet imageOverlay element must be rendered and loaded
    const rasterOverlayImg = page.locator('img.vf-eo-raster-overlay[data-raster-loaded="true"]');
    await expect(rasterOverlayImg).toBeVisible({ timeout: 10000 });

    // Verify natural dimensions > 0 (proving real decoded raster)
    const naturalWidth = await rasterOverlayImg.getAttribute('data-natural-width');
    const naturalHeight = await rasterOverlayImg.getAttribute('data-natural-height');
    expect(Number(naturalWidth)).toBeGreaterThan(0);
    expect(Number(naturalHeight)).toBeGreaterThan(0);

    // Verify streamlined control card elements
    const layerTitle = page.locator('text=Sentinel-2 Optical Preview (10m)');
    await expect(layerTitle).toBeVisible();

    const acqDate = page.locator('text=Acquired: 2024-02-27');
    await expect(acqDate).toBeVisible();

    const visibilityBadge = page.getByRole('button', { name: 'VISIBLE' });
    await expect(visibilityBadge).toBeVisible();

    const sourceLabel = page.locator('text=Source: Provider Visual');
    await expect(sourceLabel).toBeVisible();

    const sensorResLabel = page.locator('text=Sensor Res: 10 m');
    await expect(sensorResLabel).toBeVisible();

    const previewResLabel = page.locator('text=Preview Res:');
    await expect(previewResLabel).toBeVisible();

    // Verify False Recipe is strictly OMITTED for provider visual
    const falseRecipe = page.locator('text=Recipe: R=B04');
    await expect(falseRecipe).toHaveCount(0);

    // Verify Technical Lineage Inspector toggle and content
    const inspectorToggle = page.getByRole('button', { name: /View Technical Lineage/i });
    await expect(inspectorToggle).toBeVisible();
    await inspectorToggle.click({ force: true });
    const lineageSha = page.locator('text=SHA-256:');
    await expect(lineageSha).toBeVisible();

    await page.waitForTimeout(1000);

    // Capture Screenshot C: Map basemap + real Sentinel-2 optical observation
    const screenshotCPath = path.join(ARTIFACT_DIR, 'screenshot_c_map_sentinel2_observation.png');
    await activeMap.screenshot({ path: screenshotCPath });

    // Keep legacy artifact path updated too
    await activeMap.screenshot({ path: path.join(ARTIFACT_DIR, 'eo_raster_leaflet_runtime.png') });

    // Switch to Satellite basemap
    const satelliteBtn = page.locator('button[data-basemap="satellite"]');
    await satelliteBtn.click({ force: true });

    await page.waitForTimeout(1200);

    // Capture Screenshot D: Satellite basemap + real Sentinel-2 optical observation
    const screenshotDPath = path.join(ARTIFACT_DIR, 'screenshot_d_satellite_sentinel2_observation.png');
    await activeMap.screenshot({ path: screenshotDPath });
  });

  test('03. Historical Landsat observation rendering and baseline tracking (Screenshot E)', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    const leafletContainer = page.locator('.leaflet-container');
    await expect(leafletContainer).toBeVisible({ timeout: 15000 });

    // Switch to EO & MRV tab
    const eoTabBtn = page.getByRole('button', { name: /EO & MRV/i });
    await expect(eoTabBtn).toBeVisible();
    await eoTabBtn.click({ force: true });

    // Click historical Landsat observation row
    const landsatRow = page.locator('text=LE07_L2SP_168061_20230331_02_T1');
    await expect(landsatRow).toBeVisible({ timeout: 10000 });
    await landsatRow.click({ force: true });

    // Click View on Map
    const viewOnMapBtn = page.getByRole('button', { name: /View on Map/i });
    await expect(viewOnMapBtn).toBeVisible();
    await viewOnMapBtn.click({ force: true });

    // Map container should receive data-eo-raster-active="true"
    const activeMap = page.locator('.leaflet-container[data-eo-raster-active="true"]');
    await expect(activeMap).toBeVisible({ timeout: 15000 });

    // Verify Landsat layer details in control card
    const landsatTitle = page.locator('text=Landsat-7 Optical Preview (30m)');
    await expect(landsatTitle).toBeVisible();

    const landsatAcq = page.locator('text=Acquired: 2023-03-31');
    await expect(landsatAcq).toBeVisible();

    const landsatSource = page.locator('text=Source: Provider Preview');
    await expect(landsatSource).toBeVisible();

    const landsatSensorRes = page.locator('text=Sensor Res: 30 m');
    await expect(landsatSensorRes).toBeVisible();

    await page.waitForTimeout(1000);

    // Capture Screenshot E: Historical Landsat observation
    const screenshotEPath = path.join(ARTIFACT_DIR, 'screenshot_e_landsat_historical_baseline.png');
    await activeMap.screenshot({ path: screenshotEPath });
  });

  test('04. Sector and project switch isolation prevents spatial leak', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });

    const leafletContainer = page.locator('.leaflet-container');
    await expect(leafletContainer).toBeVisible({ timeout: 15000 });

    // Activate raster in Agriculture workspace
    const eoTabBtn = page.getByRole('button', { name: /EO & MRV/i });
    await expect(eoTabBtn).toBeVisible();
    await eoTabBtn.click({ force: true });

    const sceneRow = page.locator('text=S2B_37MBU_20240227_0_L2A');
    await expect(sceneRow).toBeVisible({ timeout: 15000 });
    await sceneRow.click({ force: true });

    const viewOnMapBtn = page.getByRole('button', { name: /View on Map/i });
    await expect(viewOnMapBtn).toBeVisible();
    await viewOnMapBtn.click({ force: true });

    const activeMap = page.locator('.leaflet-container[data-eo-raster-active="true"]');
    await expect(activeMap).toBeVisible({ timeout: 15000 });

    // Switch workspace to Biochar
    await page.goto(`${BASE_URL}/dashboard?workspace=biochar`, { waitUntil: 'domcontentloaded' });

    // The map container must NOT have data-eo-raster-active
    const leakedActiveMap = page.locator('.leaflet-container[data-eo-raster-active="true"]');
    await expect(leakedActiveMap).toHaveCount(0);

    // The raster image overlay must NOT exist in the DOM
    const rasterImg = page.locator('img.vf-eo-raster-overlay');
    await expect(rasterImg).toHaveCount(0);

    // The Active Footprint banner must NOT exist
    const footprintBanner = page.locator('text=Active Footprint:');
    await expect(footprintBanner).toHaveCount(0);
  });

  test('05. Cross-Sector EO truth and vegetation indices restriction across sectors', async ({ page }) => {
    // 1. Agriculture & Land Use Workspace
    await page.goto(`${BASE_URL}/dashboard?workspace=agriculture_land_use`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
    const agriEoTab = page.getByRole('button', { name: /EO & MRV/i });
    await expect(agriEoTab).toBeVisible();
    await agriEoTab.click();

    // Check Agriculture scope disclaimer
    const agriScope = page.locator('text=Agriculture & Land Use Scope:');
    await expect(agriScope).toBeVisible({ timeout: 10000 });
    // Vegetation indices ARE applicable in Agriculture
    await expect(page.locator('text=Vegetation indices (NDVI/EVI/NDWI) and photosynthetic canopy analytics are not applicable')).toHaveCount(0);

    // 2. Biochar Workspace
    await page.goto(`${BASE_URL}/dashboard?workspace=biochar`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
    const biocharEoTab = page.getByRole('button', { name: /EO & MRV/i });
    await expect(biocharEoTab).toBeVisible();
    await biocharEoTab.click();

    // Check Biochar scope disclaimer
    const biocharScope = page.locator('text=Biochar Carbon Removal Scope:');
    await expect(biocharScope).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=cannot determine batch mass')).toBeVisible();

    // Verify vegetation indices non-applicability notice & cross-sector linking
    await expect(page.locator('text=Vegetation indices (NDVI/EVI/NDWI) and photosynthetic canopy analytics are not applicable to the Biochar Carbon Removal sector')).toBeVisible();
    await expect(page.locator('text=Cross-sector linking to verified Agriculture Land Units is enabled')).toBeVisible();

    // 3. Hybrid Energy Workspace
    await page.goto(`${BASE_URL}/dashboard?workspace=hybrid_energy`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
    const energyEoTab = page.getByRole('button', { name: /EO & MRV/i });
    await expect(energyEoTab).toBeVisible();
    await energyEoTab.click();

    // Check Hybrid Energy scope disclaimer
    const energyScope = page.locator('text=Hybrid Energy & Mini-grids Scope:');
    await expect(energyScope).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=cannot determine kWh generated')).toBeVisible();

    // Verify vegetation indices non-applicability notice
    await expect(page.locator('text=Vegetation indices (NDVI/EVI/NDWI) and photosynthetic canopy analytics are not applicable to the Hybrid Energy & Mini-grids sector')).toBeVisible();

    // 4. EV Mobility Workspace
    await page.goto(`${BASE_URL}/dashboard?workspace=ev_mobility`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
    const evEoTab = page.getByRole('button', { name: /EO & MRV/i });
    await expect(evEoTab).toBeVisible();
    await evEoTab.click();

    // Check EV Mobility scope disclaimer
    const evScope = page.locator('text=EV Mobility Scope:');
    await expect(evScope).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=cannot determine charging sessions')).toBeVisible();

    // Verify vegetation indices non-applicability notice
    await expect(page.locator('text=Vegetation indices (NDVI/EVI/NDWI) and photosynthetic canopy analytics are not applicable to the EV Mobility sector')).toBeVisible();

    // 5. Clean Cookstoves Workspace
    await page.goto(`${BASE_URL}/dashboard?workspace=cookstoves`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
    const cookEoTab = page.getByRole('button', { name: /EO & MRV/i });
    await expect(cookEoTab).toBeVisible();
    await cookEoTab.click();

    // Check Clean Cookstoves scope disclaimer
    const cookScope = page.locator('text=Clean Cooking Solutions Scope:');
    await expect(cookScope).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Household deployment coordinates are protected via privacy-safe spatial clustering')).toBeVisible();
    await expect(page.locator('text=cannot determine stove usage hours')).toBeVisible();

    // Verify vegetation indices non-applicability notice
    await expect(page.locator('text=Vegetation indices (NDVI/EVI/NDWI) and photosynthetic canopy analytics are not applicable to the Clean Cooking Solutions sector')).toBeVisible();
  });
});
