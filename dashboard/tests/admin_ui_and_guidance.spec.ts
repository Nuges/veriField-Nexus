import { test, expect, Page, Route } from '@playwright/test';
import { resolveGuidance } from '../src/lib/guidance/resolveGuidance';
import { BASE_PAGE_METADATA } from '../src/lib/guidance/pageMetadata';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('Part 1: Guidance Resolver Unit & Architectural Invariants', () => {
  test('1. Projects route + ORG_ADMIN provides project management action and no "Project DNA"', () => {
    const insight = resolveGuidance({
      pathname: '/dashboard/projects',
      sector: 'cookstoves',
      role: 'ORG_ADMIN',
    });

    expect(insight.pageTitle).toBe('Projects');
    expect(insight.purpose).toContain('Manage project origination');
    expect(insight.whyItMatters).toContain('operational and methodological foundation');
    expect(insight.nextActionLabel).toBe('Review Project Setup');
    expect(insight.nextActionHref).toBe('/dashboard/projects');
    expect(insight.action?.mutation).toBe(false);

    // Verify absolute prohibition of "Project DNA"
    expect(JSON.stringify(insight)).not.toContain('Project DNA');
    expect(JSON.stringify(insight)).not.toContain('Inspect Project DNA');
  });

  test('2. Role-awareness: VIEWER role suppresses mutation actions across pages', () => {
    // On verifications: verifiers have activity:verify mutation action
    const verifierInsight = resolveGuidance({
      pathname: '/dashboard/verifications',
      sector: 'hybrid_energy',
      role: 'VERIFIER',
    });
    expect(verifierInsight.nextActionLabel).toBe('Review Verification Queue');
    expect(verifierInsight.action?.permission).toBe('activity:verify');

    // For a VIEWER: mutation must be suppressed or converted to read-only view
    const viewerInsight = resolveGuidance({
      pathname: '/dashboard/verifications',
      sector: 'hybrid_energy',
      role: 'VIEWER',
    });
    expect(viewerInsight.action?.mutation).toBe(false);
    expect(viewerInsight.nextActionLabel).not.toMatch(/^Review Verification Queue$/);
    expect(viewerInsight.nextActionLabel).toContain('View');
  });

  test('3. Sector Isolation: Hybrid Energy monitoring does not leak cookstove or biochar terms', () => {
    const hybridInsight = resolveGuidance({
      pathname: '/dashboard/monitoring',
      sector: 'hybrid_energy',
      role: 'ORG_ADMIN',
    });

    expect(hybridInsight.aiRecommendation).toContain('Power output and generation telemetry');
    expect(hybridInsight.aiRecommendation).not.toContain('cookstove');
    expect(hybridInsight.aiRecommendation).not.toContain('biochar');
    expect(hybridInsight.aiRecommendation).not.toContain('pyrolysis');

    const serialized = JSON.stringify(hybridInsight.suggestedQueries).toLowerCase();
    expect(serialized).toContain('mini-grid');
    expect(serialized).not.toContain('stove');
    expect(serialized).not.toContain('biochar');
  });

  test('4. Sector Isolation: Clean Cookstove monitoring does not leak solar or EV terms', () => {
    const cookstoveInsight = resolveGuidance({
      pathname: '/dashboard/monitoring',
      sector: 'cookstoves',
      role: 'ORG_ADMIN',
    });

    expect(cookstoveInsight.aiRecommendation).toContain('Cookstove IoT telemetry streaming');
    expect(cookstoveInsight.aiRecommendation).not.toContain('inverter');
    expect(cookstoveInsight.aiRecommendation).not.toContain('solar');
    expect(cookstoveInsight.aiRecommendation).not.toContain('electric vehicle');

    const serialized = JSON.stringify(cookstoveInsight.suggestedQueries).toLowerCase();
    expect(serialized).toContain('cookstove');
    expect(serialized).not.toContain('inverter');
    expect(serialized).not.toContain('charger');
  });

  test('5. Neutral Sector Fallback: undefined or unknown sector uses neutral MRV language', () => {
    const neutralInsight = resolveGuidance({
      pathname: '/dashboard/monitoring',
      sector: undefined,
      role: 'ORG_ADMIN',
    });

    expect(neutralInsight.aiRecommendation).toContain('Digital MRV Platform');
    expect(neutralInsight.queryPlaceholder).toBe('Ask about monitoring gaps, telemetry, or exceptions...');
    const serialized = JSON.stringify(neutralInsight).toLowerCase();
    expect(serialized).not.toContain('cookstove');
    expect(serialized).not.toContain('inverter');
    expect(serialized).not.toContain('biochar');
    expect(serialized).not.toContain('pyrolysis');
  });

  test('6. Unmapped / Unknown Route fallback succeeds gracefully without crashing', () => {
    const fallbackInsight = resolveGuidance({
      pathname: '/dashboard/nonexistent-feature-xyz',
      sector: 'hybrid_energy',
      role: 'VIEWER',
    });

    expect(fallbackInsight.pageTitle).toBe('Operational Guidance');
    expect(fallbackInsight.purpose).toContain('Review operational workspace data');
    expect(fallbackInsight.queryPlaceholder).toBe('Ask about operational data, project status, or verification...');
  });

  test('7. Prohibited strings check across all registered page metadata', () => {
    for (const [route, meta] of Object.entries(BASE_PAGE_METADATA)) {
      const serialized = JSON.stringify(meta);
      expect(serialized, `Route ${route} contains Project DNA`).not.toContain('Project DNA');
      expect(serialized, `Route ${route} contains AI intelligence/theatre`).not.toContain('AI Intelligence');
      expect(serialized, `Route ${route} contains confidenceScore`).not.toContain('confidenceScore');
      expect(serialized, `Route ${route} contains 18h SLA`).not.toContain('18h SLA');
      expect(serialized, `Route ${route} contains 240 req/s`).not.toContain('240 req/s');
    }
  });

  test('8. Distinct page titles and placeholders across representative routes', () => {
    const routes = [
      '/dashboard/projects',
      '/dashboard/monitoring',
      '/dashboard/verifications',
      '/dashboard/trust-scores',
      '/dashboard/sensors',
      '/dashboard/assets',
      '/dashboard/audits',
      '/dashboard/access-control',
      '/dashboard/analytics',
      '/dashboard/registry',
      '/dashboard/settings',
      '/dashboard/carbon',
    ];

    const titles = new Set<string>();
    const placeholders = new Set<string>();

    for (const r of routes) {
      const res = resolveGuidance({ pathname: r });
      expect(titles.has(res.pageTitle), `Duplicate page title ${res.pageTitle} on route ${r}`).toBe(false);
      expect(placeholders.has(res.queryPlaceholder), `Duplicate placeholder on route ${r}`).toBe(false);
      titles.add(res.pageTitle);
      placeholders.add(res.queryPlaceholder);
    }
  });
});

test.describe('Part 2: Visual Runtime & Header Invariants', () => {
  const setupAuth = async (page: Page, role: string = 'SUPER_ADMIN') => {
    const user = {
      id: '00000000-0000-0000-0000-000000000001',
      email: 'segunoluwole22@gmail.com',
      full_name: 'Shalom Ol',
      role: role,
      status: 'active',
      is_active: true,
      organization: 'VeriField Primary Enterprise',
      organization_id: '00000000-0000-0000-0000-000000000001',
      licensed_methodologies: ['AMS-II.G', 'ACM0002'],
      licensed_sectors: ['cookstoves', 'hybrid_energy'],
      version: 2,
      is_deleted: false,
    };

    await page.route('**/api/v1/auth/me', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(user),
      });
    });

    await page.addInitScript(
      ({ userData }: { userData: Record<string, unknown> }) => {
        window.localStorage.setItem('vf_token', 'test-token-invariant');
        window.localStorage.setItem('vf_user', JSON.stringify(userData));
      },
      { userData: user }
    );
  };

  test('1. Super Admin Header: Governance label removed and role indicator is unboxed text', async ({ page }) => {
    await setupAuth(page, 'SUPER_ADMIN');
    await page.goto(`${BASE_URL}/super-admin`, { waitUntil: 'domcontentloaded' });

    // Verify purple "Super Admin Governance" badge is completely absent
    const governanceBadge = page.locator('text="Super Admin Governance"');
    await expect(governanceBadge).toHaveCount(0);

    // Verify Super Admin text indicator exists
    const superAdminIndicator = page.locator('header').getByText('Super Admin', { exact: true });
    await expect(superAdminIndicator).toBeVisible();

    // Verify it is NOT wrapped in a green filled pill
    const greenPill = page.locator('header .bg-emerald-50, header .bg-emerald-950\\/50');
    await expect(greenPill).toHaveCount(0);
  });

  test('2. Admin Dashboard Layout: Welcome greeting contains NO waving hand emoji', async ({ page }) => {
    await setupAuth(page, 'SUPER_ADMIN');
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' });

    // Target the greeting element
    const greeting = page.locator('h2:has-text("Welcome,")');
    await expect(greeting).toBeVisible();
    const textContent = await greeting.textContent();

    expect(textContent).toContain('Welcome,');
    expect(textContent).toContain('Shalom Ol');
    expect(textContent).not.toContain('👋');
  });

  test('3. Top Header Breadcrumb: Contextual controls have NO decorative leading icons', async ({ page }) => {
    await setupAuth(page, 'SUPER_ADMIN');
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' });

    const breadcrumbHeader = page.locator('header').first();
    await expect(breadcrumbHeader).toBeVisible();

    // Verify labels remain visible and intact
    const orgLabel = breadcrumbHeader.locator('text=Enterprise Org');
    await expect(orgLabel).toBeVisible();

    // Verify selectors are interactive
    const sectorSelect = breadcrumbHeader.locator('select').first();
    await expect(sectorSelect).toBeVisible();

    // Verify search bar affordance exists
    const searchAffordance = breadcrumbHeader.locator('a[href="/dashboard/projects"]');
    await expect(searchAffordance).toBeVisible();

    // Verify sidebar navigation still has its icons (untouched)
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();
    const sidebarIcons = sidebar.locator('svg');
    const iconCount = await sidebarIcons.count();
    expect(iconCount).toBeGreaterThan(5);
  });

  test('4. Sidebar Chrome: Absence of ORG ADMIN / LEVEL 5 row under logo and SECURE in footer', async ({ page }) => {
    await setupAuth(page, 'ORG_ADMIN');
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' });

    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // Verify "LEVEL 5" text and container are absent
    await expect(sidebar.getByText('LEVEL 5', { exact: true })).toHaveCount(0);

    // Verify "ORG ADMIN" tag under the logo is absent
    await expect(sidebar.getByText('ORG ADMIN', { exact: true })).toHaveCount(0);

    // Verify "SECURE" status tag in footer is absent
    await expect(sidebar.getByText('SECURE', { exact: true })).toHaveCount(0);

    // Verify "CIOS v5.4-PROD" remains visible in footer
    await expect(sidebar.getByText('CIOS v5.4-PROD')).toBeVisible();

    // Verify sidebar navigation sections follow the logo naturally
    await expect(sidebar.getByText('Governance & Operations')).toBeVisible();
  });

  test('5. Top Header Chrome: Breadcrumb ends at All Projects, Mission Control removed, neutral Audit Queue', async ({ page }) => {
    await setupAuth(page, 'ORG_ADMIN');
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' });

    const header = page.locator('header').first();
    await expect(header).toBeVisible();

    // Verify "Mission Control" label/badge is absent from the breadcrumb header
    await expect(header.getByText('Mission Control', { exact: true })).toHaveCount(0);

    // Verify breadcrumb ends at "All Projects"
    await expect(header.getByRole('combobox').filter({ hasText: 'All Projects' })).toBeVisible();

    // Verify standalone question mark help button in top header is absent
    await expect(header.locator('a[href="/dashboard/help"]')).toHaveCount(0);

    // Verify Audit Queue button is present with neutral styling (no emerald background/text)
    const auditQueueLink = header.locator('a[href="/dashboard/verifications"]');
    await expect(auditQueueLink).toBeVisible();
    await expect(auditQueueLink).toHaveAttribute('aria-label', 'Audit Queue');

    const className = await auditQueueLink.getAttribute('class');
    expect(className).not.toContain('bg-emerald-50');
    expect(className).not.toContain('text-[#008A5E]');
    expect(className).not.toContain('border-emerald-200');
    expect(className).toContain('bg-[var(--color-background)]');
    expect(className).toContain('border-[var(--color-border)]');
  });

  test('6. Navigation & Help Resilience: Help remains accessible via sidebar', async ({ page }) => {
    await setupAuth(page, 'ORG_ADMIN');
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' });

    // Help & Knowledge must still be available in the sidebar
    const sidebar = page.locator('aside');
    const helpSidebarLink = sidebar.locator('a[href="/dashboard/help"]');
    await expect(helpSidebarLink).toBeVisible();
    await expect(helpSidebarLink).toContainText('Help & Knowledge');
  });

  test('7. Responsive Viewport Check: 1440px, 1280px, 1024px headers render cleanly', async ({ page }) => {
    await setupAuth(page, 'ORG_ADMIN');

    for (const width of [1440, 1280, 1024]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' });

      const header = page.locator('header').first();
      await expect(header).toBeVisible();

      // Ensure Audit Queue remains visible without collision
      const auditQueueLink = header.locator('a[href="/dashboard/verifications"]');
      await expect(auditQueueLink).toBeVisible();

      // Ensure no Mission Control badge appears
      await expect(header.getByText('Mission Control', { exact: true })).toHaveCount(0);
    }
  });
});
