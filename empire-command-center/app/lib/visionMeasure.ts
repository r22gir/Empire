/**
 * /vision/measure often comes back as the mockup formatter shape
 * (window_info.estimated_width / estimated_height) instead of the flat
 * width_inches / height_inches Save-to-Quote and the approval flow read.
 * Missing flats become None dimensions and $0 fabric lines.
 */

export const MEASURE_FABRIC_RATE = 45;
export const MEASURE_LABOR_RATE = 150;

type MeasureLike = Record<string, any>;

function positiveInches(value: unknown): number | null {
  if (typeof value === 'boolean' || value == null || value === '') return null;
  const numeric = typeof value === 'number'
    ? value
    : typeof value === 'string'
      ? Number(value.replace(/[^\d.+-]/g, ''))
      : Number.NaN;
  if (!Number.isFinite(numeric) || numeric <= 0) return null;
  return numeric;
}

export function normalizeMeasureResult<T extends MeasureLike>(data: T): T {
  if (!data || typeof data !== 'object') return data;
  const windowInfo = data.window_info && typeof data.window_info === 'object' && !Array.isArray(data.window_info)
    ? data.window_info as Record<string, unknown>
    : {};
  const width = positiveInches(data.width_inches)
    ?? positiveInches(windowInfo.estimated_width)
    ?? positiveInches(windowInfo.width)
    ?? positiveInches(windowInfo.width_inches);
  const height = positiveInches(data.height_inches)
    ?? positiveInches(windowInfo.estimated_height)
    ?? positiveInches(windowInfo.height)
    ?? positiveInches(windowInfo.height_inches);
  const next: MeasureLike = { ...data };
  if (width != null) next.width_inches = width;
  if (height != null) next.height_inches = height;
  if (!String(next.window_type || '').trim()) {
    const windowType = windowInfo.type || windowInfo.window_type;
    if (windowType) next.window_type = windowType;
  }
  return next as T;
}

export interface MeasureQuoteLine {
  description: string;
  quantity: number;
  unit: string;
  rate: number;
  amount: number;
  category: string;
}

/** Same fullness / hem / 54" goods as AnalysisApprovalFlow, so Save-to-Quote is not a $0 line once dims exist. */
export function measureQuoteLineItems(measure: {
  width_inches?: number | null;
  height_inches?: number | null;
  window_type?: string | null;
}): MeasureQuoteLine[] {
  const width = positiveInches(measure?.width_inches) ?? 0;
  const height = positiveInches(measure?.height_inches) ?? 0;
  const windowType = String(measure?.window_type || '').trim() || 'Standard';
  const label = `Window Measurement — ${windowType} (${width}" W x ${height}" H)`;
  if (!(width > 0) || !(height > 0)) {
    return [{
      description: label,
      quantity: 1,
      unit: 'ea',
      rate: 0,
      amount: 0,
      category: 'labor',
    }];
  }
  const fabricWidth = 54;
  const fullness = 2.5;
  const hem = 8;
  const cutLength = height + hem;
  const widths = Math.ceil((width * fullness) / fabricWidth);
  const totalYards = Math.ceil((widths * cutLength) / 36 * 10) / 10;
  const fabricAmount = Math.round(totalYards * MEASURE_FABRIC_RATE * 100) / 100;
  return [
    {
      description: `${label} — Fabric (${totalYards} yds)`,
      quantity: totalYards,
      unit: 'yd',
      rate: MEASURE_FABRIC_RATE,
      amount: fabricAmount,
      category: 'materials',
    },
    {
      description: `${label} — Labor`,
      quantity: 1,
      unit: 'ea',
      rate: MEASURE_LABOR_RATE,
      amount: MEASURE_LABOR_RATE,
      category: 'labor',
    },
  ];
}
