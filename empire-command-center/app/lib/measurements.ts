/** Workroom inch measurements as fractions (36 1/2, 96 3/8). */

const FRACTION_RE =
  /^\s*(-)?(?:(\d+)\s+(\d+)\s*\/\s*(\d+)|(\d+)\s*\/\s*(\d+)|(\d+(?:\.\d+)?))\s*(?:in|inch|inches|")?\s*$/i;

export function parseFractionInches(value: unknown): number {
  if (value === null || value === undefined || value === '') return 0;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  const text = String(value).trim();
  if (!text) return 0;
  const match = text.match(FRACTION_RE);
  if (!match) {
    const n = Number.parseFloat(text.replace(/["in]+/gi, '').trim());
    return Number.isFinite(n) ? n : 0;
  }
  const sign = match[1] ? -1 : 1;
  let inches = 0;
  if (match[2] != null) inches = Number(match[2]) + Number(match[3]) / Number(match[4]);
  else if (match[5] != null) inches = Number(match[5]) / Number(match[6]);
  else inches = Number(match[7]);
  return sign * inches;
}

export function formatFractionInches(value: unknown, maxDenominator = 16): string {
  const raw = parseFractionInches(value);
  if (raw === 0) return '0';
  const sign = raw < 0 ? '-' : '';
  const inches = Math.abs(raw);
  let whole = Math.floor(inches + 1e-9);
  let sixteenths = Math.round((inches - whole) * maxDenominator);
  if (sixteenths === maxDenominator) {
    whole += 1;
    sixteenths = 0;
  }
  if (sixteenths === 0) return `${sign}${whole}`;
  let num = sixteenths;
  let den = maxDenominator;
  while (num % 2 === 0 && den % 2 === 0) {
    num /= 2;
    den /= 2;
  }
  if (whole === 0) return `${sign}${num}/${den}`;
  return `${sign}${whole} ${num}/${den}`;
}

export function formatMeasurementTriple(width?: unknown, height?: unknown, depth?: unknown): string {
  return [width, height, depth]
    .filter((v) => v !== undefined && v !== null && v !== '' && v !== 0 && v !== '0')
    .map((v) => `${formatFractionInches(v)}"`)
    .join(' x ');
}
