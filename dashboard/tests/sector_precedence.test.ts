import { strict as assert } from 'assert';
import { resolveSectorWithPrecedence } from '../src/lib/moduleRegistry';

// Test 1: Explicit project.sector wins over compound display names
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
  assert.equal(
    resolved,
    tc.expected,
    `Failed for ${tc.name}: expected explicit ${tc.expected}, got ${resolved}`
  );
}

// Test 2: Unresolved compound ambiguous names without explicit sector resolve to neutral/empty
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
  // Ambiguous compound sector tokens must NOT arbitrarily guess a single sector
  assert.equal(
    res,
    '',
    `Failed for ambiguous name ${name}: expected empty/neutral, got ${res}`
  );
}

// Test 3: Controlled valid single-sector names with no conflicting tokens
assert.equal(
  resolveSectorWithPrecedence({ displayNameFallback: 'Acme Clean Cookstoves' }),
  'cookstoves'
);
assert.equal(
  resolveSectorWithPrecedence({ displayNameFallback: 'Dammy Solar' }),
  'hybrid_energy'
);
assert.equal(
  resolveSectorWithPrecedence({ displayNameFallback: 'Biochar Pyrolysis Facility' }),
  'biochar'
);

console.log('All sector precedence and ambiguity tests passed successfully!');
