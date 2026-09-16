import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('Puro Biochar 2025 V2 Value-Chain & Quantification E2E', () => {
  const user = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'segunoluwole22@gmail.com',
    full_name: 'Segun Oluwole',
    role: 'SUPER_ADMIN',
    status: 'active',
    is_active: true,
    organization: 'VeriField Nexus Primary Org',
    organization_id: '00000000-0000-0000-0000-000000000001',
    licensed_methodologies: ['VM0044', 'PURO_BIOCHAR_2025_V2'],
    licensed_sectors: ['biochar'],
    version: 2,
    is_deleted: false,
  };

  const mockMethodologies = [
    { id: '2', code: 'VM0044', name: 'Biochar Carbon Removal', sector: 'biochar', family_id: 'fam-biochar', ui_config: {} },
    { id: '3', code: 'PURO_BIOCHAR_2025_V2', name: 'Puro Biochar Edition 2025 V2', sector: 'biochar', family_id: 'fam-biochar', ui_config: {} },
  ];

  const mockFamilies = [
    { id: 'fam-biochar', code: 'BIOCHAR', name: 'Biochar Carbon Removal', methodologies: ['VM0044', 'PURO_BIOCHAR_2025_V2'] },
  ];

  const biocharDashboardPayload = {
    workspace: { code: 'BIOCHAR', name: 'Biochar Carbon Removal', badge: 'BIOCHAR' },
    methodology: { code: 'PURO_BIOCHAR_2025_V2', name: 'Puro Biochar Edition 2025 V2' },
    kpis: [
      { code: 'biochar_produced', label: 'BIOCHAR PRODUCED', value: '175 Tons', unit: 'Pyrolyzed biomass output', state: 'AVAILABLE' },
    ],
    charts: [],
    activities: [],
    activity_total: 0,
    asset_total: 0,
    assets: [],
  };

  const mockBatches = [
    {
      id: 'batch-001',
      project_id: '00000000-0000-0000-0000-000000000001',
      batch_number: 'BATCH-2026-001',
      facility_name: 'Alpha Pyrolysis Facility',
      kiln_id: 'KILN-01',
      feedstock_type: 'Agricultural Residues',
      feedstock_weight_tonnes: 300.0,
      biochar_yield_tonnes: 100.0,
      dry_mass_tonnes: 100.0,
      fixed_carbon_pct: 82.5,
      molar_h_c_ratio: 0.35,
      carbon_permanence_factor: 0.85,
      net_co2e_removed_tonnes: 211.45,
      quality_grade: 'PREMIUM_CORC200',
      status: 'VERIFIED',
      has_anomaly: false,
      mass_balance_allocated_tonnes: 0.0,
      mass_balance_status: 'AVAILABLE',
      created_at: '2026-09-10T10:00:00Z',
    }
  ];

  const mockQuantResult = {
    eligible_dry_biochar_mass_tonnes: 100.0,
    organic_carbon_pct: 82.5,
    molar_h_c: 0.35,
    soil_temperature_celsius: 15.0,
    persistence_fraction_pf: 0.74,
    regression_m: -0.0052,
    regression_a: 0.818,
    durability_class: 'CORC200+',
    c_stored_tco2e: 302.5,
    c_baseline_tco2e: 0.0,
    c_loss_tco2e: 78.65,
    e_project_tco2e: 12.4,
    e_leakage_tco2e: 0.0,
    net_corcs_calculated: 211.45,
    combined_uncertainty_pct: 4.82,
    deductible_uncertainty_pct: 0.0,
    final_corcs_issuable: 211.45,
    reported_uncertainty_text: '211.450 ± 4.8%',
    calculation_mode: 'AUTHORITATIVE',
    calculation_status: 'SUCCESS',
    corc_point_status: 'REACHED',
    calculation_hash: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
    methodology_version: 'PURO_BIOCHAR_EDITION_2025_V2',
    coefficient_version: 'TABLE_6_1_LEMBRECHTS_2022',
    engine_version: '2.0.0',
    timestamp: '2026-09-16T15:00:00Z',
    rule_references: ['PURO_3_5_1', 'PURO_6_1'],
    warnings: [],
  };

  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url().toLowerCase();
      if (url.includes('/auth/me')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) });
      }
      if (url.includes('/methodologies')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockMethodologies) });
      }
      if (url.includes('/methodology-families') || url.includes('/families')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFamilies) });
      }
      if (url.includes('/quantification') || url.includes('/simulate-quantification')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockQuantResult) });
      }
      if (url.includes('/biochar/batches')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockBatches) });
      }
      if (url.includes('/biochar/puro/rules')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 'R1', rule_code: 'PURO_3_5_1', rule_name: 'Molar H/Corg Ratio Limit', category: 'ELIGIBILITY', description: 'Strict limit H/Corg < 0.70', is_active: true }
          ])
        });
      }
      if (url.includes('/biochar/puro/end-use-categories')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 'cat-1', category_code: 'AF1', sector: 'Agriculture', product_name: 'Soil Amendment', eligible_for_corc: true, is_active: true }
          ])
        });
      }
      if (url.includes('/dashboard')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(biocharDashboardPayload) });
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.addInitScript(
      ({ userData }: { userData: Record<string, unknown> }) => {
        window.localStorage.setItem('vf_token', 'valid-mock-token');
        window.localStorage.setItem('vf_user', JSON.stringify(userData));
        window.localStorage.setItem('vf_workspace_00000000-0000-0000-0000-000000000001', 'biochar');
      },
      { userData: user }
    );
  });

  test('1. Biochar workspace activates Biochar Operations & Value Chain with all 6 value chain tabs', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard?workspace=biochar`, { waitUntil: 'domcontentloaded' });

    // Wait for the Biochar tab to be present
    const biocharTab = page.locator('button:has-text("Biochar Operations & Value Chain")');
    await expect(biocharTab).toBeVisible({ timeout: 15000 });

    // Sub-navigation should contain all 6 value-chain stages
    await expect(page.locator('button:has-text("Biochar Batches & Lab")')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('button:has-text("Feedstock Lots")')).toBeVisible();
    await expect(page.locator('button:has-text("Production Runs")')).toBeVisible();
    await expect(page.locator('button:has-text("Mass Balance Ledger")')).toBeVisible();
    await expect(page.locator('button:has-text("Chain of Custody Trace")')).toBeVisible();
    await expect(page.locator('button:has-text("Puro 2025 V2")')).toBeVisible();
  });

  test('2. Puro 2025 V2 Methodology tab renders normative rules, readiness gate and executes quantification', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard?workspace=biochar`, { waitUntil: 'domcontentloaded' });

    // Click into Puro 2025 V2 tab
    const puroTabBtn = page.locator('button:has-text("Puro 2025 V2")');
    await expect(puroTabBtn).toBeVisible({ timeout: 15000 });
    await puroTabBtn.click();

    // Verify Methodology Header & Badge
    await expect(page.getByText('Puro.earth Biochar Edition 2025 V2').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Approved 27 Nov 2025')).toBeVisible();
    await expect(page.getByText('Normative Methodology Alignment & CORC Verification')).toBeVisible();

    // Verify Invariant cards
    await expect(page.getByText('Crediting Period', { exact: true })).toBeVisible();
    await expect(page.getByText('10 years initial duration')).toBeVisible();
    await expect(page.getByText('Methodology Persistence', { exact: true })).toBeVisible();

    // Verify Quantification Console
    await expect(page.getByText('Deterministic CORC Quantification Console')).toBeVisible();
    const execBtn = page.locator('button:has-text("Execute Authoritative Quantification")');
    await expect(execBtn).toBeVisible();

    // Execute Authoritative Quantification
    await execBtn.click();

    // Verify calculation results render with CORC200+ durability class
    await expect(page.getByText('CORC200+').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('211.450').first()).toBeVisible({ timeout: 10000 });
  });
});
