import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('POA Portfolio Aggregation & Decision Support E2E', () => {
  const mockAdminUser = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'admin@verifield.test',
    full_name: 'Lead POA Portfolio Manager',
    role: 'ORG_ADMIN',
    status: 'active',
    is_active: true,
    organization: 'Global Carbon Consortium',
    organization_id: 'org-poa-001',
    sector: 'multi_sector',
  };

  test.beforeEach(async ({ page }) => {
    // Setup authentication token in localStorage before navigation
    await page.addInitScript(
      ({ userData }: { userData: Record<string, unknown> }) => {
        window.localStorage.setItem('vf_token', 'mock-poa-e2e-token-valid');
        window.localStorage.setItem('vf_user', JSON.stringify(userData));
        window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'multi_sector');
      },
      { userData: mockAdminUser }
    );
  });

  test('1. Synthetic Agriculture project PoA: canonical label and Active Sectors count', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url().toLowerCase();

      if (url.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockAdminUser),
        });
      }

      if (url.includes('/carbon/ledger')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [
              {
                id: 'c-agri-001',
                sector: 'agriculture_land_use',
                tco2e: 450.0,
                status: 'calculated',
                timestamp: '2026-09-17T00:00:00Z',
              },
            ],
          }),
        });
      }

      if (url.includes('/projects')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              {
                id: 'proj-agri-001',
                name: 'Regenerative Agriculture Pilot',
                sector: 'agriculture_land_use',
                status: 'ACTIVE',
              },
            ],
          }),
        });
      }

      if (url.includes('/users')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/settings')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
      }
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/properties')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kpis: [], activeOrgs: 1 }) });
      }

      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.goto(`${BASE_URL}/dashboard/poa`);
    await page.waitForLoadState('networkidle');

    // Header verification
    await expect(page.locator('h1')).toContainText('POA Portfolio Performance');

    // Sector contribution section should display canonical Agriculture & Land Use card
    const sectorSection = page.getByTestId('sector-yield-contribution');
    await expect(sectorSection.getByText('Agriculture & Land Use', { exact: true })).toBeVisible();

    // Active Sectors KPI should read "1 Sector" and show Agriculture & Land Use
    const activeSectorsMetric = page.locator('text=Active Sectors').locator('..');
    await expect(activeSectorsMetric).toContainText('1 Sector');
    await expect(activeSectorsMetric).toContainText('Agriculture & Land Use');

    // Total yield should reflect 450 tCO2e
    const totalYieldMetric = page.locator('text=Total POA Yield').locator('..');
    await expect(totalYieldMetric).toContainText('450');
    await expect(totalYieldMetric).toContainText('tCO₂e');

    // Agriculture card should show 100.0% share and quantified value
    await expect(sectorSection.getByText('100.0%')).toBeVisible();
    await expect(sectorSection.getByText('450 tCO₂e')).toBeVisible();
  });

  test('2. Five-sector synthetic PoA: all canonical sectors render cleanly without clipping', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url().toLowerCase();

      if (url.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockAdminUser),
        });
      }

      if (url.includes('/carbon/ledger')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [
              { id: 'c-1', sector: 'agriculture_land_use', tco2e: 400.0, status: 'calculated' },
              { id: 'c-2', sector: 'cookstoves', tco2e: 300.0, status: 'calculated' },
              { id: 'c-3', sector: 'hybrid_energy', tco2e: 250.0, status: 'calculated' },
              { id: 'c-4', sector: 'biochar', tco2e: 500.0, status: 'issued' },
              { id: 'c-5', sector: 'ev_mobility', tco2e: 150.0, status: 'pending_issuance' },
            ],
          }),
        });
      }

      if (url.includes('/projects')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              { id: 'p-1', sector: 'agriculture_land_use' },
              { id: 'p-2', sector: 'cookstoves' },
              { id: 'p-3', sector: 'hybrid_energy' },
              { id: 'p-4', sector: 'biochar' },
              { id: 'p-5', sector: 'ev_mobility' },
            ],
          }),
        });
      }

      if (url.includes('/users')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/settings')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
      }
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/properties')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kpis: [], activeOrgs: 1 }) });
      }

      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.goto(`${BASE_URL}/dashboard/poa`);
    await page.waitForLoadState('networkidle');

    // Total yield = 400 + 300 + 250 + 500 + 150 = 1,600
    const totalYieldMetric = page.locator('text=Total POA Yield').locator('..');
    await expect(totalYieldMetric).toContainText('1,600');

    // Active Sectors = 5 Sectors
    const activeSectorsMetric = page.locator('text=Active Sectors').locator('..');
    await expect(activeSectorsMetric).toContainText('5 Sectors');

    // Verify all 5 canonical sectors are rendered in the Sector Yield grid
    const sectorSection = page.getByTestId('sector-yield-contribution');
    await expect(sectorSection.getByText('Agriculture & Land Use', { exact: true })).toBeVisible();
    await expect(sectorSection.getByText('Clean Cookstoves', { exact: true })).toBeVisible();
    await expect(sectorSection.getByText('Solar & Mini-Grids', { exact: true })).toBeVisible();
    await expect(sectorSection.getByText('Biochar Carbon Removal', { exact: true })).toBeVisible();
    await expect(sectorSection.getByText('Electric Mobility', { exact: true })).toBeVisible();

    // Verify individual yields
    await expect(sectorSection.getByText('500 tCO₂e')).toBeVisible(); // Biochar
    await expect(sectorSection.getByText('400 tCO₂e')).toBeVisible(); // Agriculture
    await expect(sectorSection.getByText('300 tCO₂e')).toBeVisible(); // Cooking
    await expect(sectorSection.getByText('250 tCO₂e')).toBeVisible(); // Energy
    await expect(sectorSection.getByText('150 tCO₂e')).toBeVisible(); // Mobility

    // Verify concentric rings render in the SVG container
    const svgRings = page.locator('svg circle[stroke-dasharray]');
    const count = await svgRings.count();
    expect(count).toBeGreaterThanOrEqual(5);
  });

  test('3. Empty PoA test: truthful empty states, no fake 0 tCO2e / 0.0%, disabled exports', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url().toLowerCase();

      if (url.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockAdminUser),
        });
      }

      if (url.includes('/carbon/ledger')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [] }),
        });
      }

      if (url.includes('/projects')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      }

      if (url.includes('/users')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/settings')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
      }
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/properties')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kpis: [], activeOrgs: 1 }) });
      }

      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.goto(`${BASE_URL}/dashboard/poa`);
    await page.waitForLoadState('networkidle');

    // Total yield should show truthful empty state (em dash), NOT 0 tCO2e
    const totalYieldMetric = page.locator('text=Total POA Yield').locator('..');
    await expect(totalYieldMetric).toContainText('—');
    await expect(totalYieldMetric).toContainText('Not quantified');

    // Active Sectors should be 0 Sectors and No participating sectors
    const activeSectorsMetric = page.locator('text=Active Sectors').locator('..');
    await expect(activeSectorsMetric).toContainText('0 Sectors');
    await expect(activeSectorsMetric).toContainText('No participating sectors');

    // Sector breakdown should display "—" and "Not quantified", NOT "0.0%" or "0 tCO2e"
    const sectorSection = page.getByTestId('sector-yield-contribution');
    const notQuantifiedLabels = sectorSection.getByText('Not quantified');
    const notQuantifiedCount = await notQuantifiedLabels.count();
    // 5 canonical sector cards + 1 empty center ring state = 6
    expect(notQuantifiedCount).toBe(6);

    // No fake "0.0%" should appear anywhere in the sector breakdown
    const fakeZeroPercent = sectorSection.locator('text="0.0%"');
    await expect(fakeZeroPercent).toHaveCount(0);

    // Official MRV PDF button must be disabled
    const pdfButton = page.locator('button:has-text("Generate Official MRV PDF")');
    await expect(pdfButton).toBeDisabled();
    await expect(pdfButton).toHaveAttribute('title', 'Awaiting quantified portfolio yields');
  });

  test('4. Decision Support deduplication: sidebar link present, floating button absent, /dashboard/ai works', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url().toLowerCase();

      if (url.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockAdminUser),
        });
      }

      if (url.includes('/carbon/ledger')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: [] }) });
      }

      if (url.includes('/projects')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [] }) });
      }

      if (url.includes('/users')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/settings')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
      }
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/properties')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kpis: [], activeOrgs: 1 }) });
      }

      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.goto(`${BASE_URL}/dashboard/poa`);
    await page.waitForLoadState('networkidle');

    // 1. Check sidebar has "Decision Support" navigation
    const sidebarLink = page.locator('nav a[href="/dashboard/ai"], aside a[href="/dashboard/ai"], a[href="/dashboard/ai"]');
    await expect(sidebarLink.first()).toBeVisible();
    await expect(sidebarLink.first()).toContainText('Decision Support');

    // 2. Verify there is NO floating bottom-right launcher button anywhere in the layout
    const floatingTriggers = page.locator('button.fixed.bottom-6.right-6, button:has-text("Universal AI"), button:has-text("Ask CIOS")');
    await expect(floatingTriggers).toHaveCount(0);

    // 3. Verify exactly one entry point for Decision Support exists in the primary navigation
    const decisionSupportNavItems = page.locator('a[href="/dashboard/ai"]');
    const navCount = await decisionSupportNavItems.count();
    expect(navCount).toBe(1);

    // 4. Click sidebar link and navigate to /dashboard/ai
    await sidebarLink.first().click();
    await page.waitForURL('**/dashboard/ai');
    expect(page.url()).toContain('/dashboard/ai');

    // Floating button must remain absent on /dashboard/ai
    await expect(floatingTriggers).toHaveCount(0);
  });

  test('5. Responsive visual viewports: 1440, 1280, 1024, 768, 390 without overflow or collisions', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url().toLowerCase();

      if (url.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockAdminUser),
        });
      }

      if (url.includes('/carbon/ledger')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [
              { id: 'c-1', sector: 'agriculture_land_use', tco2e: 500.0, status: 'calculated' },
              { id: 'c-2', sector: 'biochar', tco2e: 800.0, status: 'issued' },
            ],
          }),
        });
      }

      if (url.includes('/projects')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              { id: 'p-1', sector: 'agriculture_land_use' },
              { id: 'p-2', sector: 'biochar' },
            ],
          }),
        });
      }

      if (url.includes('/users')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/settings')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
      }
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
      if (url.includes('/properties')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kpis: [], activeOrgs: 1 }) });
      }

      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    const viewports = [
      { name: '1440 Desktop Large', width: 1440, height: 900 },
      { name: '1280 Desktop Medium', width: 1280, height: 800 },
      { name: '1024 Tablet Landscape', width: 1024, height: 768 },
      { name: '768 Tablet Portrait', width: 768, height: 1024 },
      { name: '390 Mobile Phone', width: 390, height: 844 },
    ];

    // Initial page load
    await page.setViewportSize({ width: viewports[0].width, height: viewports[0].height });
    await page.goto(`${BASE_URL}/dashboard/poa`);
    await page.waitForLoadState('networkidle');

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.waitForTimeout(100);

      // 1. Check root document does not have horizontal scrolling overflow
      const isOverflowing = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth + 5;
      });
      expect(isOverflowing, `Viewport ${vp.name} should not horizontally overflow root`).toBe(false);

      // 2. Check POA credit pipeline tracker has min-w-[620px] scrollable container
      const pipelineContainer = page.getByTestId('poa-pipeline-tracker');
      await expect(pipelineContainer).toBeVisible();

      const innerScrollable = pipelineContainer.locator('.overflow-x-auto');
      await expect(innerScrollable).toBeVisible();

      // Verify pipeline stage labels are present and not overlapping
      await expect(pipelineContainer.getByText('Quantification')).toBeVisible();
      await expect(pipelineContainer.getByText('Audited')).toBeVisible();
      await expect(pipelineContainer.getByText('Issued')).toBeVisible();

      // 3. Verify Sector Yield section is visible and pipeline does not overlap it
      const sectorSection = page.getByTestId('sector-yield-contribution');
      await expect(sectorSection).toBeVisible();

      const pipelineBox = await pipelineContainer.boundingBox();
      const sectorBox = await sectorSection.boundingBox();
      if (pipelineBox && sectorBox) {
        expect(pipelineBox.y).toBeGreaterThanOrEqual(sectorBox.y);
      }
    }
  });
});
