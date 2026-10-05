'use client';
// Lightweight, safe markdown for Max chat bubbles.
// - HTML is escaped first (model text is never injected as raw HTML)
// - headings, bullet / numbered lists, block quotes, code fences, inline code, bold, italic, links
// - numbered citations [1](url) render as small chips; bare URLs as short domain links
// - a trailing list of sources collapses into "Sources (n)" (tap to expand)
// - EST-YYYY-NNN quote numbers and [Ask Chief e](chief-e:ask) become actions
import { Fragment, type MouseEvent, type ReactNode } from 'react';
import { chiefEHref } from '../../lib/chiefE';

type Block =
  | { t: 'h'; level: number; text: string }
  | { t: 'p'; text: string }
  | { t: 'ul' | 'ol'; items: string[]; start?: number }
  | { t: 'quote'; text: string }
  | { t: 'code'; text: string }
  | { t: 'hr' };

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const host = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; } };
const safeUrl = (u: string) => /^https?:\/\//i.test(u) ? u : '';

function parse(src: string): Block[] {
  const lines = src.replace(/\r\n?/g, '\n').split('\n');
  const out: Block[] = [];
  let para: string[] = [];
  const flush = () => { if (para.length) { out.push({ t: 'p', text: para.join('\n') }); para = []; } };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^\s*```/.test(line)) {
      flush(); const buf: string[] = []; i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) buf.push(lines[i++]);
      out.push({ t: 'code', text: buf.join('\n') }); continue;
    }
    if (!line.trim()) { flush(); continue; }
    const h = line.match(/^\s{0,3}(#{1,6})\s+(.*)$/);
    if (h) { flush(); out.push({ t: 'h', level: h[1].length, text: h[2].replace(/\s*#+\s*$/, '') }); continue; }
    if (/^\s*(?:---+|\*\*\*+|___+)\s*$/.test(line)) { flush(); out.push({ t: 'hr' }); continue; }
    if (/^\s*>\s?/.test(line)) {
      flush(); const buf: string[] = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^\s*>\s?/, ''));
      i--; out.push({ t: 'quote', text: buf.join('\n') }); continue;
    }
    const ul = /^\s*[-*•]\s+/; const ol = /^\s*(\d+)[.)]\s+/;
    if (ul.test(line) || ol.test(line)) {
      flush(); const ordered = ol.test(line) && !ul.test(line);
      const start = ordered ? Number(line.match(ol)![1]) : undefined;
      const items: string[] = [];
      while (i < lines.length && lines[i].trim()) {
        const l = lines[i];
        if ((ordered ? ol : ul).test(l)) items.push(l.replace(ordered ? ol : ul, ''));
        else if (/^\s{2,}\S/.test(l) && items.length) items[items.length - 1] += '\n' + l.trim();
        else break;
        i++;
      }
      i--; out.push({ t: ordered ? 'ol' : 'ul', items, start }); continue;
    }
    para.push(line);
  }
  flush();
  return out;
}

const QUOTE_LINK = (qn: string) => `<a class="quote-link cm-quote" data-link-type="quote-number" data-quote-number="${qn}">${qn}</a>`;

function inline(raw: string, question: string): string {
  // pull out code spans and links first so their contents are not re-formatted
  const slots: string[] = [];
  const keep = (html: string) => `\u0000${slots.push(html) - 1}\u0000`;
  let s = raw.replace(/`([^`\n]+)`/g, (_, c) => keep(`<code class="cm-code">${esc(c)}</code>`));
  s = s.replace(/\[([^\]\n]+)\]\(([^)\s]+)\)/g, (_, text: string, url: string) => {
    if (/^chief-e:/i.test(url)) return keep(`<a class="cm-chiefe" href="${esc(chiefEHref(question))}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>`);
    const u = safeUrl(url);
    if (!u) return esc(text);
    if (/^\d{1,2}$/.test(text.trim())) return keep(`<a class="cm-cite" href="${esc(u)}" target="_blank" rel="noopener noreferrer" title="${esc(host(u))}">${esc(text.trim())}</a>`);
    return keep(`<a class="cm-link" href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>`);
  });
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s)<]+[^\s)<.,;:!?'"])/g, (_, pre: string, u: string) => pre + keep(`<a class="cm-link" href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(host(u))}</a>`));
  s = esc(s);
  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>').replace(/__([^_\n]+)__/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, '$1<em>$2</em>');
  s = s.replace(/(EST-\d{4}-\d{3})/g, (m) => QUOTE_LINK(m));
  s = s.replace(/\n/g, '<br/>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, n) => slots[Number(n)]);
}

const linkCount = (s: string) => (s.match(/\]\(https?:\/\//g) || []).length;
const isSourceList = (b: Block, idx: number, all: Block[]) =>
  (b.t === 'ul' || b.t === 'ol') && b.items.length >= 2 && idx >= all.length - 3
  && b.items.filter(it => linkCount(it) >= 1 && it.replace(/\[[^\]]*\]\([^)]*\)/g, '').length < 220).length >= Math.ceil(b.items.length * 0.8);

function Html({ html, as = 'div', className }: { html: string; as?: 'div' | 'span' | 'li' | 'p'; className?: string }) {
  const Tag = as as 'div';
  return <Tag className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

export default function ChatMarkdown({ text, question = '', onQuoteNumber, onBuilder }:
  { text: string; question?: string; onQuoteNumber?: (qn: string) => void; onBuilder?: () => void }) {
  const blocks = parse(text);
  // a "Sources" heading right before the last list is folded into the collapsible
  const srcIdx = blocks.findIndex((b, i) => isSourceList(b, i, blocks));
  const onClick = (e: MouseEvent<HTMLDivElement>) => {
    const a = (e.target as HTMLElement).closest('a.quote-link') as HTMLElement | null;
    if (!a) return;
    e.preventDefault();
    const qn = a.getAttribute('data-quote-number');
    if (qn) onQuoteNumber?.(qn); else onBuilder?.();
  };
  const nodes: ReactNode[] = [];
  blocks.forEach((b, i) => {
    if (srcIdx >= 0 && i === srcIdx - 1 && b.t === 'h' && /^(sources|fuentes|references)\b/i.test(b.text.replace(/[*_:]/g, '').trim())) return;
    if (i === srcIdx && (b.t === 'ul' || b.t === 'ol')) {
      nodes.push(
        <details key={i} className="cm-sources">
          <summary>Sources ({b.items.length})</summary>
          <ol>{b.items.map((it, k) => <Html key={k} as="li" html={inline(it, question)} />)}</ol>
        </details>,
      );
      return;
    }
    switch (b.t) {
      case 'h': nodes.push(<Html key={i} className={`cm-h cm-h${Math.min(b.level, 4)}`} html={inline(b.text, question)} />); break;
      case 'p': nodes.push(<Html key={i} as="p" className="cm-p" html={inline(b.text, question)} />); break;
      case 'quote': nodes.push(<Html key={i} className="cm-quote-block" html={inline(b.text, question)} />); break;
      case 'code': nodes.push(<pre key={i} className="cm-pre"><code>{b.text}</code></pre>); break;
      case 'hr': nodes.push(<hr key={i} className="cm-hr" />); break;
      case 'ul': nodes.push(<ul key={i} className="cm-ul">{b.items.map((it, k) => <Html key={k} as="li" html={inline(it, question)} />)}</ul>); break;
      case 'ol': nodes.push(<ol key={i} className="cm-ol" start={b.start}>{b.items.map((it, k) => <Html key={k} as="li" html={inline(it, question)} />)}</ol>); break;
    }
  });
  return <div className="cm-md" onClick={onClick}>{nodes.map((n, i) => <Fragment key={i}>{n}</Fragment>)}</div>;
}
