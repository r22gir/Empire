/**
 * Live vs EXAMPLE gate for Studio screens.
 * Fixtures may be passed in, but they are returned only when example is true.
 */

export type LiveGate<T> =
  | { kind: 'example'; data: T }
  | { kind: 'loading'; data: null }
  | { kind: 'ready'; data: T };

export function isExampleSearch(search: string): boolean {
  try {
    const q = search.startsWith('?') ? search.slice(1) : search;
    return new URLSearchParams(q).get('example') === '1';
  } catch {
    return false;
  }
}

export function gateLive<T>(example: boolean, live: T | null, fixtures: T): LiveGate<T> {
  if (example) return { kind: 'example', data: fixtures };
  if (live === null) return { kind: 'loading', data: null };
  return { kind: 'ready', data: live };
}

/** Strings that must never appear in live / loading / empty Studio views. */
export const EXAMPLE_LEAK = /\bEXAMPLE\b|Client [A-F]\b|EST-####|JOB-####/;

export function leaksExample(text: string): boolean {
  return EXAMPLE_LEAK.test(text);
}

export function pipelineStatusText<T extends { title?: string }>(gate: LiveGate<T[]>): string {
  if (gate.kind === 'loading') return 'Loading pipeline';
  if (!gate.data || gate.data.length === 0) return 'No cards in this stage';
  return gate.data.map((row) => String(row.title || '')).join('\n');
}
