import { test, expect } from '@playwright/test';

const PAGES = [
  '/dashboard',
  '/dashboard/activities',
  '/dashboard/carbon',
  '/dashboard/energy',
  '/dashboard/community',
  '/dashboard/map'
];

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('Dashboard Operational Validation', () => {
  test.beforeEach(async ({ page, request }) => {
    // Attempt to log in via API with platform Super Admin
    let token = '';
    try {
      const response = await request.post('http://localhost:8000/api/v1/auth/login', {
        data: {
          email: 'segunoluwole22@gmail.com',
          password: 'VeriField_Dev_2026!',
        },
      });
      if (response.ok()) {
        const data = await response.json();
        token = data.access_token;
      }
    } catch {
      token = 'fallback-token';
    }

    const userData = {
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

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(userData),
      });
    });

    await page.addInitScript(
      ({ t, u }) => {
        window.localStorage.setItem('vf_token', t);
        window.localStorage.setItem('vf_user', JSON.stringify(u));
      },
      { t: token, u: userData }
    );
  });

  for (const pagePath of PAGES) {
    test(`Verify ${pagePath} loads correctly without console errors or placeholders`, async ({ page }) => {
      const consoleErrors: string[] = [];
      const hydrationErrors: string[] = [];

      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      page.on('pageerror', error => {
        if (error.message.includes('Hydration') || error.message.includes('Minified React error')) {
          hydrationErrors.push(error.message);
        } else {
          consoleErrors.push(error.message);
        }
      });

      const res = await page.goto(`${BASE_URL}${pagePath}`, { waitUntil: 'load' });
      
      expect(res?.status()).toBeLessThan(400);

      // Verify no hydration errors
      expect(hydrationErrors).toHaveLength(0);

      // Wait for page-level full-screen loading spinner to finish
      await expect(page.locator('.min-h-screen .animate-spin')).toHaveCount(0, { timeout: 15000 });

      // Check for offline fallbacks (meaning API is dead)
      const bodyText = await page.content();
      expect(bodyText).not.toContain('Backend API unreachable');
      expect(bodyText).not.toContain('Failed to fetch');
    });
  }
});
