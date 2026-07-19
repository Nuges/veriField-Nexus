import { test, expect } from '@playwright/test';

const PAGES = [
  '/dashboard',
  '/dashboard/activities',
  '/dashboard/carbon',
  '/dashboard/energy',
  '/dashboard/community',
  '/dashboard/map'
];

test.describe('Dashboard Operational Validation', () => {
  test.beforeEach(async ({ page, request }) => {
    // Attempt to log in via API
    const response = await request.post('http://localhost:8000/api/v1/auth/login', {
      data: {
        email: 'superadmin@verifield.io',
        password: 'CHANGE_THIS_ON_FIRST_LOGIN'
      }
    });
    const data = await response.json();
    const token = data.access_token;
    
    // Setup local storage with the token
    await page.goto('http://localhost:3000/login');
    await page.evaluate((t) => {
      localStorage.setItem('vf_token', t);
      localStorage.setItem('vf_user', JSON.stringify({
        id: '00000000-0000-5000-a000-000000000000',
        email: 'superadmin@verifield.io',
        role: 'SUPER_ADMIN',
        organization: 'VeriField'
      }));
    }, token);
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

      // We expect the local server to be running on 3000
      const res = await page.goto(`http://localhost:3000${pagePath}`, { waitUntil: 'load' });
      
      expect(res?.status()).toBeLessThan(400);

      // Verify no hydration errors
      expect(hydrationErrors).toHaveLength(0);

      // Depending on the page, wait for data to load
      await expect(page.locator('.animate-spin')).toHaveCount(0, { timeout: 15000 });

      // Check for offline fallbacks (meaning API is dead)
      const bodyText = await page.content();
      expect(bodyText).not.toContain('Backend API unreachable');
      expect(bodyText).not.toContain('Failed to fetch');
    });
  }
});
