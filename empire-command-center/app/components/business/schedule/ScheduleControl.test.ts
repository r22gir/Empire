import test from 'node:test';
import assert from 'node:assert/strict';
import { formatInches } from '../../../lib/formatInches';
import { PRESET_PARTIES, COMMON_ITEMS, PartySuggestion } from './ScheduleControl';

export function extractJobItems(job: any): string[] {
  const itemsSet = new Set<string>();
  if (job) {
    if (Array.isArray(job.items)) {
      job.items.forEach((it: string) => itemsSet.add(it));
    }
    if (Array.isArray(job.quote_lines)) {
      job.quote_lines.forEach((ql: string) => itemsSet.add(ql));
    }
    if (job.title) {
      itemsSet.add(job.title);
    }
  }
  COMMON_ITEMS.forEach((it) => itemsSet.add(it));
  return Array.from(itemsSet);
}

export function autoFillFromJob(jobId: string, jobsList: any[]) {
  const job = jobsList.find((j) => j.id === jobId || j.job_number === jobId);
  if (!job) return { party: '', items: [] };
  const party = job.client_name || job.customer_name || '';
  const items = job.items ? job.items.slice(0, 2) : [job.title];
  return { party, items, allOptions: extractJobItems(job) };
}

export function toggleChip(current: string[], item: string): string[] {
  if (current.includes(item)) {
    return current.filter((i) => i !== item);
  }
  return [...current, item];
}

export function addCustomChip(current: string[], item: string): string[] {
  const trimmed = item.trim();
  if (!trimmed || current.includes(trimmed)) return current;
  return [...current, trimmed];
}

export function mergePartiesWithApi(
  presets: PartySuggestion[],
  apiCustomers: { name: string }[],
  apiVendors: { name: string }[]
): PartySuggestion[] {
  const list: PartySuggestion[] = [...presets];
  for (const c of apiCustomers) {
    if (c.name && !list.some((p) => p.name.toLowerCase() === c.name.toLowerCase())) {
      list.push({ category: 'Customers (Max API)', name: c.name, isPreset: false });
    }
  }
  for (const v of apiVendors) {
    if (v.name && !list.some((p) => p.name.toLowerCase() === v.name.toLowerCase())) {
      list.push({ category: 'Vendors (Max API)', name: v.name, isPreset: false });
    }
  }
  return list;
}

test('COMMON_ITEMS contains standard custody item categories', () => {
  const required = [
    'cushion covers',
    'drapery',
    'roman shades',
    'fabric',
    'hardware',
    'bench parts',
    'samples',
    'other',
  ];
  for (const req of required) {
    assert.ok(COMMON_ITEMS.includes(req), `Expected COMMON_ITEMS to include "${req}"`);
  }
});

test('PRESET_PARTIES contains only real fixed vendor/place presets designated by Rafael', () => {
  const names = PRESET_PARTIES.map((p) => p.name);

  // Assert Rafael's 4 presets are present
  assert.ok(names.includes("Nelma's Workroom"), 'Expected Nelma\'s Workroom vendor preset');
  assert.ok(names.includes('Whittington Design'), 'Expected Whittington Design vendor preset');
  assert.ok(names.includes('Warehouse'), 'Expected Warehouse place preset');
  assert.ok(names.includes('Client site'), 'Expected Client site place preset');
  assert.equal(PRESET_PARTIES.length, 4, 'PRESET_PARTIES must contain strictly Rafael\'s 4 presets');

  // Verify all are marked as presets
  for (const preset of PRESET_PARTIES) {
    assert.equal(preset.isPreset, true, `${preset.name} must be marked as preset`);
    assert.ok(preset.category.includes('(Preset)'), `${preset.category} must indicate preset`);
  }

  // Assert NO fake mock names are in PRESET_PARTIES
  const forbiddenMockNames = ['Sarah Jenkins', 'Michael Chang', 'Elena Rostova', 'David Sterling', 'Kravet Fabrics'];
  for (const mock of forbiddenMockNames) {
    assert.ok(!names.includes(mock), `Forbidden fake name "${mock}" must NOT be in PRESET_PARTIES`);
  }
});

test('mergePartiesWithApi merges real API customers and vendors without duplicates', () => {
  const realApiCustomers = [{ name: 'Acme Interiors' }, { name: 'Whittington Design' }]; // Whittington already preset
  const realApiVendors = [{ name: 'Luxury Trims Co' }];

  const merged = mergePartiesWithApi(PRESET_PARTIES, realApiCustomers, realApiVendors);

  assert.equal(merged.length, 6); // 4 presets + Acme Interiors + Luxury Trims Co
  assert.ok(merged.some((p) => p.name === 'Acme Interiors' && p.category === 'Customers (Max API)'));
  assert.ok(merged.some((p) => p.name === 'Luxury Trims Co' && p.category === 'Vendors (Max API)'));
});

test('autoFillFromJob auto-populates party and quote lines when job is picked', () => {
  const sampleJobs = [
    {
      id: 'JOB-0100',
      job_number: 'JOB-0100',
      title: 'Silk Drapery Panels',
      customer_name: 'Acme Interiors',
      items: ['2 drapery panels', 'Blackout lining'],
      quote_lines: ['Custom silk drapery panels (2x)'],
    },
  ];

  const result = autoFillFromJob('JOB-0100', sampleJobs);
  assert.equal(result.party, 'Acme Interiors');
  assert.deepEqual(result.items, ['2 drapery panels', 'Blackout lining']);
  assert.ok(result.allOptions.includes('2 drapery panels'));
  assert.ok(result.allOptions.includes('Custom silk drapery panels (2x)'));
  assert.ok(result.allOptions.includes('cushion covers'));
});

test('Multi-select chip toggling and custom entry work reliably', () => {
  let selected = ['cushion covers'];

  // Toggle on fabric
  selected = toggleChip(selected, 'fabric');
  assert.deepEqual(selected, ['cushion covers', 'fabric']);

  // Toggle off cushion covers
  selected = toggleChip(selected, 'cushion covers');
  assert.deepEqual(selected, ['fabric']);

  // Add custom entry
  selected = addCustomChip(selected, '4 antique brass tieback batons');
  assert.deepEqual(selected, ['fabric', '4 antique brass tieback batons']);

  // Ignore empty or duplicate custom entry
  selected = addCustomChip(selected, '  ');
  assert.equal(selected.length, 2);
  selected = addCustomChip(selected, 'fabric');
  assert.equal(selected.length, 2);
});

test('formatInches formats fractional dimensions accurately', () => {
  assert.equal(formatInches(84.5), '84½"');
  assert.equal(formatInches(38.25), '38¼"');
  assert.equal(formatInches('96'), '96"');
  assert.equal(formatInches(0.75), '¾"');
  assert.equal(formatInches(12.125), '12⅛"');
});
