export type ChartSpec = {
  type: 'bar' | 'line' | 'pie';
  labels: string[];
  data: number[];
  title?: string;
};

export type ChatSegment =
  | { kind: 'text'; text: string }
  | { kind: 'chart'; chart: ChartSpec };

const CHART_FENCE_RE = /```chart\s*\n([\s\S]*?)\n```/g;
const CHART_LINE_RE = /^chart\s+(\{[\s\S]+\})\s*$/gim;
const RAW_CHART_JSON_RE = /^\s*(\{"type"\s*:\s*"(?:bar|line|pie)"[\s\S]*\})\s*$/gim;

function parseChartJson(raw: string): ChartSpec | null {
  try {
    const parsed = JSON.parse(raw.trim());
    if (!parsed || typeof parsed !== 'object') return null;
    const type = String(parsed.type || 'bar').toLowerCase();
    if (type !== 'bar' && type !== 'line' && type !== 'pie') return null;
    const labels = Array.isArray(parsed.labels) ? parsed.labels.map(String) : [];
    const data = Array.isArray(parsed.data)
      ? parsed.data.map((v: unknown) => (typeof v === 'number' ? v : Number(v) || 0))
      : [];
    if (!labels.length || labels.length !== data.length) return null;
    return {
      type,
      labels,
      data,
      title: parsed.title ? String(parsed.title) : undefined,
    };
  } catch {
    return null;
  }
}

/** Split assistant markdown into text and chart segments (never show raw chart JSON). */
export function splitChatContent(content: string): ChatSegment[] {
  if (!content) return [{ kind: 'text', text: '' }];

  type Mark = { start: number; end: number; chart: ChartSpec };
  const marks: Mark[] = [];

  for (const re of [CHART_FENCE_RE, CHART_LINE_RE, RAW_CHART_JSON_RE]) {
    re.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = re.exec(content)) !== null) {
      const chart = parseChartJson(match[1]);
      if (chart) marks.push({ start: match.index, end: match.index + match[0].length, chart });
    }
  }

  if (!marks.length) return [{ kind: 'text', text: content }];

  marks.sort((a, b) => a.start - b.start);
  const segments: ChatSegment[] = [];
  let cursor = 0;
  for (const mark of marks) {
    if (mark.start < cursor) continue;
    if (mark.start > cursor) {
      segments.push({ kind: 'text', text: content.slice(cursor, mark.start) });
    }
    segments.push({ kind: 'chart', chart: mark.chart });
    cursor = mark.end;
  }
  if (cursor < content.length) {
    segments.push({ kind: 'text', text: content.slice(cursor) });
  }
  return segments.length ? segments : [{ kind: 'text', text: content }];
}

export async function copyTextToClipboard(text: string): Promise<boolean> {
  const payload = (text || '').trim();
  if (!payload) return false;
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(payload);
      return true;
    }
  } catch {
    /* fall through */
  }
  try {
    const ta = document.createElement('textarea');
    ta.value = payload;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

export function displayModelLabel(model?: string | null): string | null {
  const m = (model || '').trim();
  if (!m || m.toLowerCase() === 'unknown' || m.toLowerCase() === 'none') return null;
  return m;
}
