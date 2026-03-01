/**
 * ContentAnalyzer — Real-time streaming content analysis for canvas mode detection.
 * Parses MAX's response as it streams to determine which canvas mode to render.
 */

export type CanvasMode =
  | 'avatar'       // Default conversational
  | 'chart'        // Data/metrics/tables with numbers
  | 'document'     // Document references (PDF, DOCX, etc.)
  | 'web'          // URL previews, web content
  | 'image'        // Images, galleries
  | 'split'        // Multiple content types combined
  | 'presentation' // Slide-based (Phase 2)
  | 'media'        // Video/embed (Phase 2)
  | 'comms'        // Calls/messaging (Phase 3)
  | 'workspace';   // Live workspace (Phase 3)

export interface ChartData {
  headers: string[];
  rows: Record<string, string | number>[];
  raw: string;
}

export interface MetricData {
  label: string;
  value: string;
  change?: string;
  direction?: 'up' | 'down' | 'neutral';
}

export interface WebPreview {
  url: string;
  title?: string;
  description?: string;
  type: 'link' | 'youtube' | 'map' | 'social';
}

export interface ImageData {
  src: string;
  alt?: string;
}

export interface QuoteData {
  text: string;
  source?: string;
}

export interface MediaRef {
  url: string;
  type: 'youtube' | 'vimeo' | 'video' | 'audio' | 'stream' | 'iframe';
  title?: string;
}

export interface AnalysisResult {
  primaryMode: CanvasMode;
  secondaryModes: CanvasMode[];
  charts: ChartData[];
  metrics: MetricData[];
  webPreviews: WebPreview[];
  images: ImageData[];
  quotes: QuoteData[];
  mediaRefs: MediaRef[];     // Phase 2: detected media URLs
  textContent: string;       // The text portions (non-structured)
  hasCode: boolean;
  codeBlocks: { lang: string; code: string }[];
  isPresentation: boolean;   // Phase 2: detected presentation structure
  isComms: boolean;          // Phase 3: detected comms content (calls/messages)
  isWorkspace: boolean;      // Phase 3: detected workspace content (code/terminal/quote/calendar)
}

/* ── Pattern matchers ─────────────────────────────────────────── */

const TABLE_REGEX = /(\|.+\|\n\|[\s|:-]+\|\n(?:\|.+\|\n?)+)/g;
const URL_REGEX = /(https?:\/\/[^\s)>\]]+)/g;
const IMAGE_URL_REGEX = /!\[([^\]]*)\]\(([^)]+)\)/g;
const IMAGE_EXT_REGEX = /\.(png|jpg|jpeg|gif|webp|svg)(\?.*)?$/i;
const YOUTUBE_REGEX = /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]+)/;
const VIMEO_REGEX = /vimeo\.com\/(\d+)/;
const VIDEO_EXT_REGEX = /\.(mp4|webm|ogg|mov)(\?.*)?$/i;
const AUDIO_EXT_REGEX = /\.(mp3|wav|m4a|aac|flac)(\?.*)?$/i;
const STREAM_REGEX = /\.(m3u8|mpd)(\?.*)?$/i;
const PRESENTATION_REGEX = /morning briefing|daily report|weekly report|presentation|slide deck/i;
const COMMS_REGEX = /(?:call(?:ed|ing)?|phone call|video call)\s+(?:with\s+)?[A-Z][a-z]+|(?:message|telegram|email|text|sms|whatsapp)\s+(?:from|thread|conversation)\s+[A-Z]/i;
const WORKSPACE_REGEX = /(?:terminal|console|shell|command line|running|executed|output|compile|build|npm|yarn|pip|cargo|make)\s/i;
const METRIC_REGEX = /(?:^|\n)[\s]*(?:\*\*|#+\s*)?\$?[\d,]+\.?\d*[%KMBkmb]?(?:\s*(?:→|->|↑|↓|▲|▼)\s*\$?[\d,]+\.?\d*[%KMBkmb]?)?/g;
const DOC_REF_REGEX = /\b[\w-]+\.(pdf|docx?|xlsx?|csv|pptx?)\b/gi;
const BLOCKQUOTE_REGEX = /(?:^|\n)>\s+(.+?)(?:\n(?!>)|$)/g;
const CODE_BLOCK_REGEX = /```(\w*)\n([\s\S]*?)```/g;

/** Detect bold key-value metric patterns like **Revenue:** $45,000 */
const KV_METRIC_REGEX = /\*\*([^*]+)\*\*[:\s]+\$?([\d,]+\.?\d*)\s*([%KMBkmb]?)/g;

/* ── Table parser ─────────────────────────────────────────────── */

function parseTable(raw: string): ChartData | null {
  const lines = raw.trim().split('\n').filter(l => l.trim());
  if (lines.length < 3) return null;
  const sepLine = lines[1];
  if (!sepLine.match(/^[\s|:-]+$/)) return null;
  const headers = lines[0].split('|').map(h => h.trim()).filter(Boolean);
  if (headers.length < 2) return null;

  const rows: Record<string, string | number>[] = [];
  for (let i = 2; i < lines.length; i++) {
    const cells = lines[i].split('|').map(c => c.trim()).filter(Boolean);
    if (cells.length < 2) continue;
    const row: Record<string, string | number> = {};
    headers.forEach((h, idx) => {
      const val = cells[idx] || '';
      const num = parseFloat(val.replace(/[,$%]/g, ''));
      row[h] = isNaN(num) ? val : num;
    });
    rows.push(row);
  }

  const hasNumericColumn = headers.slice(1).some(h =>
    rows.some(r => typeof r[h] === 'number')
  );

  return rows.length > 0 && hasNumericColumn ? { headers, rows, raw } : null;
}

/* ── Metric extractor ─────────────────────────────────────────── */

function extractMetrics(content: string): MetricData[] {
  const metrics: MetricData[] = [];
  let match;

  // Key-value metric patterns: **Revenue:** $45,000
  const kvRegex = new RegExp(KV_METRIC_REGEX.source, KV_METRIC_REGEX.flags);
  while ((match = kvRegex.exec(content)) !== null) {
    const label = match[1].trim();
    const value = '$' + match[2] + (match[3] || '');
    // Look for direction indicators nearby
    const surrounding = content.slice(Math.max(0, match.index - 10), match.index + match[0].length + 30);
    let direction: 'up' | 'down' | 'neutral' = 'neutral';
    if (/[↑▲\+]|increase/i.test(surrounding)) direction = 'up';
    if (/[↓▼\-]|decrease|decline/i.test(surrounding)) direction = 'down';

    if (metrics.length < 6) {
      metrics.push({ label, value, direction });
    }
  }

  return metrics;
}

/* ── URL classifier ───────────────────────────────────────────── */

function classifyUrl(url: string): WebPreview {
  if (YOUTUBE_REGEX.test(url)) {
    return { url, type: 'youtube' };
  }
  if (/maps\.google|google\.com\/maps|goo\.gl\/maps/i.test(url)) {
    return { url, type: 'map' };
  }
  if (/twitter\.com|x\.com|instagram\.com|facebook\.com|linkedin\.com/i.test(url)) {
    return { url, type: 'social' };
  }
  return { url, type: 'link' };
}

/* ── Main analyzer ────────────────────────────────────────────── */

export function analyzeContent(content: string): AnalysisResult {
  const result: AnalysisResult = {
    primaryMode: 'avatar',
    secondaryModes: [],
    charts: [],
    metrics: [],
    webPreviews: [],
    images: [],
    quotes: [],
    mediaRefs: [],
    textContent: content,
    hasCode: false,
    codeBlocks: [],
    isPresentation: false,
    isComms: false,
    isWorkspace: false,
  };

  if (!content || content.trim().length === 0) {
    return result;
  }

  // Strip code blocks before analyzing for other patterns
  let contentWithoutCode = content;
  let codeMatch;
  const codeRegex = new RegExp(CODE_BLOCK_REGEX.source, CODE_BLOCK_REGEX.flags);
  while ((codeMatch = codeRegex.exec(content)) !== null) {
    result.hasCode = true;
    result.codeBlocks.push({ lang: codeMatch[1] || 'code', code: codeMatch[2] });
    // Parse ```chart JSON blocks into ChartData for ChartCanvas
    if (codeMatch[1] === 'chart') {
      try {
        const chartJson = JSON.parse(codeMatch[2]);
        const labelHeader = chartJson.title || 'Category';
        const rows = (chartJson.labels || []).map((l: string, i: number) => ({
          [labelHeader]: l, Value: chartJson.data?.[i] ?? 0,
        }));
        if (rows.length > 0) {
          result.charts.push({ headers: [labelHeader, 'Value'], rows, raw: codeMatch[2] });
        }
      } catch { /* invalid chart JSON, skip */ }
    }
    contentWithoutCode = contentWithoutCode.replace(codeMatch[0], '');
  }

  // 1. Detect tables → charts
  let tableMatch;
  const tableRegex = new RegExp(TABLE_REGEX.source, TABLE_REGEX.flags);
  while ((tableMatch = tableRegex.exec(content)) !== null) {
    const chart = parseTable(tableMatch[1]);
    if (chart) result.charts.push(chart);
  }

  // 2. Detect metrics (key-value patterns with numbers)
  result.metrics = extractMetrics(contentWithoutCode);

  // 3. Detect images (markdown image syntax)
  let imgMatch;
  const imgRegex = new RegExp(IMAGE_URL_REGEX.source, IMAGE_URL_REGEX.flags);
  while ((imgMatch = imgRegex.exec(content)) !== null) {
    result.images.push({ src: imgMatch[2], alt: imgMatch[1] || undefined });
  }

  // 4. Detect URLs (non-image)
  let urlMatch;
  const urlRegex = new RegExp(URL_REGEX.source, URL_REGEX.flags);
  while ((urlMatch = urlRegex.exec(contentWithoutCode)) !== null) {
    const url = urlMatch[1];
    // Skip image URLs and already-found markdown images
    if (IMAGE_EXT_REGEX.test(url)) {
      if (!result.images.some(i => i.src === url)) {
        result.images.push({ src: url });
      }
      continue;
    }
    if (!result.webPreviews.some(w => w.url === url)) {
      result.webPreviews.push(classifyUrl(url));
    }
  }

  // 5. Detect blockquotes
  let quoteMatch;
  const quoteRegex = new RegExp(BLOCKQUOTE_REGEX.source, BLOCKQUOTE_REGEX.flags);
  while ((quoteMatch = quoteRegex.exec(content)) !== null) {
    result.quotes.push({ text: quoteMatch[1].trim() });
  }

  // 6. Detect document references
  const docRefs = contentWithoutCode.match(DOC_REF_REGEX);
  const hasDocRefs = docRefs && docRefs.length > 0;

  // 7. Detect media URLs (Phase 2)
  for (const wp of result.webPreviews) {
    if (YOUTUBE_REGEX.test(wp.url)) {
      result.mediaRefs.push({ url: wp.url, type: 'youtube', title: wp.title });
    } else if (VIMEO_REGEX.test(wp.url)) {
      result.mediaRefs.push({ url: wp.url, type: 'vimeo', title: wp.title });
    } else if (VIDEO_EXT_REGEX.test(wp.url)) {
      result.mediaRefs.push({ url: wp.url, type: 'video', title: wp.title });
    } else if (AUDIO_EXT_REGEX.test(wp.url)) {
      result.mediaRefs.push({ url: wp.url, type: 'audio', title: wp.title });
    } else if (STREAM_REGEX.test(wp.url)) {
      result.mediaRefs.push({ url: wp.url, type: 'stream', title: wp.title });
    }
  }

  // 8. Detect presentation structure (Phase 2)
  const headingCount = (content.match(/^##\s+/gm) || []).length;
  const dividerCount = (content.match(/^---$/gm) || []).length;
  result.isPresentation = (
    PRESENTATION_REGEX.test(content.slice(0, 300)) ||
    headingCount >= 3 ||
    (dividerCount >= 2 && headingCount >= 2)
  );

  // 9. Detect comms content (Phase 3)
  result.isComms = COMMS_REGEX.test(content);

  // 10. Detect workspace content (Phase 3)
  const hasMultipleCodeBlocks = result.codeBlocks.length >= 2;
  const hasTerminalPatterns = WORKSPACE_REGEX.test(content) && result.hasCode;
  const hasQuoteBuilder = /(?:quote|estimate|invoice|proposal)\s*(?:#|number|for)/i.test(content) &&
    /(?:subtotal|total|line items?|qty|quantity)/i.test(content);
  const hasCalendarContent = /(?:schedule|calendar|appointments?|meetings?)\s+(?:for|this|next|today)/i.test(content) &&
    /\d{1,2}:\d{2}/.test(content);
  result.isWorkspace = hasMultipleCodeBlocks || hasTerminalPatterns || hasQuoteBuilder || hasCalendarContent;

  // ── Determine primary mode ─────────────────────────────────
  const modes: CanvasMode[] = [];

  // Comms and workspace take high priority (Phase 3)
  if (result.isComms) modes.push('comms');
  if (result.isWorkspace) modes.push('workspace');
  // Presentation takes priority if detected
  if (result.isPresentation) modes.push('presentation');
  if (result.charts.length > 0) modes.push('chart');
  if (result.metrics.length >= 3) modes.push('chart'); // Multiple KPIs → chart mode
  if (hasDocRefs) modes.push('document');
  if (result.mediaRefs.length > 0) modes.push('media');
  else if (result.webPreviews.some(w => w.type === 'youtube')) modes.push('media');
  if (result.webPreviews.some(w => w.type !== 'youtube') && result.webPreviews.length > 0) modes.push('web');
  if (result.images.length > 0) modes.push('image');

  // Deduplicate
  const uniqueModes = Array.from(new Set(modes));

  if (uniqueModes.length === 0) {
    result.primaryMode = 'avatar';
  } else if (uniqueModes.length === 1) {
    result.primaryMode = uniqueModes[0];
  } else {
    // Multiple content types → split canvas
    result.primaryMode = 'split';
    result.secondaryModes = uniqueModes;
  }

  return result;
}

/**
 * Quick check: has the content changed enough to warrant re-analysis?
 * Used during streaming to avoid excessive re-renders.
 */
export function shouldReanalyze(prev: string, next: string): boolean {
  // Re-analyze if content grew by 100+ chars or a table/URL/image was just completed
  const diff = next.length - prev.length;
  if (diff < 50) return false;

  const tail = next.slice(prev.length);
  // Check if new content contains structural elements
  if (/\|.*\|/.test(tail)) return true;  // Table row
  if (/https?:\/\//.test(tail)) return true; // URL
  if (/!\[/.test(tail)) return true; // Image
  if (/```/.test(tail)) return true; // Code block
  if (/\*\*[^*]+\*\*[:\s]+\$?[\d,]/.test(tail)) return true; // Metric
  if (/call(?:ed|ing)?\s+(?:with\s+)?[A-Z]/i.test(tail)) return true; // Comms
  if (/terminal|console|schedule|calendar/i.test(tail)) return true; // Workspace
  if (diff > 200) return true; // Big chunk

  return false;
}
