/** Pure LuxeForge selection-board math. Preview estimates only — never a live quote. */

export type LuxeKind = 'fabric' | 'finish' | 'photo';

export type LuxeCatalogItem = {
  id: string;
  kind: LuxeKind;
  name: string;
  house?: string;
  family?: string;
  color?: string;
  material?: string;
  room?: string;
  mood?: string;
  width_in?: number;
  repeat_in?: number;
  price_per_yard?: number;
  price?: number;
  unit?: string;
  swatch: string;
  texture?: string;
  notes?: string;
};

export type LuxeSelection = {
  id: string;
  qty?: number;
  treatment?: string;
  notes?: string;
};

export type LuxeBoard = {
  id?: string;
  title: string;
  client_name?: string;
  project_name?: string;
  treatment: string;
  notes?: string;
  selections: LuxeSelection[];
};

export const DEFAULT_YARDS: Record<string, number> = {
  drapery: 18,
  upholstery: 12,
  roman: 8,
  bedding: 10,
};

export const DEFAULT_LABOR: Record<string, number> = {
  drapery: 980,
  upholstery: 1640,
  roman: 540,
  bedding: 420,
};

export function catalogIndex(catalog: { fabrics?: LuxeCatalogItem[]; finishes?: LuxeCatalogItem[]; photos?: LuxeCatalogItem[] }): Map<string, LuxeCatalogItem> {
  const map = new Map<string, LuxeCatalogItem>();
  for (const row of [...(catalog.fabrics || []), ...(catalog.finishes || []), ...(catalog.photos || [])]) {
    map.set(row.id, row);
  }
  return map;
}

export function defaultQty(item: LuxeCatalogItem, treatment = 'drapery'): number {
  if (item.kind === 'fabric') return DEFAULT_YARDS[treatment] || 12;
  if (item.kind === 'finish') return 1;
  return 1;
}

export function hydrateBoard(board: LuxeBoard, index: Map<string, LuxeCatalogItem>): (LuxeCatalogItem & LuxeSelection & { amount: number })[] {
  return board.selections.map((sel) => {
    const cat = index.get(sel.id);
    if (!cat) return null;
    const qty = sel.qty ?? defaultQty(cat, board.treatment || sel.treatment || 'drapery');
    const unitPrice = cat.kind === 'fabric' ? Number(cat.price_per_yard || 0) : Number(cat.price || 0);
    const amount = cat.kind === 'photo' ? 0 : Math.round(qty * unitPrice * 100) / 100;
    return { ...cat, ...sel, qty, amount };
  }).filter(Boolean) as (LuxeCatalogItem & LuxeSelection & { amount: number })[];
}

export function composeEstimate(board: LuxeBoard, index: Map<string, LuxeCatalogItem>) {
  const rows = hydrateBoard(board, index);
  const billable = rows.filter((r) => r.kind !== 'photo');
  const materials = Math.round(billable.reduce((s, r) => s + r.amount, 0) * 100) / 100;
  const hasFabric = rows.some((r) => r.kind === 'fabric');
  const labor = hasFabric ? (DEFAULT_LABOR[board.treatment] || 800) : 0;
  const subtotal = Math.round((materials + labor) * 100) / 100;
  return {
    lines: billable,
    photos: rows.filter((r) => r.kind === 'photo'),
    materials,
    labor,
    subtotal,
    deposit_suggested: Math.round(subtotal * 50) / 100,
    wrote_quote: false as const,
    wrote_live: false as const,
    sent: false as const,
  };
}

export function toggleSelection(board: LuxeBoard, item: LuxeCatalogItem): LuxeBoard {
  const has = board.selections.some((s) => s.id === item.id);
  if (has) {
    return { ...board, selections: board.selections.filter((s) => s.id !== item.id) };
  }
  return {
    ...board,
    selections: [...board.selections, { id: item.id, qty: defaultQty(item, board.treatment), treatment: board.treatment }],
  };
}

export function setSelectionQty(board: LuxeBoard, id: string, qty: number): LuxeBoard {
  return {
    ...board,
    selections: board.selections.map((s) => (s.id === id ? { ...s, qty } : s)),
  };
}

export function money(n: number): string {
  const abs = Math.abs(n);
  const dollars = Math.floor(abs);
  const cents = Math.round((abs - dollars) * 100);
  const body = cents ? `${dollars}.${String(cents).padStart(2, '0')}` : String(dollars);
  return `${n < 0 ? '-' : ''}$${body}`;
}

export const HOUSE_CATALOG = {
  fabrics: [
    { id: 'fab-belgian-flax', kind: 'fabric' as const, name: 'Belgian Flax', house: 'Liberty Atelier', color: 'Warm flax', material: 'Linen', price_per_yard: 86, swatch: 'linear-gradient(135deg,#d8c4a4 0%,#c4aa82 42%,#b89a6e 100%)' },
    { id: 'fab-silk-taffeta', kind: 'fabric' as const, name: 'Champagne Taffeta', house: 'Maison Vérone', color: 'Pale champagne', material: 'Silk', price_per_yard: 164, swatch: 'linear-gradient(120deg,#f4e6c8 0%,#e8d2a0 50%,#d4b56a 100%)' },
    { id: 'fab-mohair-velvet', kind: 'fabric' as const, name: 'Midnight Mohair', house: 'Atelier Noir', color: 'Deep ink', material: 'Mohair velvet', price_per_yard: 248, swatch: 'linear-gradient(160deg,#1a1d27 0%,#2a2438 55%,#3d3354 100%)' },
    { id: 'fab-wool-boucle', kind: 'fabric' as const, name: 'Cloud Bouclé', house: 'Nordic Weave', color: 'Ivory mist', material: 'Wool bouclé', price_per_yard: 132, swatch: 'linear-gradient(145deg,#f4efe8 0%,#e6ddd0 48%,#d2c6b4 100%)' },
    { id: 'fab-printed-botanical', kind: 'fabric' as const, name: 'Orangerie Botanical', house: 'Côte & Grove', color: 'Sage on cream', material: 'Cotton-linen print', price_per_yard: 118, swatch: 'linear-gradient(180deg,#e8ead8 0%,#c5c9a4 40%,#8a9a6a 100%)' },
    { id: 'fab-performance-oyster', kind: 'fabric' as const, name: 'Oyster Performance', house: 'Studio Endure', color: 'Oyster', material: 'Acrylic', price_per_yard: 74, swatch: 'linear-gradient(135deg,#efe8dc 0%,#ddd4c4 55%,#c9bfae 100%)' },
  ],
  finishes: [
    { id: 'fin-brass-antique', kind: 'finish' as const, name: 'Antique Brass Nailhead', family: 'Hardware', color: 'Warm brass', price: 86, unit: 'run', swatch: 'linear-gradient(90deg,#8a6a2f,#d4a017,#6b4e16)' },
    { id: 'fin-nickel-polished', kind: 'finish' as const, name: 'Polished Nickel', family: 'Hardware', color: 'Cool silver', price: 74, unit: 'run', swatch: 'linear-gradient(90deg,#9aa3ad,#e8eef4,#6d7680)' },
    { id: 'fin-walnut-handrub', kind: 'finish' as const, name: 'Hand-Rubbed Walnut', family: 'Wood', color: 'Deep walnut', price: 220, unit: 'item', swatch: 'linear-gradient(160deg,#3b2414,#6b3e22,#2a160c)' },
    { id: 'fin-welting-self', kind: 'finish' as const, name: 'Self-Welting', family: 'Upholstery', price: 48, unit: 'item', swatch: 'linear-gradient(90deg,#cfc6b8,#eee8de,#b8ae9e)' },
    { id: 'fin-interline-blackout', kind: 'finish' as const, name: 'Blackout Interlining', family: 'Drapery', price: 36, unit: 'yard', swatch: 'linear-gradient(180deg,#f7f4ee,#e8e2d6)' },
    { id: 'fin-contrast-band', kind: 'finish' as const, name: 'Contrast Leading Edge', family: 'Drapery', price: 62, unit: 'pair', swatch: 'linear-gradient(90deg,#1f2933 0 28%,#f3efe6 28% 100%)' },
  ],
  photos: [
    { id: 'pho-drawing-room', kind: 'photo' as const, name: 'Drawing room, late light', room: 'Living', mood: 'Quiet evening', swatch: 'linear-gradient(160deg,#2c241c 0%,#6a5340 38%,#c9b089 100%)' },
    { id: 'pho-banquette', kind: 'photo' as const, name: 'Banquette corner', room: 'Dining', mood: 'Gathered', swatch: 'linear-gradient(145deg,#1c1916 0%,#4a3b32 45%,#d7c4a3 100%)' },
    { id: 'pho-bedroom-shade', kind: 'photo' as const, name: 'Primary bedroom roman', room: 'Bedroom', mood: 'Soft morning', swatch: 'linear-gradient(180deg,#efe7d6 0%,#c9b8a0 55%,#8f7a62 100%)' },
    { id: 'pho-library', kind: 'photo' as const, name: 'Library club chairs', room: 'Library', mood: 'Study', swatch: 'linear-gradient(150deg,#14161c 0%,#2e3340 50%,#8a7a5c 100%)' },
  ],
};

export const DEMO_BOARD: LuxeBoard = {
  id: 'demo',
  title: 'Drawing-room study',
  client_name: 'Sample residence',
  project_name: 'North windows + pair of chairs',
  treatment: 'drapery',
  notes: 'Keep the evening light. Chair pair in mohair.',
  selections: [
    { id: 'fab-silk-taffeta', qty: 18, treatment: 'drapery' },
    { id: 'fab-mohair-velvet', qty: 14, treatment: 'upholstery' },
    { id: 'fin-brass-antique', qty: 1 },
    { id: 'fin-interline-blackout', qty: 18 },
    { id: 'pho-drawing-room' },
    { id: 'pho-library' },
  ],
};
