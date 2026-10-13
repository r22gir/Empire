/** Workroom fraction formatter — inches display as 4 3/4", never 4.75. */

function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b);
}

export function inchesToFraction(value: unknown, maxDenominator = 16): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'string') {
    const text = value.trim();
    if (!text) return '—';
    if (/[\/″"']/.test(text)) return /["″]$/.test(text) ? text : `${text}"`;
    const parsed = Number(text);
    if (Number.isNaN(parsed)) return text;
    return inchesToFraction(parsed, maxDenominator);
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  if (numeric < 0) return `-${inchesToFraction(Math.abs(numeric), maxDenominator)}`;

  const whole = Math.floor(numeric + 1e-9);
  const frac = Math.abs(numeric - whole);
  if (frac < 1 / (maxDenominator * 2)) return `${whole}"`;

  let bestDen = 2;
  let bestNum = 1;
  let bestErr = Math.abs(frac - 0.5);
  for (let den = 2; den <= maxDenominator; den *= 2) {
    const num = Math.round(frac * den);
    const err = Math.abs(frac - num / den);
    if (err < bestErr - 1e-9 || (Math.abs(err - bestErr) < 1e-9 && den < bestDen)) {
      bestErr = err;
      bestDen = den;
      bestNum = num;
    }
  }
  if (bestNum === 0) return `${whole}"`;
  if (bestNum === bestDen) return `${whole + 1}"`;
  const divisor = gcd(bestNum, bestDen);
  const piece = `${bestNum / divisor}/${bestDen / divisor}`;
  return whole === 0 ? `${piece}"` : `${whole} ${piece}"`;
}

export function pairInches(width: unknown, height: unknown): string {
  return `${inchesToFraction(width)} × ${inchesToFraction(height)}`;
}
