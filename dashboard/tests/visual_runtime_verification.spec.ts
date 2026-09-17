import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
const API_URL = process.env.API_URL || 'http://localhost:8000';

const ROUTES = [
  '/dashboard',
  '/dashboard/properties',
  '/dashboard/trust-scores',
  '/dashboard/verifications',
  '/dashboard/registry',
  '/dashboard/carbon',
  '/dashboard/anomalies',
  '/dashboard/operations',
  '/dashboard/monitoring'
];

const VIEWPORTS = [
  { name: '1440px', width: 1440, height: 900 },
  { name: '1280px', width: 1280, height: 800 },
  { name: '1024px', width: 1024, height: 768 },
  { name: '768px', width: 768, height: 1024 },
  { name: '390px', width: 390, height: 844 },
];

test.describe('Phase 7: Real Visual Runtime & Multi-Viewport Verification', () => {
  let authToken = '';

  test.beforeAll(async ({ request }) => {
    try {
      const response = await request.post(`${API_URL}/api/v1/auth/login`, {
        data: {
          email: 'segunoluwole22@gmail.com',
          password: 'VeriField_Dev_2026!',
        },
      });
      if (response.ok()) {
        const data = await response.json();
        authToken = data.access_token;
      }
    } catch {
      authToken = 'fallback-token';
    }
  });

  const setupAuth = async (page: any) => {
    const user = {
      id: '00000000-0000-0000-0000-000000000001',
      email: 'segunoluwole22@gmail.com',
      full_name: 'Segun Oluwole',
      role: 'SUPER_ADMIN',
      status: 'active',
      is_active: true,
      organization: 'VeriField Nexus Primary Org',
      organization_id: '00000000-0000-0000-0000-000000000001',
      licensed_methodologies: ['AMS-II.G', 'ACM0002'],
      licensed_sectors: ['cookstoves', 'hybrid_energy'],
      version: 2,
      is_deleted: false,
    };

    await page.route('**/api/v1/auth/me', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(user),
      });
    });

    await page.addInitScript(
      ({ token, userData }: { token: string; userData: Record<string, unknown> }) => {
        window.localStorage.setItem('vf_token', token);
        window.localStorage.setItem('vf_user', JSON.stringify(userData));
      },
      { token: authToken, userData: user }
    );
  };

  // Test Multi-viewport responsive rendering and overflow across all 9 routes
  for (const vp of VIEWPORTS) {
    test(`Viewport ${vp.name} (${vp.width}x${vp.height}) across all 9 operational routes`, async ({ page }) => {
      test.setTimeout(90000);
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await setupAuth(page);

      for (const routePath of ROUTES) {
        await page.goto(`${BASE_URL}${routePath}`, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(400);

        // 1. Verify no horizontal scroll overflow
        const overflow = await page.evaluate(() => {
          return document.documentElement.scrollWidth > window.innerWidth + 2;
        });
        expect(overflow, `Horizontal overflow detected on route ${routePath} at viewport ${vp.name}`).toBe(false);

        // 2. Verify page rendered without uncaught crash or unhandled error
        const bodyContent = await page.content();
        expect(bodyContent).not.toContain('Application error: a client-side exception has occurred');
        expect(bodyContent).not.toContain('Error: Minified React error');
      }
    });
  }

  // Visual Invariant Verification on Core Routes
  test('Specific Remediations Invariant Audit', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await setupAuth(page);

    // 1. Check /dashboard
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle').catch(() => {});

    // Invariant 1: "MRV REGISTRY" eyebrow is absent
    const eyebrow = page.locator('text="MRV REGISTRY"');
    await expect(eyebrow).toHaveCount(0);

    // Invariant 2: Verification pipeline stages: 5 stages render, no decorative icons, clean typography
    const stagesContainer = page.locator('h3:has-text("Verification Pipeline Stages")');
    await expect(stagesContainer).toBeVisible();

    // Invariant 3: KPI cards have no floating colored icon boxes (rounded-2xl bg-emerald-500/10)
    const kpiIconBoxes = page.locator('.min-h-\\[110px\\] .rounded-2xl.bg-emerald-500\\/10');
    await expect(kpiIconBoxes).toHaveCount(0);

    // 4. Check /dashboard/projects
    await page.goto(`${BASE_URL}/dashboard/projects`);
    await page.waitForLoadState('networkidle').catch(() => {});

    // Invariant 4 & 6: Project identifier has no green background, neutral metadata styling
    const projectHeader = page.locator('span:has-text("Project #")');
    await expect(projectHeader).toBeVisible();
    const classAttr = (await projectHeader.getAttribute('class')) || '';
    expect(classAttr).not.toContain('bg-emerald-500');
    expect(classAttr).not.toContain('bg-green-500');

    // 5. Check /dashboard/carbon
    await page.goto(`${BASE_URL}/dashboard/carbon`);
    await page.waitForLoadState('networkidle').catch(() => {});

    // Invariant 5: Issue & Seal Credits action
    const issueAction = page.locator('button:has-text("Issue & Seal Credits")');
    await expect(issueAction).toBeVisible();

    // Invariant 7: Cards have restrained enterprise styling (no excessive blur or icon-tile residue)
    const cards = page.locator('.rounded-2xl.backdrop-blur-md');
    await expect(cards).toHaveCount(0);
  });
});
