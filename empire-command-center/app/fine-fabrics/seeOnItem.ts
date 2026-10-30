/** Client-side "See it on your item" mockups. No photo upload is stored. */

export const MOCKUP_ITEMS = [
  { id: 'pillow', label: 'Pillow' },
  { id: 'drapery_panel', label: 'Drapery panel' },
  { id: 'roman_shade', label: 'Roman shade' },
  { id: 'sofa', label: 'Sofa' },
  { id: 'accent_chair', label: 'Accent chair' },
  { id: 'bench', label: 'Bench' },
] as const;

export type MockupItemId = (typeof MOCKUP_ITEMS)[number]['id'];

export type Point = { x: number; y: number };

export const VIEW = { w: 400, h: 300 };

export const SHOP_THIS_LOOK = [
  { id: 'pillow-square', label: 'Square pillow', note: 'Coming — Empire pillow line' },
  { id: 'pillow-lumbar', label: 'Lumbar pillow', note: 'Coming — Empire pillow line' },
  { id: 'pillow-box', label: 'Box-edge pillow', note: 'Coming — Empire pillow line' },
] as const;

export function parseInches(raw: string | null | undefined): number | null {
  if (!raw) return null;
  const match = String(raw).replace(',', '.').match(/(\d+(?:\.\d+)?)/);
  return match ? Number(match[1]) : null;
}

export function parseRepeat(raw: string | null | undefined): { h: number | null; v: number | null } {
  if (!raw) return { h: null, v: null };
  const nums = String(raw).match(/(\d+(?:\.\d+)?)/g);
  if (!nums || !nums.length) return { h: null, v: null };
  const h = Number(nums[0]);
  const v = nums[1] ? Number(nums[1]) : h;
  return { h, v };
}

/** Tile size in SVG units. Repeat/width scale the pattern when known. */
export function tileSizePx(width: string, repeat: string, viewWidth = VIEW.w): number {
  const fabricW = parseInches(width) || 54;
  const { h, v } = parseRepeat(repeat);
  const repeatIn = v || h;
  if (!repeatIn) return 64;
  const shownInches = 42;
  const tile = (repeatIn / shownInches) * viewWidth * (fabricW / 54);
  return Math.max(28, Math.min(140, Math.round(tile)));
}

export function sampleHref(productId: number): string {
  return `/fine-fabrics/samples?id=${productId}`;
}

export function quoteHref(productId: number, itemType: string, empireCode?: string): string {
  const params = new URLSearchParams({
    product_id: String(productId),
    item: itemType,
  });
  if (empireCode) params.set('code', empireCode);
  return `/fine-fabrics/quote?${params.toString()}`;
}

export function polygonToPath(points: Point[]): string {
  if (!points.length) return '';
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ') + ' Z';
}

export function pointInPolygon(point: Point, polygon: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;
    const intersect = yi > point.y !== yj > point.y
      && point.x < ((xj - xi) * (point.y - yi)) / (yj - yi + 0.00001) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

export type TemplateShape = {
  id: MockupItemId;
  fill: string;
  shade: string[];
  outline: string[];
  wood?: string[];
};

export const TEMPLATES: TemplateShape[] = [
  {
    id: 'pillow',
    fill: 'M86 78 h228 v150 a18 18 0 0 1 -18 18 h-192 a18 18 0 0 1 -18 -18 z',
    shade: [
      'M86 78 h80 l-20 168 h-42 a18 18 0 0 1 -18 -18 z',
      'M274 78 h40 v150 a18 18 0 0 1 -18 18 h-22 z',
    ],
    outline: [
      'M78 70 h244 v166 a26 26 0 0 1 -26 26 h-192 a26 26 0 0 1 -26 -26 z',
    ],
  },
  {
    id: 'drapery_panel',
    fill: 'M90 36 h220 v240 h-220 z',
    shade: [
      'M90 36 h28 v240 h-28 z',
      'M150 36 h22 v240 h-22 z',
      'M210 36 h22 v240 h-22 z',
      'M270 36 h40 v240 h-40 z',
    ],
    outline: [
      'M70 28 h260 v8 h-260 z',
      'M88 36 h224 v242 h-224 z',
    ],
  },
  {
    id: 'roman_shade',
    fill: 'M70 40 h260 v200 h-260 z',
    shade: [
      'M70 88 h260 v10 h-260 z',
      'M70 136 h260 v10 h-260 z',
      'M70 184 h260 v10 h-260 z',
      'M70 40 h30 v200 h-30 z',
    ],
    outline: [
      'M62 32 h276 v8 h-276 z',
      'M70 40 h260 v202 h-260 z',
    ],
  },
  {
    id: 'sofa',
    fill: 'M48 118 h304 v92 h-304 z',
    shade: [
      'M48 118 h48 v92 h-48 z',
      'M304 118 h48 v92 h-48 z',
      'M48 118 h304 v22 h-304 z',
    ],
    outline: [
      'M40 110 h320 v108 h-40 v-70 h-240 v70 h-40 z',
    ],
    wood: [
      'M70 218 h16 v28 h-16 z',
      'M314 218 h16 v28 h-16 z',
    ],
  },
  {
    id: 'accent_chair',
    fill: 'M120 70 h150 v70 h-150 z',
    shade: [
      'M120 70 h150 v18 h-150 z',
      'M120 140 h160 v70 h-40 v-50 h-120 z',
    ],
    outline: [
      'M118 68 h154 v74 h-154 z',
      'M118 142 h164 v72 h-44 v-50 h-120 z',
    ],
    wood: [
      'M128 214 h16 v30 h-16 z',
      'M246 214 h16 v30 h-16 z',
    ],
  },
  {
    id: 'bench',
    fill: 'M60 130 h280 v70 h-280 z',
    shade: [
      'M60 130 h280 v16 h-280 z',
      'M60 130 h24 v70 h-24 z',
    ],
    outline: [
      'M56 126 h288 v78 h-288 z',
    ],
    wood: [
      'M78 206 h16 v28 h-16 z',
      'M306 206 h16 v28 h-16 z',
    ],
  },
];

export function templateFor(id: string): TemplateShape {
  return TEMPLATES.find((t) => t.id === id) || TEMPLATES[0];
}

export function uploadIsClientOnly(): true {
  return true;
}
