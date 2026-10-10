import test from 'node:test';
import assert from 'node:assert/strict';
import { formatInches } from '../../../lib/formatInches';

// Testable helper functions extracted/matching ScheduleControl logic
export const COMMON_ITEMS = [
  'cushion covers',
  'drapery',
  'roman shades',
  'fabric',
  'hardware',
  'bench parts',
  'samples',
  'other',
];

export const DEFAULT_PARTIES = [
  { category: 'Customers', name: 'Sarah Jenkins (Jenkins Design Studio)' },
  { category: 'Customers', name: 'Whittington Design' },
  { category: 'Customers', name: 'Michael Chang' },
  { category: 'Customers', name: 'Elena Rostova' },
  { category: 'Customers', name: 'David Sterling' },
  { category: 'Vendors', name: "Nelma's Workroom" },
  { category: 'Vendors', name: 'Kravet Fabrics' },
  { category: 'Vendors', name: 'Schumacher & Co' },
  { category: 'Vendors', name: 'Robert Allen' },
  { category: 'Vendors', name: 'Sunbrella' },
  { category: 'Vendors', name: 'Highland Hardware' },
  { category: 'Places', name: 'Warehouse / Receiving Dock' },
  { category: 'Places', name: 'Client site / Residence' },
  { category: 'Places', name: 'Studio Workroom' },
  { category: 'Places', name: 'Off-site Upholstery Shop' },
];

export const MOCK_JOBS = [
  {
    id: 'JOB-0010',
    job_number: 'JOB-0010',
    title: 'Custom Velvet Sectional & Bolsters',
    customer_name: 'Sarah Jenkins',
    client_name: 'Sarah Jenkins',
    items: ['4 cushion covers', '2 bolster cushions', '1 sectional frame', '5 bolt velvet'],
    quote_lines: ['Custom 3-piece sectional upholstery', 'High-density foam cushions (4x)', 'Velvet bolster pillows (2x)'],
  },
  {
    id: 'JOB-0005',
    job_number: 'JOB-0005',
    title: 'Master Bedroom Silk Drapery Panels',
    customer_name: 'Whittington Design',
    client_name: 'Whittington Design',
    items: ['2 drapery panels', 'Blackout lining', 'Traverse rod hardware', 'Tiebacks'],
    quote_lines: ['Custom 96" pinch pleat silk drapery panels', 'Blackout thermal interlining', 'Antique brass baton rods'],
  },
  {
    id: 'JOB-0004',
    job_number: 'JOB-0004',
    title: 'Linen Roman Shades with Motorized Track',
    customer_name: "Nelma's Workroom",
    client_name: "Nelma's Workroom",
    items: ['3 roman shades', 'Somfy motor pack', 'Mounting brackets'],
    quote_lines: ['Linen relaxed roman shades (3x)', 'Somfy WireFree RTS motor kit'],
  },
];

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

test('COMMON_ITEMS contains all required preset item types', () => {
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

test('DEFAULT_PARTIES includes required vendors, customers, and common places', () => {
  const names = DEFAULT_PARTIES.map((p) => p.name);
  assert.ok(names.some((n) => n.includes("Nelma's Workroom")), 'Expected Nelma\'s Workroom vendor');
  assert.ok(names.some((n) => n.includes('Whittington Design')), 'Expected Whittington Design');
  assert.ok(names.some((n) => n.includes('Sarah Jenkins')), 'Expected Sarah Jenkins customer');
  assert.ok(names.some((n) => n.includes('Warehouse')), 'Expected Warehouse place');
  assert.ok(names.some((n) => n.includes('Client site')), 'Expected Client site place');
});

test('autoFillFromJob auto-populates party and quote lines when job is picked', () => {
  // Select JOB-0010
  const job10 = autoFillFromJob('JOB-0010', MOCK_JOBS);
  assert.equal(job10.party, 'Sarah Jenkins');
  assert.deepEqual(job10.items, ['4 cushion covers', '2 bolster cushions']);
  assert.ok(job10.allOptions.includes('4 cushion covers'));
  assert.ok(job10.allOptions.includes('Custom 3-piece sectional upholstery'));
  assert.ok(job10.allOptions.includes('cushion covers'));

  // Select JOB-0005
  const job5 = autoFillFromJob('JOB-0005', MOCK_JOBS);
  assert.equal(job5.party, 'Whittington Design');
  assert.deepEqual(job5.items, ['2 drapery panels', 'Blackout lining']);
  assert.ok(job5.allOptions.includes('2 drapery panels'));
  assert.ok(job5.allOptions.includes('Custom 96" pinch pleat silk drapery panels'));

  // Select JOB-0004
  const job4 = autoFillFromJob('JOB-0004', MOCK_JOBS);
  assert.equal(job4.party, "Nelma's Workroom");
  assert.deepEqual(job4.items, ['3 roman shades', 'Somfy motor pack']);
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
