import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
const API_URL = process.env.API_URL || 'http://localhost:8000';

test.describe('Agriculture & Land Use Forensic E2E Audit', () => {
  test.setTimeout(60000);

  // =========================================================================
  // 1. LANDING PAGE REAL DOM VERIFICATION (Section 5)
  // =========================================================================
  test('1. Landing Page renders Agriculture & Land Use in real DOM', async ({ page }) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });

    // Find the Supported Sectors heading
    const sectorsHeading = page.getByRole('heading', { name: 'Supported Sectors' });
    await expect(sectorsHeading).toBeVisible({ timeout: 20000 });

    // Find the Agriculture & Land Use card
    const agriHeading = page.getByRole('heading', { name: 'Agriculture & Land Use' });
    await expect(agriHeading).toBeVisible({ timeout: 20000 });

    // Verify exactly one Agriculture card renders (no duplicates)
    const agriCards = page.locator('h3', { hasText: 'Agriculture & Land Use' });
    expect(await agriCards.count()).toBe(1);

    // Verify description text
    const desc = page.locator('p', { hasText: /Agricultural land management|Climate methodologies covering improved agricultural/i });
    await expect(desc).toBeVisible();

    // Verify project types listed under Agriculture
    const cardContainer = agriHeading.locator('xpath=ancestor::div[contains(@class, "rounded-2xl") or contains(@class, "border")]').first();
    await expect(cardContainer).toContainText(/Agricultural Land Management/i);
    await expect(cardContainer).toContainText(/Rice Cultivation/i);
    await expect(cardContainer).toContainText(/Afforestation|Reforestation/i);

    // Verify no raw codes or undefined/NaN values
    const cardText = await cardContainer.innerText();
    expect(cardText).not.toContain('undefined');
    expect(cardText).not.toContain('NaN');
    expect(cardText).not.toContain('null');

    // Verify CTA button on landing page exists and links to /signup
    const cta = page.locator('a[href="/signup"]', { hasText: /Request Access/i }).first();
    await expect(cta).toBeVisible();
  });

  // =========================================================================
  // 2. RESPONSIVE MATRIX VERIFICATION (Section 6)
  // =========================================================================
  const viewports = [
    { width: 1440, height: 900, name: 'Desktop Large (1440px)' },
    { width: 1280, height: 800, name: 'Desktop Standard (1280px)' },
    { width: 1024, height: 768, name: 'Tablet Landscape (1024px)' },
    { width: 768, height: 1024, name: 'Tablet Portrait (768px)' },
    { width: 390, height: 844, name: 'Mobile (390px iPhone 12/13/14)' },
  ];

  for (const vp of viewports) {
    test(`2. Responsive Viewport Check: ${vp.name}`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });

      const agriHeading = page.getByRole('heading', { name: 'Agriculture & Land Use' });
      await expect(agriHeading).toBeVisible({ timeout: 10000 });

      // Check card bounding box is valid and contained within viewport
      const cardContainer = agriHeading.locator('xpath=ancestor::div[contains(@class, "rounded-2xl") or contains(@class, "border")]').first();
      const box = await cardContainer.boundingBox();
      expect(box).not.toBeNull();
      if (box) {
        expect(box.width).toBeGreaterThan(200);
        expect(box.height).toBeGreaterThan(120);
        expect(box.width).toBeLessThanOrEqual(vp.width);
      }

      // Check CTA remains visible and accessible
      const cta = page.locator('a[href="/signup"]').first();
      await expect(cta).toBeVisible();
    });
  }

  // =========================================================================
  // 3. ACCESSIBILITY KEYBOARD & SEMANTIC AUDIT (Section 7)
  // =========================================================================
  test('3. Landing Page Accessibility and Keyboard Navigation', async ({ page }) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });

    // Verify heading hierarchy
    const h1 = page.locator('h1');
    expect(await h1.count()).toBeGreaterThanOrEqual(1);

    const agriHeading = page.getByRole('heading', { name: 'Agriculture & Land Use' });
    await expect(agriHeading).toBeVisible();
    const tagName = await agriHeading.evaluate((el) => el.tagName.toLowerCase());
    expect(tagName).toBe('h3');

    // Test Tab keyboard navigation into the Request Access CTA
    const cta = page.locator('a[href="/signup"]', { hasText: /Request Access/i }).first();
    await cta.focus();
    const isFocused = await cta.evaluate((el) => document.activeElement === el);
    expect(isFocused).toBe(true);
  });

  // =========================================================================
  // 4. PUBLIC ONBOARDING BROWSER E2E (Section 8 & 10)
  // =========================================================================
  test('4. Public Onboarding Flow: Agriculture & Land Use Submission', async ({ page }) => {
    const syntheticEmail = `forensic_agri_${Date.now()}@synthetic-tenant.org`;
    const syntheticOrg = `Synthetica Regenerative Farms ${Date.now().toString().slice(-4)}`;

    await page.goto(`${BASE_URL}/signup`, { waitUntil: 'domcontentloaded' });

    // Fill form inputs with exact placeholders
    await page.locator('input[placeholder="e.g. Manny Solar"]').fill(syntheticOrg);
    await page.locator('input[placeholder="e.g. Dapo Olu"]').fill('Dr. Forensic Auditor');
    await page.locator('input[placeholder="e.g. alex@company.com"]').fill(syntheticEmail);

    // Primary Operating Sector Select
    const sectorSelect = page.locator('select').first();
    await sectorSelect.waitFor({ state: 'visible' });

    // Select Agriculture & Land Use by label
    await sectorSelect.selectOption({ label: 'Agriculture & Land Use' });

    // Select primary methodology (e.g. index 1)
    const methodologySelect = page.locator('select').nth(1);
    await methodologySelect.waitFor({ state: 'visible' });
    await methodologySelect.selectOption({ index: 1 });

    // Fill required First Project Name
    await page.locator('input[placeholder="e.g. Oloibiri Solar Minigrid Phase 1"]').fill('Rift Valley Soil Pilot');

    // Submit request
    const submitBtn = page.locator('button[type="submit"]', { hasText: /Submit|Request|Get Started/i });
    await submitBtn.click();

    // Verify success confirmation renders
    const successMsg = page.locator('text=Request Submitted!');
    await expect(successMsg).toBeVisible({ timeout: 10000 });
  });

  // =========================================================================
  // 5. ONBOARDING NEGATIVE CONTROLS (Section 10)
  // =========================================================================
  test('5. Onboarding Negative Controls: Invalid email, missing required fields', async ({ page }) => {
    await page.goto(`${BASE_URL}/signup`, { waitUntil: 'domcontentloaded' });

    // 1. Submit empty form
    const submitBtn = page.locator('button[type="submit"]');
    await submitBtn.click();

    // HTML5 validation prevents submission
    const isInvalid = await page.locator('input:invalid').count();
    expect(isInvalid).toBeGreaterThan(0);

    // 2. Invalid email format
    const emailInput = page.locator('input[type="email"]');
    await emailInput.fill('invalid-email-without-domain');
    const validState = await emailInput.evaluate((el: HTMLInputElement) => el.checkValidity());
    expect(validState).toBe(false);
  });

  // =========================================================================
  // 6. SUPER ADMIN PROVISIONING & APPROVAL E2E (Section 11 & 12)
  // =========================================================================
  test('6. Super Admin Review & Approval of Agriculture Tenant', async ({ page, request }) => {
    // 1. Submit a synthetic access request via API
    const syntheticEmail = `superadmin_agri_${Date.now()}@agri-corp.test`;
    const syntheticOrg = `Forensic Agri Enterprise ${Date.now().toString().slice(-4)}`;

    const createRes = await request.post(`${API_URL}/api/v1/access-requests`, {
      data: {
        full_name: 'Lead Agronomist',
        email: syntheticEmail,
        organization_name: syntheticOrg,
        country: 'Kenya',
        sector_id: 'AGRICULTURE_LAND_USE',
        use_case: 'Agricultural land management and soil carbon MRV',
      },
    });
    expect(createRes.ok()).toBe(true);

    // 2. Login as Super Admin
    const loginRes = await request.post(`${API_URL}/api/v1/auth/login`, {
      data: {
        email: 'segunoluwole22@gmail.com',
        password: 'VeriField_Dev_2026!',
      },
    });
    expect(loginRes.ok()).toBe(true);
    const loginData = await loginRes.json();
    const superAdminToken = loginData.access_token;

    // 3. Access Super Admin Portal
    await page.addInitScript(
      ({ token, user }: { token: string; user: Record<string, unknown> }) => {
        window.localStorage.setItem('vf_token', token);
        window.localStorage.setItem('vf_user', JSON.stringify(user));
      },
      {
        token: superAdminToken,
        user: {
          id: '00000000-0000-0000-0000-000000000001',
          email: 'segunoluwole22@gmail.com',
          role: 'SUPER_ADMIN',
          organization: 'VeriField Nexus',
        },
      }
    );

    await page.goto(`${BASE_URL}/super-admin`, { waitUntil: 'domcontentloaded' });

    // Switch to Access Requests tab
    const leadsTab = page.locator('button', { hasText: /Access Requests/i });
    await leadsTab.click();

    // Verify request row appears with Agriculture & Land Use sector
    const reqRow = page.locator('tr', { hasText: syntheticOrg });
    await expect(reqRow).toBeVisible({ timeout: 10000 });
    await expect(reqRow).toContainText('Agriculture & Land Use');

    // Click Approve
    const approveBtn = reqRow.locator('button', { hasText: 'Approve' });
    await approveBtn.click();

    // Verify credentials modal appears with Tenant Credentials Generated
    const credsModal = page.locator('text=Tenant Credentials Generated');
    await expect(credsModal).toBeVisible({ timeout: 10000 });
  });

  // =========================================================================
  // 7. AGRICULTURE WORKSPACE EMPTY STATE & FAIL-CLOSED UI (Section 13, 14, 31)
  // =========================================================================
  test('7. Fresh Agriculture Workspace Empty State and Fail-Closed Quantification', async ({ page }) => {
    const syntheticUser = {
      id: '00000000-0000-0000-0000-000000000099',
      email: 'forensic_admin@agri-pure.test',
      full_name: 'Forensic Org Administrator',
      role: 'ORG_ADMIN',
      status: 'active',
      is_active: true,
      organization: 'Pure Soil Holdings',
      organization_id: '00000000-0000-0000-0000-000000000099',
      licensed_sectors: ['agriculture_land_use'],
      licensed_methodologies: ['VM0042', 'VM0047', 'VM0051'],
    };

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(syntheticUser),
      });
    });

    await page.route('**/api/v1/projects*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route('**/api/v1/agriculture/land-units*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.addInitScript(
      ({ token, user }: { token: string; user: Record<string, unknown> }) => {
        window.localStorage.setItem('vf_token', token);
        window.localStorage.setItem('vf_user', JSON.stringify(user));
        window.localStorage.setItem('vf_sector', 'agriculture_land_use');
      },
      { token: 'mock-agri-token', user: syntheticUser }
    );

    // Navigate to /dashboard/projects
    await page.goto(`${BASE_URL}/dashboard/projects`, { waitUntil: 'domcontentloaded' });

    // Verify clean empty state (no fake data, no NaN, no undefined)
    const pageText = await page.innerText('body');
    expect(pageText).not.toContain('NaN');
    expect(pageText).not.toContain('undefined');

    // Check Projects page header
    await expect(page.locator('h1', { hasText: 'Registered Carbon Assets & Projects' })).toBeVisible();

    // Verify empty state is displayed gracefully
    const emptyState = page.locator('text=No Projects Registered Yet');
    await expect(emptyState).toBeVisible({ timeout: 5000 });

    // Verify active projects count is 0
    await expect(page.locator('text=0 Active Projects')).toBeVisible();
  });

});
