/**
 * Photo Analyzer → Workroom quote lines.
 *
 * Workroom lists SQL quotes (`/quotes-v2`, business_unit=workroom).
 * Photo and QIS display lines often use catalog categories (`labor`, `fabric`)
 * whose engine requires inputs the photo path does not have. Writing those
 * categories fails the save or stores a different price. Positive rates become
 * `manual_line` (qty × unit_price). A detected item with no price becomes a
 * `note` so it still appears on the quote instead of vanishing.
 */
import { measureQuoteLineItems, normalizeMeasureResult } from './visionMeasure';

export interface WorkroomQuoteLine {
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  rate: number;
  amount: number;
  category: 'manual_line' | 'note';
  inputs?: {
    description: string;
    unit_price: number;
    quantity: number;
  };
}

export interface AnalyzedPhotoItem {
  type?: string;
  name?: string;
  description?: string;
  width?: number | string | null;
  height?: number | string | null;
  quantity?: number;
  dimensions?: { width?: number | string | null; height?: number | string | null };
  selected?: boolean;
  line_items?: DisplayLine[];
}

export interface DisplayLine {
  description?: string;
  quantity?: number;
  unit?: string;
  rate?: number;
  amount?: number;
  unit_price?: number;
  category?: string;
}

const WINDOW_TYPES = new Set([
  'window', 'drapery', 'drapery_panel', 'roman_shade', 'roller_shade',
  'valance', 'cornice', 'swag', 'sheer',
]);

function roundMoney(value: number): number {
  return Math.round(value * 100) / 100;
}

function positiveNumber(value: unknown): number | null {
  if (typeof value === 'boolean' || value == null || value === '') return null;
  const numeric = typeof value === 'number'
    ? value
    : typeof value === 'string'
      ? Number(value.replace(/[^\d.+-]/g, ''))
      : Number.NaN;
  if (!Number.isFinite(numeric) || numeric <= 0) return null;
  return numeric;
}

export function asWorkroomQuoteLine(raw: DisplayLine | null | undefined): WorkroomQuoteLine | null {
  if (!raw || typeof raw !== 'object') return null;
  const description = String(raw.description || '').trim();
  if (!description) return null;

  const quantity = positiveNumber(raw.quantity) ?? 1;
  const unit = String(raw.unit || 'ea').trim() || 'ea';
  let rate = positiveNumber(raw.rate) ?? positiveNumber(raw.unit_price);
  const amount = positiveNumber(raw.amount);
  if (rate == null && amount != null) {
    rate = roundMoney(amount / quantity);
  }

  if (rate == null) {
    return {
      description,
      quantity: 1,
      unit: 'ea',
      unit_price: 0,
      rate: 0,
      amount: 0,
      category: 'note',
    };
  }

  return {
    description,
    quantity,
    unit,
    unit_price: rate,
    rate,
    amount: roundMoney(quantity * rate),
    category: 'manual_line',
    inputs: { description, unit_price: rate, quantity },
  };
}

function fromDisplayLines(lines: DisplayLine[] | null | undefined): WorkroomQuoteLine[] {
  return (lines || [])
    .map((line) => asWorkroomQuoteLine(line))
    .filter((line): line is WorkroomQuoteLine => line != null);
}

export function linesFromMeasureResult(measure: {
  width_inches?: number | null;
  height_inches?: number | null;
  window_type?: string | null;
  window_info?: Record<string, unknown>;
} | null | undefined): WorkroomQuoteLine[] {
  if (!measure) return [];
  return fromDisplayLines(measureQuoteLineItems(normalizeMeasureResult(measure)));
}

export function linesFromUpholsteryResult(data: {
  furniture_type?: string;
  style?: string;
  estimated_labor_cost_low?: number;
  fabric_yards_plain?: number;
} | null | undefined): WorkroomQuoteLine[] {
  if (!data) return [];
  const lines: DisplayLine[] = [{
    description: `${data.furniture_type || 'Furniture'} Reupholstery — ${data.style || 'Standard'}`,
    quantity: 1,
    unit: 'ea',
    rate: data.estimated_labor_cost_low || 0,
    amount: data.estimated_labor_cost_low || 0,
  }];
  if ((data.fabric_yards_plain || 0) > 0) {
    const yards = data.fabric_yards_plain as number;
    lines.push({
      description: `Fabric (plain) — ${yards} yards`,
      quantity: yards,
      unit: 'yd',
      rate: 25,
      amount: yards * 25,
    });
  }
  return fromDisplayLines(lines);
}

export function linesFromMockupResult(data: {
  proposals?: Array<{ tier?: string; treatment_type?: string; style?: string; price_range_low?: number }>;
} | null | undefined): WorkroomQuoteLine[] {
  if (!data?.proposals?.length) return [];
  return fromDisplayLines(data.proposals.map((proposal) => ({
    description: `Design Proposal: ${proposal.tier || ''} — ${proposal.treatment_type || ''} ${proposal.style || ''}`.trim(),
    quantity: 1,
    unit: 'ea',
    rate: proposal.price_range_low || 0,
    amount: proposal.price_range_low || 0,
  })));
}

export function linesFromAnalysisBag(bag: Record<string, any> | null | undefined): WorkroomQuoteLine[] {
  if (!bag) return [];
  return [
    ...linesFromMeasureResult(bag.measure),
    ...linesFromUpholsteryResult(bag.upholstery),
    ...linesFromMockupResult(bag.mockup),
  ];
}

/** Every analyzed photo in the gallery, not only the photo currently on screen. */
export function linesFromPhotoGallery(
  photos: Array<{ results?: Record<string, any> }> | null | undefined,
  fallback?: Record<string, any> | null,
): WorkroomQuoteLine[] {
  const bags = (photos || [])
    .map((photo) => photo.results)
    .filter((results) => results && (results.measure || results.upholstery || results.mockup));
  if (!bags.length && fallback) bags.push(fallback);
  return bags.flatMap((bag) => linesFromAnalysisBag(bag));
}

function itemLabel(item: AnalyzedPhotoItem): string {
  return String(item.description || item.name || item.type || 'Photo item').trim() || 'Photo item';
}

function itemInches(item: AnalyzedPhotoItem): { width: number | null; height: number | null } {
  return {
    width: positiveNumber(item.width ?? item.dimensions?.width),
    height: positiveNumber(item.height ?? item.dimensions?.height),
  };
}

function tierItemsFromQuote(quote: any): any[] {
  const tiers = quote?.tiers;
  if (!tiers) return [];
  if (Array.isArray(tiers)) return tiers[0]?.items || [];
  const tier = tiers.A || tiers.a || tiers.Essential || null;
  return tier?.items || [];
}

function pricedLinesForItem(item: AnalyzedPhotoItem, index: number, tierItems: any[]): DisplayLine[] {
  if (item.line_items?.length) return item.line_items;
  const label = itemLabel(item).toLowerCase();
  const named = tierItems.find((entry) => {
    const name = String(entry?.name || entry?.description || '').toLowerCase();
    const type = String(entry?.type || '').toLowerCase();
    return (name && name === label) || (type && type === String(item.type || '').toLowerCase() && name === label);
  });
  if (named?.line_items?.length) return named.line_items;
  const byIndex = tierItems[index];
  if (byIndex?.line_items?.length) {
    const name = String(byIndex.name || '').toLowerCase();
    if (!name || name === label || name === String(item.name || '').toLowerCase()) {
      return byIndex.line_items;
    }
  }
  return [];
}

export function linesFromAnalyzedItems(
  items: AnalyzedPhotoItem[] | null | undefined,
  quote?: any,
): WorkroomQuoteLine[] {
  const tierItems = tierItemsFromQuote(quote);
  const lines: WorkroomQuoteLine[] = [];
  (items || []).forEach((item, index) => {
    if (!item || item.selected === false) return;
    const priced = fromDisplayLines(pricedLinesForItem(item, index, tierItems))
      .filter((line) => line.category === 'manual_line');
    if (priced.length) {
      lines.push(...priced);
      return;
    }
    const { width, height } = itemInches(item);
    const type = String(item.type || '').toLowerCase();
    const label = itemLabel(item);
    if (width && height && (WINDOW_TYPES.has(type) || type === '')) {
      const measured = linesFromMeasureResult({
        width_inches: width,
        height_inches: height,
        window_type: label,
      }).filter((line) => line.category === 'manual_line');
      if (measured.length) {
        lines.push(...measured);
        return;
      }
    }
    const dims = width && height ? ` (${width}" × ${height}")` : '';
    const note = asWorkroomQuoteLine({
      description: `${label}${dims}`,
      quantity: item.quantity || 1,
      rate: 0,
    });
    if (note) lines.push(note);
  });
  return lines;
}

export function newWorkroomPhotoQuoteBody(opts: {
  customerName?: string | null;
  customerEmail?: string | null;
  projectName?: string;
  projectDescription?: string;
  notes?: string;
  lines: WorkroomQuoteLine[];
  measurements?: Record<string, unknown> | null;
  taxRate?: number;
}): Record<string, unknown> {
  const subtotal = roundMoney(opts.lines.reduce((sum, line) => sum + (line.amount || 0), 0));
  const taxRate = opts.taxRate ?? 0.06;
  const taxAmount = roundMoney(subtotal * taxRate);
  return {
    customer_name: (opts.customerName || '').trim() || 'Walk-in Customer',
    customer_email: opts.customerEmail || null,
    business_unit: 'workroom',
    pricing_mode: 'flat',
    project_name: opts.projectName || 'AI Photo Analysis',
    project_description: opts.projectDescription || 'Created from Photo Analyzer',
    line_items: opts.lines,
    measurements: opts.measurements || null,
    tax_rate: taxRate,
    notes: opts.notes || 'Generated from AI Photo Analysis.',
    subtotal,
    tax_amount: taxAmount,
    total: roundMoney(subtotal + taxAmount),
  };
}

export function quoteLineDescriptions(lines: Array<{ description?: string }> | null | undefined): Set<string> {
  return new Set(
    (lines || [])
      .map((line) => String(line.description || '').trim())
      .filter(Boolean),
  );
}
