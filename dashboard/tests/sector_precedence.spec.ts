import { test, expect } from '@playwright/test';
import { resolveSectorWithPrecedence } from '../src/lib/moduleRegistry';

test.describe('Sector Canonicalization Precedence & Ambiguity Invariant Tests', () => {
  test('1. Explicit project.sector wins over compound display names', () => {
    const testCases = [
      {
        name: 'Solar Biochar Ventures',
        projectSector: 'biochar',
        expected: 'biochar',
      },
      {
        name: 'EV Agriculture Holdings',
        projectSector: 'agriculture_land_use',
        expected: 'agriculture_land_use',
      },
      {
        name: 'Hybrid Cookstove Energy',
        projectSector: 'cookstoves',
        expected: 'cookstoves',
      },
      {
        name: 'Biochar Mobility Ltd',
        projectSector: 'ev_mobility',
        expected: 'ev_mobility',
      },
    ];

    for (const tc of testCases) {
      const resolved = resolveSectorWithPrecedence({
        projectSector: tc.projectSector,
        displayNameFallback: tc.name,
      });
      expect(resolved).toBe(tc.expected);
    }
  });

  test('2. Ambiguous compound sector tokens fail closed to empty/neutral without guessing', () => {
    const ambiguousCases = [
      'Solar Biochar Ventures',
      'EV Agriculture Holdings',
      'Hybrid Cookstove Energy',
      'Biochar Mobility Ltd',
      'Acme Holdings Global',
    ];

    for (const name of ambiguousCases) {
      const res = resolveSectorWithPrecedence({
        displayNameFallback: name,
      });
      expect(res).toBe('');
    }
  });

  test('3. Single-sector clean display names resolve to canonical sector codes', () => {
    expect(resolveSectorWithPrecedence({ displayNameFallback: 'Acme Clean Cookstoves' })).toBe('cookstoves');
    expect(resolveSectorWithPrecedence({ displayNameFallback: 'Dammy Solar' })).toBe('hybrid_energy');
    expect(resolveSectorWithPrecedence({ displayNameFallback: 'Biochar Pyrolysis Facility' })).toBe('biochar');
  });
});
