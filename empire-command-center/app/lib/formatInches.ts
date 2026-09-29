/** Display inches as fractions or whole inches. 14.5 → 14½" ; 72.00 → 72". */

const SIXTEENTHS: Record<number, string> = {
  1: '1/16',
  2: '⅛',
  3: '3/16',
  4: '¼',
  5: '5/16',
  6: '⅜',
  7: '7/16',
  8: '½',
  9: '9/16',
  10: '⅝',
  11: '11/16',
  12: '¾',
  13: '13/16',
  14: '⅞',
  15: '15/16',
};

export function formatInches(value: unknown, withMark = true): string {
  if (value === null || value === undefined || value === '') return '';
  const number = typeof value === 'number' ? value : parseFloat(String(value));
  if (!Number.isFinite(number)) return '';
  const sign = number < 0 ? '-' : '';
  const abs = Math.abs(number);
  let whole = Math.floor(abs + 1e-9);
  let sixteenths = Math.round((abs - whole) * 16);
  if (sixteenths === 16) {
    whole += 1;
    sixteenths = 0;
  }
  const mark = withMark ? '"' : '';
  if (sixteenths === 0) return `${sign}${whole}${mark}`;
  const frac = SIXTEENTHS[sixteenths];
  if (whole === 0) return `${sign}${frac}${mark}`;
  return `${sign}${whole}${frac}${mark}`;
}

export function formatInchList(values: Array<unknown>): string {
  return values
    .filter(v => v !== null && v !== undefined && v !== '')
    .map(v => formatInches(v))
    .filter(Boolean)
    .join(' × ');
}
