import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
const API_URL = process.env.API_URL || 'http://localhost:8000';

test.describe('PWA Offline-First Telemetry Ingestion & PostgreSQL Sync E2E', () => {
  let authToken = '';

  test.beforeAll(async ({ request }) => {
    const response = await request.post(`${API_URL}/api/v1/auth/login`, {
      data: {
        email: 'segunoluwole22@gmail.com',
        password: 'VeriField_Dev_2026!',
      },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    authToken = data.access_token;
  });

  test.beforeEach(async ({ context }) => {
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 9.0765, longitude: 7.3986 });
  });

  const setupAuth = async (page: any) => {
    const user = {
      id: '00000000-0000-0000-0000-000000000001',
      email: 'segunoluwole22@gmail.com',
      full_name: 'Audited Administrator',
      role: 'SUPER_ADMIN',
      status: 'active',
      is_active: true,
      organization: 'VeriField Nexus Primary Org',
      organization_id: '00000000-0000-0000-0000-000000000001',
      licensed_methodologies: ['AMS-II.G', 'C-Sink'],
      licensed_sectors: ['cookstoves', 'biochar'],
      version: 2,
      is_deleted: false,
    };

    await page.addInitScript(
      ({ token, userData }: { token: string; userData: Record<string, unknown> }) => {
        window.localStorage.setItem('vf_token', token);
        window.localStorage.setItem('vf_user', JSON.stringify(userData));
      },
      { token: authToken, userData: user }
    );
  };

  test('PWA Online Submission creates verified PostgreSQL record', async ({ page, request }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/capture`);

    // Ensure capture form is visible
    await expect(page.locator('text=PWA COLLECTOR')).toBeVisible();
    await expect(page.locator('text=ONLINE')).toBeVisible();

    const uniqueAsset = `STOVE-ONLINE-${Date.now()}`;
    await page.fill('input[placeholder*="STOVE-9042"]', uniqueAsset);
    await page.fill('input[placeholder*="4.5"]', '5.5');
    await page.fill('textarea[placeholder*="Observed installation"]', 'Online E2E ingestion verification');

    await page.click('button[type="submit"]');

    // Verification of submission success
    await expect(page.locator('text=Telemetry Logged Successfully')).toBeVisible({ timeout: 15000 });
    const recordIdText = await page.locator('text=Record ID:').textContent();
    expect(recordIdText).toBeTruthy();
    const createdId = recordIdText?.replace('Record ID:', '').trim() || '';

    // Verify directly in backend API / PostgreSQL
    const getRes = await request.get(`${API_URL}/api/v1/activities/${createdId}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(getRes.ok()).toBeTruthy();
    const dbRecord = await getRes.json();
    expect(dbRecord.activity_data.asset_identifier).toBe(uniqueAsset);
    expect(dbRecord.activity_data.metric_quantity).toBe(5.5);
  });

  test('PWA Offline Mode queues locally, survives reload, syncs to DB, and deduplicates client_id', async ({
    page,
    request,
  }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/capture`);
    await expect(page.locator('text=PWA COLLECTOR')).toBeVisible();

    // 1. Enter Offline Mode via browser navigator.onLine mock and event
    await page.evaluate(() => {
      Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
      window.dispatchEvent(new Event('offline'));
    });

    // Verify Offline Banner is displayed
    const offlineBanner = page.locator('[data-testid="pwa-offline-banner"]');
    await expect(offlineBanner).toBeVisible({ timeout: 5000 });

    // 2. Submit record while offline
    const offlineAsset = `STOVE-OFFLINE-${Date.now()}`;
    await page.fill('input[placeholder*="STOVE-9042"]', offlineAsset);
    await page.fill('input[placeholder*="4.5"]', '7.2');
    await page.fill('textarea[placeholder*="Observed installation"]', 'Field collection in air-gapped site');

    await page.click('button[type="submit"]');

    // Confirmation of local queuing
    await expect(page.locator('text=Telemetry Logged Successfully')).toBeVisible();

    // Verify localStorage has the queued record
    const queueData1 = await page.evaluate(() => {
      const q = localStorage.getItem('verifield_pwa_offline_queue');
      return q ? JSON.parse(q) : [];
    });
    expect(queueData1.length).toBe(1);
    expect(queueData1[0].activity_data.asset_identifier).toBe(offlineAsset);
    const queuedClientId = queueData1[0].client_id;
    expect(queuedClientId).toBeTruthy();

    // Click "Log Another Record"
    await page.click('button:has-text("Log Another Record")');

    // Verify Queue Banner is visible with 1 record
    const queueBanner = page.locator('[data-testid="pwa-queue-banner"]');
    await expect(queueBanner).toBeVisible();
    await expect(queueBanner).toContainText('1 record(s) queued locally');

    // 3. Reload while still offline to test persistence
    await page.reload();
    await page.evaluate(() => {
      Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
      window.dispatchEvent(new Event('offline'));
    });

    await expect(page.locator('[data-testid="pwa-offline-banner"]')).toBeVisible();
    const queueBannerAfterReload = page.locator('[data-testid="pwa-queue-banner"]');
    await expect(queueBannerAfterReload).toBeVisible();
    await expect(queueBannerAfterReload).toContainText('1 record(s) queued locally');

    // 4. Restore Online Connectivity
    await page.evaluate(() => {
      Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
      window.dispatchEvent(new Event('online'));
    });

    // Offline banner should disappear
    await expect(page.locator('[data-testid="pwa-offline-banner"]')).toHaveCount(0);

    // Sync button should now be enabled
    const syncButton = page.locator('[data-testid="pwa-sync-button"]');
    await expect(syncButton).toBeEnabled();

    // 5. Trigger Sync
    await syncButton.click();

    // Queue banner should disappear once emptied
    await expect(page.locator('[data-testid="pwa-queue-banner"]')).toHaveCount(0, { timeout: 10000 });

    const queueDataAfterSync = await page.evaluate(() => {
      const q = localStorage.getItem('verifield_pwa_offline_queue');
      return q ? JSON.parse(q) : [];
    });
    expect(queueDataAfterSync.length).toBe(0);

    // 6. Verify record is in PostgreSQL via backend
    const searchRes = await request.get(`${API_URL}/api/v1/activities?limit=10`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(searchRes.ok()).toBeTruthy();
    const searchData = await searchRes.json();
    const activitiesList = searchData.activities || [];
    const syncedActivity = activitiesList.find(
      (a: any) => a.activity_data?.asset_identifier === offlineAsset || a.client_id === queuedClientId
    );
    expect(syncedActivity).toBeTruthy();
    expect(syncedActivity.client_id).toBe(queuedClientId);
    const syncedDbId = syncedActivity.id;

    // 7. Client ID Deduplication Test: Re-submit same client_id payload directly
    const duplicateRes = await request.post(`${API_URL}/api/v1/activities`, {
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        client_id: queuedClientId,
        activity_type: 'stove_usage',
        latitude: 9.0765,
        longitude: 7.3986,
        captured_at: new Date().toISOString(),
        activity_data: {
          asset_identifier: offlineAsset,
          metric_quantity: 7.2,
          sector: 'cookstoves',
        },
      },
    });

    expect(duplicateRes.ok()).toBeTruthy();
    const dedupResult = await duplicateRes.json();
    // Server must return existing record ID, not create a new one
    expect(dedupResult.id).toBe(syncedDbId);
  });

  test('PWA Multi-Sector Ingestion: Biochar Pyrolysis batch telemetry', async ({ page, request }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/capture`);

    // Switch to Biochar
    await page.click('button:has-text("Biochar Carbon Removal")');

    const biocharAsset = `PYRO-KILN-${Date.now()}`;
    await page.fill('input[placeholder*="STOVE-9042"]', biocharAsset);
    await page.fill('input[placeholder*="4.5"]', '1250');
    await page.fill('textarea[placeholder*="Observed installation"]', 'Puro-compliant continuous pyrolysis run');

    await page.click('button[type="submit"]');

    await expect(page.locator('text=Telemetry Logged Successfully')).toBeVisible({ timeout: 15000 });
    const recordIdText = await page.locator('text=Record ID:').textContent();
    const createdId = recordIdText?.replace('Record ID:', '').trim() || '';

    // Verify in backend
    const getRes = await request.get(`${API_URL}/api/v1/activities/${createdId}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(getRes.ok()).toBeTruthy();
    const dbRecord = await getRes.json();
    expect(dbRecord.activity_type).toBe('production_batch');
    expect(dbRecord.activity_data.sector).toBe('biochar');
    expect(dbRecord.activity_data.metric_quantity).toBe(1250);
  });
});
